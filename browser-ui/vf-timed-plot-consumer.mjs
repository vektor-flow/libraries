import {mountRetainedPlot} from "./vf-retained-plot-element.mjs";
import {createTimedPlotOwner} from "./vf-timed-plot-owner.mjs";

export {createTimedPlotOwner};

/** The embedding consumer owns both the production clock and library mount.
 * Optional subscribeNativePackets is the real executor replacement stream,
 * returning an unsubscribe function; frame presentation never re-emits an
 * edited compiler arena. History and camera navigation touch only the mount.
 */
export async function mountTimedCompilerPlot(container,packet,{
  clock={},subscribeNativePackets=null,...options
}={}) {
  if(Object.hasOwn(options,"animation")||Object.hasOwn(options,"elapsedSeconds")||Object.hasOwn(options,"layerTimeOffsets"))throw new TypeError("The timed consumer owns animation and elapsed time");
  const owner=createTimedPlotOwner(packet,{platform:container?.ownerDocument?.defaultView,...clock});
  let plot=null,unpacket=()=>{},unnative=()=>{},closed=false,closing=null;
  try {
    plot=await mountRetainedPlot(container,packet,{...options,animation:owner,elapsedSeconds:owner.elapsedSeconds});
    unpacket=owner.subscribePackets(frame=>{if(!closed)plot.update(frame.packet,{elapsedSeconds:frame.elapsedSeconds,layerTimeOffsets:frame.layerTimeOffsets});});
    if(subscribeNativePackets!==null){
      if(typeof subscribeNativePackets!=="function")throw new TypeError("Native packet subscription must be a function");
      const release=subscribeNativePackets(next=>{if(!closed)owner.replacePacket(next);});
      if(typeof release!=="function")throw new TypeError("Native packet subscription must return unsubscribe");
      unnative=release;
    }
    owner.start();
  }catch(error){
    closed=true;const errors=[error];
    for(const cleanup of [()=>unpacket(),()=>unnative(),()=>owner.close(),()=>plot?.dispose()])try{await cleanup();}catch(e){errors.push(e);}
    if(errors.length>1)throw new AggregateError(errors,"Timed consumer initialization failed");throw error;
  }
  return Object.freeze({plot,owner,
    close(){
      if(closing)return closing;closed=true;
      closing=(async()=>{
        const errors=[];
        // Initiate cancellation synchronously, then join every accepted job and
        // toolbar/capture operation even when an unsubscribe throws.
        const ownerClose=owner.close();ownerClose.catch(()=>{});
        for(const cleanup of [()=>unpacket(),()=>unnative(),()=>plot.dispose(),()=>ownerClose])try{await cleanup();}catch(e){errors.push(e);}
        if(errors.length)throw new AggregateError(errors,"Timed consumer cleanup failed");
      })();return closing;
    }
  });
}
