import assert from 'node:assert/strict';
import {sceneColumns as oracle} from './direct-columns-oracle/document_scene_bridge.mjs';
import {sceneColumns as candidate} from '../document_scene_bridge.mjs';
import {prepareTypedPacket} from './direct-columns-oracle/document_typed_bridge.mjs';
const checks=[];
function fixture(kinds){
 const n=kinds.length,a={count:n,kinds:Int32Array.from(kinds),keys:Array(n).fill('tile'),paints:new Int32Array(n).fill(-1),payloads:new Int32Array(n).fill(-1),draws:new Uint8Array(n).fill(1),paint_table:[],payload_table:[]};
 for(const key of ['xs','ys','sxs','sys','widths','heights'])a[key]=new Float64Array(n).fill(key==='widths'||key==='heights'?4:1);
 const sources=[],resources=[],links=[],images=[];let count=0;
 for(let i=0;i<n;i++){
  const k=kinds[i];let p=null,rows=1;
  if(k===3)p={border_width:1,target:'url'};
  if(k===4)p={asset:'image'};
  if(k===5||k===6)p={dx:3,dy:2,line_width:1,dash:0,c1x:1,c1y:2,c2x:3,c2y:4};
  if(k===7||k===8){p={fill:true,line_width:1,dash:k===8?1:0,fill_paint:-1,stroke_paint:-1};rows=k===8?5:2;}
  if(p){a.payloads[i]=a.payload_table.length;a.payload_table.push(p);}
  for(let j=0;j<rows;j++){sources.push(i);resources.push(k<2||k===4?['atlas']:[]);}
  if(k===3)links.push({leaf:count,target:'url'});
  if(k===4)images.push({leaf:count,asset:'image',resourceId:'atlas'});
  count+=rows;
 }
 const metadata={documentId:'d',revision:0,leafIds:Array.from({length:count},(_,i)=>'l'+i),groups:[{id:'g',first:0,count,contentVersion:0,layoutVersion:0,dependencies:[]}],resources:[{id:'atlas',version:0}],leafResources:resources,links,images,sourceLeafIds:Array.from({length:n},(_,i)=>'s'+i),drawSources:sources};
 return {scene:{arena:a},metadata,tiles:new Map([['tile',{resourceId:'atlas',plane:new Float64Array([-0,-0,4,4]),uv:new Float64Array([-0,0,1,1])}]])};
}
function evaluate(fn,f){try{return {packet:fn(f.scene,f.metadata,f.tiles)}}catch(e){return {error:[e.name,e.message]}}}
function compare(name,f,invalid=false){
 const b=evaluate(oracle,structuredClone(f)),c=evaluate(candidate,structuredClone(f));
 assert.deepEqual(c.error,b.error,name);
 if(invalid)assert.ok(c.error,name);else{
  assert.ok(c.packet,name);assert.deepEqual(c.packet,b.packet);
  for(let j=0;j<16;j++)assert.deepEqual(new Uint8Array(c.packet.columns[j].buffer),new Uint8Array(b.packet.columns[j].buffer));
  assert.deepEqual(prepareTypedPacket(c.packet),prepareTypedPacket(b.packet));
  assert.equal(new Set(c.packet.columns.map(x=>x.buffer)).size,16);
 }
 checks.push(name);return c.packet;
}
for(const k of [0,1,2,3])compare('single kind '+k,fixture([k,k]));
compare('empty',fixture([]));compare('mixed fixed',fixture([0,1,2,3]));
for(const k of [4,5,6,7,8])compare('fallback kind '+k,fixture([k]));
compare('mixed variable mapping',fixture([7,0,8,3,1,2,4,5,6]));
let f=fixture([0,1]);f.scene.arena.payloads[0]=f.scene.arena.payload_table.length;f.scene.arena.payload_table.push({crop_x:true,crop_left:true,left:1,crop_right:false,crop_y:true,crop_top:false,crop_bottom:true,bottom:3});compare('crop endpoint presence',f);
f=fixture([3]);f.scene.arena.payload_table[0].border_width=0;compare('zero link border',f);
f=fixture([0,1]);for(const key of ['xs','ys','sxs','sys'])f.scene.arena[key].fill(-0);compare('signed zero bytes',f);
const bad=[
 ['geometry NaN',f=>f.scene.arena.xs[0]=NaN],['geometry overflow',f=>f.scene.arena.xs[0]=1e21],
 ['invalid kind',f=>f.scene.arena.kinds[0]=99],['negative kind',f=>f.scene.arena.kinds[0]=-1],
 ['paint reference',f=>f.scene.arena.paints[0]=0],['payload reference',f=>f.scene.arena.payloads[0]=99],['draw flag',f=>f.scene.arena.draws[0]=0],
 ['resource',f=>f.metadata.leafResources[0]=[]],['tile extent',f=>f.tiles.get('tile').plane[2]=0],['tile uv',f=>f.tiles.get('tile').uv[0]=NaN],
 ['paint value',f=>{f.scene.arena.paints[0]=0;f.scene.arena.paint_table.push({red:NaN,green:0,blue:0,alpha:1});}],
 ['crop malformed',f=>{f.scene.arena.payloads[0]=f.scene.arena.payload_table.length;f.scene.arena.payload_table.push({crop_x:true,crop_left:1});}],
 ['crop empty',f=>{f.scene.arena.payloads[0]=f.scene.arena.payload_table.length;f.scene.arena.payload_table.push({crop_x:true,crop_left:true,left:5,crop_right:false});}],
 ['mapping',f=>f.metadata.drawSources[0]=1],['metadata extent',f=>f.metadata.leafIds.pop()],
 ['validation order',f=>{f.scene.arena.xs[0]=NaN;f.scene.arena.kinds[0]=99;}]
];
for(const [name,mutate] of bad){f=fixture([0,1,2,3]);mutate(f);compare(name,f,true);}
f=fixture([0,1,2,3]);const p=candidate(f.scene,f.metadata,f.tiles),saved=structuredClone(p);f.scene.arena.xs.fill(99);f.tiles.get('tile').uv.fill(.5);assert.deepEqual(p,saved);const q=candidate(f.scene,f.metadata,f.tiles);q.columns[0].fill(13);assert.deepEqual(p,saved);p.columns[0][0]=88;assert.equal(p.columns[1][0],saved.columns[1][0]);checks.push('independent output and caller lifetime');
console.log(JSON.stringify({passed:true,checks,groups:checks.length}));
