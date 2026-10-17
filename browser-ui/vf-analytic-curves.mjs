// Explicit polynomial branches only. No reconstruction from sampled vertices.
// Projection is an affine 2x4 world-to-CSS matrix; perspective is unsupported.
const finite = (a,n) => Array.isArray(a) && a.length===n && a.every(Number.isFinite);
export function curveContract(value) {
  if(value?.version!==1 || !Array.isArray(value.branches) || value.branches.length>1024) throw TypeError('curve version/branches');
  const ids=new Set();
  const branches=value.branches.map(b=>{
    if(typeof b.id!=='string'||!b.id||ids.has(b.id)) throw TypeError('curve branch id');
    ids.add(b.id);
    if(!Array.isArray(b.controls)||![2,3,4].includes(b.controls.length)||!b.controls.every(p=>finite(p,3))) throw TypeError('finite linear/quadratic/cubic controls required');
    const domain=b.domain??[0,1];
    if(!finite(domain,2)||domain[0]<0||domain[1]>1||domain[0]>=domain[1]) throw RangeError('finite increasing branch domain within [0,1]');
    if(!finite(b.color,4)) throw TypeError('finite branch RGBA required');
    return Object.freeze({id:b.id,controls:Object.freeze(b.controls.map(p=>Object.freeze([...p]))),domain:Object.freeze([...domain]),color:Object.freeze([...b.color])});
  });
  return Object.freeze({version:1,branches:Object.freeze(branches)});
}
function split(points,t) {
  const levels=[points];
  while(levels.at(-1).length>1) {const row=levels.at(-1);levels.push(row.slice(1).map((p,i)=>p.map((v,j)=>row[i][j]*(1-t)+v*t)));}
  return [levels.map(row=>row[0]),levels.map(row=>row.at(-1)).reverse()];
}
function distance(p,a,b) {
  const dx=b[0]-a[0],dy=b[1]-a[1],l=Math.hypot(dx,dy);
  if(!l)return Math.hypot(p[0]-a[0],p[1]-a[1]);
  const ux=dx/l,uy=dy/l,t=Math.max(0,Math.min(l,(p[0]-a[0])*ux+(p[1]-a[1])*uy));
  return Math.hypot(p[0]-a[0]-t*ux,p[1]-a[1]-t*uy);
}
export function projectCurves(contract,{matrix,pixelRatio=1,tolerance=.25,maxSegments=65536}={}) {
  if(!finite(matrix,8)||!Number.isFinite(pixelRatio)||pixelRatio<=0||!Number.isFinite(tolerance)||tolerance<=0||!Number.isSafeInteger(maxSegments)||maxSegments<1||maxSegments>65536)throw TypeError('finite affine projection/budget required');
  const project=p=>[matrix[0]*p[0]+matrix[1]*p[1]+matrix[2]*p[2]+matrix[3],matrix[4]*p[0]+matrix[5]*p[1]+matrix[6]*p[2]+matrix[7]].map(v=>v*pixelRatio);
  let count=0;
  return contract.branches.map(b=>{
    let controls=b.controls;
    const [lo,hi]=b.domain;
    if(hi<1)controls=split(controls,hi)[0];
    if(lo>0)controls=split(controls,lo/hi)[1];
    controls=controls.map(project);
    // Keep arithmetic safely below overflow; reject instead of connecting across singularities.
    if(!controls.every(p=>p.every(v=>Number.isFinite(v)&&Math.abs(v)<=1e12)))throw RangeError('projection outside finite supported range');
    const points=[controls[0]],stack=[[controls,0]];
    while(stack.length){
      const [c,depth]=stack.pop();
      const error=Math.max(...c.slice(1,-1).map(p=>distance(p,c[0],c.at(-1))),0);
      if(error<=tolerance){if(++count>maxSegments)throw RangeError('curve segment budget exceeded');points.push(c.at(-1));}
      else {if(depth>=32)throw RangeError('curve precision limit');const [a,b]=split(c,.5);stack.push([b,depth+1],[a,depth+1]);}
    }
    return {id:b.id,points,color:b.color};
  });
}
// Consume the actual vectorPacket ABI (kind 6, local cubic controls, scaled width).
export function contractFromTikzPacket(packet,id='tikz') {
  if(!finite(packet,16)||packet[12]!==6||packet[14]!==0||packet[15]!==0)throw TypeError('solid cubic vectorPacket required');
  const p=(x,y)=>[packet[0]+x,packet[1]+y,0];
  return curveContract({version:1,branches:[{id,controls:[p(0,0),p(packet[4],packet[5]),p(packet[6],packet[7]),p(packet[2],packet[3])],color:packet.slice(8,12)}]});
}
export function drawCurves(scene,scope,id,contract,projection,width) {
  if(!Number.isFinite(width)||width<0)throw RangeError('finite nonnegative stroke width required');
  const paths=projectCurves(contract,projection);
  for(const b of paths)scene.path(scope,`${id}:curve:${b.id}`,b.points,width,[{offset:0,color:b.color},{offset:1,color:b.color}]);
  return paths;
}
