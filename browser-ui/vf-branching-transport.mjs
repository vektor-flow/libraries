// Constructed moving-branch example, not an optimizer or a conserved-mass model.
import {transitionClock} from './vf-transition-clock.mjs';
const plans=new WeakSet();
const finite=x=>typeof x==='number'&&Number.isFinite(x);
const point=p=>Array.isArray(p)&&p.length===2&&p.every(finite);
const fail=m=>{throw new TypeError(m);};
export function createBranchingCopies({source,targets,radius,separationPower=2}) {
  if(!point(source)||!Array.isArray(targets)||targets.length<2||targets.length>16||!targets.every(p=>point(p.position)&&typeof p.id==='string'&&p.id))fail('Expected a 2D source and 2..16 named targets');
  if(new Set(targets.map(p=>p.id)).size!==targets.length)fail('Duplicate target ID');
  if(!finite(radius)||radius<=0)fail('Positive finite radius required');
  if(!Number.isInteger(separationPower)||separationPower<1||separationPower>6)fail('Separation power must be an integer from 1 to 6');
  const center=[0,1].map(k=>targets.reduce((sum,p)=>sum+p.position[k]/targets.length,0));
  if(!center.every(finite))fail('Center overflow');
  const copyTargets=targets.map(p=>Object.freeze({id:p.id,position:Object.freeze([...p.position])}));
  const plan=Object.freeze({version:1,mode:'visual-duplication',source:Object.freeze([...source]),targets:Object.freeze(copyTargets),center:Object.freeze(center),radius,separationPower});
  plans.add(plan);return plan;
}

export function sampleBranchingCopies(plan,t,duration=1) {
  if(!plans.has(plan)||!finite(t)||t<0||t>1||!finite(duration)||duration<=0)fail('Invalid plan, time or duration');
  const {value:u,velocity:du,acceleration:ddu}=transitionClock(t);
  const power=plan.separationPower,spread=u**power,end=t===0||t===1;
  const dSpread=end?0:power*u**(power-1)*du;
  const ddSpread=end?0:(power===1?0:power*(power-1)*u**(power-2)*du*du)+power*u**(power-1)*ddu;
  return plan.targets.map(target=>{
    const delta=plan.center.map((x,k)=>x-plan.source[k]);
    const offset=target.position.map((x,k)=>x-plan.center[k]);
    const position=t===0?[...plan.source]:t===1?[...target.position]:delta.map((x,k)=>plan.source[k]+u*x+spread*offset[k]);
    const velocity=delta.map((x,k)=>end?0:(du*x+dSpread*offset[k])/duration);
    const acceleration=delta.map((x,k)=>end?0:(ddu*x+ddSpread*offset[k])/duration/duration);
    if(![...position,...velocity,...acceleration].every(finite))fail('Branch evaluation overflow');
    return {id:target.id,position,velocity,acceleration,radius:plan.radius,mode:plan.mode};
  });
}
