import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';
import {createDocumentRenderSession} from '../document_render_session.mjs';
globalThis.GPUTextureUsage={TEXTURE_BINDING:4,COPY_DST:2};globalThis.GPUBufferUsage={VERTEX:32,COPY_DST:8,UNIFORM:64};
function backend(){
 const resources=[],gates=[],commands=[];let lossResolve;
 const d={auto:true,validation:null,throwWrite:false,lost:new Promise(r=>lossResolve=r),lose(){lossResolve({reason:'synthetic'});},limits:{maxTextureDimension2D:8192},
  pushErrorScope(){},async popErrorScope(){return d.validation;},
  createTexture(desc){const r={desc,kind:'texture',destroyed:0,destroy(){this.destroyed++;},createView(){return {texture:this};}};resources.push(r);return r;},
  createBuffer(desc){const r={desc,kind:'buffer',destroyed:0,destroy(){this.destroyed++;}};resources.push(r);return r;},
  createSampler:x=>x,createBindGroup:x=>x,
  createCommandEncoder(){if(d.encodeError)throw d.encodeError;const c={draws:[],beginRenderPass(){return {setPipeline(){},setVertexBuffer(i,b){c.buffer=b;},setBindGroup(i,b){c.bind=b;},draw(...args){c.draws.push({args,bind:c.bind});},end(){}};},finish(){if(d.finishError)throw d.finishError;return c;}};commands.push(c);return c;},
  queue:{writeTexture({texture},bytes,layout,size){if(d.throwWrite)throw Error('synthetic write failure');texture.bytes=bytes.slice();texture.layout=layout;texture.size=size;},writeBuffer(buffer,offset,bytes){buffer.bytes=bytes.slice();if(d.writeError)throw d.writeError;},submit(c){if(d.submitError)throw d.submitError;d.submitted=c;},onSubmittedWorkDone(){if(d.fenceError)throw d.fenceError;return d.auto?Promise.resolve():new Promise((resolve,reject)=>gates.push({resolve,reject}));}},
  flush(){for(const x of gates.splice(0))x.resolve();},resources,commands,gates};return d;
}
import {rgba} from './rgba-fixture.mjs';
const image={format:'rgba8unorm',width:1,height:2,bytesPerRow:4,alphaMode:'straight'};
const a={count:1,keys:['glyph'],kinds:new Int32Array([0]),draws:new Uint8Array([1]),paints:new Int32Array([-1]),payloads:new Int32Array([-1]),paint_table:[],payload_table:[]};
for(const [k,v] of Object.entries({xs:0,ys:0,sxs:1,sys:1,widths:20,heights:20}))a[k]=new Float64Array([v]);
const tiles=new Map([['glyph',{resourceId:'pixels',plane:new Float64Array([0,0,1,2]),uv:new Float64Array([0,0,1,1])}]]);

const view={canvas:{width:100,height:100},context:{getCurrentTexture(){return {createView(){return {};}};}},scale:1,defaultResourceId:'other'};
const pipeline={getBindGroupLayout(){return {};}};
const tick=()=>new Promise(r=>setImmediate(r));
function fixture(v,multi=false){
 const ids=multi?['pixels','other']:['pixels'];
 return {complete:true,diagnostics:[],unresolved:[],scene:{arena:a},metadata:{documentId:'D296',revision:v,leafIds:['glyph'],groups:[{id:'glyph',first:0,count:1,contentVersion:0,layoutVersion:0,dependencies:[]}],resources:ids.map(id=>({id,version:v})),leafResources:[ids],links:[],images:[]},tiles:new Map(tiles),resources:ids.map(id=>({id,version:v,bytes:rgba.slice(),image:{...image}}))};
}
const checks=[];
for(const mode of ['invalid','failed','cancel','encode','submit']){
 const d=backend(),s=createDocumentRenderSession({device:d,pipeline});await s.update(fixture(0,true));
 const old=d.resources.slice(),generation=s.generation;d.auto=false;
 const frame=await s.render(view);const frameGate=d.gates.shift();
 if(mode==='invalid'){const x=fixture(1);x.tiles.clear();assert.throws(()=>s.update(x));assert.equal(s.generation,generation);}
 if(mode==='failed'){d.throwWrite=true;const p=s.update(fixture(1,true));const rejected=assert.rejects(p,/write failure/);await tick();d.flush();await rejected;d.throwWrite=false;assert.equal(s.generation,generation);}
 if(mode==='cancel'){
  const p=s.update(fixture(1,true)),rejected=assert.rejects(p,/Cancelled|Superseded/);await tick();
  const render=s.render(view),cancelled=assert.rejects(render,/Cancelled/);s.cancel();await cancelled;d.flush();await rejected;
 }
 if(mode==='encode'||mode==='submit'){
  const stale=s.update(fixture(1,true)),r1=assert.rejects(stale,/Cancelled|Superseded/);await tick();
  const latest=s.update(fixture(2,true)),r2=assert.rejects(latest,/Cancelled|Superseded/);
  const error=Error(mode);if(mode==='encode'){d.encodeError=error;assert.throws(()=>s.render(view),e=>e===error);}else{d.submitError=error;await assert.rejects(s.render(view),e=>e===error);}
  const end=s.dispose();let done=false;end.then(()=>done=true);await tick();assert.equal(done,false);
  assert.ok(old.every(r=>r.destroyed===0));d.flush();await tick();d.flush();await r1;await r2;
  frameGate.resolve();await frame.completion;await end;
 }else{
  assert.ok(old.every(r=>r.destroyed===0));frameGate.resolve();await frame.completion;d.auto=true;d.flush();await s.dispose();
 }
 assert.equal(s.metrics.liveSnapshots,0);assert.ok(d.resources.every(r=>r.destroyed===1));checks.push(mode+': pending old frame plus candidate interaction; exact-once resources and CPU leases drained');
}
const result={passed:true,checks,synthetic_only:true};await writeFile(new URL('interaction-results.json',process.env.VKF_HOST_RESULT_DIR),JSON.stringify(result,null,2));console.log(JSON.stringify(result));
