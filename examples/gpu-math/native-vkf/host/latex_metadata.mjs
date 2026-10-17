// Source/edit-owner records. No IDs, revisions, dependency edges or versions
// are inferred from glyph keys, coordinates, row numbers or document revision.
const check=(ok,message)=>{if(!ok)throw Error(message);};
const id=x=>typeof x==='string'&&x.length>0;
const ver=x=>Number.isSafeInteger(x)&&x>=0;
const list=x=>Array.isArray(x);
const equal=(a,b)=>a.length===b.length&&a.every((x,i)=>x===b[i]);
const issuedMetadata=new WeakSet();
const kinds=new Set(['flow','macro','reference','font']);
export function bindMetadata(count,owner,previous=null){
 check(ver(count)&&owner&&id(owner.documentId)&&ver(owner.revision),'Invalid scope');
 check(list(owner.leafIds)&&owner.leafIds.length===count&&owner.leafIds.every(id)&&new Set(owner.leafIds).size===count,'Invalid leaf IDs');
 check(list(owner.groups)&&list(owner.resources)&&list(owner.leafResources)&&owner.leafResources.length===count&&list(owner.links),'Missing owner columns');
 const resources=owner.resources.map(r=>{check(r&&id(r.id)&&ver(r.version)&&id(r.binding),'Invalid immutable resource');return Object.freeze({id:r.id,version:r.version,binding:r.binding});});
 const resourceMap=new Map(resources.map(r=>[r.id,r]));check(resourceMap.size===resources.length,'Duplicate resources');
 const leafResources=owner.leafResources.map(rs=>{check(list(rs)&&rs.every(r=>resourceMap.has(r))&&new Set(rs).size===rs.length,'Invalid leaf resources');return Object.freeze([...rs]);});
 const seen=new Uint8Array(count),groupMap=new Map();
 const groups=owner.groups.map(g=>{
  check(g&&id(g.id)&&!groupMap.has(g.id)&&ver(g.contentVersion)&&ver(g.layoutVersion)&&id(g.contentKey)&&id(g.layoutKey),'Invalid group identity/version');
  check(ver(g.first)&&ver(g.count)&&g.first<=count&&g.count<=count-g.first&&list(g.edges),'Invalid group range');
  for(let i=g.first;i<g.first+g.count;i++){check(!seen[i],'Overlapping groups');seen[i]=1;}
  const edges=g.edges.map(e=>{check(e&&kinds.has(e.kind)&&id(e.target),'Invalid dependency');return Object.freeze({kind:e.kind,target:e.target});});
  check(new Set(edges.map(e=>e.kind+'\0'+e.target)).size===edges.length,'Duplicate dependency');
  const out=Object.freeze({id:g.id,contentVersion:g.contentVersion,layoutVersion:g.layoutVersion,contentKey:g.contentKey,layoutKey:g.layoutKey,first:g.first,count:g.count,edges:Object.freeze(edges),dependencies:Object.freeze([...new Set(edges.map(e=>e.target))])});groupMap.set(g.id,out);return out;
 });
 check(seen.every(x=>x===1)&&groups.every(g=>g.dependencies.every(d=>groupMap.has(d))),'Incomplete coverage/dependencies');
 const links=owner.links.map(l=>{check(l&&ver(l.leaf)&&l.leaf<count&&id(l.target),'Invalid link');return Object.freeze({leaf:l.leaf,target:l.target});});
 const result=Object.freeze({documentId:owner.documentId,revision:owner.revision,leafIds:Object.freeze([...owner.leafIds]),groups:Object.freeze(groups),resources:Object.freeze(resources),leafResources:Object.freeze(leafResources),links:Object.freeze(links)});
 const invalidated=new Set();
 if(previous){
  check(previous.documentId===result.documentId&&result.revision>previous.revision,'Revision must advance within document');
  const oldGroups=new Map(previous.groups.map(g=>[g.id,g])),oldResources=new Map(previous.resources.map(r=>[r.id,r]));
  for(const r of resources){const old=oldResources.get(r.id);if(old){check(r.version>=old.version,'Resource version regressed');check(r.version!==old.version||r.binding===old.binding,'Resource version rebound');}}
  // Only module-issued frozen normalized rows may be indexed. Public previous
  // objects retain the exact find/filter path, including getter/error order.
  // Index lifetime is one bind request; the module keeps only weak identities.
  const signatureIndexes=new Map();
  const indexFor=m=>{
   if(m!==result&&!issuedMetadata.has(m))return null;
   if(signatureIndexes.has(m))return signatureIndexes.get(m);
   // Owner accessors can change values between validation and normalization.
   // Such unusual issued rows keep legacy lookup semantics too.
   if(!m.resources.every(r=>typeof r.id==='string')||!m.links.every(l=>Number.isSafeInteger(l.leaf))){signatureIndexes.set(m,null);return null;}
   const byResource=m===result?resourceMap:new Map(),byLeaf=new Map();
   if(m!==result)m.resources.forEach(r=>{if(!byResource.has(r.id))byResource.set(r.id,r);});
   m.links.forEach(l=>{let rows=byLeaf.get(l.leaf);if(!rows){rows=[];byLeaf.set(l.leaf,rows);}rows.push(l);});
   const index={byResource,byLeaf};signatureIndexes.set(m,index);return index;
  };
  const findResource=(m,r)=>{const index=indexFor(m);return index?index.byResource.get(r):m.resources.find(x=>x.id===r);};
  const leafLinks=(m,n)=>{const index=indexFor(m);return index?(index.byLeaf.get(n)??[]):m.links.filter(l=>l.leaf===n);};
  const signature=(m,g)=>m.leafIds.slice(g.first,g.first+g.count).flatMap((leaf,i)=>{const n=g.first+i;return [leaf,...m.leafResources[n].flatMap(r=>{const v=findResource(m,r);return [r,v.version,v.binding];}),'|',...leafLinks(m,n).map(l=>l.target)];});
  for(const g of groups){
   const old=oldGroups.get(g.id);if(!old){invalidated.add(g.id);continue;}
   check(g.contentVersion>=old.contentVersion&&g.layoutVersion>=old.layoutVersion,'Group version regressed');
   check(g.contentKey===old.contentKey||g.contentVersion>old.contentVersion,'Content changed without version');
   const changed=g.contentVersion!==old.contentVersion||g.layoutKey!==old.layoutKey||!equal(signature(result,g),signature(previous,old))||!equal(g.edges.map(e=>e.kind+'\0'+e.target),old.edges.map(e=>e.kind+'\0'+e.target));
   if(changed||g.layoutVersion!==old.layoutVersion)invalidated.add(g.id);
  }
  // Include deleted dependencies from the previous graph. Conservative fixed
  // point: each reachable retained group must carry an advanced layout version.
  const affected=new Set([...invalidated,...previous.groups.filter(g=>!groupMap.has(g.id)).map(g=>g.id)]);
  let more=true;while(more){more=false;for(const g of groups){const old=oldGroups.get(g.id);if(!affected.has(g.id)&&[...g.dependencies,...(old?.dependencies??[])].some(d=>affected.has(d))){affected.add(g.id);invalidated.add(g.id);more=true;}}}
  for(const gid of invalidated){const old=oldGroups.get(gid);if(old)check(groupMap.get(gid).layoutVersion>old.layoutVersion,'Affected group requires new layout version');}
 }
 issuedMetadata.add(result);
 return Object.freeze({metadata:result,invalidated:Object.freeze([...invalidated]),cost:Object.freeze({validatedLeaves:count,validatedGroups:groups.length,invalidatedGroups:invalidated.size,policy:'conservative declared dependency closure; no layout reuse claimed'})});
}
// Preserve the exact typed result and its Arena columns. Owner metadata is a
// separate immutable snapshot; never convert the layout to JSON or re-layout.
export function bindFragment(fragment,owner,previous=null){
 check(fragment?.scene?.arena&&typeof fragment.complete==='boolean','Missing typed Fragment');
 const bound=bindMetadata(fragment.scene.arena.count,owner,previous);
 return Object.freeze({...fragment,...bound});
}
export function bindDocument(result,owner,previous=null){
 const d=result?.document;check(d?.arena&&typeof result.complete==='boolean'&&ver(d.page_count)&&d.firsts?.length===d.page_count&&d.counts?.length===d.page_count,'Missing typed DocumentResult');
 let end=0;for(let p=0;p<d.page_count;p++){check(d.firsts[p]===end&&ver(d.counts[p]),'Invalid page ranges');end+=d.counts[p];}
 check(end===d.arena.count,'Incomplete page coverage');
 return Object.freeze({...result,...bindMetadata(d.arena.count,owner,previous)});
}
