import assert from 'node:assert/strict';
import {writeFileSync} from 'node:fs';
import {pathToFileURL} from 'node:url';
import {resolve} from 'node:path';
import {fixture} from './columns-fixture.mjs';
import {backend} from './multipage-session-backend.mjs';
const root=process.env.VKF_LIFECYCLE_MODULE_ROOT ? pathToFileURL(resolve(process.env.VKF_LIFECYCLE_MODULE_ROOT)+'/') : new URL('../',import.meta.url);
const {beginProvenance,reviseProvenance}=await import(new URL('latex_operation_binding.mjs',root));
const {prepareProducerDocument,selectProducerPage}=await import(new URL('document_producer_adapter.mjs',root));
const {createDocumentRenderSession}=await import(new URL('document_render_session.mjs',root));
globalThis.GPUTextureUsage={TEXTURE_BINDING:4,COPY_DST:2};globalThis.GPUBufferUsage={VERTEX:32,COPY_DST:8,UNIFORM:64};
const f=fixture(1),a=f.result.document.arena;
Object.assign(f.result.document,{page_count:3,firsts:[0,1,2],counts:[1,1,1],widths:[100,110,120],heights:[200,210,220]});
Object.assign(a,{kinds:[0,0,0],keys:['glyph-0','glyph-0','glyph-0'],payloads:[-1,-1,-1],xs:[1,20,40],ys:[2,3,4],a260_scopes:['parse-0','parse-1','parse-2'],a260_texts:['α','x','z'],a260_operations:[0,0,0],a260_stops:[2,1,1]});
f.owner.sources=['α','x','z'].map((text,i)=>({id:'s'+i,version:0,text}));
f.owner.scopes=f.owner.sources.map((s,i)=>({id:'parse-'+i,sourceId:s.id,text:s.text,baseByte:0,operations:[{operation:0,start:0,stop:i?1:2,groupId:'group-'+i,leaves:[{part:0,id:'leaf-'+i,resources:['resource-0']}]}]}));
f.owner.groups.forEach((g,i)=>{g.spans=[{sourceId:'s'+i,start:0,end:1}];g.edges=i===1?[{kind:'flow',target:'group-0'}]:[];});

