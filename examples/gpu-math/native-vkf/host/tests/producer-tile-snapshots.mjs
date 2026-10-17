import assert from 'node:assert/strict';
import {fixture} from './columns-fixture.mjs';
import {beginProvenance} from '../latex_operation_binding.mjs';
const baseline=process.argv[2]==='baseline';
const api=await import(baseline?'../baseline333.mjs':'../document_producer_adapter.mjs');
const checks=[],counts=[];
function test(name,fn){fn();checks.push(name);}
function glyphs(distinct=2){
 const f=fixture(3),a=f.result.document.arena;
 const tile=f.options.tiles.get('glyph-1');
 f.options.tiles=new Map([['shared-a',tile],['shared-b',{...tile,uv:new Float64Array([0.25,0,0.75,1])}]]);
 for(let i=0;i<a.count;i++){
  a.kinds[i]=i%2;a.keys[i]=distinct===2&&i%3===2?'shared-b':'shared-a';a.payloads[i]=-1;
  const leaf=f.owner.scopes[0].operations[i].leaves[0];delete leaf.link;leaf.resources=['resource-1'];
 }
 f.options.page=1;return f;
}
function prepare(f){return api.prepareProducerDocument(f.result,beginProvenance(f.owner),f.options);}
// Instrument only synchronous page selections, delegating every call unchanged.
function measured(fn){
 const native=globalThis.structuredClone;let tiles=0;
 globalThis.structuredClone=function(...args){const v=args[0];if(v?.resourceId&&v.plane instanceof Float64Array&&v.uv instanceof Float64Array)tiles++;return Reflect.apply(native,this,args);};
 try{return {value:fn(),tiles};}finally{globalThis.structuredClone=native;}
}
test('repeated glyph occurrences snapshot each unique key once per selected page',()=>{
 for(const unique of [1,2]){
  const f=glyphs(unique),prepared=prepare(f),m=measured(()=>api.selectProducerPage(prepared,1));
  assert.equal(m.tiles,baseline?3:unique);assert.equal(m.value.update.tiles.size,unique);
  assert.deepEqual([...m.value.update.tiles.keys()],unique===1?['shared-a']:['shared-a','shared-b']);
  for(const [key,tile] of m.value.update.tiles)assert.deepEqual(tile,f.options.tiles.get(key));
  counts.push({glyphOccurrences:3,uniqueKeys:unique,tileClones:m.tiles});
 }
});
test('distinct tile keys preserve exact tile and resource identities',()=>{
 const f=glyphs(),p=prepare(f);assert.deepEqual(p.update.scene.arena.keys,['shared-a','shared-a','shared-b']);
 assert.equal(p.update.tiles.get('shared-a').resourceId,'resource-1');assert.equal(p.update.tiles.get('shared-b').resourceId,'resource-1');
 assert.notDeepEqual(p.update.tiles.get('shared-a').uv,p.update.tiles.get('shared-b').uv);
 assert.deepEqual(p.update.resources.map(r=>[r.id,r.version]),[['resource-1',0]]);
});
test('missing repeated or distinct explicit glyph keys reject',()=>{
 for(const key of ['shared-a','shared-b']){const f=glyphs();f.options.tiles.delete(key);assert.throws(()=>prepare(f),/glyph|tile/i);}
});
test('mutated returned tiles and input tiles cannot alter retained selection',()=>{
 const f=glyphs(),p=prepare(f),expected=structuredClone(p.update.tiles);
 for(const t of p.update.tiles.values()){t.uv.fill(99);t.plane.fill(99);t.resourceId='bad';}p.update.tiles.clear();
 for(const t of f.options.tiles.values())t.uv.fill(88);f.options.tiles.clear();
 assert.deepEqual(api.selectProducerPage(p,1).update.tiles,expected);
});
test('two page outputs with shared keys remain independently mutable',()=>{
 const p=prepare(glyphs()),q=api.selectProducerPage(p,2),expected=structuredClone(q.update.tiles);
 assert.deepEqual(p.update.tiles,q.update.tiles);
 for(const key of p.update.tiles.keys()){assert.notEqual(p.update.tiles.get(key),q.update.tiles.get(key));assert.notEqual(p.update.tiles.get(key).uv.buffer,q.update.tiles.get(key).uv.buffer);p.update.tiles.get(key).uv.fill(33);}
 assert.deepEqual(q.update.tiles,expected);q.update.tiles.get('shared-a').plane.fill(55);
 assert.deepEqual(api.selectProducerPage(p,2).update.tiles,expected);
});
console.log(JSON.stringify({passed:true,checks,counts,synthetic_only:true}));
