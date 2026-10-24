import {materializeRetainedSceneArena} from "./vf-retained-scene-arena.mjs";

const fail=message=>{throw Object.assign(new TypeError(message),{status:"FAIL",code:"RETAINED_LAYER_TIME"});};
const finite=value=>typeof value==="number"&&Number.isFinite(value);
const elapsed=value=>{if(!finite(value)||value<0)fail("Layer elapsed time must be finite and non-negative");};

/** Source port of native vkf_retained_scene_packet.hpp LayerTimeSampler.
 * Repeat includes the final-to-first closing interval, equal to the last
 * coordinate interval. Each layer has its own origin and period. This is
 * linear channel interpolation, never the UI transition-clock easing curve.
 */
export function createLayerTimeEvaluator(descriptor) {
  if(!descriptor||descriptor.axis!=="t"||!["repeat","mirror","stop","reset"].includes(descriptor.mode))fail("Unsupported Layer time axis or mode");
  const coordinates=descriptor.coordinates;
  if(!Array.isArray(coordinates)||coordinates.length<2||coordinates.some((v,i)=>!finite(v)||(i>0&&v<=coordinates[i-1])))fail("Layer t coordinates must be finite and strictly increasing");
  const first=coordinates[0],last=coordinates.at(-1),duration=last-first,closing=last-coordinates.at(-2),period=duration+closing;
  if(!finite(duration)||!finite(period)||!finite(duration*2))fail("Layer time interval overflow");
  if(!Array.isArray(descriptor.channels)||descriptor.channels.length!==3)fail("Temporal Frame.add requires p, c and s channels");
  const channels=new Map();
  for(const channel of descriptor.channels) {
    const name=channel?.name,axes=name==="s"?["t"]:["t","c"];
    if(!["p","c","s"].includes(name)||channels.has(name)||JSON.stringify(channel.semantic_axes)!==JSON.stringify(axes))fail("Unsupported or duplicate temporal channel/axes");
    const values=channel.value;
    if(!Array.isArray(values)||values.length!==coordinates.length)fail("Temporal channel length differs from coordinates");
    if(name==="s") {
      if(!values.every(finite))fail("Temporal size samples must be finite numbers");
    } else {
      const width=values[0]?.length;
      if(!(name==="p"?[2,3]:[4]).includes(width)||values.some(v=>!Array.isArray(v)||v.length!==width||!v.every(finite)))fail("Temporal channel has invalid sample width or values");
      if(name==="c"&&values.some(v=>v.some(c=>c<0||c>1)))fail("Retained color components must be normalized RGBA");
    }
    // Snapshot compiler descriptors only. Source metadata and arena stay untouched.
    channels.set(name,structuredClone(values));
  }
  const times=coordinates.slice(),mode=descriptor.mode;
  function sample(seconds) {
    elapsed(seconds);
    let position,running=true,direction=1,lower,upper,alpha;
    if(mode==="repeat") {
      const phase=seconds%period;
      if(phase>=duration)return Object.freeze({lower:times.length-1,upper:0,alpha:(phase-duration)/closing,axisPosition:first+phase,running,direction});
      position=first+phase;
    } else if(mode==="mirror") {
      const phase=seconds%(duration*2),returning=phase>=duration;
      position=returning?last-(phase-duration):first+phase;direction=returning?-1:1;
    } else if(seconds<duration)position=first+seconds;
    else {position=mode==="stop"?last:first;running=false;direction=0;}
    upper=times.findIndex(v=>v>position);if(upper<0)upper=times.length-1;
    lower=upper-1;alpha=(position-times[lower])/(times[upper]-times[lower]);
    return Object.freeze({lower,upper,alpha,axisPosition:position,running,direction});
  }
  return Object.freeze({duration,period,mode,sample,evaluate(seconds) {
    const time=sample(seconds),values={};
    for(const [name,data]of channels) {
      const a=data[time.lower],b=data[time.upper];
      values[name]=name==="s"?a+(b-a)*time.alpha:a.map((v,i)=>v+(b[i]-v)*time.alpha);
    }
    if(!Object.values(values).flat().every(finite))fail("Temporal interpolation overflow");
    return {time,values};
  }});
}

