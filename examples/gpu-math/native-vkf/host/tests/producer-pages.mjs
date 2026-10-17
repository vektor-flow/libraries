import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {beginProvenance} from '../latex_operation_binding.mjs';
import {prepareProducerDocument,selectProducerPage} from '../document_producer_adapter.mjs';
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
function backend(){
 let lose;
 const d={samplers:[],binds:[],textures:[],buffers:[],commands:[],gates:[],auto:true,writes:0,lost:new Promise(r=>lose=r),lose(){lose();},pushErrorScope(){},async popErrorScope(){return null;},
 createTexture(desc){const t={desc,destroyed:0,destroy(){this.destroyed++;},createView(){return {texture:this};}};d.textures.push(t);return t;},
 createBuffer(desc){const b={desc,destroyed:0,destroy(){this.destroyed++;}};d.buffers.push(b);return b;},
 createSampler(x){d.samplers.push(x);return x;},createBindGroup(x){d.binds.push(x);return x;},
 createCommandEncoder(){const c={draws:[],beginRenderPass(){return {setPipeline(){},setVertexBuffer(i,b){c.buffer=b;},setBindGroup(i,b){c.bind=b;},draw(...args){c.draws.push({args,bind:c.bind});},end(){}};},finish(){return c;}};d.commands.push(c);return c;},
 queue:{writeTexture({texture},raw){d.writes++;texture.bytes=raw.slice();},writeBuffer(b,o,raw){d.bufferWrites=(d.bufferWrites??0)+1;b.bytes=raw.slice();},submit(){d.submits=(d.submits??0)+1;},onSubmittedWorkDone(){return d.auto?Promise.resolve():new Promise(r=>d.gates.push(r));}},flush(){for(const r of d.gates.splice(0))r();}};return d;
}

globalThis.GPUTextureUsage={TEXTURE_BINDING:4,COPY_DST:2};globalThis.GPUBufferUsage={VERTEX:32,COPY_DST:8,UNIFORM:64};

const view={canvas:{width:100,height:100},context:{getCurrentTexture(){return {createView(){return {};}};}},scale:1};
const tick=()=>new Promise(r=>setImmediate(r));

