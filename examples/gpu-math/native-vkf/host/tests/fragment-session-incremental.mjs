import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {fixture} from './columns-fixture.mjs';
import {beginProvenance,reviseProvenance} from '../latex_operation_binding.mjs';
import {prepareProducerFragment} from '../fragment_producer_adapter.mjs';
import {createDocumentRenderSession} from '../document_render_session.mjs';
import {sceneColumns} from '../document_scene_bridge.mjs';
const schema=JSON.parse(readFileSync(new URL('./fixtures/fragment-schema.json',import.meta.url)));
// Backend copied from existing reuse.mjs fixture; synthetic queue, no physical GPU.
globalThis.GPUTextureUsage={TEXTURE_BINDING:4,COPY_DST:2};globalThis.GPUBufferUsage={VERTEX:32,COPY_DST:8,UNIFORM:64};
function backend(){
 const resources=[],gates=[],commands=[];let uploads=0;let lossResolve;
 const d={auto:true,validation:null,throwWrite:false,lost:new Promise(r=>lossResolve=r),lose(){lossResolve({reason:'synthetic'});},limits:{maxTextureDimension2D:8192},
  pushErrorScope(){},async popErrorScope(){return d.validation;},
  createTexture(desc){const r={desc,kind:'texture',destroyed:0,destroy(){this.destroyed++;},createView(){return {texture:this};}};resources.push(r);return r;},
  createBuffer(desc){const r={desc,kind:'buffer',destroyed:0,destroy(){this.destroyed++;}};resources.push(r);return r;},
  createSampler:x=>x,createBindGroup:x=>x,
  createCommandEncoder(){if(d.encodeError)throw d.encodeError;const c={draws:[],beginRenderPass(){return {setPipeline(){},setVertexBuffer(i,b){c.buffer=b;},setBindGroup(i,b){c.bind=b;},draw(...args){c.draws.push({args,bind:c.bind});},end(){}};},finish(){if(d.finishError)throw d.finishError;return c;}};commands.push(c);return c;},
  queue:{writeTexture({texture},bytes,layout,size){if(d.throwWrite)throw Error('synthetic write failure');uploads++;texture.bytes=bytes.slice();texture.layout=layout;texture.size=size;},writeBuffer(buffer,offset,bytes){buffer.bytes=bytes.slice();if(d.writeError)throw d.writeError;},submit(c){if(d.submitError)throw d.submitError;d.submitted=c;},onSubmittedWorkDone(){if(d.fenceError)throw d.fenceError;return d.auto?Promise.resolve():new Promise((resolve,reject)=>gates.push({resolve,reject}));}},
  flush(){for(const x of gates.splice(0))x.resolve();},resources,commands,gates,get uploads(){return uploads;}};return d;
}
function fresh(){
 const f=fixture(1),arena=f.result.document.arena;
 arena.destination_firsts=[0,0,0];arena.destination_counts=[0,0,0];
 f.owner.groups[2].edges=[];
 const scene=Object.fromEntries(schema.Scene.map(k=>[k,[]]));
 Object.assign(scene,{arena,anchor_count:0,anchor_metadata:{kinds:[],ends:[],texts:[],numbers:[],count:0},width:100,height:80,depth:20,tag_width:0,inline_destinations:false});
 f.result={scene,complete:true,diagnostics:'',pending_count:0,a272_anchor_origins:{scope:'parse',text:'x',ids:[],operations:[],starts:[],stops:[]},a277_anchor_placements:{scenes:[],scene_count:3},a280_anchor_receipts:{leaves:[],slots:[]},a282_point_receipts:{points:[]},a283_final_anchors:{leaves:[],slots:[],points:[]}};
 // Add a field with its own explicit operation/leaf/group, sharing the glyph resource.
 for(const [key,value] of Object.entries(arena))if(Array.isArray(value)&&value.length===3)value.push(value[0]);
 arena.count=4;arena.kinds[3]=1;arena.xs[3]=3;arena.a260_operations[3]=3;
 f.owner.scopes[0].operations.push({operation:3,start:0,stop:1,groupId:'group-3',leaves:[{part:0,id:'leaf-3',resources:['resource-0']}]});
 f.owner.groups.push({id:'group-3',contentVersion:0,layoutVersion:0,contentKey:'group-3',layoutKey:'group-3',edges:[],spans:[{sourceId:'s',start:0,end:1}]});
 f.result.a277_anchor_placements.scene_count=4;
 delete f.options.page;return f;
}

