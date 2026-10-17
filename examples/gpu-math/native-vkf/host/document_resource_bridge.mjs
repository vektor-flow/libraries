import {sceneColumns} from './document_scene_bridge.mjs';
import {prepareTypedPacket,sameMetadata} from './document_typed_bridge.mjs';
const equal=(a,b)=>a.length===b.length&&a.every((v,i)=>v===b[i]);
// Owns immutable CPU staging/resources. Optional GPU arena is exclusively owned
// by this bridge. Latest resource versions are cached until dispose; older bytes
// live only through consumer leases. Resource IDs/versions come from the owner.
const descriptorEqual=(a,b)=>a===b||!!a&&!!b&&['format','width','height','bytesPerRow','alphaMode'].every(k=>a[k]===b[k]);
function imageDescriptor(p,required){
 const d=p.image;
 if(d==null){if(required)throw Error('Missing decoded image descriptor');return null;}
 if(d.format!=='rgba8unorm'||d.alphaMode!=='straight'||!Number.isSafeInteger(d.width)||d.width<=0||!Number.isSafeInteger(d.height)||d.height<=0||d.width*d.height>16777216||d.bytesPerRow!==d.width*4||p.bytes.byteLength!==d.bytesPerRow*d.height)throw Error('Invalid decoded image descriptor');
 return Object.freeze({format:d.format,width:d.width,height:d.height,bytesPerRow:d.bytesPerRow,alphaMode:d.alphaMode});
}
export function createRetainedSceneBridge({gpuArena=null}={}){
 let current=null,disposed=false,generation=0,documentId=null;
 const latest=new Map();
 const metrics={commits:0,noops:0,resourceCopies:0,resourceReuses:0,liveSnapshots:0};
 function drop(s){if(--s.refs===0){s.gpu?.release();s.bytes=null;s.resources.clear();metrics.liveSnapshots--;}}
 function lease(s){
  s.refs++;let released=false;
  const live=()=>{if(released)throw Error('Released snapshot');};
  return Object.freeze({generation:s.generation,count:s.count,metadata:s.metadata,
   // Copies at the public mutable-array boundary protect all other consumers.
   bytes(){live();return s.bytes.slice();},
   resource(id){live();const r=s.resources.get(id);if(!r)throw Error('Unknown resource');return r.bytes.slice();},
   resourceDescriptor(id){live();const r=s.resources.get(id);if(!r)throw Error('Unknown resource');return r.image;},
   get buffer(){live();return s.gpu?.buffer;},
   release(){if(!released){released=true;drop(s);}}
  });
 }
 function commitScene(scene,metadata,tiles,payloads){
  if(disposed)throw Error('Disposed bridge');
  const packet=sceneColumns(scene,metadata,tiles),next=prepareTypedPacket(packet);
  if(documentId!==null&&next.metadata.documentId!==documentId)throw Error('Bridge document ownership mismatch');
  if(!Array.isArray(payloads)||payloads.length!==next.metadata.resources.length)throw Error('Missing resource payloads');
  const incoming=new Map();
  for(const p of payloads){
   if(!p||incoming.has(p.id)||!(p.bytes instanceof Uint8Array)||(typeof SharedArrayBuffer!=='undefined'&&p.bytes.buffer instanceof SharedArrayBuffer))throw Error('Invalid resource payload');
   incoming.set(p.id,p);
  }
  const imageIds=new Set([...next.metadata.images,...next.metadata.glyphs].map(i=>i.resourceId));
  const resources=new Map();let copies=0,reuses=0;
  for(const r of next.metadata.resources){
   const p=incoming.get(r.id),old=latest.get(r.id);
   if(!p||p.version!==r.version)throw Error('Resource version mismatch');
   const image=imageDescriptor(p,imageIds.has(r.id));
   if(old&&(r.version<old.version||(r.version===old.version&&(!equal(p.bytes,old.bytes)||!descriptorEqual(image,old.image)))))throw Error('Immutable resource version changed');
   if(old&&r.version===old.version){resources.set(r.id,old);reuses++;}
   else{resources.set(r.id,{version:r.version,bytes:new Uint8Array(p.bytes),image});copies++;}
  }
  if(current&&sameMetadata(current.metadata,next.metadata)&&equal(current.bytes,next.bytes)){
   metrics.noops++;return lease(current);
  }
  // All input validation completes before the optional GPU mutation. A throw
  // leaves current and the latest resource-version cache unchanged.
  const gpu=gpuArena?.commitColumns(packet);
  const state={...next,resources,gpu,refs:1,generation:++generation};
  for(const [id,r]of resources)latest.set(id,r);
  documentId=next.metadata.documentId;
  const prior=current;current=state;metrics.commits++;metrics.resourceCopies+=copies;metrics.resourceReuses+=reuses;metrics.liveSnapshots++;
  if(prior)drop(prior);return lease(state);
 }
 return Object.freeze({commitScene,metrics,
  snapshot(){if(disposed||!current)throw Error('No live scene');return lease(current);},
  dispose(){if(!disposed){disposed=true;if(current){drop(current);current=null;}latest.clear();gpuArena?.dispose();}},
  async drained(){await gpuArena?.drained();}
 });
}
