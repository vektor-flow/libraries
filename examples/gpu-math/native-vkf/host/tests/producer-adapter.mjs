import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {beginProvenance} from '../latex_operation_binding.mjs';
import {prepareProducerDocument} from '../document_producer_adapter.mjs';
import {createDocumentRenderSession} from '../document_render_session.mjs';
import {createRetainedSceneBridge} from '../document_resource_bridge.mjs';
const schema=JSON.parse(readFileSync(new URL('./fixtures/schema314.json',import.meta.url)));
const checks=[];
function test(name,fn){fn();checks.push(name);}
const span={sourceId:'source',start:0,end:1};
function owner(revision=0){return beginProvenance({documentId:'document',revision,sources:[{id:'source',version:0,text:'x'}],scopes:[{id:'parse',sourceId:'source',text:'x',baseByte:0,operations:[{operation:0,start:0,stop:1,groupId:'group',leaves:[{part:0,id:'leaf',resources:[]}]}]}],groups:[{id:'group',contentVersion:0,layoutVersion:0,contentKey:'text-x',layoutKey:'rule-x',edges:[],spans:[span]}],resources:[]});}
function fixture(){
 const a=Object.fromEntries(schema.Arena.map(k=>[k,[]]));
 Object.assign(a,{count:1,keys:[''],kinds:[2],xs:[1],ys:[2],sxs:[1],sys:[1],widths:[3],heights:[4],draws:[true],paints:[-1],payloads:[-1],paint_table:[],payload_table:[],paint_count:0,payload_count:0,a260_scopes:['parse'],a260_texts:['x'],a260_operations:[0],a260_starts:[0],a260_stops:[1],a260_parts:[0]});
 const d=Object.fromEntries(schema.PageDocument.map(k=>[k,[]]));Object.assign(d,{arena:a,page_count:1,destination_count:0,firsts:[0],counts:[1],widths:[100],heights:[100]});
 return {document:d,complete:true,diagnostics:'',unresolved_json:'[]'};
}
const good=prepareProducerDocument(fixture(),owner());
test('accepted source-bound rule subset projects to installed typed scene',()=>{assert.equal(good.update.metadata.leafIds[0],'leaf');assert.equal(good.bound.sourceBinding.leaves[0].spans[0].end,1);assert(good.update.scene.arena.xs instanceof Float64Array);});
for(const key of ['a260_scopes','a260_texts','a260_operations','a260_starts','a260_stops','a260_parts']){
 test(key+' extent rejected',()=>{let f=fixture();f.document.arena[key]=[];assert.throws(()=>prepareProducerDocument(f,owner()),/extent/);});
 test(key+' type rejected',()=>{let f=fixture();f.document.arena[key]=[key==='a260_scopes'||key==='a260_texts'?0:'0'];assert.throws(()=>prepareProducerDocument(f,owner()),/type/);});
}
for(const [key,value] of [['a260_scopes','unknown'],['a260_texts','y'],['a260_operations',8],['a260_starts',1],['a260_stops',0],['a260_parts',8]])test(key+' owner mismatch rejected',()=>{let f=fixture();f.document.arena[key]=[value];assert.throws(()=>prepareProducerDocument(f,owner()));});
for(const [key,value] of [['complete',false],['diagnostics','warning'],['unresolved_json','["missing"]']])test('reject '+key,()=>assert.throws(()=>prepareProducerDocument({...fixture(),[key]:value},owner()),/Incomplete/));
test('missing display provenance rejected',()=>{const f=fixture();f.document.arena.a260_scopes=[''];assert.throws(()=>prepareProducerDocument(f,owner()),/Unbound/);});
test('anchor destination provenance unsupported',()=>{const f=fixture();f.document.destination_count=1;assert.throws(()=>prepareProducerDocument(f,owner()),/Unsupported/);});
test('multipage subset explicitly unsupported',()=>{const f=fixture();f.document.page_count=2;assert.throws(()=>prepareProducerDocument(f,owner()),/Unsupported/);});
test('unconsumed mapping rejected',()=>{let f=fixture();f.document.arena.count=0;for(const k of schema.Arena)if(Array.isArray(f.document.arena[k]))f.document.arena[k]=[];assert.throws(()=>prepareProducerDocument(f,owner()),/Unconsumed/);});
test('unchanged revision guard preserved',()=>assert.throws(()=>prepareProducerDocument(fixture(),owner(),{previous:good.bound}),/Revision/));
test('advanced revision keeps source-owned identity',()=>assert.equal(prepareProducerDocument(fixture(),owner(1),{previous:good.bound}).update.metadata.leafIds[0],'leaf'));
test('input geometry snapshot',()=>{let f=fixture(),r=prepareProducerDocument(f,owner());f.document.arena.xs[0]=99;assert.equal(r.update.scene.arena.xs[0],1);});
test('immutable versioned glyph transport and rejection retain committed snapshot',()=>{
 const o=structuredClone(owner());o.resources=[{id:'font',version:2,binding:'atlas-owner'}];o.scopes[0].operations[0].leaves[0].resources=['font'];
 const f=fixture();f.document.arena.kinds=[0];f.document.arena.keys=['glyph'];
 const tiles=new Map([['glyph',{resourceId:'font',plane:new Float64Array([0,0,1,1]),uv:new Float64Array([0,0,1,1])}]]);
 const resources=[{id:'font',version:2,bytes:new Uint8Array([255,0,0,255]),image:{format:'rgba8unorm',alphaMode:'straight',width:1,height:1,bytesPerRow:4}}];
 const r=prepareProducerDocument(f,beginProvenance(o),{tiles,resources});resources[0].bytes[0]=0;
 assert.equal(r.update.resources[0].bytes[0],255);
 const b=createRetainedSceneBridge(),u=r.update,l=b.commitScene(u.scene,u.metadata,u.tiles,u.resources);assert.equal(l.resource('font')[0],255);l.release();
 const bad=structuredClone(u.resources);bad[0].bytes[0]=0;
 assert.throws(()=>b.commitScene(u.scene,u.metadata,u.tiles,bad),/Immutable resource/);
 const retained=b.snapshot();assert.equal(retained.resource('font')[0],255);retained.release();b.dispose();
 const wrong=structuredClone(resources);wrong[0].version=3;assert.throws(()=>prepareProducerDocument(f,beginProvenance(o),{tiles,resources:wrong}),/payload\/version/);
});
// Structural mock only: no GPU implementation or execution.
globalThis.GPUBufferUsage={VERTEX:1,COPY_DST:2};let writes=0;
const device={lost:new Promise(()=>{}),pushErrorScope(){},async popErrorScope(){return null;},createBuffer(){return {destroy(){}};},queue:{writeBuffer(){writes++;},async onSubmittedWorkDone(){}}};
const session=createDocumentRenderSession({device,pipeline:{}});
await session.update(good.update);assert.equal(session.generation,1);assert.equal(writes,1);
checks.push('installed E312 session accepts prepared packet using structural device mock');
const before=session.metrics.commits;
assert.throws(()=>session.update({...good.update,diagnostics:'',unresolved_json:'[]'}),/Incomplete/);assert.equal(session.metrics.commits,before);
await session.dispose();
const bridge=createRetainedSceneBridge();const lease=bridge.commitScene(good.update.scene,good.update.metadata,good.update.tiles,good.update.resources);assert.equal(lease.count,1);lease.release();bridge.dispose();await bridge.drained();
console.log(JSON.stringify({passed:true,checks:checks,synthetic_only:true}));
