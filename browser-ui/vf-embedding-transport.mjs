// Experimental weighted visual measures. No compiler syntax or physics semantics.
import {transitionClock} from './vf-transition-clock.mjs';
const MAX_ITEMS = 10000;
const TOLERANCE = 1e-9;
const prepared = new WeakSet();
const fail = message => { throw new TypeError(message); };
const finite = value => typeof value === 'number' && Number.isFinite(value);
const close = (a, b) => Math.abs(a - b) <= TOLERANCE * Math.max(Math.abs(a), Math.abs(b));
const freeze = value => {
  if (value && typeof value === 'object') {
    Object.values(value).forEach(freeze);
    Object.freeze(value);
  }
  return value;
};

function measure(input, label) {
  if (!Array.isArray(input) || !input.length || input.length > MAX_ITEMS) fail(`${label}: expected 1..${MAX_ITEMS} atoms`);
  const ids = new Set();
  const dimension = input[0]?.position?.length;
  if (![2, 3].includes(dimension)) fail(`${label}: positions must be 2D or 3D`);
  const atoms = input.map(atom => {
    if (!atom || typeof atom.id !== 'string' || !atom.id || ids.has(atom.id)) fail(`${label}: unique nonempty IDs required`);
    ids.add(atom.id);
    if (!Array.isArray(atom.position) || atom.position.length !== dimension || !atom.position.every(finite)) fail(`${label}: invalid position`);
    if (!finite(atom.weight) || atom.weight <= 0) fail(`${label}: positive finite weight required`);
    return { id: atom.id, position: [...atom.position], weight: atom.weight };
  });
  const total = atoms.reduce((sum, atom) => sum + atom.weight, 0);
  if (!finite(total)) fail(`${label}: weight overflow`);
  return { atoms, total, dimension };
}

function pair(source, target) {
  const a = measure(source, 'source'), b = measure(target, 'target');
  if (a.dimension !== b.dimension) fail('Declare a common coordinate space before transporting');
  if (!close(a.total, b.total)) fail('Unequal total weight: declare creation/removal separately');
  return [a, b];
}

/** Ordered interval coupling: deterministic, O(n+m), not a spatial/semantic optimizer.
 * Callers choose the ordering (e.g. along a curve). Units and frame must already agree.
 */
export function orderedMassCoupling(source, target) {
  const [a, b] = pair(source, target);
  const result = [];
  let i = 0, j = 0, left = 0, endA = a.atoms[0].weight, endB = b.atoms[0].weight;
  while (i < a.atoms.length && j < b.atoms.length) {
    const right = Math.min(endA, endB);
    if (right > left) result.push({ source: a.atoms[i].id, target: b.atoms[j].id, weight: right - left });
    left = right;
    const advanceA = endA <= endB, advanceB = endB <= endA;
    if (advanceA && ++i < a.atoms.length) endA += a.atoms[i].weight;
    if (advanceB && ++j < b.atoms.length) endB += b.atoms[j].weight;
  }
  // Validate marginal recovery too: reject unrepresentable tiny intervals, not silently drop them.
  createEmbeddingTransport(source, target, result, { motion: 'linear' });
  return result;
}

/** Explicit coupling lifts both endpoint measures into the same carrier.
 * A route's optional `midpoint` specifies its position at t=1/2.
 */
