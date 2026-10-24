import {createRetainedTimeProjection} from "./vf-retained-layer-time.mjs";
const failure=message=>Object.assign(new Error(message),{status:"FAIL",code:"TIMED_PLOT_OWNER"});

/** Production UI clock for immutable compiler-owned retained packets.
 * Clock units are seconds of native Layer elapsed time. Layer coordinates,
 * channel interpolation and end modes belong to the native projection ABI.
 * request/cancel/now are injectable platform adapters, not geometry suppliers.
 */
export function createTimedPlotOwner(initialPacket,{
  platform=globalThis,now=()=>platform.performance.now(),
  request=callback=>platform.requestAnimationFrame(callback),
  cancel=handle=>platform.cancelAnimationFrame(handle),
  playing=true,rate=1,onError=()=>{}
}={}) {
  let projection=createRetainedTimeProjection(initialPacket),seconds=0,layerTimeOffsets={};
  const validRate=value=>Number.isFinite(value)&&value>=-4&&value<=4&&Math.abs(value*10-Math.round(value*10))<1e-9;
  if(!validRate(rate))throw failure("Playback rate must be -4.0 through +4.0 in steps of 0.1");
  if(typeof playing!=="boolean"||![now,request,cancel,onError].every(fn=>typeof fn==="function"))throw failure("Invalid clock/control adapters");
  let active=playing&&projection.timed,started=false,closed=false,handle=null,anchor=null,closing=null;
  const stateListeners=new Set(),packetListeners=new Set(),pending=new Set(),errors=[];
  let latest=projection.at(seconds,{layerTimeOffsets});
  function assertOpen(){if(closed)throw failure("Timed plot owner is closed");}
  function clock(){const value=now();if(!Number.isFinite(value))throw failure("Clock must return finite monotonic milliseconds");return value;}
  function stopFrame(){if(handle!==null){const h=handle;handle=null;cancel(h);}}
  function fail(error){errors.push(error);active=false;try{stopFrame();}catch(e){errors.push(e);}try{onError(error);}catch(e){errors.push(e);}}
  function accept(fn,value){
    const result=fn(value);
    if(result&&typeof result.then==="function"){
      const job=Promise.resolve(result).catch(error=>fail(error)).finally(()=>pending.delete(job));pending.add(job);
    }
  }
  function publish(){
    latest=projection.at(seconds,{layerTimeOffsets});
    if(!active||rate===0)stopFrame();
    const advancing=rate===0||latest.layers.some(layer=>rate>0?layer.canAdvanceForward:layer.canAdvanceReverse);
    if(projection.timed&&!advancing){active=false;stopFrame();}
    // All packet listeners see the same original immutable packet and time.
    for(const fn of packetListeners)accept(fn,latest);
    for(const fn of stateListeners)accept(fn,state());
  }
  function advance(){
    const next=clock();
    if(anchor!==null&&next<anchor)throw failure("Clock moved backwards");
    if(started&&active&&anchor!==null){const value=seconds+(next-anchor)/1000*rate;if(!Number.isFinite(value))throw failure("Elapsed time overflow");seconds=value;}
    anchor=next;
  }
  function schedule(){if(!closed&&started&&active&&rate!==0&&handle===null)handle=request(tick);}
  function tick(){
    handle=null;if(closed||!started||!active)return;
    try{advance();publish();schedule();}catch(error){fail(error);}
  }
  function state(){return Object.freeze({timed:projection.timed,playing:active,rate,elapsedSeconds:seconds,layers:latest.layers,closed,error:errors[0]??null});}
  function subscribe(set,fn){assertOpen();if(typeof fn!=="function")throw failure("Listener must be a function");set.add(fn);return()=>set.delete(fn);}
  function rebaseFinitePhases(){
    // Reversing from a finite terminal frame must move from that frame,
    // without spending overshoot time or jumping from reset-first to last.
    // These UI phase offsets do not alter the reported clock or source packet.
    const frame=projection.at(seconds,{layerTimeOffsets}),next={...layerTimeOffsets};
    for(const layer of frame.layers){
      if(layer.mode==="repeat"||layer.mode==="mirror")continue;
      const phase=layer.mode==="reset"&&layer.sourceElapsedSeconds>=layer.duration?0:
        Math.max(0,Math.min(layer.duration,layer.sourceElapsedSeconds));
      next[layer.id]=phase-seconds;
    }
    layerTimeOffsets=next;
  }
  function control(action){assertOpen();try{advance();action();publish();schedule();}catch(error){fail(error);throw error;}}
  const owner={
    get timed(){return projection.timed;},get playing(){return active;},get rate(){return rate;},get elapsedSeconds(){return seconds;},
    get packet(){return projection.packet;},state,
    packetAt(time=seconds){assertOpen();return projection.at(time,{layerTimeOffsets});},
    subscribe:fn=>subscribe(stateListeners,fn),subscribePackets:fn=>subscribe(packetListeners,fn),
    start(){assertOpen();if(started)return;anchor=clock();started=true;try{schedule();}catch(error){fail(error);throw error;}},
    toggle(){control(()=>{if(!projection.timed)throw failure("Static plot has no timed controls");rebaseFinitePhases();active=!active;});},
    setRate(value){if(!validRate(value))throw failure("Playback rate must be -4.0 through +4.0 in steps of 0.1");control(()=>{rebaseFinitePhases();rate=value;});},
    seek(time){if(!Number.isFinite(time)||time<0)throw failure("Native elapsed time must be finite and non-negative");control(()=>{seconds=time;layerTimeOffsets={};});},
    replacePacket(packet){
      assertOpen();const next=createRetainedTimeProjection(packet);next.at(seconds,{layerTimeOffsets});
      control(()=>{projection=next;active=active&&next.timed;});
    },
    close(){
      if(closing)return closing;
      closed=true;active=false;started=false;
      try{stopFrame();}catch(error){errors.push(error);}
      stateListeners.clear();packetListeners.clear();
      closing=(async()=>{while(pending.size)await Promise.allSettled([...pending]);if(errors.length)throw new AggregateError(errors,"Timed plot owner failed or cleanup failed");})();
      return closing;
    }
  };
  return Object.freeze(owner);
}