/** Validate the supported native temporal Frame.add ABI once. Evaluation
 * produces presentation values over materialized compiler storage, never a
 * rewritten arena, generated geometry packet, or substitute source program.
 */
export function createRetainedTimeProjection(packet) {
  let source;
  try{source=materializeRetainedSceneArena(packet);}catch(error){throw Object.assign(error,{status:"FAIL",code:"RETAINED_LAYER_TIME"});}
  const evaluators=new Map();
  if(source.camera?._camera_time||source.views?.some(v=>v.camera?._camera_time||v.meshes?.some(m=>m._layer_time))||source.surfaces?.some(m=>m._layer_time))fail("Unsupported retained temporal camera/view/surface");
  if(!Array.isArray(source.meshes))fail("Retained scene requires meshes");
  for(const mesh of source.meshes) {
    if(!Object.hasOwn(mesh,"_layer_time"))continue;
    if(mesh.type!=="field_mesh"||mesh.topology!=="point-list"||mesh.vertices.length!==10||mesh.indices.length!==1||mesh.indices[0]!==0)fail("Unsupported temporal Frame.add geometry ABI");
    if(evaluators.has(mesh.id))fail("Duplicate timed mesh identity");
    evaluators.set(mesh.id,createLayerTimeEvaluator(mesh._layer_time));
  }
  const claimed=packet.has_layer_time??packet.metadata.has_layer_time;
  if(claimed!==undefined&&typeof claimed!=="boolean")fail("Malformed has_layer_time flag");
  if(claimed!==undefined&&claimed!==(evaluators.size>0))fail("has_layer_time disagrees with compiler descriptors");
  return Object.freeze({packet,timed:evaluators.size>0,
    at(seconds=0,{layerTimeOffsets={}}={}) {
      if(!finite(seconds)||!layerTimeOffsets||Object.getPrototypeOf(layerTimeOffsets)!==Object.prototype||Object.entries(layerTimeOffsets).some(([id,n])=>!evaluators.has(id)||!finite(n)))fail("Invalid signed UI clock/phase offsets");
      const layers=[];
      const meshes=source.meshes.map(mesh=>{
        const evaluator=evaluators.get(mesh.id);if(!evaluator)return mesh;
        const offset=Object.hasOwn(layerTimeOffsets,mesh.id)?layerTimeOffsets[mesh.id]:0;
        const sourceSeconds=seconds+offset;if(!finite(sourceSeconds))fail("Signed phase overflow");
        // Keep the original native evaluator's nonnegative contract. The UI
        // clock may run backward, so periodic layers use a positive native
        // phase and finite layers clamp to the source-defined terminal frame.
        const modulo=(n,d)=>{const r=n%d;return r<0?r+d:r;};
        const nativeSeconds=evaluator.mode==="repeat"?modulo(sourceSeconds,evaluator.period):
          evaluator.mode==="mirror"?modulo(sourceSeconds,evaluator.duration*2):
          Math.max(0,Math.min(evaluator.duration,sourceSeconds));
        const {time,values}=evaluator.evaluate(nativeSeconds);
        const periodic=evaluator.mode==="repeat"||evaluator.mode==="mirror";
        layers.push(Object.freeze({id:mesh.id,...time,mode:evaluator.mode,duration:evaluator.duration,
          sourceElapsedSeconds:sourceSeconds,nativeElapsedSeconds:nativeSeconds,
          canAdvanceForward:periodic||sourceSeconds<evaluator.duration,
          canAdvanceReverse:periodic||sourceSeconds>0}));
        const vertices=mesh.vertices.slice();
        vertices.set(values.p,0);vertices.set(values.c,6);
        if(!Array.from(vertices).every(finite))fail("Temporal values exceed float32 storage");
        return {...mesh,vertices,vertex_size:values.s};
      });
      return Object.freeze({packet,elapsedSeconds:seconds,layerTimeOffsets:Object.freeze({...layerTimeOffsets}),scene:{...source,meshes},layers:Object.freeze(layers),running:layers.some(layer=>layer.running)});
    }
  });
}
