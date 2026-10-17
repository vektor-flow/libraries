// Numeric-column producer boundary. Semantic identities belong to the source owner.
// Rows use the existing sixteen-number renderer instance ABI. No JSON transport.
const id=x=>typeof x==='string'&&x.length>0;
const version=x=>Number.isSafeInteger(x)&&x>=0;
export function prepareTypedPacket(packet){
 const {count,columns,metadata:m}=packet;
 if(!Number.isSafeInteger(count)||count<0||!Array.isArray(columns)||columns.length!==16)throw Error('Invalid numeric column count');
 for(const c of columns){
  if(!(c instanceof Float64Array)||c.length!==count||c.byteOffset%8||(typeof SharedArrayBuffer!=="undefined"&&c.buffer instanceof SharedArrayBuffer))throw Error('Expected aligned immutable Float64 columns');
  for(const n of c)if(!Number.isFinite(n)||Math.abs(n)>1e20)throw Error('Invalid geometry');
 }
 if(!m||!id(m.documentId)||!version(m.revision)||!Array.isArray(m.leafIds)||m.leafIds.length!==count||m.leafIds.some(x=>!id(x))||new Set(m.leafIds).size!==count||!Array.isArray(m.groups)||!Array.isArray(m.resources)||!Array.isArray(m.leafResources)||m.leafResources.length!==count||!Array.isArray(m.links))throw Error('Missing source-owner metadata');
 if(m.drawSources!==undefined&&(!Array.isArray(m.sourceLeafIds)||m.sourceLeafIds.some(x=>!id(x))||new Set(m.sourceLeafIds).size!==m.sourceLeafIds.length||!Array.isArray(m.drawSources)||m.drawSources.length!==count||m.drawSources.some(i=>!Number.isSafeInteger(i)||i<0||i>=m.sourceLeafIds.length)))throw Error('Invalid source-to-draw mapping');
 const resources=m.resources.map(r=>{if(!id(r.id)||!version(r.version))throw Error('Missing immutable resource version');return Object.freeze({id:r.id,version:r.version});});
 if(new Set(resources.map(r=>r.id)).size!==resources.length)throw Error('Duplicate resource');
 const resourceIds=new Set(resources.map(r=>r.id));
 const leafResources=m.leafResources.map(rs=>{if(!Array.isArray(rs)||rs.some(r=>!resourceIds.has(r)))throw Error('Unknown leaf resource');return Object.freeze([...rs]);});
 const covered=new Uint8Array(count),groupIds=new Set();
 const groups=m.groups.map(g=>{
  if(!id(g.id)||groupIds.has(g.id)||!version(g.contentVersion)||!version(g.layoutVersion)||!Number.isSafeInteger(g.first)||!Number.isSafeInteger(g.count)||g.first<0||g.count<0||g.first+g.count>count||!Array.isArray(g.dependencies)||g.dependencies.some(d=>!id(d)))throw Error('Invalid group contract');
  groupIds.add(g.id);for(let i=g.first;i<g.first+g.count;i++){if(covered[i])throw Error('Overlapping groups');covered[i]=1;}
  return Object.freeze({...g,dependencies:Object.freeze([...g.dependencies])});
 });
 if(covered.some(x=>!x)||groups.some(g=>g.dependencies.some(d=>!groupIds.has(d))))throw Error('Incomplete group coverage/dependencies');
 const links=m.links.map(l=>{if(!Number.isSafeInteger(l.leaf)||l.leaf<0||l.leaf>=count||!id(l.target))throw Error('Invalid explicit link');return Object.freeze({leaf:l.leaf,target:l.target});});
 const imageLeaves=new Set();
 if(m.images!==undefined&&!Array.isArray(m.images))throw Error('Invalid image bindings');
 const images=(m.images??[]).map(t=>{
  if(!Number.isSafeInteger(t.leaf)||t.leaf<0||t.leaf>=count||imageLeaves.has(t.leaf)||columns[12][t.leaf]!==2||!id(t.asset)||!id(t.resourceId)||!leafResources[t.leaf].includes(t.resourceId))throw Error('Invalid explicit image binding');
  imageLeaves.add(t.leaf);return Object.freeze({leaf:t.leaf,asset:t.asset,resourceId:t.resourceId});
 });
 for(let i=0;i<count;i++)if(columns[12][i]===2&&!imageLeaves.has(i))throw Error('Missing explicit image binding');
 const glyphLeaves=new Set();
 if(m.glyphs!==undefined&&!Array.isArray(m.glyphs))throw Error('Invalid glyph bindings');
 const glyphs=(m.glyphs??[]).map(t=>{
  if(!Number.isSafeInteger(t.leaf)||t.leaf<0||t.leaf>=count||glyphLeaves.has(t.leaf)||columns[12][t.leaf]!==0||!id(t.resourceId)||!leafResources[t.leaf].includes(t.resourceId))throw Error('Invalid explicit glyph binding');
  glyphLeaves.add(t.leaf);return Object.freeze({leaf:t.leaf,resourceId:t.resourceId});
 });
 for(let i=0;i<count;i++)if(columns[12][i]===0&&!glyphLeaves.has(i))throw Error('Missing explicit glyph binding');
 // Materialize the SAME tagged numeric ABI consumed by document_gpu_arena.wgsl.
 // This staging allocation owns its bytes; caller mutations cannot change a snapshot.
 const size=16+count*4+count*(16+16*4+16*16);
 if(!Number.isSafeInteger(size)||size>0xffffffff)throw Error('Packet exceeds address space');
 const bytes=new Uint8Array(size),v=new DataView(bytes.buffer);
 const u=(p,n)=>v.setUint32(p,n,true);
 u(0,4);u(4,count);u(8,16);
 for(let i=0;i<count;i++){
  const row=16+count*4+i*336,values=row+16,numbers=values+64;
  u(16+i*4,row);u(row,4);u(row+4,16);u(row+8,values);
  for(let j=0;j<16;j++){const n=numbers+j*16;u(values+j*4,n);u(n,2);v.setFloat64(n+8,columns[j][i],true);}
 }
 return {bytes,count,metadata:Object.freeze({documentId:m.documentId,revision:m.revision,...(m.drawSources===undefined?{}:{sourceLeafIds:Object.freeze([...m.sourceLeafIds]),drawSources:Object.freeze([...m.drawSources])}),leafIds:Object.freeze([...m.leafIds]),groups:Object.freeze(groups),resources:Object.freeze(resources),leafResources:Object.freeze(leafResources),links:Object.freeze(links),images:Object.freeze(images),glyphs:Object.freeze(glyphs)})};
}
export function sameMetadata(a,b){
 if(a.documentId!==b.documentId||a.revision!==b.revision)return false;
 const same=(x,y)=>x.length===y.length&&x.every((v,i)=>v===y[i]);
 const ag=a.glyphs??[],bg=b.glyphs??[];
 if(ag.length!==bg.length||ag.some((t,i)=>t.leaf!==bg[i].leaf||t.resourceId!==bg[i].resourceId))return false;
 const ai=a.images??[],bi=b.images??[];
 if(ai.length!==bi.length||ai.some((t,i)=>t.leaf!==bi[i].leaf||t.asset!==bi[i].asset||t.resourceId!==bi[i].resourceId))return false;
 return same(a.sourceLeafIds??[],b.sourceLeafIds??[])&&same(a.drawSources??[],b.drawSources??[])&&same(a.leafIds,b.leafIds)&&a.groups.length===b.groups.length&&a.groups.every((g,i)=>{const h=b.groups[i];return g.id===h.id&&g.contentVersion===h.contentVersion&&g.layoutVersion===h.layoutVersion&&g.first===h.first&&g.count===h.count&&same(g.dependencies,h.dependencies);})&&a.resources.length===b.resources.length&&a.resources.every((r,i)=>r.id===b.resources[i].id&&r.version===b.resources[i].version)&&a.leafResources.length===b.leafResources.length&&a.leafResources.every((r,i)=>same(r,b.leafResources[i]))&&a.links.length===b.links.length&&a.links.every((l,i)=>l.leaf===b.links[i].leaf&&l.target===b.links[i].target);
}
