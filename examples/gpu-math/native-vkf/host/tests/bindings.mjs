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
 createBuffer(){const b={destroyed:0,destroy(){this.destroyed++;}};d.buffers.push(b);return b;},
 createSampler(x){d.samplers.push(x);return x;},createBindGroup(x){d.binds.push(x);return x;},
 createCommandEncoder(){const c={draws:[],beginRenderPass(){return {setPipeline(){},setVertexBuffer(){},setBindGroup(i,b){c.bind=b;},draw(...args){c.draws.push({args,bind:c.bind});},end(){}};},finish(){return c;}};d.commands.push(c);return c;},
 queue:{writeTexture({texture},raw){d.writes++;texture.bytes=raw.slice();},writeBuffer(b,o,raw){b.bytes=raw.slice();},submit(){},onSubmittedWorkDone(){return d.auto?Promise.resolve():new Promise(r=>d.gates.push(r));}},flush(){for(const r of d.gates.splice(0))r();}};return d;
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
const checks=[],scaling=[];
for(const n of [64,256,1024]){
 const d=backend(),c=createDocumentTextureConsumer({device:d,pipeline}),l=lease(n);for(const k in counts)counts[k]=0;
 await c.replace(l);const prepare={...counts};
 assert.equal(prepare.metadata,2*n);assert.equal(prepare.descriptor,n/4);assert.equal(prepare.resource,n/4);assert.ok(prepare.map+prepare.set<12*n);
 const frames=[c.encodePage(view),c.encodePage(view,2,[1,2]),c.encodePage(view,3,[3,4])];
 assert.equal(d.samplers.length,2);assert.equal(d.binds.length,12);
 for(let f=0;f<3;f++)for(let i=0;i<n;i++){
  const draw=d.commands[f].draws[i];assert.deepEqual(draw.args,[6,1,0,i]);assert.equal(draw.bind.entries[1].resource.texture,d.textures[i%4]);
  assert.equal(draw.bind.entries[2].resource.magFilter,i%2?'nearest':'linear');
  assert.equal(draw.bind.entries[0].resource.buffer,d.buffers[1+f]);
 }
 assert.notEqual(d.binds[0].entries[0].resource.buffer,d.binds[4].entries[0].resource.buffer);
 await Promise.all(frames.map(f=>f.submit()));c.dispose();await c.drained();assert.equal(l.released,1);assert.ok(d.textures.every(t=>t.destroyed===1));
 scaling.push({n,resources:n/4,prepare,samplers:d.samplers.length,bindGroups:d.binds.length,draws:n*3});
}
checks.push('production metadata reads, Map/Set operations and descriptor/resource calls scale linearly at 64/256/1024 leaves');
checks.push('three simultaneous uniforms: two consumer samplers, four bind groups per draw, exact order/firstInstance/filter/resource');
// Same texture may appear with both filtering policies; first matching metadata wins.
{
 const d=backend(),c=createDocumentTextureConsumer({device:d,pipeline}),l=lease(4);
 l.metadata.leafResources=l.metadata.leafResources.map(()=>['r0']);
 l.metadata.images=[{leaf:1,resourceId:'r0'},{leaf:1,resourceId:'wrong'},{leaf:3,resourceId:'r0'}];
 l.metadata.glyphs=[{leaf:0,resourceId:'r0'},{leaf:0,resourceId:'wrong'},{leaf:2,resourceId:'r0'}];
 await c.replace(l);await c.encodePage(view).submit();assert.equal(d.binds.length,2);assert.equal(d.samplers.length,2);
 assert.equal(d.binds[0].entries[1].resource.texture,d.binds[1].entries[1].resource.texture);
 c.dispose();await c.drained();
 checks.push('duplicate image/glyph metadata keeps first match; one texture has separate nearest/linear groups');
}
for(const mode of ['absent-glyph','absent-image','unknown','invalid-descriptor','invalid-bytes','invalid-first-duplicate']){
 const d=backend(),c=createDocumentTextureConsumer({device:d,pipeline}),l=lease(4);
 if(mode==='absent-glyph')delete l.metadata.glyphs;
 if(mode==='absent-image')l.metadata.images=[];
 if(mode==='unknown')l.metadata.resources=l.metadata.resources.filter(x=>x.id!=='r2');
 if(mode==='invalid-descriptor')l.resourceDescriptor=()=>({format:'rgba8unorm',alphaMode:'straight',width:2,height:1,bytesPerRow:4});
 if(mode==='invalid-bytes')l.resource=()=>new Uint8Array(3);
 if(mode==='invalid-first-duplicate')l.metadata.images.unshift({leaf:1,resourceId:'wrong'});
 if(mode==='absent-glyph'){await c.replace(l);await c.encodePage(view).submit();}
 else {await assert.rejects(c.replace(l),/Missing explicit|Unknown draw|Missing decoded/);assert.equal(d.writes,0);assert.equal(d.textures.length,0);}
 c.dispose();await c.drained();assert.equal(l.released,1);checks.push(mode+' preserves resolution/rejection before writes');
}
{
 const d=backend(),c=createDocumentTextureConsumer({device:d,pipeline}),a=lease(4);await c.replace(a);
 d.auto=false;const old=c.encodePage(view),oldDone=old.submit(),oldGate=d.gates.shift();
 const b=lease(4,1),update=c.replace(b);await new Promise(r=>setImmediate(r));d.flush();await update;
 const newer=c.encodePage(view),newDone=newer.submit();d.flush();await newDone;
 assert.equal(d.textures[0].destroyed,0);assert.equal(d.commands[0].draws[0].bind.entries[1].resource.texture.bytes[0],0);
 assert.equal(d.commands[1].draws[0].bind.entries[1].resource.texture.bytes[0],1);
 assert.notEqual(d.commands[0].draws[0].bind.entries[0].resource.buffer,d.commands[1].draws[0].bind.entries[0].resource.buffer);
 assert.equal(d.samplers.length,2);oldGate();await oldDone;assert.equal(d.textures[0].destroyed,1);
 d.auto=true;c.dispose();await c.drained();assert.equal(a.released,1);assert.equal(b.released,1);assert.ok(d.textures.every(t=>t.destroyed===1));
 checks.push('replacement retains old frame texture/uniform until its own fence; samplers reused across generations');
}
await writeFile(new URL('bindings-results.json',process.env.VKF_HOST_RESULT_DIR),JSON.stringify({passed:true,checks,scaling,synthetic_only:true},null,2));console.log(JSON.stringify({passed:true,checks,scaling}));
