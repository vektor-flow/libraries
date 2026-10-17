import assert from 'node:assert/strict';
import {sceneColumns as oracle} from './glyph-emission-oracle/document_scene_bridge.mjs';
import {sceneColumns as candidate} from '../document_scene_bridge.mjs';
import {prepareTypedPacket} from './glyph-emission-oracle/document_typed_bridge.mjs';
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

for(const kind of [0,1]){
 const fixed=fixture([kind]),mixed=fixture([kind,5]);
 const a=compare('fixed glyph '+kind,fixed),b=compare('mixed glyph '+kind,mixed);
 for(let j=0;j<16;j++)assert.deepEqual(new Uint8Array(a.columns[j].buffer),new Uint8Array(b.columns[j].slice(0,1).buffer));
 for(const kinds of [[kind],[kind,5]]){
  const f=fixture(kinds);f.scene.arena.payloads[0]=f.scene.arena.payload_table.length;
  f.scene.arena.payload_table.push({crop_x:true,crop_left:true,left:NaN});
  compare('malformed crop '+kinds.join(','),f,true);
 }
}
function observed(fn){
 const f=fixture([0,1]),trace=[];
 for(const key of ['sxs','sys']){const v=f.scene.arena[key];Object.defineProperty(f.scene.arena,key,{get(){trace.push(key);return v;}});}
 const paint={};for(const [key,value] of Object.entries({red:0,green:.25,blue:.5,alpha:1}))Object.defineProperty(paint,key,{get(){trace.push(key);return value;}});
 f.scene.arena.paint_table.push(paint);f.scene.arena.paints.fill(0);
 const p={};for(const [key,value] of Object.entries({crop_x:true,crop_left:true,left:1,crop_right:false,crop_y:false}))Object.defineProperty(p,key,{get(){trace.push(key);return value;}});
 f.scene.arena.payload_table.push(p);f.scene.arena.payloads.fill(0);
 return {packet:fn(f.scene,f.metadata,f.tiles),trace};
}
assert.deepEqual(observed(candidate),observed(oracle));checks.push('observable property evaluation order');
console.log(JSON.stringify({passed:true,checks,groups:checks.length}));
