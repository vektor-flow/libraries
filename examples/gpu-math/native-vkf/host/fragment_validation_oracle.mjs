import {bindOperationFragment} from './latex_operation_binding.mjs';
import {createFinalObservationBinding} from './latex_final_observation.mjs';
import {sceneColumns} from './document_scene_bridge.mjs';
import {createRetainedSceneBridge} from './document_resource_bridge.mjs';
const check=(ok,message)=>{if(!ok)throw Error(message);};
const integer=x=>Number.isSafeInteger(x)&&x>=0;
const sequence=x=>Array.isArray(x)||ArrayBuffer.isView(x)&&!(x instanceof DataView)&&!(typeof SharedArrayBuffer!=='undefined'&&x.buffer instanceof SharedArrayBuffer);
const empty=x=>sequence(x)&&x.length===0;
const finalObservation=createFinalObservationBinding(),prepared=new WeakMap();
/** Decoded latex_library.Fragment (text_owned/math_owned) subset, no layout or
 * parser invocation. Owner session must precede production. Glyph/field/rule/link
 * only, without anchors/destinations. No document/page identity is synthesized.
 * previous is the exact returned full Fragment bound, scoped to this adapter.
 * Extents remain baseline-relative; update.height is height + depth, no translation.
 */
export function prepareProducerFragment(result,owner,{tiles=new Map(),resources=[],previous=null}={}){
 check(result?.complete===true&&result.diagnostics===''&&result.pending_count===0,'Incomplete fragment producer result');
 const s=result.scene,a=s?.arena,n=a?.count;
 check(integer(n),'Missing fragment arena');
 const extents=['width','height','depth','tag_width'].map(k=>s[k]);
 check(extents.every(x=>Number.isFinite(x)&&x>=0)&&s.width>0&&s.height+s.depth>0&&Number.isFinite(s.height+s.depth)&&s.inline_destinations===false,'Unsupported fragment dimensions/mode');
 check(s.anchor_count===0&&['anchor_ids','anchor_xs','anchor_ys','anchor_lines','anchor_roots'].every(k=>empty(s[k])),'Unsupported fragment anchor provenance');
 const origins=result.a272_anchor_origins;
 check(origins&&typeof origins.scope==='string'&&typeof origins.text==='string'&&['ids','operations','starts','stops'].every(k=>empty(origins[k])),'Unsupported fragment anchor origins');
 for(const [key,columns] of Object.entries({a277_anchor_placements:['scenes'],a280_anchor_receipts:['leaves','slots'],a282_point_receipts:['points'],a283_final_anchors:['leaves','slots','points']}))
  check(result[key]&&columns.every(k=>empty(result[key][k])),'Unsupported fragment anchor receipt');
 check(integer(result.a277_anchor_placements.scene_count),'Unsupported fragment anchor placement');
 check(empty(a.destination_ids),'Unsupported fragment destinations');
 for(const key of ['destination_firsts','destination_counts'])check(sequence(a[key])&&a[key].length===n&&Array.from(a[key]).every(x=>x===0),'Unsupported fragment destinations');
 const column=(key,predicate,Type=null)=>{
  const c=a[key];check(sequence(c)&&c.length===n,'Invalid column extent '+key);
  const out=Type===null?null:new Type(n);
  for(let i=0;i<n;i++){check(predicate(c[i]),'Invalid column type '+key);if(out!==null)out[i]=c[i];}
  return out;
 };
 for(const k of ['a260_scopes','a260_texts'])column(k,x=>typeof x==='string');
 for(const k of ['a260_operations','a260_starts','a260_stops','a260_parts'])column(k,integer);
 const arena={count:n};
 for(const k of ['xs','ys','sxs','sys','widths','heights'])arena[k]=column(k,x=>Number.isFinite(x)&&(!['widths','heights'].includes(k)||x>=0),Float64Array);
 for(const k of ['kinds','paints','payloads'])arena[k]=column(k,x=>Number.isInteger(x)&&x>=-2147483648&&x<=2147483647,Int32Array);
 check(arena.kinds.every(k=>k>=0&&k<=3),'Unsupported fragment leaf provenance/resource mapping');
 arena.keys=column('keys',x=>typeof x==='string',Array);
 arena.draws=column('draws',x=>x===true||x===1,Uint8Array);
 check(Array.isArray(a.paint_table)&&a.paint_count===a.paint_table.length&&Array.isArray(a.payload_table)&&a.payload_count===a.payload_table.length,'Invalid table extents');
 arena.paint_table=structuredClone(a.paint_table);arena.payload_table=structuredClone(a.payload_table);
 check(tiles instanceof Map&&Array.isArray(resources),'Invalid resource transport');
 // Reject shared resource memory before cloning. Existing retained bridge validates
 // exact descriptors/bytes and same-version changes; no second resource algorithm.
 for(const r of resources)check(r?.bytes instanceof Uint8Array&&!(typeof SharedArrayBuffer!=='undefined'&&r.bytes.buffer instanceof SharedArrayBuffer),'Invalid resource payload');
 const prior=previous===null?null:prepared.get(previous);
 check(previous===null||prior,'Previous prepared fragment bound required');
 const bound=bindOperationFragment(structuredClone(result),owner,previous);
 if(prior&&extents.some((x,i)=>!Object.is(x,prior.extents[i]))){
  const oldGroups=new Map(previous.metadata.groups.map(g=>[g.id,g]));
  for(const g of bound.metadata.groups){const old=oldGroups.get(g.id);check(!old||g.layoutVersion>old.layoutVersion,'Fragment extent edit requires layout version');}
 }
 const update={complete:true,diagnostics:[],unresolved:[],scene:{arena},metadata:structuredClone(bound.metadata),tiles:structuredClone(tiles),resources:structuredClone(resources),width:s.width,height:s.height+s.depth};
 const packet=sceneColumns(update.scene,update.metadata,update.tiles);
 const bridge=createRetainedSceneBridge();
 try{
  if(prior){const u=prior.update;bridge.commitScene(u.scene,u.metadata,u.tiles,u.resources).release();}
  bridge.commitScene(update.scene,update.metadata,update.tiles,update.resources).release();
 }finally{bridge.dispose();}
 // No state is issued until every validation and snapshot succeeds. Retained
 // state is independent of both mutable output and the caller's original ABI.
 const retained={extents:[...extents],update:structuredClone(update)};
 finalObservation(bound,packet,previous);
 prepared.set(bound,retained);
 return Object.freeze({bound,extent:Object.freeze({width:s.width,height:s.height,depth:s.depth,tagWidth:s.tag_width}),update:Object.freeze(update)});
}