function multi(revision=0,text='x',version=0){
 const f=fixture(),o=structuredClone(owner(revision)),a=f.document.arena;
 for(const k of schema.Arena)if(Array.isArray(a[k])&&a[k].length===1&&!['paint_table','payload_table'].includes(k))a[k].push(a[k][0]);
 a.count=2;a.xs=[1,20];a.a260_operations=[0,1];a.a260_texts=[text,text];
 Object.assign(f.document,{page_count:3,firsts:[0,1,1],counts:[1,0,1],widths:[100,120,200],heights:[90,110,300]});
 o.sources[0].text=text;o.sources[0].version=version;o.scopes[0].text=text;
 const op=structuredClone(o.scopes[0].operations[0]);op.operation=1;op.groupId='other';op.leaves[0].id='last-leaf';o.scopes[0].operations.push(op);
 o.groups.push({...structuredClone(o.groups[0]),id:'other'});
 o.groups[0].edges=[{kind:'flow',target:'other'}];
 for(const g of o.groups){g.contentVersion=version;g.layoutVersion=version;g.contentKey='text-'+text;}
 return {f,o};
}
function prepare(pair=multi(),options={}){return prepareProducerDocument(pair.f,beginProvenance(pair.o),{page:0,...options});}
const first=prepare(),last=selectProducerPage(first,2),empty=selectProducerPage(first,1);
test('exact schema three pages select first empty and last with unequal explicit dimensions',()=>{
 const {f}=multi();assert.deepEqual(Object.keys(f.document).sort(),schema.PageDocument.slice().sort());assert.deepEqual(Object.keys(f.document.arena).sort(),schema.Arena.slice().sort());
 assert.deepEqual(first.update.metadata.leafIds,['leaf']);assert.deepEqual(last.update.metadata.leafIds,['last-leaf']);assert.equal(last.update.scene.arena.xs[0],20);assert.equal(empty.update.scene.arena.count,0);
 assert.equal(last.update.width,200);assert.equal(last.update.height,300);assert.equal(empty.update.width,120);assert.equal(last.bound,first.bound);assert.equal(first.bound.metadata.leafIds.length,2);
});
test('projection retains dependency identities and versions with empty off-page ranges',()=>{const gs=last.update.metadata.groups;assert.deepEqual(gs.map(g=>[g.id,g.first,g.count]),[['group',0,0],['other',0,1]]);assert.deepEqual(gs[0].dependencies,['other']);assert.equal(gs[1].layoutVersion,0);});
test('page outputs and input arrays never share mutable projection storage',()=>{const again=selectProducerPage(first,2);last.update.scene.arena.xs[0]=999;last.update.metadata.groups[0].edges.length=0;last.update.metadata.leafIds[0]='mutated';assert.equal(again.update.scene.arena.xs[0],20);assert.equal(again.update.metadata.leafIds[0],'last-leaf');assert.equal(again.update.metadata.groups[0].edges.length,1);});
test('explicit selection is required and invalid selectors rejected',()=>{const {f,o}=multi();assert.throws(()=>prepareProducerDocument(f,beginProvenance(o)),/implicit/);for(const page of [-1,3,0.5,NaN,'1'])assert.throws(()=>selectProducerPage(first,page),/selected page/);assert.throws(()=>selectProducerPage({...first},0),/Prepared/);});
test('all page directories extents overlaps gaps ranges and dimensions validated',()=>{
 for(const change of [d=>d.firsts=[0,0,1],d=>d.firsts=[0,2,2],d=>d.counts=[1,0,2],d=>d.counts=[1,-1,2],d=>d.firsts=[0,1],d=>d.counts=[1,0,0],d=>d.widths=[100,NaN,200],d=>d.heights=[90,110,0],d=>d.widths=[100],d=>d.page_count=0]){const pair=multi();change(pair.f.document);assert.throws(()=>prepare(pair));}
});
test('semantic groups crossing any page boundary explicitly rejected',()=>{const pair=multi();pair.o.scopes[0].operations[1].groupId='group';pair.o.groups[0].edges=[];assert.throws(()=>prepare(pair),/crossing page/);});
test('off-page ownership and geometry validated before projection',()=>{let pair=multi();pair.f.document.arena.a260_operations[1]=99;assert.throws(()=>prepare(pair),/Parser/);pair=multi();pair.f.document.arena.xs[1]=NaN;assert.throws(()=>prepare(pair),/type/);});
test('page switches retain full previous provenance and source edits keep owner leaf IDs',()=>{
 const changed=prepare(multi(1,'y',1),{page:2,previous:first.bound});assert.deepEqual(changed.update.metadata.leafIds,['last-leaf']);assert.equal(changed.bound.sourceBinding.sources[0].text,'y');
 const staleSource=multi(1,'y',1);staleSource.o.sources[0].version=0;assert.throws(()=>prepare(staleSource,{page:2,previous:first.bound}),/Source changed/);
 assert.throws(()=>prepare(multi(1),{previous:{metadata:first.bound.metadata}}),/Previous source/);
 const pair=multi(1);pair.o.documentId='foreign';assert.throws(()=>prepare(pair,{previous:first.bound}),/Revision/);
 const bad=multi(1,'y',1);bad.o.groups[1].contentVersion=0;bad.o.groups[1].contentKey='text-x';assert.throws(()=>prepare(bad,{previous:first.bound}),/Source edit/);
});
test('glyph tiles and resource payloads are exactly selected missing differs from empty',()=>{
 const pair=multi(),a=pair.f.document.arena; a.kinds=[0,0];a.keys=['left','right'];
 pair.o.resources=['a','b'].map(id=>({id,version:0,binding:'owner-'+id}));pair.o.scopes[0].operations.forEach((op,i)=>op.leaves[0].resources=[i?'b':'a']);
 const tiles=new Map(['left','right'].map((key,i)=>[key,{resourceId:i?'b':'a',plane:new Float64Array([0,0,1,1]),uv:new Float64Array([0,0,1,1])}]));
 const resources=['a','b'].map(id=>({id,version:0,bytes:new Uint8Array([0,0,0,255]),image:{format:'rgba8unorm',alphaMode:'straight',width:1,height:1,bytesPerRow:4}}));
 const p=prepare(pair,{tiles,resources}),end=selectProducerPage(p,2),none=selectProducerPage(p,1);
 assert.deepEqual([...p.update.tiles.keys()],['left']);assert.deepEqual(end.update.resources.map(r=>r.id),['b']);assert.equal(none.update.tiles.size,0);assert.deepEqual(none.update.resources,[]);
 assert.throws(()=>prepare(pair,{tiles:new Map([['left',tiles.get('left')]]),resources}),/Missing explicit glyph/);assert.throws(()=>prepare(pair,{tiles,resources:resources.slice(0,1)}),/Missing resource/);
 end.update.resources[0].bytes[0]=42;end.update.tiles.get('right').uv[0]=0.5;const again=selectProducerPage(p,2);assert.equal(again.update.resources[0].bytes[0],0);assert.equal(again.update.tiles.get('right').uv[0],0);
});
test('link local index rebased without changing explicit target',()=>{const pair=multi();pair.f.document.arena.kinds[1]=3;pair.f.document.arena.payloads[1]=0;pair.f.document.arena.payload_count=1;pair.f.document.arena.payload_table=[{target:'https://example.test',border_width:1}];pair.o.scopes[0].operations[1].leaves[0].link='https://example.test';const p=prepare(pair,{page:2});assert.deepEqual(p.update.metadata.links,[{leaf:0,target:'https://example.test'}]);});
{
 const d=backend(),s=createDocumentRenderSession({device:d,pipeline:{getBindGroupLayout(){return {};}}});
 const p=prepare();await s.update(p.update);d.auto=false;const left=await s.render(view);await tick();const fence1=d.gates.shift();
 d.auto=true;await s.update(selectProducerPage(p,2).update);d.auto=false;const right=await s.render({...view,canvas:{width:200,height:300}});await tick();const fence2=d.gates.shift();
 assert.notEqual(left.generation,right.generation);assert.notEqual(d.commands[0].buffer,d.commands[1].buffer);assert.notDeepEqual(d.commands[0].buffer.bytes,d.commands[1].buffer.bytes);
 const disposal=s.dispose();await tick();assert.equal(d.commands[0].buffer.destroyed,0);assert.equal(d.commands[1].buffer.destroyed,0);
 fence1();await left.completion;assert.equal(d.commands[1].buffer.destroyed,0);fence2();await right.completion;await disposal;
 assert.ok(d.buffers.every(b=>b.destroyed===1));assert.ok(d.textures.every(t=>t.destroyed===1));checks.push('two pending different page draws retain geometry and retire only after their fences');
}
console.log(JSON.stringify({passed:true,checks,synthetic_only:true}));
