// F326 raw-lease regression. Baseline branch is historical defect reproduction only.
import assert from 'node:assert/strict';
import {createDocumentTextureConsumer} from '../document_texture_consumer.mjs';
const candidate=process.argv[2]==='candidate',checks=[];
globalThis.GPUTextureUsage={TEXTURE_BINDING:4,COPY_DST:2};globalThis.GPUBufferUsage={VERTEX:32,COPY_DST:8,UNIFORM:64};
function backend(){
 const objects=[];let writes=0,scopes=0,drawTexture;
 const make=kind=>{const r={kind,destroyed:0,destroy(){this.destroyed++;},createView(){return {texture:this};}};objects.push(r);return r;};
 return {objects,get writes(){return writes;},get scopes(){return scopes;},get drawTexture(){return drawTexture;},lost:new Promise(()=>{}),pushErrorScope(){scopes++;},async popErrorScope(){return null;},createTexture(){return make('texture');},createBuffer(){return make('buffer');},createSampler:x=>x,createBindGroup:x=>x,
 createCommandEncoder(){return {beginRenderPass(){return {setPipeline(){},setVertexBuffer(){},setBindGroup(i,b){drawTexture=b.entries[1].resource.texture;},draw(){},end(){}};},finish(){return {};}};},queue:{writeTexture(){writes++;},writeBuffer(){writes++;},submit(){},async onSubmittedWorkDone(){}}};
}
const pipeline={getBindGroupLayout(){return {};}};
const view={canvas:{width:100,height:100},scale:1,context:{getCurrentTexture(){return {createView(){return {};}};}}};
function lease(generation,{duplicate=false,conflict=false,descriptor=false,version=0}={}){
 const raw=new Uint8Array(356),v=new DataView(raw.buffer);v.setUint32(0,4,true);v.setUint32(4,1,true);v.setUint32(8,16,true);v.setUint32(16,20,true);v.setUint32(20,4,true);v.setUint32(24,16,true);v.setUint32(28,36,true);
 for(let j=0;j<16;j++){const n=100+j*16;v.setUint32(36+j*4,n,true);v.setUint32(n,2,true);v.setFloat64(n+8,j===12?0:1,true);}
 let calls=0,releases=0;const bytes=new Uint8Array([1,2,3,4,5,6,7,8]);if(conflict&&!duplicate)bytes[0]=9;
 return {generation,count:1,metadata:{documentId:'raw-test',images:[],glyphs:[],leafResources:[['p']],resources:duplicate?[{id:'p',version},{id:'p',version}]:[{id:'p',version}]},bytes:()=>raw,resourceDescriptor(){return {format:'rgba8unorm',alphaMode:'straight',width:descriptor?2:1,height:descriptor?1:2,bytesPerRow:descriptor?8:4};},resource(){const b=bytes.slice();if(duplicate&&conflict&&calls++)b[0]=9;return b;},release(){releases++;assert.equal(releases,1);},get releases(){return releases;}};
}
async function draw(s,d,t){await s.encodePage(view).submit();assert.equal(d.drawTexture,t);assert.equal(t.destroyed,0);}
async function clean(s,d,ls){s.dispose();await s.drained();assert.ok(ls.every(l=>l.releases===1));assert.ok(d.objects.every(o=>o.destroyed===1));}
{
 const d=backend(),s=createDocumentTextureConsumer({device:d,pipeline}),ls=[];
 const a=lease(1);ls.push(a);await s.replace(a);const t=d.objects.find(o=>o.kind==='texture');const b=lease(2);ls.push(b);const n=d.objects.length,w=d.writes;await s.replace(b);assert.equal(d.objects.length,n);assert.equal(d.writes,w);assert.equal(a.releases,1);
 checks.push('identical direct raw lease reuses texture and instance');
 for(const options of [{conflict:true},{descriptor:true}]){
  const x=lease(3,options);ls.push(x);const n=d.objects.length,w=d.writes,sc=d.scopes;await assert.rejects(s.replace(x),/Immutable resource version changed/);assert.equal(x.releases,1);assert.equal(s.generation,2);assert.equal(d.objects.length,n);assert.equal(d.writes,w);assert.equal(d.scopes,sc);await draw(s,d,t);
 }
 const c=lease(4);ls.push(c);const n2=d.objects.length,w2=d.writes;await s.replace(c);assert.equal(d.objects.length,n2);assert.equal(d.writes,w2);await draw(s,d,t);await clean(s,d,ls);
 checks.push('byte and descriptor equality conflicts reject before writes; active drawable and cache survive; subsequent reuse; exact-once disposal');
}
for(const conflict of [false,true]){
 const d=backend(),s=createDocumentTextureConsumer({device:d,pipeline}),ls=[];const x=lease(1,{duplicate:true,conflict});ls.push(x);
 if(candidate){await assert.rejects(s.replace(x),/Duplicate resource ID/);assert.equal(d.objects.length,0);assert.equal(d.writes,0);assert.equal(d.scopes,0);assert.equal(x.releases,1);assert.equal(s.generation,null);}
 else {await s.replace(x);assert.equal(d.objects.filter(x=>x.kind==='texture').length,2);}
 const a=lease(2,{conflict:!candidate&&conflict});ls.push(a);await s.replace(a);const t=d.objects.filter(o=>o.kind==='texture').at(-1),n=d.objects.length,w=d.writes;
 if(candidate){const bad=lease(3,{duplicate:true,conflict});ls.push(bad);await assert.rejects(s.replace(bad),/Duplicate resource ID/);assert.equal(d.objects.length,n);assert.equal(d.writes,w);assert.equal(s.generation,2);await draw(s,d,t);}
 const b=lease(4,{conflict:!candidate&&conflict});ls.push(b);const before=d.objects.filter(o=>o.kind==='texture').length;await s.replace(b);
 assert.equal(d.objects.filter(o=>o.kind==='texture').length,before+(candidate?0:1));
 if(candidate)await draw(s,d,t);await clean(s,d,ls);
 checks.push(`${conflict?'conflicting':'identical'} duplicate: ${candidate?'rejected empty/live before allocations; recovery reuses correct entry':'baseline accepted and successor loses cache mapping, forcing later reupload'}`);
}
console.log(JSON.stringify({passed:true,mode:process.argv[2],synthetic_only:true,canonical_bridge_bypassed_for_raw_tests_only:true,checks}));
