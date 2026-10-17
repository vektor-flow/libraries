import assert from 'node:assert/strict';
import {writeFile} from 'node:fs/promises';
import {createDocumentTextureConsumer} from '../document_texture_consumer.mjs';
globalThis.GPUTextureUsage={TEXTURE_BINDING:4,COPY_DST:2};globalThis.GPUBufferUsage={VERTEX:32,COPY_DST:8,UNIFORM:64};
const counts={metadata:0,descriptor:0,resource:0,map:0,set:0};
const NativeMap=globalThis.Map,NativeSet=globalThis.Set;
globalThis.Map=class extends NativeMap {get(k){counts.map++;return super.get(k);}has(k){counts.map++;return super.has(k);}set(k,v){counts.map++;return super.set(k,v);}};
globalThis.Set=class extends NativeSet {has(k){counts.set++;return super.has(k);}add(k){counts.set++;return super.add(k);}};
function backend(){
 const d={samplers:[],binds:[],textures:[],buffers:[],commands:[],gates:[],auto:true,writes:0,lost:new Promise(()=>{}),pushErrorScope(){},async popErrorScope(){return null;},
 createTexture(){const t={destroyed:0,destroy(){this.destroyed++;},createView(){return {texture:this};}};d.textures.push(t);return t;},
 createBuffer(desc){const b={desc,destroyed:0,destroy(){this.destroyed++;}};d.buffers.push(b);return b;},
 createSampler(x){d.samplers.push(x);return x;},createBindGroup(x){d.binds.push(x);return x;},
 createCommandEncoder(){const c={draws:[],beginRenderPass(){return {setPipeline(){},setVertexBuffer(i,b){c.buffer=b;},setBindGroup(i,b){c.bind=b;},draw(...args){c.draws.push({args,bind:c.bind});},end(){}};},finish(){return c;}};d.commands.push(c);return c;},
 queue:{writeTexture({texture},raw){d.writes++;texture.bytes=raw.slice();},writeBuffer(b,o,raw){d.bufferWrites=(d.bufferWrites??0)+1;b.bytes=raw.slice();},submit(){},onSubmittedWorkDone(){return d.auto?Promise.resolve():new Promise(r=>d.gates.push(r));}},flush(){for(const r of d.gates.splice(0))r();}};return d;
}
function lease(n,version=0){
 const raw=new Uint8Array(16+n*340),v=new DataView(raw.buffer);v.setUint32(0,4,true);v.setUint32(4,n,true);v.setUint32(8,16,true);
 const images=[],glyphs=[],leafResources=[];
 const record=(leaf,id)=>({get leaf(){counts.metadata++;return leaf;},resourceId:id});
 for(let i=0;i<n;i++){
  const row=16+n*4+i*336,values=row+16,numbers=values+64;
  v.setUint32(16+i*4,row,true);v.setUint32(row,4,true);v.setUint32(row+4,16,true);v.setUint32(row+8,values,true);
  for(let j=0;j<16;j++){const p=numbers+j*16;v.setUint32(values+j*4,p,true);v.setUint32(p,2,true);v.setFloat64(p+8,j===12?(i%2?2:0):1,true);}
  (i%2?images:glyphs).push(record(i,'r'+(i%4)));leafResources.push(['r'+(i%4)]);
 }
 const l={count:n,generation:version,metadata:{documentId:'counter',images,glyphs,leafResources,resources:Array.from({length:Math.max(4,n/4)},(_,i)=>({id:'r'+i,version}))},bytes:()=>raw,
 resourceDescriptor(){counts.descriptor++;return {format:'rgba8unorm',alphaMode:'straight',width:1,height:1,bytesPerRow:4};},resource(){counts.resource++;return new Uint8Array([version,2,3,4]);},released:0,release(){this.released++;}};
 return l;
}
const pipeline={getBindGroupLayout(){return {};}};
const view={canvas:{width:100,height:100},context:{getCurrentTexture(){return {createView(){return {};}};}},scale:1,defaultResourceId:'r0'};

