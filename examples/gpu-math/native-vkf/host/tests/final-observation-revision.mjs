import assert from 'node:assert/strict';
import {fixture} from './columns-fixture.mjs';
import {beginProvenance,reviseProvenance} from '../latex_operation_binding.mjs';
import {prepareProducerDocument} from '../document_producer_adapter.mjs';
import {sceneColumns} from '../document_scene_bridge.mjs';
import {prepareTypedPacket} from '../document_typed_bridge.mjs';
const checks=[];const test=(name,f)=>{f();checks.push(name);};
const packet=p=>prepareTypedPacket(sceneColumns(p.update.scene,p.update.metadata,p.update.tiles)).bytes;
function start(){const f=fixture(1);const owner=beginProvenance(f.owner);return {f,owner,p:prepareProducerDocument(f.result,owner,f.options)};}
function delta(owner,revision){return {revision,sources:[],scopes:[],groups:owner.groups.map(g=>({...g,contentVersion:revision,layoutVersion:revision,layoutKey:g.id+'-'+revision}))};}
test('certified second edit through guarded adapter equals full fresh and advances dependencies',()=>{
 let {f,owner,p}=start();const initial=packet(p);
 for(let revision=1;revision<=2;revision++){
  const d=delta(owner,revision);owner=reviseProvenance(owner,d);f.options.tiles.get('glyph-0').uv[2]=1-revision/4;
  const q=prepareProducerDocument(f.result,owner,{...f.options,previous:p.bound});
  const fresh=prepareProducerDocument(f.result,beginProvenance(structuredClone(owner)),f.options);
  assert.deepEqual(packet(q),packet(fresh));assert.deepEqual(q.bound.metadata,fresh.bound.metadata);assert.deepEqual(q.bound.sourceBinding,fresh.bound.sourceBinding);
  assert.deepEqual(q.bound.invalidated,['group-0','group-1','group-2']);assert(q.bound.metadata.groups.every(g=>g.layoutVersion===revision));
  assert.deepEqual(q.bound.metadata.leafIds,p.bound.metadata.leafIds);p=q;
 }
 assert.notDeepEqual(packet(p),initial);
 const stable=reviseProvenance(owner,{revision:3,sources:[],scopes:[],groups:[]});
 const q=prepareProducerDocument(f.result,stable,{...f.options,previous:p.bound});assert.deepEqual(q.bound.invalidated,[]);assert.deepEqual(packet(q),packet(p));
});
test('certified retained chain rejects stale tileUV plane paint crop and incomplete dependency advancement',()=>{
 const mutations=[f=>f.options.tiles.get('glyph-0').uv[2]=.5,f=>f.options.tiles.get('glyph-0').plane[2]=2,f=>{const a=f.result.document.arena;a.paint_table=[{red:1,green:0,blue:0,alpha:1}];a.paint_count=1;a.paints[0]=0;},f=>{const a=f.result.document.arena;a.payload_table.push({crop_x:true,crop_left:true,left:.25,crop_right:false});a.payload_count++;a.payloads[0]=1;}];
 for(const mutate of mutations){let {f,owner,p}=start();owner=reviseProvenance(owner,{revision:1,sources:[],scopes:[],groups:[]});p=prepareProducerDocument(f.result,owner,{...f.options,previous:p.bound});
  const stale=reviseProvenance(owner,{revision:2,sources:[],scopes:[],groups:[]});mutate(f);
  assert.throws(()=>prepareProducerDocument(f.result,stale,{...f.options,previous:p.bound}),/Typed output edit requires layout version/);
  const incomplete=delta(owner,2);incomplete.groups=incomplete.groups.slice(0,1);
  assert.throws(()=>reviseProvenance(owner,incomplete),/dependent group/);
  const advanced=reviseProvenance(owner,delta(owner,2));const q=prepareProducerDocument(f.result,advanced,{...f.options,previous:p.bound});
  const fresh=prepareProducerDocument(f.result,beginProvenance(structuredClone(advanced)),f.options);assert.deepEqual(packet(q),packet(fresh));assert.deepEqual(q.bound.invalidated,['group-0','group-1','group-2']);
 }
});
console.log(JSON.stringify({passed:true,checks,synthetic_only:true}));
