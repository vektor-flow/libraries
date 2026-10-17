import assert from 'node:assert/strict';
import {fixture} from './columns-fixture.mjs';
import {backend} from './multipage-session-backend.mjs';
import {beginProvenance,reviseProvenance} from '../latex_operation_binding.mjs';
import {prepareProducerDocument,selectProducerPage} from '../document_producer_adapter.mjs';
import {createDocumentRenderSession} from '../document_render_session.mjs';
import {sceneColumns} from '../document_scene_bridge.mjs';
globalThis.GPUTextureUsage={TEXTURE_BINDING:4,COPY_DST:2};globalThis.GPUBufferUsage={VERTEX:32,COPY_DST:8,UNIFORM:64};
const f=fixture(1),a=f.result.document.arena;
Object.assign(f.result.document,{page_count:3,firsts:[0,1,2],counts:[1,1,1],widths:[100,110,120],heights:[200,210,220]});
Object.assign(a,{kinds:[0,0,0],keys:['glyph-0','glyph-0','glyph-0'],payloads:[-1,-1,-1],xs:[1,20,40],ys:[2,3,4],a260_scopes:['parse-0','parse-1','parse-2'],a260_texts:['α','x','z'],a260_operations:[0,0,0],a260_stops:[2,1,1]});
f.owner.sources=['α','x','z'].map((text,i)=>({id:'s'+i,version:0,text}));
f.owner.scopes=f.owner.sources.map((s,i)=>({id:'parse-'+i,sourceId:s.id,text:s.text,baseByte:0,operations:[{operation:0,start:0,stop:i?1:2,groupId:'group-'+i,leaves:[{part:0,id:'leaf-'+i,resources:['resource-0']}]}]}));
f.owner.groups.forEach((g,i)=>{g.spans=[{sourceId:'s'+i,start:0,end:1}];g.edges=i===1?[{kind:'flow',target:'group-0'}]:[];});
const checks=[],owner=beginProvenance(f.owner),p=prepareProducerDocument(f.result,owner,f.options);
const row=(x,y)=>[x,y,1,1,0,0,1,1,0,0,0,1,0,0,0,0];
const expected=[row(1,2),row(20,3),row(40,4)];
const values=u=>sceneColumns(u.scene,u.metadata,u.tiles).columns.map(c=>c[0]);
function parity(prepared,provenance,want){
 for(let page=0;page<3;page++){
  const selected=selectProducerPage(prepared,page),fresh=prepareProducerDocument(structuredClone(f.result),beginProvenance(structuredClone(provenance)),{...f.options,page});
  assert.deepEqual(values(selected.update),want[page]);assert.deepEqual(values(selected.update),values(fresh.update));
  assert.deepEqual(selected.update.metadata,fresh.update.metadata);assert.deepEqual(selected.bound.sourceBinding,fresh.bound.sourceBinding);
  assert.equal(selected.bound,prepared.bound);assert.equal(selected.update.width,100+page*10);assert.equal(selected.update.height,200+page*10);
 }
}
parity(p,owner,expected);
const d=backend(),s=createDocumentRenderSession({device:d,pipeline:{getBindGroupLayout(){return {};}}});
const view={canvas:{width:120,height:220},context:{getCurrentTexture(){return {createView(){return {};}};}},scale:1};
let submission=0;
async function draw(want){const r=await s.render(view);assert.equal(r.submission,++submission);assert.equal(r.generation,s.generation);assert(r.completion instanceof Promise);await r.completion;const c=d.submitted[0];assert.deepEqual([...c.buffer.bytes],want);assert.deepEqual(c.draws.map(x=>x.args),[[6,1,0,0]]);return c.draws[0].bind.entries[1].resource.texture;}
let texture;
for(let page=0;page<3;page++){const u=await s.update(selectProducerPage(p,page).update);assert.equal(u.revision,0);const t=await draw(expected[page]);if(texture)assert.equal(t,texture);texture=t;}
assert.equal(d.uploads,1);
checks.push('three explicit pages match fresh preparation and literal geometry while one session shares texture');
const changedGroups=owner.groups.slice(0,2).map((g,i)=>({...structuredClone(g),contentVersion:1,layoutVersion:1,contentKey:i?g.contentKey:'beta',layoutKey:'edited-'+i}));
const delta={revision:1,sources:[{...owner.sources[0],version:1,text:'β'}],scopes:[{...structuredClone(owner.scopes[0]),text:'β'}],groups:changedGroups};
const edited=reviseProvenance(owner,delta);
a.a260_texts[0]='β';a.xs[0]=2;a.xs[1]=21;
const q=prepareProducerDocument(f.result,edited,{...f.options,previous:p.bound});
const changed=[row(2,2),row(21,3),row(40,4)];parity(q,edited,changed);
assert.deepEqual(q.bound.invalidated,['group-0','group-1']);assert.equal(q.bound.sourceBinding.sources[0].text,'β');
assert.deepEqual(selectProducerPage(q,2).update.scene,selectProducerPage(p,2).update.scene);
for(let page=0;page<3;page++){assert.equal((await s.update(selectProducerPage(q,page).update)).revision,1);assert.equal(await draw(changed[page]),texture);}
assert.equal(d.uploads,1);
checks.push('Unicode source edit with explicit dependent closure and exact full prior bound matches fresh pages and preserves unaffected page');
const generation=s.generation;
assert.throws(()=>reviseProvenance(owner,{...delta,groups:[changedGroups[0]]}),/Missing dependent group replacement/);
const stale=beginProvenance({...structuredClone(edited),groups:[changedGroups[0],structuredClone(owner.groups[1]),structuredClone(owner.groups[2])]});
assert.throws(()=>prepareProducerDocument(f.result,stale,{...f.options,previous:p.bound}),/Affected group requires new layout version/);
const unchanged=reviseProvenance(edited,{revision:2,sources:[],scopes:[],groups:[]});
a.xs[1]=99;
assert.throws(()=>prepareProducerDocument(f.result,unchanged,{...f.options,previous:q.bound}),/Typed output edit requires layout version/);
a.xs[1]=21;assert.equal(s.generation,generation);await draw(changed[2]);
checks.push('stale dependency and off-page layout reject without changing last drawable');
const resourceOwner=beginProvenance({...structuredClone(edited),revision:2,groups:edited.groups.map(g=>({...structuredClone(g),layoutVersion:g.layoutVersion+1})),resources:[{...edited.resources[0],version:1,binding:'binding-new'}]});
f.options.resources[0].version=1;f.options.resources[0].bytes[0]=77;
const r=prepareProducerDocument(f.result,resourceOwner,{...f.options,previous:q.bound});parity(r,resourceOwner,changed);
await s.update(r.update);const replacement=await draw(changed[0]);assert.notEqual(replacement,texture);assert.equal(d.uploads,2);assert.equal(replacement.bytes[0],77);
await s.update(selectProducerPage(r,1).update);assert.equal(await draw(changed[1]),replacement);assert.equal(d.uploads,2);
checks.push('changed resource version replaces texture once and shares replacement across pages');
const selected=selectProducerPage(r,2),pending=s.update(selected.update);
selected.update.scene.arena.xs[0]=999;selected.update.metadata.leafIds[0]='wrong';selected.update.tiles.get('glyph-0').uv.fill(0);selected.update.resources[0].bytes.fill(0);
await pending;assert.equal(await draw(changed[2]),replacement);
const again=selectProducerPage(r,2);assert.deepEqual(values(again.update),changed[2]);assert.equal(again.update.metadata.leafIds[0],'leaf-2');assert.equal(again.update.resources[0].bytes[0],77);
checks.push('selected output mutation cannot alter prepared pages or committed session snapshot');
d.auto=false;const receipt=await s.render(view);let completed=false;receipt.completion.then(()=>completed=true);await Promise.resolve();assert.equal(completed,false);
s.cancel();assert.equal(s.generation,null);assert.throws(()=>s.render(view),/No completed update/);assert.equal(replacement.destroyed,0);
const disposal=s.dispose();assert.equal(s.dispose(),disposal);let drained=false;disposal.then(()=>drained=true);await Promise.resolve();assert.equal(drained,false);
d.flush();await receipt.completion;await disposal;assert.equal(completed,true);assert(d.resources.every(x=>x.destroyed===1));
checks.push('cancel and idempotent disposal retain final page submission until completion then destroy once');
console.log(JSON.stringify({passed:true,checks,synthetic_only:true,native_producer_qualified:false,performance_claim:false}));
