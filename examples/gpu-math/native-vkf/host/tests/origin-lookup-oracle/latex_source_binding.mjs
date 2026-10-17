import {bindFragment,bindDocument} from '../../latex_metadata.mjs';
const check=(ok,msg)=>{if(!ok)throw Error(msg);};
const id=x=>typeof x==='string'&&x.length>0;
const num=x=>Number.isSafeInteger(x)&&x>=0;
// Explicit UTF-16 offsets supplied by the parser/edit owner. Offsets are not IDs.
// Origin spans may overlap (ligatures/macros) and a leaf may have multiple origins.
function bind(bound,provenance,previous){
 check(provenance?.offsetUnit==='utf16'&&Array.isArray(provenance.sources)&&Array.isArray(provenance.groups)&&Array.isArray(provenance.leaves),'Missing source provenance');
 const sources=provenance.sources.map(s=>{check(s&&id(s.id)&&num(s.version)&&typeof s.text==='string','Invalid source');return Object.freeze({id:s.id,version:s.version,text:s.text});});
 const bySource=new Map(sources.map(s=>[s.id,s]));check(bySource.size===sources.length,'Duplicate source');
 const span=s=>{const src=bySource.get(s?.sourceId);check(src&&num(s.start)&&num(s.end)&&s.start<=s.end&&s.end<=src.text.length,'Invalid source span');
  // Reject boundaries inside surrogate pairs: offsets must preserve scalar text.
  const boundary=n=>n===0||n===src.text.length||!(src.text.charCodeAt(n-1)>=0xd800&&src.text.charCodeAt(n-1)<=0xdbff&&src.text.charCodeAt(n)>=0xdc00&&src.text.charCodeAt(n)<=0xdfff);
  check(boundary(s.start)&&boundary(s.end),'Split Unicode scalar');return Object.freeze({sourceId:s.sourceId,start:s.start,end:s.end});};
 const records=(rows,ids)=>{const map=new Map();for(const r of rows){check(r&&ids.has(r.id)&&!map.has(r.id)&&Array.isArray(r.spans)&&r.spans.length>0,'Invalid origin identity/coverage');map.set(r.id,Object.freeze({id:r.id,spans:Object.freeze(r.spans.map(span))}));}check(map.size===ids.size,'Missing origin coverage');return map;};
 const groups=records(provenance.groups,new Set(bound.metadata.groups.map(g=>g.id)));
 const leaves=records(provenance.leaves,new Set(bound.metadata.leafIds));
 // Bound leaf IDs are a frozen dense ordinary array. Keep slice fallback for
 // unusual owner getters whose stored range differs from validation reads.
 for(const g of bound.metadata.groups){const direct=num(g.first)&&num(g.count)&&g.first<=bound.metadata.leafIds.length&&g.count<=bound.metadata.leafIds.length-g.first;
   const ids=direct?bound.metadata.leafIds:bound.metadata.leafIds.slice(g.first,g.first+g.count);
   const first=direct?g.first:0,end=direct?g.first+g.count:ids.length;
   for(let i=first;i<end;i++){const leaf=ids[i];for(const s of leaves.get(leaf).spans)check(groups.get(g.id).spans.some(t=>t.sourceId===s.sourceId&&t.start<=s.start&&s.end<=t.end),'Leaf outside declared group origins');}
 }
 const sourceBinding=Object.freeze({offsetUnit:'utf16',sources:Object.freeze(sources),groups:Object.freeze([...groups.values()]),leaves:Object.freeze([...leaves.values()])});
 if(previous){
  check(previous.sourceBinding,'Previous source binding required');
  const old=previous.sourceBinding,oldSources=new Map(old.sources.map(s=>[s.id,s]));
  for(const s of sources){const o=oldSources.get(s.id);if(o){check(s.version>=o.version,'Source version regressed');check(s.text===o.text||s.version>o.version,'Source changed without version');}}
  // Compare source ID and selected text, never absolute offsets. An insertion
  // before an unchanged group must not change its semantic identity/version.
  const signature=(r,ss)=>r.spans.flatMap(s=>[s.sourceId,ss.get(s.sourceId).text.slice(s.start,s.end)]);
  const same=(a,b)=>a.length===b.length&&a.every((v,i)=>v===b[i]);
  const oldGroups=new Map(old.groups.map(g=>[g.id,g])),oldMeta=new Map(previous.metadata.groups.map(g=>[g.id,g]));
  for(const g of bound.metadata.groups){const o=oldGroups.get(g.id);if(o&&!same(signature(groups.get(g.id),bySource),signature(o,oldSources)))check(g.contentVersion>oldMeta.get(g.id).contentVersion&&g.layoutVersion>oldMeta.get(g.id).layoutVersion,'Source edit requires content/layout versions');}
  // A group's enclosing source may be unchanged while an explicit operation
  // mapping rebinds a retained leaf to different text (including macro origins).
  // Compare authoritative leaf IDs and selected source text, never positions.
  const oldLeaves=new Map(old.leaves.map(l=>[l.id,l]));
  for(const g of bound.metadata.groups){
   const prior=oldMeta.get(g.id);if(!prior)continue;
   const direct=num(g.first)&&num(g.count)&&g.first<=bound.metadata.leafIds.length&&g.count<=bound.metadata.leafIds.length-g.first;
   const ids=direct?bound.metadata.leafIds:bound.metadata.leafIds.slice(g.first,g.first+g.count);
   const first=direct?g.first:0,end=direct?g.first+g.count:ids.length;
   for(let i=first;i<end;i++){const leafId=ids[i];
    const before=oldLeaves.get(leafId),after=leaves.get(leafId);
    if(before&&!same(signature(after,bySource),signature(before,oldSources)))
     check(g.contentVersion>prior.contentVersion&&g.layoutVersion>prior.layoutVersion,'Leaf origin edit requires content/layout versions');
   }
  }
 }
 return Object.freeze({...bound,sourceBinding});
}
export function bindSourceFragment(fragment,owner,provenance,previous=null){return bind(bindFragment(fragment,owner,previous?.metadata),provenance,previous);}
export function bindSourceDocument(result,owner,provenance,previous=null){return bind(bindDocument(result,owner,previous?.metadata),provenance,previous);}
