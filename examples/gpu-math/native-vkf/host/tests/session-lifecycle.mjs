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
const retainedDevice=countedBackend(),retained=createDocumentRenderSession({device:retainedDevice,pipeline});
await retained.update(selectProducerPage(p,0).update);
let settled=0;
async function draw(s,d,want){const r=await s.render(view);await r.completion;settled+=2;assert.deepEqual([...d.submitted[0].buffer.bytes],want);assert.equal(d.submitted[0].buffer.destroyed,0);return r;}
const rows=[];
for(let cycle=0;cycle<24;cycle++){
 const d=countedBackend(),s=createDocumentRenderSession({device:d,pipeline});
 for(let page=0;page<3;page++){await s.update(selectProducerPage(p,page).update);settled++;await draw(s,d,original[page]);}
 // Every cycle forks the retained original; its explicit dependent group changes too.
 const delta={revision:1,sources:[{...owner.sources[0],version:1,text:'β'}],scopes:[{...structuredClone(owner.scopes[0]),text:'β'}],groups:owner.groups.slice(0,2).map((g,i)=>({...structuredClone(g),contentVersion:1,layoutVersion:1,contentKey:i?g.contentKey:'beta',layoutKey:'edited-'+cycle+'-'+i}))};
 const edited=reviseProvenance(owner,delta),result=structuredClone(f.result);
 result.document.arena.a260_texts[0]='β';result.document.arena.xs[0]=2+cycle;result.document.arena.xs[1]=21+cycle;
 const q=prepareProducerDocument(result,edited,{...f.options,previous:p.bound});
 assert.deepEqual(q.bound.invalidated,['group-0','group-1']);
 const changed=[row(2+cycle,2),row(21+cycle,3),row(40,4)];
 for(let page=0;page<3;page++){await s.update(selectProducerPage(q,page).update);settled++;await draw(s,d,changed[page]);}
 const before=s.generation;
 d.validation=new Error('lifecycle rejected upload');
 await assert.rejects(s.update(selectProducerPage(q,2).update),/lifecycle rejected upload/);settled++;
 assert.equal(s.generation,before);d.validation=null;
 await s.update(selectProducerPage(q,2).update);settled++;await draw(s,d,changed[2]);
 // Abort before submission, then complete another render from the same committed state.
 const abort=new AbortController();const cancelled=s.render(view,{signal:abort.signal});abort.abort();
 await assert.rejects(cancelled,/Cancelled render/);settled++;
 const delayed=cycle%4===0;d.auto=!delayed;
 const last=await s.render(view);settled++;let completed=false;last.completion.then(()=>completed=true);
 if(delayed){await Promise.resolve();assert.equal(completed,false);assert.equal(d.gates.length,1);}
 s.cancel();assert.equal(s.generation,null);
 const disposal=s.dispose();assert.equal(s.dispose(),disposal);let drained=false;disposal.then(()=>drained=true);
 if(delayed){await Promise.resolve();assert.equal(drained,false);assert(d.resources.some(x=>!x.destroyed));d.flush();}
 await last.completion;await disposal;settled+=2;
 assert.equal(completed,true);assert.equal(d.gates.length,0);
 assert(d.resources.every(x=>x.destroyed===1));
 const counts={textures:d.resources.filter(x=>x.kind==='texture').length,buffers:d.resources.filter(x=>x.kind==='buffer').length,uploads:d.uploads,bufferWrites:d.bufferWrites};
 assert.deepEqual(counts,{textures:1,buffers:15,uploads:1,bufferWrites:15});
 assert.deepEqual(s.metrics,{commits:6,noops:2,resourceCopies:1,resourceReuses:5,liveSnapshots:0,submissions:8});
 assert.equal(retained.metrics.liveSnapshots,1);assert.equal(p.bound.sourceBinding.sources[0].text,'α');
 assert.equal(q.bound.sourceBinding.sources[0].text,'β');
 await draw(retained,retainedDevice,original[0]);
 assert.equal(retainedDevice.uploads,1);assert.equal(retainedDevice.resources.filter(x=>!x.destroyed).length,2);
 rows.push({cycle,delayed,counts,metrics:s.metrics,liveResources:0,retainedLiveSnapshots:1});
}
await retained.dispose();settled++;
assert.equal(retained.metrics.liveSnapshots,0);assert(retainedDevice.resources.every(x=>x.destroyed===1));
assert.equal(retainedDevice.resources.length,26);assert.equal(retainedDevice.bufferWrites,25);assert.equal(retainedDevice.uploads,1);
const checks=[
 '24 lifecycle forks preserve retained sibling geometry and Unicode provenance after real edits and page switches',
 '24 rejected replacements recover through valid successors with exact texture and instance upload reuse',
 '24 cancellation and disposal cycles settle all operations with six delayed completion fences and zero live snapshots or mock resources'
];
const report={passed:true,checks,cycles:24,settledOperations:settled,rows,retained:{resources:26,uploads:1,bufferWrites:25,metrics:retained.metrics},synthetic_only:true,physical_gpu_pdf_native_memory_claim:false};
if(process.env.VKF_HOST_RESULT_DIR)writeFileSync(new URL('lifecycle-results.json',process.env.VKF_HOST_RESULT_DIR),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report));
