// Input belongs to the compiled runtime. Retained geometry remains read-only.
export function createNativePlotInteraction({targets = {}} = {}) {
  const entries = new Map();
  for (const [id,target] of Object.entries(targets)) entries.set(id,prepare(target));
  let active = null;

  function begin(id,screen,coordinates,{dimensions = 2} = {}) {
    active = null;
    const target = entries.get(id);
    if (!target || dimensions === 3 && !target.constraint) return false;
    const constraint = target.constraint ?? {kind:'plane',point:[0,0,0],normal:[0,0,1]};
    const hit = constrainedPoint(screen,coordinates,dimensions,constraint);
    if (!hit) return false;
    const state = target.runtime.readState();
    const local = ['x','y','z'].map(axis=>state[target.positionFields[axis]]);
    const world = toWorld(target.reference,vector(local,'native position'));
    active = {id,target,coordinates,dimensions,constraint,offset:subtract(world,hit),
      lastScreen:[...screen],viewKey:viewKey(coordinates)};
    return true;
  }

  function move(screen) {
    if (!active) return null;
    const {id,target,coordinates,dimensions} = active;
    const nextViewKey = viewKey(coordinates);
    if (active.constraint.kind === 'camera-plane' && nextViewKey !== active.viewKey) {
      const state = target.runtime.readState();
      const world = toWorld(target.reference,vector(['x','y','z'].map(axis=>state[target.positionFields[axis]]),'native position'));
      const constraint = {...active.constraint,point:world};
      const hit = constrainedPoint(active.lastScreen,coordinates,dimensions,constraint);
      if (!hit) return null;
      active.constraint = constraint;
      active.offset = subtract(world,hit);
      active.viewKey = nextViewKey;
    }
    const {constraint,offset} = active;
    const hit = constrainedPoint(screen,coordinates,dimensions,constraint);
    if (!hit) return null;
    // Rebase the mapping above, but a stationary pointer supplies no input.
    // Calling update here could advance a runtime even though only its camera moved.
    if (screen[0] === active.lastScreen[0] && screen[1] === active.lastScreen[1]) return null;
    const local = toLocal(target.reference,add(hit,offset));
    const input = {...target.runtime.readInput()};
    for (const [index,axis] of ['x','y','z'].entries()) {
      input[target.inputFields[axis]] = target.quantized ? Math.round(local[index]) : local[index];
    }
    target.runtime.writeInput(input);
    target.runtime.update();
    active.lastScreen = [...screen];
    return Object.freeze({id,state:Object.freeze({...target.runtime.readState()})});
  }

  function end() { active = null; }
  return Object.freeze({begin,move,end,cancel:end});
}

function prepare(target) {
  const {runtime,inputFields,positionFields,quantized = false} = target;
  for (const name of ['inputLayout','readInput','writeInput','readState','update']) {
    if (typeof runtime?.[name] !== 'function') throw new TypeError('interaction requires a compiled writable-input runtime');
  }
  const fields = runtime.inputLayout().fields;
  for (const axis of ['x','y','z']) {
    if (typeof positionFields?.[axis] !== 'string') throw new TypeError('native position fields must be declared');
    const field = fields.find(field=>field.name===inputFields?.[axis]);
    if (!field || field.axis_length) throw new TypeError('native scalar input fields must be declared');
    if (!['f64','f32'].includes(field.storage ?? field.type) && !quantized) {
      throw new TypeError('integer native position input requires quantized:true');
    }
  }
  const reference = referenceFrame(target.referenceSystem);
  const constraint = target.constraint ? prepareConstraint(target.constraint) : null;
  return {runtime,inputFields:{...inputFields},positionFields:{...positionFields},quantized,reference,constraint};
}

function referenceFrame(system) {
  if (system === 'world') return {origin:[0,0,0],basis:[[1,0,0],[0,1,0],[0,0,1]]};
  const origin = vector(system?.origin,'reference origin');
  if (!Array.isArray(system?.basis) || system.basis.length !== 3) throw new TypeError('reference axes must be declared');
  const basis = system.basis.map(axis=>vector(axis,'reference axis'));
  for (let i=0;i<3;i++) for (let j=0;j<3;j++) {
    if (Math.abs(dot(basis[i],basis[j])-(i===j ? 1 : 0))>1e-8) throw new TypeError('reference axes must be orthonormal');
  }
  return {origin,basis};
}

function prepareConstraint(value) {
  const point = vector(value.point,'constraint point');
  if (value.kind === 'camera-plane') return {kind:'camera-plane',point};
  if (value.kind === 'plane') return {kind:'plane',point,normal:unit(value.normal)};
  if (value.kind === 'axis') return {kind:'axis',point,direction:unit(value.direction)};
  throw new TypeError('drag constraint must be a declared plane, camera-plane or axis');
}

function constrainedPoint(screen,coordinates,dimensions,constraint) {
  const ray = dimensions === 3 ? coordinates.screenLine(screen)
    : {point:[...coordinates.screenToWorld(screen).slice(0,2),0],direction:[0,0,1]};
  if (constraint.kind === 'plane' || constraint.kind === 'camera-plane') {
    const normal = constraint.kind === 'camera-plane' ? unit(ray.direction) : constraint.normal;
    const denominator = dot(ray.direction,normal);
    if (Math.abs(denominator)<1e-10) return null;
    return add(ray.point,scale(ray.direction,dot(subtract(constraint.point,ray.point),normal)/denominator));
  }
  const direction = constraint.direction;
  const alignment = dot(direction,ray.direction);
  const denominator = 1-alignment*alignment;
  if (Math.abs(denominator)<1e-10) return null;
  const delta = subtract(ray.point,constraint.point);
  return add(constraint.point,scale(direction,(dot(delta,direction)-alignment*dot(delta,ray.direction))/denominator));
}

function viewKey(coordinates) {
  return JSON.stringify(coordinates.snapshot?.() ?? null);
}

function vector(value,label) {
  if (!Array.isArray(value) || value.length!==3 || !value.every(Number.isFinite)) throw new TypeError(label+' requires three finite coordinates');
  return [...value];
}
const dot = (a,b)=>a.reduce((total,value,index)=>total+value*b[index],0);
const add = (a,b)=>a.map((value,index)=>value+b[index]);
const subtract = (a,b)=>a.map((value,index)=>value-b[index]);
const scale = (a,factor)=>a.map(value=>value*factor);
function unit(value) {
  const result = vector(value,'constraint direction'),length = Math.hypot(...result);
  if (length<1e-10) throw new TypeError('constraint direction must be nonzero');
  return scale(result,1/length);
}
const toWorld = (frame,local)=>frame.basis.reduce((world,axis,index)=>add(world,scale(axis,local[index])),frame.origin);
const toLocal = (frame,world)=>frame.basis.map(axis=>dot(subtract(world,frame.origin),axis));
