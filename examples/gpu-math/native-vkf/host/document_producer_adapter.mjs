import {bindOperationDocument} from './latex_operation_binding.mjs';
import {createFinalObservationBinding} from './latex_final_observation.mjs';
import {sceneColumns} from './document_scene_bridge.mjs';
const preparedDocuments=new WeakMap();
const bindFinalObservation=createFinalObservationBinding();
const check=(ok,msg)=>{if(!ok)throw Error(msg);};
const integer=x=>Number.isSafeInteger(x)&&x>=0;
const sequence=x=>Array.isArray(x)||ArrayBuffer.isView(x)&&!(x instanceof DataView)&&!(typeof SharedArrayBuffer!=='undefined'&&x.buffer instanceof SharedArrayBuffer);
/** C286 source-schema subset: explicitly selected page, no destinations, glyph/field/rule/link.
 * Input is a decoded typed ABI record, never a JSON serialization of layout.
 * Owner must be an authentic beginProvenance session issued before layout.
 * Output can be passed directly to installed E312 renderSession.update().
 * previous is the previous returned bound value, for source/version guards.
 */
export function prepareProducerDocument(result,owner,{tiles=new Map(),resources=[],previous=null,page}={}){
 check(result?.complete===true&&result.diagnostics===''&&result.unresolved_json==='[]','Incomplete producer result');
 const d=result.document,a=d?.arena,n=a?.count;
 check(integer(n)&&integer(d.page_count)&&d.page_count>0&&d.destination_count===0,'Unsupported page/destination provenance');
 check(page!==undefined||d.page_count===1,'Unsupported implicit multipage selection');
 page??=0;
 for(const key of ['destination_names','destination_pages','destination_xs','destination_ys'])check(sequence(d[key])&&d[key].length===0,'Unsupported destination provenance');
 for(const key of ['widths','heights'])check(sequence(d[key])&&d[key].length===d.page_count&&Array.from(d[key]).every(x=>Number.isFinite(x)&&x>0),'Invalid page dimensions');
 // Validate original values before writing a caller-independent snapshot.
 // A null constructor validates ownership columns without a discarded copy.
 const array=(key,predicate,Type=null)=>{
  const c=a[key];check(sequence(c)&&c.length===n,'Invalid column extent '+key);
  const out=Type===null?null:new Type(n);
  for(let i=0;i<n;i++){const value=c[i];check(predicate(value),'Invalid column type '+key);if(out!==null)out[i]=value;}
  return out;
 };
 for(const key of ['a260_scopes','a260_texts'])array(key,x=>typeof x==='string');
 for(const key of ['a260_operations','a260_starts','a260_stops','a260_parts'])array(key,integer);
 // Binding validates scope/text/span/part ownership, resource versions and page
 // coverage before projection or any render-session commit.
 const bound=bindOperationDocument(result,owner,previous);
 const arena={count:n};
 for(const key of ['xs','ys','sxs','sys','widths','heights'])arena[key]=array(key,Number.isFinite,Float64Array);
 for(const key of ['kinds','paints','payloads'])arena[key]=array(key,x=>Number.isInteger(x)&&x>=-2147483648&&x<=2147483647,Int32Array);
 check(Array.from(arena.kinds).every(x=>[0,1,2,3].includes(x)),'Unsupported leaf provenance/resource mapping');
 arena.keys=array('keys',x=>typeof x==='string',Array);
 arena.draws=array('draws',x=>x===true||x===1,Uint8Array);
 check(Array.isArray(a.paint_table)&&a.paint_count===a.paint_table.length&&Array.isArray(a.payload_table)&&a.payload_count===a.payload_table.length,'Invalid table extents');
 arena.paint_table=structuredClone(a.paint_table);arena.payload_table=structuredClone(a.payload_table);
 check(tiles instanceof Map&&Array.isArray(resources),'Invalid resource transport');
 const scene={arena},tileSnapshot=structuredClone(tiles),resourceSnapshot=structuredClone(resources);
 // Preserve exact resource IDs/versions/bytes; installed bridge owns immutable
 // admission and cross-update version checks. Reject shared memory before copy.
 const refs=new Map(bound.metadata.resources.map(r=>[r.id,r.version])),seen=new Set();
 for(const r of resources){check(r&&refs.has(r.id)&&!seen.has(r.id)&&r.version===refs.get(r.id)&&r.bytes instanceof Uint8Array&&!(typeof SharedArrayBuffer!=='undefined'&&r.bytes.buffer instanceof SharedArrayBuffer),'Invalid resource payload/version');seen.add(r.id);}
 check(seen.size===refs.size,'Missing resource payload');
 const finalColumns=sceneColumns(scene,bound.metadata,tileSnapshot);
 // Validate the entire directory and reject groups split across any page.
 for(const key of ['firsts','counts'])check(sequence(d[key])&&d[key].length===d.page_count&&Array.from(d[key]).every(integer),'Invalid page directory');
 const pages=Array.from(d.firsts,(first,i)=>({first,count:d.counts[i],width:d.widths[i],height:d.heights[i]}));
 const work={indexPages:0,indexLeaves:0,indexGroups:0,indexLinks:0,indexResources:0,indexResourceReferences:0,groupRangeChecks:0,selections:0,projectedGroupCopies:0};
 const indexes=pageIndexes(bound.metadata,pages,resourceSnapshot,work);
 const state={bound,arena,pages,indexes,work,tiles:tileSnapshot,resources:resourceSnapshot};
 const output=projectPage(state,page);
 bindFinalObservation(bound,finalColumns,previous);
 return output;
}

