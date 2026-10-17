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
  createCommandEncoder(){const c={draws:[],beginRenderPass(){return {setPipeline(){},setVertexBuffer(i,b){c.buffer=b;},setBindGroup(i,b){c.bind=b;},draw(...args){c.draws.push({args,bind:c.bind});},end(){}};},finish(){return c;}};commands.push(c);return c;},
  queue:{writeTexture({texture},bytes,layout,size){if(d.throwWrite)throw Error('synthetic write failure');texture.bytes=bytes.slice();texture.layout=layout;texture.size=size;},writeBuffer(buffer,offset,bytes){buffer.bytes=bytes.slice();},submit(c){if(d.throwSubmit)throw Error('submit failure');d.submitted=c;},onSubmittedWorkDone(){return d.auto?Promise.resolve():new Promise((resolve,reject)=>gates.push({resolve,reject,label:d.nextFence}));}},
  complete(label){const i=gates.findIndex(x=>x.label===label);assert.notEqual(i,-1,'missing fence '+label);gates.splice(i,1)[0].resolve();},
  flush(){for(const x of gates.splice(0))x.resolve();},resources,commands};return d;
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
const d=backend(),s=createDocumentRenderSession({device:d,pipeline});
await s.update(fixture(0));const first=s.generation,firstTexture=d.resources.find(r=>r.kind==='texture');
async function draw(){const r=await s.render(view);await r.completion;return r;}
await draw();
for(const mutate of [
 x=>x.tiles.clear(),
 x=>x.tiles.set('glyph',{...tiles.get('glyph'),resourceId:'absent'}),
 x=>x.tiles.set('glyph',{...tiles.get('glyph'),resourceId:7}),
 x=>x.resources[0].version++,
 x=>delete x.resources[0].image,
 x=>x.resources[0].image.width=2,
 x=>x.metadata.resources.pop(),
]){
 const x=fixture(1,true);mutate(x);const before=d.resources.length,commits=s.metrics.commits;
 assert.throws(()=>s.update(x));assert.equal(s.generation,first);assert.equal(d.resources.length,before);assert.equal(s.metrics.commits,commits);assert.equal(firstTexture.destroyed,0);await draw();
}
const foreign=fixture(1);foreign.metadata.documentId='foreign';Object.defineProperty(foreign.resources[0],'bytes',{get(){throw Error('FOREIGN PAYLOAD READ');}});
assert.throws(()=>s.update(foreign),/ownership/);await draw();
checks.push('missing map, wrong identity/type, missing resource, descriptor and version rejected before mutations; D295 foreign payload untouched');
await s.update(fixture(1,true));await draw();
const glyphTexture=d.commands.at(-1).draws[0].bind.entries[1].resource.texture;
assert.equal(glyphTexture,d.resources.filter(r=>r.kind==='texture').at(-2));
assert.notEqual(glyphTexture,d.resources.filter(r=>r.kind==='texture').at(-1));
checks.push('explicit tile identity survives multi-dependency typed admission and encoding despite conflicting default atlas');
// Candidate upload failure retains committed generation and its CPU lease.
const committed=s.generation,old=glyphTexture;
d.throwWrite=true;await assert.rejects(s.update(fixture(2,true)),/write failure/);d.throwWrite=false;
assert.equal(s.generation,committed);assert.equal(old.destroyed,0);await draw();
checks.push('failed upload preserves drawable and CPU lease without reconstruction');
d.throwSubmit=true;await assert.rejects(s.render(view),/submit failure/);d.throwSubmit=false;
assert.equal(s.generation,committed);assert.equal(old.destroyed,0);await draw();
checks.push('failed submission preserves committed resources');
// Independently controlled upload and draw callbacks expose ownership causality.
d.auto=false;d.nextFence='old-draw';const frame=await s.render(view);
assert.equal(frame.generation,committed);assert.equal(d.submitted[0],d.commands.at(-1));
d.nextFence='candidate-upload';const candidate=s.update(fixture(3,true));await tick();
assert.equal(s.generation,committed);assert.equal(old.destroyed,0);
d.complete('candidate-upload');await candidate;
assert.notEqual(s.generation,committed);assert.equal(old.destroyed,0);assert.equal(s.metrics.liveSnapshots,2);
d.nextFence='new-draw';const newer=await s.render(view);
d.complete('new-draw');await newer.completion;
assert.equal(old.destroyed,0);assert.equal(s.metrics.liveSnapshots,2);
d.complete('old-draw');await frame.completion;
assert.equal(old.destroyed,1);assert.equal(s.metrics.liveSnapshots,1);
await tick();assert.equal(old.destroyed,1);
checks.push('pending candidate retains prior display; old submitted frame and CPU snapshot survive upload and newer completion; old completion cleans exactly once');
// Reverse causal order: completed draw retains active snapshot only until replacement.
const completedTexture=d.commands.at(-1).draws[0].bind.entries[1].resource.texture;
d.nextFence='early-draw';const early=await s.render(view);
d.complete('early-draw');await early.completion;
assert.equal(completedTexture.destroyed,0);assert.equal(s.metrics.liveSnapshots,1);
const lateInput=fixture(3,true);lateInput.metadata.revision=30;
d.nextFence='late-upload';const late=s.update(lateInput);await tick();
assert.equal(completedTexture.destroyed,0);
d.complete('late-upload');await late;
assert.equal(completedTexture.destroyed,0);assert.equal(s.metrics.liveSnapshots,1);
await tick();assert.equal(completedTexture.destroyed,0);
checks.push('draw completed before replacement: active drawable retained while upload pending, then shared texture retained by unchanged replacement until final owner retirement');
// Latest accepted candidate wins; stale upload cannot publish.
d.auto=false;const stale=s.update(fixture(4,true));const staleRejected=assert.rejects(stale,/Cancelled|Superseded/);await tick();
const latest=s.update(fixture(5,true));d.flush();await staleRejected;await tick();d.flush();await latest;
d.auto=true;await draw();
checks.push('superseded candidate releases after fence without replacing committed drawable');
await s.dispose();assert.equal(s.metrics.liveSnapshots,0);assert.ok(d.resources.every(r=>r.destroyed===1));
checks.push('dispose joins all work; every synthetic resource destroyed exactly once');
const result={passed:true,checks,backend:'synthetic instrumented queue; unchanged retained pdf-images RGBA bytes',real_engine_parser_identity:false,real_gpu_qualified:false,pdf_save_qualified:false,original_credit:0};
await writeFile(new URL('raw-results.json',process.env.VKF_HOST_RESULT_DIR),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result));
