/** One normalized clock for geometry, branching and observable attributes. */
export function transitionClock(t,duration=1) {
  if(typeof t!=='number'||!Number.isFinite(t)||t<0||t>1||typeof duration!=='number'||!Number.isFinite(duration)||duration<=0)throw new TypeError('Invalid transition time or duration');
  const value=t*t*t*(10+t*(-15+6*t));
  const velocity=t===0||t===1?0:30*t*t*(1-t)*(1-t)/duration;
  const acceleration=t===0||t===1?0:60*t*(1-t)*(1-2*t)/duration/duration;
  if(!Number.isFinite(velocity)||!Number.isFinite(acceleration))throw new TypeError('Transition clock overflow');
  return {value,velocity,acceleration};
}
