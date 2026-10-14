import {transitionClock} from './vf-transition-clock.mjs';
const plans=new WeakSet();
const valid=x=>typeof x==='number'&&Number.isFinite(x);
function endpoint(state){
  if(!state||!valid(state.mass)||state.mass<0||!valid(state.coverage)||state.coverage<0||!valid(state.opacity)||state.opacity<0||state.opacity>1||!Array.isArray(state.color)||state.color.length!==3||!state.color.every(x=>valid(x)&&x>=0&&x<=1))throw new TypeError('Expected nonnegative mass/coverage, opacity and linear RGB in [0,1]');
  return Object.freeze({mass:state.mass,coverage:state.coverage,opacity:state.opacity,color:Object.freeze([...state.color])});
}
/** Declared scalar attributes and straight linear-light RGB. Units must agree.
 * `coverage` is continuous area/coverage, never a claimed integer pixel count.
 * A changed mass is explicit creation/removal, not conservative physical evolution.
 */
export function createVisualProperties(source,target){
  const plan=Object.freeze({source:endpoint(source),target:endpoint(target),colorSpace:'linear-srgb'});plans.add(plan);return plan;
}
export function sampleVisualProperties(plan,t,duration=1){
  if(!plans.has(plan))throw new TypeError('Expected validated properties');
  const clock=transitionClock(t,duration);
  const channel=(a,b)=>({value:t===0?a:t===1?b:(1-clock.value)*a+clock.value*b,velocity:(b-a)*clock.velocity,acceleration:(b-a)*clock.acceleration});
  const mass=channel(plan.source.mass,plan.target.mass),coverage=channel(plan.source.coverage,plan.target.coverage),opacity=channel(plan.source.opacity,plan.target.opacity);
  const color=plan.source.color.map((x,k)=>channel(x,plan.target.color[k]));
  // Multiplication follows the product rule. Premultiplied values remain smooth
  // even when alpha is zero; do not divide by zero to invent hidden RGB.
  const premultiplied=color.map(c=>({value:c.value*opacity.value,velocity:c.velocity*opacity.value+c.value*opacity.velocity,
    acceleration:c.acceleration*opacity.value+2*c.velocity*opacity.velocity+c.value*opacity.acceleration}));
  const result={mass,coverage,opacity,color,premultiplied,colorSpace:plan.colorSpace};
  if([mass,coverage,opacity,...color,...premultiplied].some(x=>!Object.values(x).every(valid)))throw new TypeError('Property overflow');
  return result;
}
export function linearRgbToCss(color){
  if(!Array.isArray(color)||color.length!==3||!color.every(x=>valid(x)&&x>=0&&x<=1))throw new TypeError('Invalid linear RGB');
  return `rgb(${color.map(x=>255*(x<=.0031308?12.92*x:1.055*x**(1/2.4)-.055)).join(' ')})`;
}
