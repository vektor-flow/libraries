import {insideRegion,validateRings,strokeRegions} from './vf-selection-outline.mjs';
import {buildFaceSelectionBoundaryPaths,buildEdgeSelectionPaths} from './vf-selection-contours.mjs';
const id=value=>{if(typeof value!=='string'||!value)throw new TypeError('producer-issued identity required');return value};
const project=(rings,coordinates)=>rings.map(r=>r.map(p=>coordinates.worldToScreen(p).slice(0,2)));
const snapshot=rings=>validateRings(rings).map(r=>r.map(p=>[...p]));

// Already decoded, host-issued geometry only. No font loading, shaping, word
// guessing, bbox hit tests or fabricated parse parents. Logical cluster IDs may
// identify multiple parts (ligature/constructed math). Offsets retain their unit.
export function textSelectionObjects({elementId,clusters,groups=[],coordinates,clip=null}) {
  id(elementId);const groupMap=new Map();
  for(const g of groups){id(g.id);if(groupMap.has(g.id)||g.id===elementId||!['word','math'].includes(g.kind))throw new TypeError('invalid issued text group');groupMap.set(g.id,{...g})}
  const parts=new Map();
  for(const c of clusters){
    id(c.id);if(c.id===elementId||groupMap.has(c.id))throw new TypeError('duplicate text identity');
    if(c.groupId!=null&&!groupMap.has(c.groupId))throw new TypeError('unknown word/math scope');
    if(!c.source||typeof c.source.text!=='string'||!['utf8','utf16','codepoint'].includes(c.source.offsetUnit)||!Number.isSafeInteger(c.source.start)||!Number.isSafeInteger(c.source.end)||c.source.start<0||c.source.end<c.source.start)throw new TypeError('explicit source origin required');
    id(c.source.id);
    const part={...c,rings:snapshot(c.rings),source:Object.freeze({...c.source})};
    if(parts.has(c.id)&&parts.get(c.id)[0].groupId!==c.groupId)throw new TypeError('cluster parts disagree on parent');
    if(!parts.has(c.id))parts.set(c.id,[]);parts.get(c.id).push(part);
  }
  const clipCopy=clip&&snapshot(clip);
  const regions=values=>()=>values.map(p=>({rings:project(p.rings,coordinates),fillRule:p.fillRule??'evenodd',clip:clipCopy&&project(clipCopy,coordinates)}));
  const all=[...parts.values()].flat(),result=[];
  const make=(key,values,parentId)=>({id:key,parentId,regions:regions(values),detailRegions:regions(values),detailSize:()=>{
    let size=0;for(const p of values){const ys=project(p.rings,coordinates).flat().map(p=>p[1]);if(ys.length)size=Math.max(size,Math.max(...ys)-Math.min(...ys))}return size;
  }});
  result.push({...make(elementId,all,null),pickable:false});
  for(const g of groupMap.values())result.push({...make(g.id,all.filter(p=>p.groupId===g.id),elementId),pickable:false});
  for(const [key,values]of parts){const parent=values[0].groupId??null,object=make(key,values,parent??elementId);
    // Unknown math scope explicitly stays on the logical cluster on double-click.
    object.clickTargets=[key,parent??key,elementId];object.fallback=parent===null?'cluster-no-issued-group':null;
    object.origins=Object.freeze(values.map(v=>v.source));object.hitTest=p=>object.regions().some(r=>insideRegion(p,r));result.push(object);
  }
  return result;
}

// Boundary is the actual transformed image quad/polygon. Pixel content is never
// replaced or traced. Explicit alpha geometry may be provided by the image owner.
export function imageSelectionObject({imageId,boundary,coordinates,alphaRegions=null,clip=null}) {
  id(imageId);const shape=snapshot(alphaRegions??[boundary]),clipping=clip&&snapshot(clip);
  const regions=()=>[{rings:project(shape,coordinates),clip:clipping&&project(clipping,coordinates)}];
  return {id:imageId,regions,hitTest:p=>regions().some(r=>insideRegion(p,r))};
}

// Native meshes/graph nodes/edges/relation curves can share this geometry adapter
// only when the host supplies their issued paths/topology and ownership. It does
// not sample relations or invent graph hierarchy. Mesh triangles retain fill;
// transferred Platonic primitives supply their topological boundary paths.
export function nativeGeometrySelectionObject({objectId,points,indices,topology,coordinates,
  width=2,radius=7,parentId=null,clickTargets=null,clip=null}) {
  id(objectId);const vertices=points.map(p=>[...p]),ix=[...indices],clipping=clip&&snapshot(clip);
  if(vertices.some(p=>p.length<2||p.some(x=>!Number.isFinite(x)))||ix.some(i=>!Number.isSafeInteger(i)||i<0||i>=vertices.length))throw new TypeError('invalid native geometry');
  if(!['triangle-list','line-list','line-strip','point-list'].includes(topology)||topology==='triangle-list'&&ix.length%3||topology==='line-list'&&ix.length%2)throw new TypeError('invalid native topology');
  const faces=[],edges=[];
  if(topology==='triangle-list')for(let i=0;i<ix.length;i+=3)faces.push(ix.slice(i,i+3));
  if(topology==='line-list')for(let i=0;i<ix.length;i+=2)edges.push({a:ix[i],b:ix[i+1]});
  if(topology==='line-strip')for(let i=1;i<ix.length;i++)edges.push({a:ix[i-1],b:ix[i]});
  const paths=faces.length?buildFaceSelectionBoundaryPaths(faces):buildEdgeSelectionPaths(edges);
  const regions=()=>{
    const p=vertices.map(v=>coordinates.worldToScreen(v).slice(0,2));let result=[];
    if(faces.length)result=faces.map(f=>({rings:[f.map(i=>p[i])]}));
    else if(topology==='point-list')result=ix.flatMap(i=>strokeRegions([p[i]],typeof radius==='function'?radius():radius));
    else result=paths.flatMap(path=>strokeRegions(path.map(i=>p[i]),(typeof width==='function'?width():width)/2));
    return result.map(r=>({...r,clip:clipping&&project(clipping,coordinates)}));
  };
  return {id:objectId,parentId,clickTargets,regions,hitTest:p=>regions().some(r=>insideRegion(p,r)),boundaryPaths:()=>{const p=vertices.map(v=>coordinates.worldToScreen(v).slice(0,2));return paths.map(path=>path.map(i=>p[i]))}};
}
