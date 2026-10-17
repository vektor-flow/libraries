// CPU vector arrangement in CSS screen pixels. Rings use even-odd fill; regions
// are ORed. No raster tracing, bounding-box replacement or semantic inference.
const EPS = 1e-7;
const cross = (a,b) => a[0]*b[1]-a[1]*b[0];
const sub = (a,b) => [a[0]-b[0],a[1]-b[1]];
const lerp = (a,b,t) => [a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t];
export function validateRings(rings) {
  if (!Array.isArray(rings) || rings.some(r=>!Array.isArray(r)||r.length<3||r.some(p=>!Array.isArray(p)||p.length!==2||p.some(v=>!Number.isFinite(v)||Math.abs(v)>1e7)))) throw new TypeError('finite polygon rings in supported screen range required');
  return rings;
}
export function insideRings(p,rings) {
  let inside=false;
  for(const ring of rings) for(let i=0,j=ring.length-1;i<ring.length;j=i++) {
    const a=ring[j],b=ring[i];
    if ((a[1]>p[1])!==(b[1]>p[1]) && p[0]<(b[0]-a[0])*(p[1]-a[1])/(b[1]-a[1])+a[0]) inside=!inside;
  }
  return inside;
}
export const insideRegion=(p,r)=>insideRings(p,r.rings)&&(!r.clip||insideRings(p,r.clip));
export function strokeRegions(path,radius,{tolerance=.25}={}) {
  if(!(radius>0&&Number.isFinite(radius)&&tolerance>0))throw new RangeError('positive stroke radius/tolerance required');
  const regions=[];
  const count=Math.max(12,Math.ceil(Math.PI/Math.acos(Math.max(-1,1-Math.min(tolerance,radius)/radius))))*2;
  if(count>256)throw new RangeError('stroke tessellation exceeds supported precision budget');
  for(const p of path)regions.push({rings:[Array.from({length:count},(_,i)=>[p[0]+radius*Math.cos(i*2*Math.PI/count),p[1]+radius*Math.sin(i*2*Math.PI/count)])]});
  for(let i=1;i<path.length;i++) {
    const a=path[i-1],b=path[i],d=sub(b,a),l=Math.hypot(...d);if(l<EPS)continue;
    const n=[-d[1]*radius/l,d[0]*radius/l];
    regions.push({rings:[[[a[0]+n[0],a[1]+n[1]],[b[0]+n[0],b[1]+n[1]],[b[0]-n[0],b[1]-n[1]],[a[0]-n[0],a[1]-n[1]]]]});
  }
  return regions;
}
// Balanced spatial index: local intersections and point classification only.
// Bounds are broad-phase filters, never replacements for the actual geometry.
function bounds(points) {
  const b=[Infinity,Infinity,-Infinity,-Infinity];
  for(const p of points){b[0]=Math.min(b[0],p[0]);b[1]=Math.min(b[1],p[1]);b[2]=Math.max(b[2],p[0]);b[3]=Math.max(b[3],p[1])}return b;
}
function tree(items) {
  if(!items.length)return null;
  // Merge stored bounds directly: avoid allocating two points per item at
  // every level of the spatial tree. Geometry and traversal order are unchanged.
  const b=[Infinity,Infinity,-Infinity,-Infinity];
  for(const item of items){const a=item.bounds;
    b[0]=Math.min(b[0],a[0]);b[1]=Math.min(b[1],a[1]);
    b[2]=Math.max(b[2],a[2]);b[3]=Math.max(b[3],a[3]);
  }
  if(items.length<=8)return {bounds:b,items};
  const axis=b[2]-b[0]>=b[3]-b[1]?0:1;
  items.sort((a,c)=>a.bounds[axis]+a.bounds[axis+2]-c.bounds[axis]-c.bounds[axis+2]);
  const mid=items.length>>1;return {bounds:b,left:tree(items.slice(0,mid)),right:tree(items.slice(mid))};
}
function overlaps(a,b){return a[0]<=b[2]+EPS&&a[2]+EPS>=b[0]&&a[1]<=b[3]+EPS&&a[3]+EPS>=b[1]}
function visit(node,b,fn){
  if(!node||!overlaps(node.bounds,b))return false;
  if(node.items){for(const x of node.items)if(overlaps(x.bounds,b)&&fn(x))return true;return false}
  return visit(node.left,b,fn)||visit(node.right,b,fn);
}
// Convex glyph/face dilation is a single Minkowski polygon, rather than a
// separate circle at every vertex plus four-sided envelopes for every edge.
// The same inscribed circle approximation/tolerance as strokeRegions is used.
function convexPadding(r,padding) {
  if(r.rings.length!==1)return null;
  let ring=r.rings[0];if(ring.length>3&&ring[0][0]===ring.at(-1)[0]&&ring[0][1]===ring.at(-1)[1])ring=ring.slice(0,-1);
  let sign=0;
  for(let i=0;i<ring.length;i++){const c=cross(sub(ring[(i+1)%ring.length],ring[i]),sub(ring[(i+2)%ring.length],ring[(i+1)%ring.length]));if(Math.abs(c)>EPS){if(sign&&Math.sign(c)!==sign)return null;sign=Math.sign(c)}}
  if(!sign)return null;
  const circle=strokeRegions([[0,0]],padding)[0].rings[0];
  const points=ring.flatMap(p=>circle.map(q=>[p[0]+q[0],p[1]+q[1]])).sort((a,b)=>a[0]-b[0]||a[1]-b[1]);
  const half=ps=>{const h=[];for(const p of ps){while(h.length>=2&&cross(sub(h.at(-1),h.at(-2)),sub(p,h.at(-1)))<=EPS)h.pop();h.push(p)}return h};
  const lower=half(points),upper=half([...points].reverse());lower.pop();upper.pop();return {rings:[[...lower,...upper]],clip:r.clip};
}
// Split all crossings/collinear endpoints, retain only edges separating filled
// and empty cells, orient filled side left, and stitch. Internal seams disappear.
export function unionOutlines(regions,{padding=0,maxEdges=4096,maxTotalEdges=262144,maxIntersections=4000000}={}) {
  if(!Number.isFinite(padding)||padding<0)throw new RangeError('nonnegative padding required');
  const unique=new Map();
  for(const r of regions) {
    validateRings(r.rings);if(r.clip)validateRings(r.clip);
    const expanded=padding&&convexPadding(r,padding);
    const local=expanded?[expanded]:[r];
    if(padding&&!expanded)for(const ring of r.rings)for(const shape of strokeRegions([...ring,ring[0]],padding))local.push({...shape,clip:r.clip});
    if(local.reduce((n,s)=>n+s.rings.reduce((k,r)=>k+r.length,0)+(s.clip||[]).reduce((k,r)=>k+r.length,0),0)>maxEdges)throw new RangeError('selection vector union per-region edge budget exceeded');
    for(const shape of local)unique.set(JSON.stringify([shape.rings,shape.clip]),shape);
  }
  const shapes=[...unique.values()];
  const edges=[];
  for(const r of shapes)for(const ring of [...r.rings,...(r.clip||[])])for(let i=0;i<ring.length;i++) {
    const a=ring[i],b=ring[(i+1)%ring.length];if(Math.hypot(...sub(b,a))>EPS)edges.push({a,b,ts:[0,1],id:edges.length,bounds:bounds([a,b])});
  }
  if(edges.length>maxTotalEdges)throw new RangeError('selection vector union total edge budget exceeded');
  const edgeTree=tree([...edges]);
  const shapeTree=tree(shapes.map(shape=>({shape,bounds:bounds(shape.rings.flat())})));
  const parameter=(p,e)=>{const d=sub(e.b,e.a);return Math.abs(d[0])>Math.abs(d[1])?(p[0]-e.a[0])/d[0]:(p[1]-e.a[1])/d[1]};
  const add=(e,t)=>{if(t>=-EPS&&t<=1+EPS)e.ts.push(Math.max(0,Math.min(1,t)))};
  let intersections=0;
  for(const e of edges)visit(edgeTree,e.bounds,f=>{
    if(f.id<=e.id)return false;
    if(++intersections>maxIntersections)throw new RangeError('selection vector union local intersection budget exceeded');
    const u=sub(e.b,e.a),v=sub(f.b,f.a),w=sub(f.a,e.a),det=cross(u,v);
    if(Math.abs(det)>EPS) {const t=cross(w,v)/det,s=cross(w,u)/det;if(t>=-EPS&&t<=1+EPS&&s>=-EPS&&s<=1+EPS){add(e,t);add(f,s)}}
    else if(Math.abs(cross(w,u))<EPS){add(e,parameter(f.a,e));add(e,parameter(f.b,e));add(f,parameter(e.a,f));add(f,parameter(e.b,f))}
  return false;
  });
  const filled=p=>visit(shapeTree,[p[0],p[1],p[0],p[1]],x=>insideRegion(p,x.shape));
  const key=p=>p.map(x=>Math.round(x/EPS)).join(',');
  const boundary=new Map();
  for(const e of edges) {
    e.ts.sort((a,b)=>a-b);
    for(let i=1;i<e.ts.length;i++) {
      let a=lerp(e.a,e.b,e.ts[i-1]),b=lerp(e.a,e.b,e.ts[i]);const d=sub(b,a),l=Math.hypot(...d);if(l<EPS)continue;
      const m=lerp(a,b,.5),delta=Math.min(1e-5,l*1e-4),n=[-d[1]*delta/l,d[0]*delta/l];
      const left=filled([m[0]+n[0],m[1]+n[1]]),right=filled([m[0]-n[0],m[1]-n[1]]);
      if(left===right)continue;if(!left)[a,b]=[b,a];
      boundary.set(key(a)+'>'+key(b),{a,b,start:key(a),end:key(b)});
    }
  }
  const outgoing=new Map();
  for(const e of boundary.values()){if(!outgoing.has(e.start))outgoing.set(e.start,[]);outgoing.get(e.start).push(e)}
  const unused=new Set(boundary.values()),paths=[];
  while(unused.size) {
    const first=unused.values().next().value;let e=first;const path=[e.a];
    while(true){unused.delete(e);path.push(e.b);if(e.end===first.start)break;
      const candidates=(outgoing.get(e.end)||[]).filter(x=>unused.has(x));
      if(!candidates.length)throw new Error('selection arrangement did not close (precision limit)');
      // Keep the filled cell on the left at a touching vertex.
      const back=Math.atan2(e.a[1]-e.b[1],e.a[0]-e.b[0]);
      const turn=x=>(back-Math.atan2(x.b[1]-x.a[1],x.b[0]-x.a[0])+Math.PI*2)%(Math.PI*2);
      candidates.sort((a,b)=>turn(a)-turn(b));e=candidates[0];
    }
    paths.push(path);
  }
  return paths;
}