export function createEmbeddingTransport(source, target, coupling, { motion = 'affine-2d' } = {}) {
  const [a, b] = pair(source, target);
  if (!['linear', 'rigid-2d', 'affine-2d'].includes(motion)) fail('Unknown motion model');
  if (motion !== 'linear' && a.dimension !== 2) fail('Pose decomposition currently requires 2D');
  if (!Array.isArray(coupling) || !coupling.length || coupling.length > MAX_ITEMS) fail('Invalid coupling size');
  const sourceIndex = new Map(a.atoms.map(atom => [atom.id, atom]));
  const targetIndex = new Map(b.atoms.map(atom => [atom.id, atom]));
  const rows = new Map(), columns = new Map(), seen = new Set();
  const routes = coupling.map((edge, index) => {
    const start = sourceIndex.get(edge?.source), end = targetIndex.get(edge?.target);
    if (!start || !end) fail('Unknown coupling endpoint');
    const key = JSON.stringify([start.id, end.id]);
    if (seen.has(key)) fail('Duplicate coupling route');
    seen.add(key);
    if (!finite(edge.weight) || edge.weight <= 0) fail('Invalid coupling weight');
    if (motion !== 'linear' && edge.midpoint !== undefined) fail('Explicit midpoint requires linear motion model');
    rows.set(start.id, (rows.get(start.id) || 0) + edge.weight);
    columns.set(end.id, (columns.get(end.id) || 0) + edge.weight);
    const midpoint = edge.midpoint ?? start.position.map((x, k) => x / 2 + end.position[k] / 2);
    if (!Array.isArray(midpoint) || midpoint.length !== a.dimension || !midpoint.every(finite)) fail('Invalid midpoint');
    const control = midpoint.map((x, k) => 2 * x - start.position[k] / 2 - end.position[k] / 2);
    if (!control.every(finite)) fail('Path control overflow');
    return { id: `route-${index}`, source: start.id, target: end.id, weight: edge.weight,
      start: [...start.position], end: [...end.position], midpoint: [...midpoint], control };
  });
  for (const atom of a.atoms) if (!close(rows.get(atom.id) || 0, atom.weight)) fail(`Source marginal mismatch: ${atom.id}`);
  for (const atom of b.atoms) if (!close(columns.get(atom.id) || 0, atom.weight)) fail(`Target marginal mismatch: ${atom.id}`);
  let pose = null;
  if (motion !== 'linear') {
    // Weighted orientation-preserving Procrustes fit, conditional on this coupling.
    // This does not solve correspondence or prove residual deformation is injective.
    const center = name => [0, 1].map(k => routes.reduce((s, r) => s + (r.weight / a.total) * r[name][k], 0));
    const start = center('start'), end = center('end');
    let dot = 0, cross = 0;
    for (const r of routes) {
      const x = r.start[0] - start[0], y = r.start[1] - start[1];
      const X = r.end[0] - end[0], Y = r.end[1] - end[1];
      dot += (r.weight / a.total) * (x * X + y * Y);
      cross += (r.weight / a.total) * (x * Y - y * X);
    }
    if (![...start, ...end, dot, cross].every(finite)) fail('Rigid fit overflow');
    let angle = dot === 0 && cross === 0 ? 0 : Math.atan2(cross, dot);
    const fit = motion === 'affine-2d' ? selectAffineFit(routes,start,end,a.total,angle) : null;
    if(fit) angle=fit.angle;
    const c = Math.cos(angle), s = Math.sin(angle);
    let residualSquared = 0;
    for (const r of routes) {
      r.localStart = r.start.map((x, k) => x - start[k]);
      const dx = r.end[0] - end[0], dy = r.end[1] - end[1];
      r.localEnd = [c * dx + s * dy, -s * dx + c * dy];
      residualSquared += (r.weight / a.total) * r.localEnd.reduce((sum, x, k) => sum + (x - r.localStart[k]) ** 2, 0);
    }
    if (!finite(residualSquared)) fail('Residual overflow');
    pose = { start, end, angle, residualRms: fit?.residualRms ?? Math.sqrt(residualSquared),
      fit,
      rotationDetermined: dot !== 0 || cross !== 0 };
    for (const r of routes) r.midpoint = posedPosition(r, pose, 0.5);
  }
  const plan = freeze({ version: 1, motion, pose, dimension: a.dimension, totalWeight: a.total, source: a.atoms, target: b.atoms, routes });
  prepared.add(plan);
  return plan;
}

function selectAffineFit(routes,start,end,total,rigidAngle) {
  const points=routes.map(r=>({x:r.start.map((v,k)=>v-start[k]),y:r.end.map((v,k)=>v-end[k]),w:r.weight/total}));
  const apply=(m,x)=>[m[0]*x[0]+m[1]*x[1],m[2]*x[0]+m[3]*x[1]];
  const error=m=>Math.sqrt(points.reduce((sum,p)=>sum+p.w*apply(m,p.x).reduce((s,v,k)=>s+(v-p.y[k])**2,0),0));
  const extent=Math.sqrt(points.reduce((s,p)=>s+p.w*(p.x[0]**2+p.x[1]**2+p.y[0]**2+p.y[1]**2),0));
  if(!finite(extent)) fail('Affine fit overflow');
  const tolerance=TOLERANCE*extent;
  const c=Math.cos(rigidAngle),s=Math.sin(rigidAngle);
  const candidates=[{kind:'translation',matrix:[1,0,0,1],angle:0},{kind:'rigid',matrix:[c,-s,s,c],angle:rigidAngle}];
  let xx=0,xy=0,yy=0,ax=0,ay=0,bx=0,by=0;
  for(const p of points){
    xx+=p.w*p.x[0]*p.x[0];xy+=p.w*p.x[0]*p.x[1];yy+=p.w*p.x[1]*p.x[1];
    ax+=p.w*p.y[0]*p.x[0];ay+=p.w*p.y[0]*p.x[1];
    bx+=p.w*p.y[1]*p.x[0];by+=p.w*p.y[1]*p.x[1];
  }
  const scale=xx+yy===0?1:(c*(ax+by)+s*(bx-ay))/(xx+yy);
  if(scale>0&&finite(scale))candidates.push({kind:'similarity',matrix:[scale*c,-scale*s,scale*s,scale*c],angle:rigidAngle});
  const covarianceDet=xx*yy-xy*xy;
  const fullRank=finite(covarianceDet)&&covarianceDet>1e-12*(xx+yy)**2;
  if(fullRank){
    const matrix=[(ax*yy-ay*xy)/covarianceDet,(ay*xx-ax*xy)/covarianceDet,
      (bx*yy-by*xy)/covarianceDet,(by*xx-bx*xy)/covarianceDet];
    if(!matrix.every(finite))fail('Affine fit overflow');
    const determinant=matrix[0]*matrix[3]-matrix[1]*matrix[2];
    if(!finite(determinant))fail('Affine determinant overflow');
    const residual=error(matrix);
    if(determinant<=0&&residual<=tolerance)fail('Singular or orientation-reversing affine map requires an explicit event or higher-dimensional path');
    if(determinant>0)candidates.push({kind:'affine',matrix,angle:Math.atan2(matrix[2]-matrix[1],matrix[0]+matrix[3])});
  }
  // Hard preference for the simplest adequate family; morphology is residual only.
  const scored=candidates.map(candidate=>({...candidate,residualRms:error(candidate.matrix)}));
  if(scored.some(candidate=>!finite(candidate.residualRms)))fail('Affine residual overflow');
  const exact=scored.find(candidate=>candidate.residualRms<=tolerance);
  const chosen=exact??scored.reduce((a,b)=>a.residualRms<=b.residualRms?a:b);
  return {...chosen,kind:exact?chosen.kind:'morphology',baseKind:chosen.kind,fullRank,
    determinant:chosen.matrix[0]*chosen.matrix[3]-chosen.matrix[1]*chosen.matrix[2],tolerance};
}

