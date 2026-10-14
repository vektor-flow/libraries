// Match identical atlas regions (including style/size), then interpolate their
// rectangles and ink. Different outlines crossfade; this is not contour morphing.
const stride=16;
function identity(packet,i){return [packet[i+12],...packet.slice(i+4,i+8)].join(',');}
export function planTransition(from,to){
 const available=new Map(),pairs=[],used=new Set();
 for(let j=0;j<to.length;j+=stride){const key=identity(to,j);if(!available.has(key))available.set(key,[]);available.get(key).push(j);}
 for(let i=0;i<from.length;i+=stride){
  const choices=available.get(identity(from,i))??[];let best=-1,distance=Infinity;
  for(const j of choices){if(used.has(j))continue;const d=(from[i]-to[j])**2+(from[i+1]-to[j+1])**2;if(d<distance){distance=d;best=j;}}
  if(best>=0){used.add(best);pairs.push([i,best]);}else pairs.push([i,-1]);
 }
 for(let j=0;j<to.length;j+=stride)if(!used.has(j))pairs.push([-1,j]);
 if(pairs.length>12000)throw Error('Transition draw limit exceeded');
 return {from,to,pairs,matched:pairs.filter(([a,b])=>a>=0&&b>=0).length};
}
export function transitionFrame(plan,progress){
 if(progress<=0)return plan.from;if(progress>=1)return plan.to;
 const t=progress**3*(progress*(progress*6-15)+10),out=new Float32Array(plan.pairs.length*stride);
 plan.pairs.forEach(([a,b],n)=>{
  const offset=n*stride,packet=a<0?plan.to:plan.from,index=a<0?b:a;out.set(packet.subarray(index,index+stride),offset);
  if(a>=0&&b>=0){for(const k of [0,1,2,3,8,9,10,11,13,14])out[offset+k]=plan.from[a+k]+(plan.to[b+k]-plan.from[a+k])*t;}
  else out[offset+11]*=a<0?t:1-t;
 });return out;
}
