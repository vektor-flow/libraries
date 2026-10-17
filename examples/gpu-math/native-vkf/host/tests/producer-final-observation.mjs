import assert from 'node:assert/strict';
import {fixture} from './columns-fixture.mjs';
const baseline=process.argv[2]==='baseline';
const root=baseline?'../../base/':'../';
const api=await import(root+'document_producer_adapter.mjs');
const {beginProvenance,bindOperationDocument}=await import(root+'latex_operation_binding.mjs');
const {sceneColumns}=await import(root+'document_scene_bridge.mjs');
const {prepareTypedPacket}=await import(root+'document_typed_bridge.mjs');
const {createRetainedSceneBridge}=await import(root+'document_resource_bridge.mjs');
const checks=[];const test=(name,fn)=>{fn();checks.push(name);};
// Decoded host-synthetic typed ABI fixture; not native/parser output.
function fresh(){const f=fixture(1);f.owner.groups[2].edges=[];return f;}
function prepare(f,previous=null){return api.prepareProducerDocument(f.result,beginProvenance(f.owner),{...f.options,previous});}
function packet(p){return prepareTypedPacket(sceneColumns(p.update.scene,p.update.metadata,p.update.tiles)).bytes;}
const mutations={
 tileUV:f=>f.options.tiles.get('glyph-0').uv[2]=0.75,
 plane:f=>f.options.tiles.get('glyph-0').plane[2]=2,
 paint:f=>{const a=f.result.document.arena;a.paint_table=[{red:1,green:0,blue:0,alpha:1}];a.paint_count=1;a.paints[0]=0;},
 crop:f=>{const a=f.result.document.arena;a.payload_table.push({crop_x:true,crop_left:true,left:0.25,crop_right:false});a.payload_count++;a.payloads[0]=1;}
};
for(const [name,mutate] of Object.entries(mutations))test(name+': stale final change rejected; advanced dependency closure accepted',()=>{
 const f=fresh(),p=prepare(f),before=packet(p),source=p.bound.sourceBinding,unrelated=structuredClone(p.update.scene.arena);
 f.owner.revision=1;mutate(f);
 if(baseline){const stale=prepare(f,p.bound);assert.notDeepEqual(packet(stale),before);assert.deepEqual(stale.bound.invalidated,[]);}
 else assert.throws(()=>prepare(f,p.bound),/Typed output edit requires layout version/);
 f.owner.groups[0].layoutVersion=1;
 assert.throws(()=>prepare(f,p.bound),/Affected group requires new layout version/);
 f.owner.groups[1].layoutVersion=1;
 const q=prepare(f,p.bound);
 assert.deepEqual(q.bound.invalidated,['group-0','group-1']);assert.deepEqual(q.bound.sourceBinding,source);
 assert.deepEqual(q.bound.metadata.leafIds,p.bound.metadata.leafIds);assert.deepEqual(q.update.resources,p.update.resources);
 assert.equal(q.bound.metadata.groups[2].layoutVersion,0);
 for(const key of ['xs','ys','sxs','sys','widths','heights','kinds'])assert.deepEqual(q.update.scene.arena[key],unrelated[key]);
 assert.notDeepEqual(packet(q),before);assert.deepEqual(packet(p),before);
 const bridge=createRetainedSceneBridge();let u=p.update,l=bridge.commitScene(u.scene,u.metadata,u.tiles,u.resources);l.release();u=q.update;l=bridge.commitScene(u.scene,u.metadata,u.tiles,u.resources);assert.equal(l.count,3);l.release();bridge.dispose();
 f.owner.revision=2;const stable=prepare(f,q.bound);assert.deepEqual(stable.bound.invalidated,[]);assert.deepEqual(packet(stable),packet(q));
});
test('unchanged final bytes preserve identities across glyph lookup alias',()=>{
 const f=fresh(),p=prepare(f);f.owner.revision=1;f.options.tiles.set('alias',f.options.tiles.get('glyph-0'));f.options.tiles.delete('glyph-0');f.result.document.arena.keys[0]='alias';
 const q=prepare(f,p.bound);assert.deepEqual(q.bound.invalidated,[]);assert.deepEqual(packet(q),packet(p));assert.deepEqual(q.bound.sourceBinding,p.bound.sourceBinding);
});
test('caller and output mutations cannot rewrite previous observations or retained page',()=>{
 const f=fresh(),p=prepare(f),before=packet(p);p.update.scene.arena.xs.fill(99);p.update.tiles.get('glyph-0').uv.fill(0);p.update.resources[0].bytes.fill(0);
 f.owner.revision=1;mutations.tileUV(f);
 if(!baseline)assert.throws(()=>prepare(f,p.bound),/Typed output edit requires layout version/);
 assert.deepEqual(packet(api.selectProducerPage(p,0)),before);
 f.owner.groups[0].layoutVersion=1;f.owner.groups[1].layoutVersion=1;const q=prepare(f,p.bound);assert.notDeepEqual(packet(q),before);
});
test('off-page final changes validated against full document bound',()=>{
 const f=fixture(3);f.options.page=1;const p=prepare(f);f.owner.revision=1;f.options.tiles.get('glyph-2').uv[2]=0.5;
 if(baseline)assert.deepEqual(prepare(f,p.bound).bound.invalidated,[]);
 else assert.throws(()=>prepare(f,p.bound),/Typed output edit requires layout version/);
 for(const g of f.owner.groups.slice(3))g.layoutVersion=1;
 const q=prepare(f,p.bound);assert.deepEqual(packet(p),packet(q));assert.notDeepEqual(packet(api.selectProducerPage(p,2)),packet(api.selectProducerPage(q,2)));
});
test('copied and unobserved previous bounds cannot bypass guard; authentic owner required',()=>{
 const f=fresh(),p=prepare(f);f.owner.revision=1;
 assert.throws(()=>api.prepareProducerDocument(f.result,f.owner,{...f.options,previous:p.bound}),/Entry owner session required/);
 if(!baseline){
  assert.throws(()=>prepare(f,{...p.bound}),/Previous final observation bound required/);
  const raw=bindOperationDocument(f.result,beginProvenance(f.owner));f.owner.revision=2;
  assert.throws(()=>prepare(f,raw),/Previous final observation bound required/);
 }
});
test('fragment producer adapter is absent; no synthetic entry substituted',()=>assert.equal(api.prepareProducerFragment,undefined));
console.log(JSON.stringify({passed:true,checks,synthetic_only:true,baseline,fragmentAdapterSupported:false}));