const checks=[];
const view={canvas:{width:100,height:100},context:{getCurrentTexture(){return {createView(){return {};}};}},scale:1};
const pipeline={getBindGroupLayout(){return {};}};
const rows=p=>{const c=sceneColumns(p.update.scene,p.update.metadata,p.update.tiles).columns;return Array.from({length:4},(_,i)=>c.map(x=>x[i]));};
// Independent literal geometry: glyph, rule, link border, field. Baseline-relative.
const expected=[
 [0,0,1,1,0,0,1,1,0,0,0,1,0,0,0,0],
 [0,-1,5,6,0,0,0,0,0,0,0,1,1,3,4,0],
 [0.5,-1.5,6,7,0,0,0,0,0,0,0,1,1,4,5,1],
 [3,0,1,1,0,0,1,1,0,0,0,1,0,0,0,0]
];
const f=fresh(),owner=beginProvenance(f.owner);
const p=prepareProducerFragment(f.result,owner,f.options);
assert.deepEqual(rows(p),expected);
assert.deepEqual(p.extent,{width:100,height:80,depth:20,tagWidth:0});assert.equal(p.update.height,100);
assert.equal(p.bound.document,undefined);assert.equal(p.page,undefined);
assert.deepEqual(p.update.metadata.leafIds,['leaf-0','leaf-1','leaf-2','leaf-3']);
const d=backend(),session=createDocumentRenderSession({device:d,pipeline});
async function draw(want,submission){
 const receipt=await session.render(view);assert.equal(receipt.submission,submission);assert.equal(receipt.generation,session.generation);
 assert(receipt.completion instanceof Promise);await receipt.completion;
 const command=d.submitted[0];assert.deepEqual([...command.buffer.bytes],want.flat());
 assert.deepEqual(command.draws.map(x=>x.args),[[6,1,0,0],[6,1,0,1],[6,1,0,2],[6,1,0,3]]);
 return command;
}
const first=await session.update(p.update);assert.equal(first.revision,0);
const initial=await draw(expected,1);assert.equal(d.uploads,1);
checks.push('fragment glyph field rule link reaches session receipt and completion with explicit extent');
// One-character same-topology source edit; all four spans cover that character.
const delta={revision:1,sources:[{...owner.sources[0],version:1,text:'y'}],scopes:[{...structuredClone(owner.scopes[0]),text:'y'}],groups:owner.groups.map(g=>({...structuredClone(g),contentVersion:1,layoutVersion:1,contentKey:g.id+'-y',layoutKey:g.id+'-y'}))};
const edited=reviseProvenance(owner,delta);
f.result.scene.arena.a260_texts.fill('y');f.result.scene.arena.xs[0]=2;
const q=prepareProducerFragment(f.result,edited,{...f.options,previous:p.bound});
const freshPrepared=prepareProducerFragment(f.result,beginProvenance(structuredClone(edited)),f.options);
const changed=expected.map(x=>[...x]);changed[0][0]=2;
assert.deepEqual(rows(q),changed);assert.deepEqual(rows(q),rows(freshPrepared));
assert.deepEqual(q.bound.metadata,freshPrepared.bound.metadata);assert.deepEqual(q.bound.sourceBinding,freshPrepared.bound.sourceBinding);
assert.equal(q.bound.sourceBinding.sources[0].text,'y');
assert.deepEqual(q.bound.invalidated,['group-0','group-1','group-2','group-3']);
const second=await session.update(q.update);assert.equal(second.revision,1);
const updated=await draw(changed,2);assert.notEqual(updated.buffer,initial.buffer);
assert.equal(d.uploads,1);assert.equal(updated.draws[0].bind.entries[1].resource.texture,initial.draws[0].bind.entries[1].resource.texture);
assert.deepEqual([...initial.buffer.bytes],expected.flat());
checks.push('real source edit via reviseProvenance and exact bound matches fresh geometry metadata and reuses resource');
// Session snapshots before returning its update promise; adapter also guards its private predecessor.
const stable=reviseProvenance(edited,{revision:2,sources:[],scopes:[],groups:[]});
const stablePrepared=prepareProducerFragment(f.result,stable,{...f.options,previous:q.bound});
const pending=session.update(stablePrepared.update);
stablePrepared.update.scene.arena.xs[0]=999;stablePrepared.update.tiles.get('glyph-0').uv.fill(0);stablePrepared.update.resources[0].bytes.fill(0);
await pending;await draw(changed,3);assert.equal(d.uploads,1);
checks.push('caller mutation after update cannot change drawable or immutable resource');
const before=session.generation,stale=reviseProvenance(stable,{revision:3,sources:[],scopes:[],groups:[]});
f.result.scene.arena.xs[0]=7;
assert.throws(()=>prepareProducerFragment(f.result,stale,{...f.options,previous:stablePrepared.bound}),/Typed output edit requires layout version/);
assert.equal(session.generation,before);await draw(changed,4);
checks.push('stale layoutVersion rejection preserves previously committed drawable');
// Hold completion to prove cancel/dispose retain resources until queue completion.
d.auto=false;const receipt=await session.render(view);let completed=false;receipt.completion.then(()=>completed=true);
await Promise.resolve();assert.equal(completed,false);
const texture=d.resources.find(x=>x.kind==='texture');session.cancel();assert.equal(session.generation,null);
assert.throws(()=>session.render(view),/No completed update/);assert.equal(texture.destroyed,0);
const disposed=session.dispose();assert.equal(session.dispose(),disposed);let drained=false;disposed.then(()=>drained=true);
await Promise.resolve();assert.equal(drained,false);d.flush();await receipt.completion;await disposed;
assert.equal(completed,true);assert(d.resources.length>0);assert(d.resources.every(x=>x.destroyed===1));
checks.push('cancel and idempotent dispose await submission completion and destroy every lifetime exactly once');
console.log(JSON.stringify({passed:true,checks,synthetic_only:true,native_producer_qualified:false,performance_claim:false}));
