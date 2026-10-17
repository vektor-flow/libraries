import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {fixture} from './columns-fixture.mjs';
import {prepareProducerFragment} from '../fragment_producer_adapter.mjs';
import {beginProvenance,bindOperationFragment} from '../latex_operation_binding.mjs';
import {sceneColumns} from '../document_scene_bridge.mjs';
import {prepareTypedPacket} from '../document_typed_bridge.mjs';
import {createRetainedSceneBridge} from '../document_resource_bridge.mjs';
const checks=[],test=(name,fn)=>{fn();checks.push(name);};
const schema=JSON.parse(readFileSync(new URL('./fixtures/fragment-schema.json',import.meta.url)));
// Synthetic decoded ABI, field names extracted from sealed A283 library source.
// This is not native producer output. Owner IDs are explicit inputs before bind.
function fresh(){
 const f=fixture(1),arena=f.result.document.arena;
 arena.destination_firsts=[0,0,0];arena.destination_counts=[0,0,0];
 f.owner.groups[2].edges=[];
 const scene=Object.fromEntries(schema.Scene.map(k=>[k,[]]));
 Object.assign(scene,{arena,anchor_count:0,anchor_metadata:{kinds:[],ends:[],texts:[],numbers:[],count:0},width:100,height:80,depth:20,tag_width:0,inline_destinations:false});
 f.result={scene,complete:true,diagnostics:'',pending_count:0,a272_anchor_origins:{scope:'parse',text:'x',ids:[],operations:[],starts:[],stops:[]},a277_anchor_placements:{scenes:[],scene_count:3},a280_anchor_receipts:{leaves:[],slots:[]},a282_point_receipts:{points:[]},a283_final_anchors:{leaves:[],slots:[],points:[]}};
 delete f.options.page;return f;
}
const prepare=(f,previous=null)=>prepareProducerFragment(f.result,beginProvenance(f.owner),{...f.options,previous});
const packet=p=>prepareTypedPacket(sceneColumns(p.update.scene,p.update.metadata,p.update.tiles)).bytes;
const bump=f=>{f.owner.revision++;for(const g of f.owner.groups)g.layoutVersion++;};
// Independent frozen row oracle: glyph, rule, link, matching hand-authored geometry.
const expected=Object.freeze([
 Object.freeze([0,0,1,1,0,0,1,1,0,0,0,1,0,0,0,0]),
 Object.freeze([0,-1,5,6,0,0,0,0,0,0,0,1,1,3,4,0]),
 Object.freeze([0.5,-1.5,6,7,0,0,0,0,0,0,0,1,1,4,5,1])
]);
test('fragment exact schema and independent typed row transport',()=>{
 const f=fresh();assert.deepEqual(Object.keys(f.result).sort(),[...schema.Fragment].sort());
 const p=prepare(f),bound=bindOperationFragment(f.result,beginProvenance(f.owner));
 assert.deepEqual(p.bound.metadata,bound.metadata);assert.deepEqual(p.bound.sourceBinding,bound.sourceBinding);
 const columns=sceneColumns(p.update.scene,p.update.metadata,p.update.tiles).columns;
 for(let i=0;i<3;i++)assert.deepEqual(columns.map(c=>c[i]),expected[i]);
 assert.deepEqual(p.extent,{width:100,height:80,depth:20,tagWidth:0});assert.equal(p.update.height,100);
 assert.equal(p.bound.scene.arena.count,3);assert.equal(p.bound.document,undefined);assert.equal(p.page,undefined);
 const bridge=createRetainedSceneBridge(),u=p.update,l=bridge.commitScene(u.scene,u.metadata,u.tiles,u.resources);
 assert.deepEqual(l.bytes(),packet(p));assert.equal(l.resource('resource-0')[3],255);l.release();bridge.dispose();
});
test('repeated fragment revisions retain full authentic identity and source binding',()=>{
 const f=fresh(),p=prepare(f);f.owner.revision++;const q=prepare(f,p.bound);f.owner.revision++;const r=prepare(f,q.bound);
 assert.deepEqual(r.bound.invalidated,[]);assert.deepEqual(packet(r),packet(p));assert.deepEqual(r.bound.sourceBinding,p.bound.sourceBinding);
 assert.deepEqual(r.bound.metadata.leafIds,['leaf-0','leaf-1','leaf-2']);
 assert.throws(()=>prepare(f,r.bound),/Revision/);
});
const mutations={tileUV:f=>f.options.tiles.get('glyph-0').uv[2]=0.75,plane:f=>f.options.tiles.get('glyph-0').plane[2]=2,paint:f=>{const a=f.result.scene.arena;a.paint_table=[{red:1,green:0,blue:0,alpha:1}];a.paint_count=1;a.paints[0]=0;},crop:f=>{const a=f.result.scene.arena;a.payload_table.push({crop_x:true,crop_left:true,left:0.25,crop_right:false});a.payload_count++;a.payloads[0]=1;}};
for(const [name,mutate] of Object.entries(mutations))test(name+' stale fragment output rejected with dependency advancement',()=>{
 const f=fresh(),p=prepare(f),before=packet(p);f.owner.revision++;mutate(f);
 assert.throws(()=>prepare(f,p.bound),/Typed output edit/);
 f.owner.groups[0].layoutVersion++;assert.throws(()=>prepare(f,p.bound),/Affected group/);
 f.owner.groups[1].layoutVersion++;const q=prepare(f,p.bound);
 assert.notDeepEqual(packet(q),before);assert.deepEqual(q.bound.invalidated,['group-0','group-1']);
 assert.deepEqual(q.bound.sourceBinding,p.bound.sourceBinding);assert.deepEqual(packet(p),before);
 f.owner.revision++;assert.deepEqual(prepare(f,q.bound).bound.invalidated,[]);
});
test('source text changes require source content layout and dependency revisions',()=>{
 const f=fresh(),p=prepare(f);f.owner.revision++;f.owner.sources[0].text='y';f.owner.scopes[0].text='y';f.result.scene.arena.a260_texts.fill('y');
 assert.throws(()=>prepare(f,p.bound),/Source changed/);f.owner.sources[0].version++;
 assert.throws(()=>prepare(f,p.bound),/Source edit/);
 for(const g of f.owner.groups){g.contentVersion++;g.layoutVersion++;}
 const q=prepare(f,p.bound);assert.equal(q.bound.sourceBinding.sources[0].text,'y');assert.deepEqual(q.bound.metadata.leafIds,p.bound.metadata.leafIds);
});
test('extent observations require layout advance and unsupported dimensions reject',()=>{
 for(const key of ['width','height','depth','tag_width']){const f=fresh(),p=prepare(f);f.owner.revision++;f.result.scene[key]++;assert.throws(()=>prepare(f,p.bound),/extent edit/);for(const g of f.owner.groups)g.layoutVersion++;assert(prepare(f,p.bound));}
 for(const [key,value] of [['width',0],['height',-1],['depth',NaN],['tag_width',Infinity],['inline_destinations',true]]){const f=fresh();f.result.scene[key]=value;assert.throws(()=>prepare(f),/dimensions/);}
});
test('resource bytes descriptors versions and missing payloads remain guarded',()=>{
 const f=fresh(),p=prepare(f);f.owner.revision++;f.options.resources[0].bytes[0]=4;
 assert.throws(()=>prepare(f,p.bound),/Immutable resource/);
 f.options.resources[0].version++;f.owner.resources[0].version++;
 assert.throws(()=>prepare(f,p.bound),/Affected group/);for(const g of f.owner.groups)g.layoutVersion++;
 const q=prepare(f,p.bound);assert.equal(q.update.resources[0].bytes[0],4);
 const bad=fresh();bad.options.resources=[];assert.throws(()=>prepare(bad),/Missing resource/);
 const desc=fresh(),d=prepare(desc);desc.owner.revision++;desc.options.resources[0].image.width=2;assert.throws(()=>prepare(desc,d.bound),/descriptor/);
});
test('owner sessions spans and all provenance columns are mandatory',()=>{
 const f=fresh();assert.throws(()=>prepareProducerFragment(f.result,f.owner,f.options),/Entry owner/);
 for(const key of ['a260_scopes','a260_texts','a260_operations','a260_starts','a260_stops','a260_parts']){
  const g=fresh();delete g.result.scene.arena[key];assert.throws(()=>prepare(g),/extent/);
 }
 for(const [key,value] of [['a260_scopes','missing'],['a260_texts','wrong'],['a260_operations',99],['a260_starts',1],['a260_stops',0],['a260_parts',99]]){const g=fresh();g.result.scene.arena[key][0]=value;assert.throws(()=>prepare(g));}
});
test('unsupported incomplete anchor destination and leaf state rejected',()=>{
 for(const edit of [f=>f.result.complete=false,f=>f.result.diagnostics='warning',f=>f.result.pending_count=1,f=>f.result.scene.anchor_count=1,f=>f.result.scene.arena.destination_ids=['a'],f=>f.result.a283_final_anchors.leaves=[0],f=>f.result.scene.arena.kinds[0]=8,f=>f.result.scene.arena.widths[0]=-1]){const f=fresh();edit(f);assert.throws(()=>prepare(f));}
});
test('caller output and bound scene mutation cannot rewrite retained observations',()=>{
 const f=fresh(),p=prepare(f),expectedBytes=packet(p);f.result.scene.arena.xs[0]=77;assert.equal(p.bound.scene.arena.xs[0],0);
 p.bound.scene.arena.xs[0]=88;p.update.scene.arena.xs[0]=99;p.update.tiles.get('glyph-0').uv.fill(0);p.update.resources[0].bytes.fill(0);
 const g=fresh();g.owner.revision++;const q=prepare(g,p.bound);assert.deepEqual(packet(q),expectedBytes);assert.equal(q.update.resources[0].bytes[3],255);
 mutations.tileUV(g);g.owner.revision++;assert.throws(()=>prepare(g,q.bound),/Typed output/);
});
test('copied raw and foreign predecessors rejected without poisoning authentic branch',()=>{
 const f=fresh(),p=prepare(f);f.owner.revision++;
 for(const previous of [{...p.bound},bindOperationFragment(f.result,beginProvenance(f.owner))])assert.throws(()=>prepare(f,previous),/Previous prepared/);
 const bad=structuredClone(f);bad.result.scene.arena.a260_stops[0]=0;assert.throws(()=>prepare(bad,p.bound));
 assert.deepEqual(prepare(f,p.bound).bound.invalidated,[]);
});
test('reordered explicit owner leaves preserve source to row mapping',()=>{
 const f=fresh(),p=prepare(f),a=f.result.scene.arena;
 for(const [k,v] of Object.entries(a))if(Array.isArray(v)&&v.length===3&&!['paint_table','payload_table'].includes(k))a[k]=[v[2],v[0],v[1]];
 bump(f);const q=prepare(f,p.bound);
 assert.deepEqual(q.bound.metadata.leafIds,['leaf-2','leaf-0','leaf-1']);assert.deepEqual(q.bound.sourceBinding.leaves.map(l=>l.id),q.bound.metadata.leafIds);
 const columns=sceneColumns(q.update.scene,q.update.metadata,q.update.tiles).columns;
 for(let i=0;i<3;i++)assert.deepEqual(columns.map(c=>c[i]),expected[[2,0,1][i]]);
});
console.log(JSON.stringify({passed:true,checks,synthetic_only:true,native_producer_qualified:false}));