const checks=[],evidence=[];
const nativeGet=DataView.prototype.getFloat64;let decodes=0;
DataView.prototype.getFloat64=function(...args){decodes++;return nativeGet.apply(this,args);};
const vertices=d=>d.buffers.filter(b=>b.desc.usage&GPUBufferUsage.VERTEX);
const change=l=>{const v=new DataView(l.bytes().buffer);v.setFloat64(16+l.count*4+16+64+8,7,true);return l;};
{
 const d=backend(),c=createDocumentTextureConsumer({device:d,pipeline}),a=lease(4);await c.replace(a);
 const first=vertices(d)[0],original=first.bytes.slice();const old=c.encodePage(view);
 const before={buffers:vertices(d).length,writes:d.bufferWrites,decodes};
 const b=lease(4);await c.replace(b);
 assert.equal(vertices(d).length,before.buffers);assert.equal(d.bufferWrites,before.writes);assert.equal(decodes,before.decodes);
 evidence.push({unchanged:{newVertexBuffers:0,newBufferWrites:0,decodedNumbers:0}});
 checks.push('equal full canonical content skips packing and vertex allocation/write');
 // Change resources and their binding independently of equal geometry.
 const bound=lease(4,1);bound.metadata.glyphs[0]={leaf:0,resourceId:'r1'};bound.metadata.leafResources[0]=['r1'];
 await c.replace(bound);const current=c.encodePage(view);
 assert.equal(d.commands.at(-1).buffer,first);assert.equal(d.commands.at(-1).draws[0].bind.entries[1].resource.texture,d.textures[5]);
 assert.equal(d.commands[0].draws[0].bind.entries[1].resource.texture,d.textures[0]);
 checks.push('equal geometry with new resource ID/version binds new texture; old encoded draw keeps old binding');
 const changed=change(lease(4,1));const prior=vertices(d).length;await c.replace(changed);
 assert.equal(vertices(d).length,prior+1);assert.deepEqual(first.bytes,original);assert.equal(first.destroyed,0);
 assert.notDeepEqual(vertices(d).at(-1).bytes,original);checks.push('changed geometry allocates distinct immutable buffer; old encoded bytes unchanged');
 // Caller storage changes cannot rewrite a cached canonical identity.
 changed.bytes().fill(0);const equal=change(lease(4,1));const snapshotCount=vertices(d).length;await c.replace(equal);assert.equal(vertices(d).length,snapshotCount);
 await assert.rejects(c.replace(changed),/Invalid instance extent/);
 checks.push('mutable caller canonical bytes are snapshotted; invalid replacement rejected');
 await old.submit();await current.submit();assert.equal(first.destroyed,1);
 c.dispose();await c.drained();assert.ok(d.buffers.every(b=>b.destroyed===1));
 assert.ok([a,b,bound,changed,equal].every(l=>l.released===(l===changed?2:1)));
 checks.push('each generation reference and GPU buffer retires exactly once after encoded/submitted owners');
}
{
 const d=backend(),c=createDocumentTextureConsumer({device:d,pipeline}),a=lease(0),b=lease(0);
 await c.replace(a);const before=d.bufferWrites??0;await c.replace(b);
 assert.equal(vertices(d).length,1);assert.equal(vertices(d)[0].desc.size,4);assert.equal(d.bufferWrites??0,before);
 await c.encodePage(view).submit();assert.equal(d.commands[0].draws.length,0);
 c.clearDocumentProject();assert.equal(vertices(d)[0].destroyed,1);
 await c.replace(lease(0));assert.equal(vertices(d).length,2);c.dispose();await c.drained();
 checks.push('zero extent reuses minimum buffer without writes; clear removes history so new owner allocates');
}
for(const mutate of [l=>l.count++,l=>new DataView(l.bytes().buffer).setUint32(16,0,true),l=>new DataView(l.bytes().buffer).setFloat64(16+l.count*4+16+64+8,NaN,true)]){
 const d=backend(),c=createDocumentTextureConsumer({device:d,pipeline});await c.replace(lease(4));const invalid=lease(4);mutate(invalid);
 await assert.rejects(c.replace(invalid),/Invalid instance/);assert.equal(vertices(d).length,1);c.dispose();await c.drained();
 checks.push('full extent/count/tags/nonfinite bytes cannot alias validated instance');
}
DataView.prototype.getFloat64=nativeGet;
await writeFile(new URL('instances-results.json',process.env.VKF_HOST_RESULT_DIR),JSON.stringify({passed:true,checks,evidence,synthetic_only:true},null,2));console.log(JSON.stringify({passed:true,checks,evidence}));