const owner=beginProvenance(f.owner),p=prepareProducerDocument(f.result,owner,f.options);
const view={canvas:{width:120,height:220},context:{getCurrentTexture(){return {createView(){return {};}};}},scale:1};
const pipeline={getBindGroupLayout(){return {};}};
const row=(x,y)=>[x,y,1,1,0,0,1,1,0,0,0,1,0,0,0,0];
const original=[row(1,2),row(20,3),row(40,4)];
function countedBackend(){const d=backend();d.bufferWrites=0;const w=d.queue.writeBuffer;d.queue.writeBuffer=(...a)=>{d.bufferWrites++;return w(...a);};return d;}
const checks=[
 'Second and third Unicode revisions and two warm sibling branches equal fresh public preparation',
 'Rejected warm semantic revisions publish no usable owner or render generation and preserve retained branches',
 'Warm branch sessions release exact mock resources and snapshots after delayed completion fences'
];
const rows=[];
for(let cycle=0;cycle<4;cycle++){
 const snapshots=[{owner,result:f.result,prepared:p,text:'α',x:1}];
 function deltaFor(old,text,offset){
  const scope=structuredClone(old.owner.scopes[0]);scope.text=text;scope.operations[0].stop=new TextEncoder().encode(text).length;
  const revision=old.owner.revision+1;
  return {revision,sources:[{...old.owner.sources[0],version:old.owner.sources[0].version+1,text}],scopes:[scope],groups:old.owner.groups.slice(0,2).map((g,i)=>({...structuredClone(g),contentVersion:g.contentVersion+1,layoutVersion:g.layoutVersion+1,contentKey:i?g.contentKey:text,layoutKey:'warm-'+cycle+'-'+offset+'-'+i,spans:i?structuredClone(g.spans):[{sourceId:'s0',start:0,end:text.length}]}))};
 }
 function revision(old,text,offset){
  const delta=deltaFor(old,text,offset),next=reviseProvenance(old.owner,delta);
  const result=structuredClone(old.result),a=result.document.arena;
  a.a260_texts[0]=text;a.a260_stops[0]=new TextEncoder().encode(text).length;a.xs[0]=offset;a.xs[1]=offset+19;
  const opts={...f.options,previous:old.prepared.bound};
  const prepared=prepareProducerDocument(result,next,opts);
  // Fresh authenticated entry performs complete public validation of the same value.
  const fresh=prepareProducerDocument(structuredClone(result),beginProvenance(structuredClone(next)),opts);
  assert.deepEqual(prepared,fresh);
  assert.deepEqual(prepared.bound.invalidated,['group-0','group-1']);
  assert.equal(next.scopes[2],old.owner.scopes[2]);assert.equal(next.sources[2],old.owner.sources[2]);
  assert.equal(prepared.bound.sourceBinding.sources[0].text,text);
  const value={owner:next,result,prepared,text,x:offset};snapshots.push(value);return value;
 }
 const one=revision(snapshots[0],'β',2+cycle);
 // Rejection occurs on an authentic first revision (certified on E363).
 const bad=deltaFor(one,'😀',30+cycle);bad.scopes[0].operations[0].stop=1;
 let published;
 assert.throws(()=>{published=reviseProvenance(one.owner,bad);},/Byte offset splits scalar/);
 assert.equal(published,undefined);
 assert.throws(()=>reviseProvenance({...one.owner,revision:bad.revision},deltaFor(one,'γ',31)),/Entry owner session required/);
 const two=revision(one,'😀',3+cycle);
 const sibling1=revision(one,'漢',10+cycle),sibling2=revision(one,'δ',20+cycle);
 // Another rejected semantic edit between successful second and third revisions.
 const missing=deltaFor(two,'ε',40+cycle);missing.groups.pop();
 assert.throws(()=>reviseProvenance(two.owner,missing),/Missing dependent group replacement/);
 const three=revision(two,'é',4+cycle);
 const sessions=[];
 for(const snap of snapshots){
  const d=countedBackend(),s=createDocumentRenderSession({device:d,pipeline});
  await s.update(selectProducerPage(snap.prepared,0).update);
  const first=await s.render(view);await first.completion;
  assert.deepEqual([...d.submitted[0].buffer.bytes],row(snap.x,2));
  sessions.push({s,d,snap});
 }
 for(const {s,d,snap} of sessions){
  const before=s.generation,metrics=s.metrics;
  const malformed=deltaFor(snap,'ζ',50+cycle);malformed.scopes=[];
  assert.throws(()=>reviseProvenance(snap.owner,malformed),/Missing dependent scope replacement/);
  assert.equal(s.generation,before);assert.deepEqual(s.metrics,metrics);
  assert.equal(snap.prepared.bound.sourceBinding.sources[0].text,snap.text);
  assert.deepEqual(prepareProducerDocument(snap.result,beginProvenance(structuredClone(snap.owner)),f.options).bound.metadata,snap.prepared.bound.metadata);
  d.auto=false;const last=await s.render(view);
  assert.deepEqual([...d.submitted[0].buffer.bytes],row(snap.x,2));
  assert.equal(d.gates.length,1);s.cancel();assert.equal(s.generation,null);
  const disposal=s.dispose();assert.equal(s.dispose(),disposal);let disposed=false;disposal.then(()=>disposed=true);
  await Promise.resolve();assert.equal(disposed,false);assert(d.resources.some(x=>!x.destroyed));
  d.flush();await last.completion;await disposal;
  assert.equal(d.gates.length,0);assert(d.resources.every(x=>x.destroyed===1));
  const counts={textures:d.resources.filter(x=>x.kind==='texture').length,buffers:d.resources.filter(x=>x.kind==='buffer').length,uploads:d.uploads,bufferWrites:d.bufferWrites};
  assert.deepEqual(counts,{textures:1,buffers:3,uploads:1,bufferWrites:3});
  assert.deepEqual(s.metrics,{commits:1,noops:0,resourceCopies:1,resourceReuses:0,liveSnapshots:0,submissions:2});
  rows.push({cycle,revision:snap.owner.revision,text:snap.text,counts,metrics:s.metrics});
 }
}
const report={passed:true,checks,cycles:4,sessions:rows.length,rows,synthetic_only:true,certificate_visibility:'private; public rejection and subsequent valid revision behavior only'};
if(process.env.VKF_HOST_RESULT_DIR)writeFileSync(new URL('warm-results.json',process.env.VKF_HOST_RESULT_DIR),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report));