/** Select another page from an authenticated prepared document without pretending
 * that a page switch is a source revision. The bound value remains full-document.
 */
export function selectProducerPage(prepared,page){
 const state=preparedDocuments.get(prepared);
 check(state,'Prepared producer document required');
 return projectPage(state,page);
}
/** Adapter operation counts only: excludes binding, validation and output copying
 * outside the explicitly named counters. A detached snapshot cannot mutate state. */
export function producerPageWork(prepared){
 const state=preparedDocuments.get(prepared);check(state,'Prepared producer document required');
 return Object.freeze({...state.work});
}
function pageIndexes(m,pages,resources,work){
 const leafPages=new Int32Array(m.leafIds.length);
 const indexes=pages.map((p,page)=>{
  work.indexPages++;
  for(let i=p.first;i<p.first+p.count;i++){leafPages[i]=page;work.indexLeaves++;}
  return {groups:new Map(),links:[],metadataResources:[],resources:[]};
 });
 // The binder has already authenticated a contiguous, complete page directory.
 // Positive groups belong to the page of their first leaf. Empty boundary ranges
 // retain the prior inclusive containment rule (including adjacent empty pages).
 m.groups.forEach((g,i)=>{
  work.indexGroups++;
  if(g.count){
   const page=leafPages[g.first],p=pages[page];work.groupRangeChecks++;
   check(p&&g.first>=p.first&&g.first+g.count<=p.first+p.count,'Unsupported group crossing page boundary');
   indexes[page].groups.set(i,g.first-p.first);
  }else{
   let lo=0,hi=pages.length;
   while(lo<hi){const mid=(lo+hi)>>>1;work.groupRangeChecks++;if(pages[mid].first+pages[mid].count<g.first)lo=mid+1;else hi=mid;}
   let matched=false;
   for(let page=lo;page<pages.length&&pages[page].first<=g.first;page++){
    work.groupRangeChecks++;indexes[page].groups.set(i,g.first-pages[page].first);matched=true;
   }
   check(matched,'Unsupported group crossing page boundary');
  }
 });
 for(const l of m.links){work.indexLinks++;indexes[leafPages[l.leaf]].links.push(l);}
 const metaById=new Map(),payloadById=new Map();
 m.resources.forEach((r,i)=>{work.indexResources++;metaById.set(r.id,i);});
 resources.forEach((r,i)=>{work.indexResources++;payloadById.set(r.id,i);});
 pages.forEach((p,page)=>{
  const needed=new Set();
  for(let i=p.first;i<p.first+p.count;i++)for(const id of m.leafResources[i]){work.indexResourceReferences++;needed.add(id);}
  // Sort selected indices to preserve each original table's independent order.
  indexes[page].metadataResources=Object.freeze([...needed].map(id=>metaById.get(id)).sort((a,b)=>a-b));
  indexes[page].resources=Object.freeze([...needed].map(id=>payloadById.get(id)).sort((a,b)=>a-b));
  Object.freeze(indexes[page].links);Object.freeze(indexes[page]);Object.freeze(p);
 });
 return Object.freeze(indexes);
}

function projectPage(state,page){
 const {bound,pages}=state;
 check(integer(page)&&page<pages.length,'Invalid selected page');
 const p=pages[page],end=p.first+p.count,m=bound.metadata,index=state.indexes[page];
 state.work.selections++;
 const arena={count:p.count};
 for(const key of ['xs','ys','sxs','sys','widths','heights','kinds','paints','payloads','keys','draws'])arena[key]=state.arena[key].slice(p.first,end);
 for(const key of ['paint_table','payload_table'])arena[key]=structuredClone(state.arena[key]);
 const leafResources=m.leafResources.slice(p.first,end).map(rs=>[...rs]);
 // Keep the complete dependency graph. Off-page groups have empty local ranges;
 // owner identities/versions/edges are never synthesized or renumbered.
 const metadata=structuredClone({...m,leafIds:m.leafIds.slice(p.first,end),leafResources,
  groups:m.groups.map((g,i)=>{state.work.projectedGroupCopies++;const first=index.groups.get(i);return {...g,first:first??0,count:first===undefined?0:g.count};}),
  links:index.links.map(l=>({...l,leaf:l.leaf-p.first})),
  resources:index.metadataResources.map(i=>m.resources[i])});
 const tiles=new Map();
 for(let i=0;i<arena.count;i++)if(arena.kinds[i]<2){const key=arena.keys[i];check(state.tiles.has(key),'Missing explicit glyph resource');if(!tiles.has(key))tiles.set(key,structuredClone(state.tiles.get(key)));}
 const resources=structuredClone(index.resources.map(i=>state.resources[i]));
 const scene={arena};sceneColumns(scene,metadata,tiles);
 const output=Object.freeze({bound,page:Object.freeze({index:page,...p}),update:Object.freeze({complete:true,diagnostics:[],unresolved:[],scene,metadata,tiles,resources,width:p.width,height:p.height})});
 preparedDocuments.set(output,state);return output;
}
