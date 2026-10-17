import {bindOperationDocument} from '../../latex_operation_binding.mjs';
import {sceneColumns} from '../../document_scene_bridge.mjs';
const preparedDocuments=new WeakMap();
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
 const array=(key,predicate)=>{const c=a[key];check(sequence(c)&&c.length===n,'Invalid column extent '+key);check(Array.from(c).every(predicate),'Invalid column type '+key);return Array.from(c);};
 for(const key of ['a260_scopes','a260_texts'])array(key,x=>typeof x==='string');
 for(const key of ['a260_operations','a260_starts','a260_stops','a260_parts'])array(key,integer);
 // Binding validates scope/text/span/part ownership, resource versions and page
 // coverage before projection or any render-session commit.
 const bound=bindOperationDocument(result,owner,previous);
 const arena={count:n};
 for(const key of ['xs','ys','sxs','sys','widths','heights'])arena[key]=Float64Array.from(array(key,Number.isFinite));
 for(const key of ['kinds','paints','payloads'])arena[key]=Int32Array.from(array(key,x=>Number.isInteger(x)&&x>=-2147483648&&x<=2147483647));
 check(Array.from(arena.kinds).every(x=>[0,1,2,3].includes(x)),'Unsupported leaf provenance/resource mapping');
 arena.keys=array('keys',x=>typeof x==='string');
 arena.draws=Uint8Array.from(array('draws',x=>x===true||x===1));
 check(Array.isArray(a.paint_table)&&a.paint_count===a.paint_table.length&&Array.isArray(a.payload_table)&&a.payload_count===a.payload_table.length,'Invalid table extents');
 arena.paint_table=structuredClone(a.paint_table);arena.payload_table=structuredClone(a.payload_table);
 check(tiles instanceof Map&&Array.isArray(resources),'Invalid resource transport');
 const scene={arena},tileSnapshot=structuredClone(tiles),resourceSnapshot=structuredClone(resources);
 // Preserve exact resource IDs/versions/bytes; installed bridge owns immutable
 // admission and cross-update version checks. Reject shared memory before copy.
 const refs=new Map(bound.metadata.resources.map(r=>[r.id,r.version])),seen=new Set();
 for(const r of resources){check(r&&refs.has(r.id)&&!seen.has(r.id)&&r.version===refs.get(r.id)&&r.bytes instanceof Uint8Array&&!(typeof SharedArrayBuffer!=='undefined'&&r.bytes.buffer instanceof SharedArrayBuffer),'Invalid resource payload/version');seen.add(r.id);}
 check(seen.size===refs.size,'Missing resource payload');
 sceneColumns(scene,bound.metadata,tileSnapshot);
 // Validate the entire directory and reject groups split across any page.
 for(const key of ['firsts','counts'])check(sequence(d[key])&&d[key].length===d.page_count&&Array.from(d[key]).every(integer),'Invalid page directory');
 const pages=Array.from(d.firsts,(first,i)=>({first,count:d.counts[i],width:d.widths[i],height:d.heights[i]}));
 for(const g of bound.metadata.groups)check(pages.some(p=>g.first>=p.first&&g.first+g.count<=p.first+p.count),'Unsupported group crossing page boundary');
 const state={bound,arena,pages,tiles:tileSnapshot,resources:resourceSnapshot};
 return projectPage(state,page);
}

/** Select another page from an authenticated prepared document without pretending
 * that a page switch is a source revision. The bound value remains full-document.
 */
export function selectProducerPage(prepared,page){
 const state=preparedDocuments.get(prepared);
 check(state,'Prepared producer document required');
 return projectPage(state,page);
}
function projectPage(state,page){
 const {bound,pages}=state;
 check(integer(page)&&page<pages.length,'Invalid selected page');
 const p=pages[page],end=p.first+p.count,m=bound.metadata;
 const arena={count:p.count};
 for(const key of ['xs','ys','sxs','sys','widths','heights','kinds','paints','payloads','keys','draws'])arena[key]=state.arena[key].slice(p.first,end);
 for(const key of ['paint_table','payload_table'])arena[key]=structuredClone(state.arena[key]);
 const leafResources=m.leafResources.slice(p.first,end).map(rs=>[...rs]);
 const needed=new Set(leafResources.flat());
 // Keep the complete dependency graph. Off-page groups have empty local ranges;
 // owner identities/versions/edges are never synthesized or renumbered.
 const metadata=structuredClone({...m,leafIds:m.leafIds.slice(p.first,end),leafResources,
  groups:m.groups.map(g=>({...g,first:g.first>=p.first&&g.first+g.count<=end?g.first-p.first:0,count:g.first>=p.first&&g.first+g.count<=end?g.count:0})),
  links:m.links.filter(l=>l.leaf>=p.first&&l.leaf<end).map(l=>({...l,leaf:l.leaf-p.first})),
  resources:m.resources.filter(r=>needed.has(r.id))});
 const tiles=new Map();
 for(let i=0;i<arena.count;i++)if(arena.kinds[i]<2){const key=arena.keys[i];check(state.tiles.has(key),'Missing explicit glyph resource');tiles.set(key,structuredClone(state.tiles.get(key)));}
 const resources=structuredClone(state.resources.filter(r=>needed.has(r.id)));
 const scene={arena};sceneColumns(scene,metadata,tiles);
 const output=Object.freeze({bound,page:Object.freeze({index:page,...p}),update:Object.freeze({complete:true,diagnostics:[],unresolved:[],scene,metadata,tiles,resources,width:p.width,height:p.height})});
 preparedDocuments.set(output,state);return output;
}
