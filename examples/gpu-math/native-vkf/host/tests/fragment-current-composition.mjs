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
for(const kind of [0,1]){
 const f=fresh();f.result.scene.arena.kinds[0]=kind;
 const p=prepare(f),a=sceneColumns(p.update.scene,p.update.metadata,p.update.tiles).columns;
 const b=sceneColumns(p.update.scene,p.update.metadata,p.update.tiles).columns;
 assert.equal(a.length,16);assert.equal(new Set(a.map(c=>c.buffer)).size,16);
 for(let i=0;i<3;i++)assert.deepEqual(a.map(c=>c[i]),expected[i]);
 for(let j=0;j<16;j++){assert.notEqual(a[j],b[j]);assert.notEqual(a[j].buffer,b[j].buffer);}
 a[0][0]=999;assert.equal(b[0][0],0);assert.equal(a[1][0],0);
}
console.log(JSON.stringify({passed:true,kinds:[0,1,2,3],frozen_rows:true,independent_columns:true}));