function posedPosition(route, pose, u) {
  const local = route.localStart.map((x, k) => (1-u)*x + u*route.localEnd[k]);
  const c = Math.cos(u * pose.angle), s = Math.sin(u * pose.angle);
  return [(1-u)*pose.start[0] + u*pose.end[0] + c*local[0] - s*local[1],
    (1-u)*pose.start[1] + u*pose.end[1] + s*local[0] + c*local[1]];
}

/** Pure evaluation: seek/reverse independent of frame history. Not a physics integrator.
 * Result is a weighted measure: coincident route atoms add, not alpha-overdraw.
 */
export function sampleEmbeddingTransport(plan, t) {
  if (!prepared.has(plan)) fail('Expected a validated transport plan');
  if (!finite(t) || t < 0 || t > 1) fail('Time must be finite and in [0,1]');
  // Quintic easing: zero first/second derivative at both ends; no forced midpoint stop.
  const u = transitionClock(t).value;
  return plan.routes.map(route => {
    const position = t === 0 ? [...route.start] : t === 1 ? [...route.end] : t === 0.5 ? [...route.midpoint]
      : plan.pose ? posedPosition(route, plan.pose, u)
      : route.start.map((x, k) => (1-u)*(1-u)*x + 2*(1-u)*u*route.control[k] + u*u*route.end[k]);
    if (!position.every(finite)) fail('Sample overflow');
    return { id: route.id, source: route.source, target: route.target, weight: route.weight, position };
  });
}

/** Endpoint-side views of the SAME plan; both arrive at the shared midpoint at local t=1. */
export function sampleEmbeddingHalf(plan, side, t) {
  if (side !== 'source' && side !== 'target') fail('Unknown endpoint side');
  if (!finite(t) || t < 0 || t > 1) fail('Half time must be in [0,1]');
  return sampleEmbeddingTransport(plan, side === 'source' ? t / 2 : 1 - t / 2);
}

/** Derivatives in coordinate units/second and /second² for a declared duration.
 * All routes share a deadline. Longer travel naturally gives higher speed.
 * Positive clock speed inside (0,1) does NOT imply a nonzero geometric velocity.
 */
export function sampleEmbeddingKinematics(plan, t, duration = 1) {
  if (!finite(duration) || duration <= 0) fail('Duration must be positive and finite');
  const samples = sampleEmbeddingTransport(plan,t);
  const {value:u,velocity:du,acceleration:ddu}=transitionClock(t);
  return samples.map((sample,index)=>{
    const r=plan.routes[index];
    let first,second;
    if(plan.pose){
      const p=plan.pose,angle=p.angle,c=Math.cos(angle*u),s=Math.sin(angle*u);
      const local=r.localStart.map((x,k)=>(1-u)*x+u*r.localEnd[k]);
      const delta=r.localEnd.map((x,k)=>x-r.localStart[k]);
      const rotate=([x,y])=>[c*x-s*y,s*x+c*y];
      first=rotate([delta[0]-angle*local[1],delta[1]+angle*local[0]]).map((x,k)=>x+p.end[k]-p.start[k]);
      second=rotate([-2*angle*delta[1]-angle*angle*local[0],2*angle*delta[0]-angle*angle*local[1]]);
    }else{
      first=r.start.map((x,k)=>2*(1-u)*(r.control[k]-x)+2*u*(r.end[k]-r.control[k]));
      second=r.start.map((x,k)=>2*(x-2*r.control[k]+r.end[k]));
    }
    const endpoint=t===0||t===1;
    const velocity=first.map(x=>endpoint?0:x*du/duration);
    const acceleration=first.map((x,k)=>endpoint?0:(second[k]*du*du+x*ddu)/duration/duration);
    if (![...velocity,...acceleration].every(finite)) fail('Kinematic overflow');
    return {...sample,velocity,acceleration};
  });
}
