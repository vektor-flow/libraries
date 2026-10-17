import {createRetainedSceneBridge} from './document_resource_bridge.mjs';
import {createDocumentTextureConsumer} from './document_texture_consumer.mjs';
/** One document per session. Producer supplies complete typed Scene, canonical
 * metadata, glyph tiles and versioned decoded resources. No layout or ID inference.
 * render() returns a submission receipt; receipt.completion means queue completion,
 * never PDF save. update() snapshots caller data synchronously before returning.
 */
export function createDocumentRenderSession({device,pipeline}) {
 const bridge=createRetainedSceneBridge(),consumer=createDocumentTextureConsumer({device,pipeline});
 let closed=false,epoch=0,ready=false,submission=0,renderEpoch=0,disposed;
 const pending=new Set();
 function track(p){pending.add(p);p.then(()=>pending.delete(p),()=>pending.delete(p));return p;}
 function live(){if(closed)throw Error('Disposed render session');}
 function update(result){
  live();
  if(!result||result.complete!==true||!Array.isArray(result.diagnostics)||result.diagnostics.length||!Array.isArray(result.unresolved)||result.unresolved.length)throw Error('Incomplete producer result');
  // Candidate admission retains the committed drawable; D295 binds only on
  // first successful commit and rejects foreign ownership before payload access.
  const lease=bridge.commitScene(result.scene,result.metadata,result.tiles,result.resources);
  const ticket=++epoch;
  return track(consumer.replace(lease).then(generation=>{
   if(closed||ticket!==epoch)throw Error('Superseded update');
   ready=true;return Object.freeze({generation,revision:lease.metadata.revision});
  }));
 }
 function cancel(){live();epoch++;renderEpoch++;ready=false;consumer.clearDocumentProject();}
 function render(view,{zoom=1,origin=[0,0],signal}={}){
  live();if(!ready)throw Error('No completed update');
  const ticket=renderEpoch,draw=consumer.encodePage(view,zoom,origin);
  return track((async()=>{
   // One microtask permits cancellation/epoch revocation before submission.
   // Queue ordering covers the upload; the draw owns all deferred cleanup.
   await Promise.resolve();
   if(closed||ticket!==renderEpoch||signal?.aborted){draw.cancel();throw Error('Cancelled render');}
   const completion=draw.submit();track(completion);
   return Object.freeze({submission:++submission,generation:draw.generation,completion});
  })());
 }
 function dispose(){
  if(disposed)return disposed;
  closed=true;epoch++;renderEpoch++;ready=false;consumer.dispose();bridge.dispose();
  disposed=(async()=>{while(pending.size)await Promise.allSettled([...pending]);await consumer.drained();await bridge.drained();})();
  return disposed;
 }
 return Object.freeze({update,render,cancel,dispose,get generation(){return ready?consumer.generation:null;},get metrics(){return {...bridge.metrics,submissions:submission};}});
}
