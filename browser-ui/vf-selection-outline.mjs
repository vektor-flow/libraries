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
export function insideRings(p,rings,{fillRule='evenodd'}={}) {
  if(!['evenodd','nonzero'].includes(fillRule))throw TypeError('unsupported physical fill rule');
  let winding=0;
  for(const ring of rings)for(let i=0,j=ring.length-1;i<ring.length;j=i++){
    const a=ring[j],b=ring[i];
    if((a[1]>p[1])!==(b[1]>p[1])&&p[0]<(b[0]-a[0])*(p[1]-a[1])/(b[1]-a[1])+a[0])winding+=b[1]>a[1]?1:-1;
  }
  return fillRule==='nonzero'?winding!==0:Math.abs(winding)%2===1;
}
export const insideRegion=(p,r)=>insideRings(p,r.rings,{fillRule:r.fillRule??'evenodd'})&&(!r.clip||insideRings(p,r.clip));
export function strokeRegions(path,radius,{tolerance=.25}={}) {
  if(!(radius>0&&Number.isFinite(radius)&&tolerance>0))throw new RangeError('positive stroke radius/tolerance required');
  const regions=[];
  const count=Math.max(12,Math.ceil(Math.PI/Math.acos(Math.max(-1,1-Math.min(tolerance,radius)/radius))))*2;
  if(count>4096)throw new RangeError('stroke tessellation exceeds supported precision budget');
  // One convex round capsule per drawn segment. The previous decomposition
  // into two disks and a rectangle generated redundant overlapping arrangement
  // edges at every sample, exhausting resources at high DPR. These arcs use
  // the same radius/chord precision and exact segment normals, with no change
  // to the physical centerline or a bounds approximation.
  for(let i=1;i<path.length;i++) {
    const a=path[i-1],b=path[i],d=sub(b,a),l=Math.hypot(...d);if(l===0)continue;
    const angle=Math.atan2(d[1],d[0]),half=count/2,ring=[];
    for(let j=0;j<=half;j++){const t=angle+Math.PI/2+j*Math.PI/half;ring.push([a[0]+radius*Math.cos(t),a[1]+radius*Math.sin(t)])}
    for(let j=0;j<=half;j++){const t=angle-Math.PI/2+j*Math.PI/half;ring.push([b[0]+radius*Math.cos(t),b[1]+radius*Math.sin(t)])}
    regions.push({rings:[ring]});
  }
  if(!regions.length)for(const p of path)regions.push({rings:[Array.from({length:count},(_,i)=>[p[0]+radius*Math.cos(i*2*Math.PI/count),p[1]+radius*Math.sin(i*2*Math.PI/count)])]});
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
function convexPadding(r,padding,tolerance) {
  if(r.rings.length!==1)return null;
  let ring=r.rings[0];if(ring.length>3&&ring[0][0]===ring.at(-1)[0]&&ring[0][1]===ring.at(-1)[1])ring=ring.slice(0,-1);
  let sign=0;
  for(let i=0;i<ring.length;i++){const c=cross(sub(ring[(i+1)%ring.length],ring[i]),sub(ring[(i+2)%ring.length],ring[(i+1)%ring.length]));if(Math.abs(c)>EPS){if(sign&&Math.sign(c)!==sign)return null;sign=Math.sign(c)}}
  if(!sign)return null;
  const circle=strokeRegions([[0,0]],padding,{tolerance})[0].rings[0];
  const points=ring.flatMap(p=>circle.map(q=>[p[0]+q[0],p[1]+q[1]])).sort((a,b)=>a[0]-b[0]||a[1]-b[1]);
  const half=ps=>{const h=[];for(const p of ps){while(h.length>=2&&cross(sub(h.at(-1),h.at(-2)),sub(p,h.at(-1)))<=EPS)h.pop();h.push(p)}return h};
  const lower=half(points),upper=half([...points].reverse());lower.pop();upper.pop();return {rings:[[...lower,...upper]],clip:r.clip};
}
// Split all crossings/collinear endpoints, retain only edges separating filled
// and empty cells, orient filled side left, and stitch. Internal seams disappear.
export function unionOutlines(regions,{padding=0,tolerance=.125,maxEdges=16384,maxTotalEdges=262144,maxIntersections=4000000,maxArrangementNodes=131072}={}) {
  if(!Number.isFinite(padding)||padding<0)throw new RangeError('nonnegative padding required');
  const unique=new Map();
  for(const r of regions) {
    validateRings(r.rings);if(r.clip)validateRings(r.clip);
    const expanded=padding&&convexPadding(r,padding,tolerance);
    const local=expanded?[expanded]:[r];
    if(padding&&!expanded)for(const ring of r.rings)for(const shape of strokeRegions([...ring,ring[0]],padding,{tolerance}))local.push({...shape,clip:r.clip});
    if(local.reduce((n,s)=>n+s.rings.reduce((k,r)=>k+r.length,0)+(s.clip||[]).reduce((k,r)=>k+r.length,0),0)>maxEdges)throw new RangeError('selection vector union per-region edge budget exceeded');
    for(const shape of local)unique.set(JSON.stringify([shape.rings,shape.clip,shape.fillRule]),shape);
  }
  const shapes=[...unique.values()];
  // Arrangement vertices are shared by incidence, not independently rounded
  // endpoints. In particular, nearly parallel intersections must not be called
  // collinear merely because their determinant is smaller than a length EPS.
  const nodes=[],cells=new Map();
  const cellSize=EPS; // broad phase only, never the coordinate snap precision
  const node=p=>{
    const cell=p.map(x=>Math.floor(x/cellSize));
    const error=Math.min(EPS/16,64*Number.EPSILON*Math.max(1,Math.abs(p[0]),Math.abs(p[1])));
    for(let dx=-1;dx<=1;dx++)for(let dy=-1;dy<=1;dy++)for(const n of cells.get([cell[0]+dx,cell[1]+dy].join(','))||[])
      if(Math.hypot(p[0]-n.p[0],p[1]-n.p[1])<=error)return n;
    if(nodes.length>=maxArrangementNodes)throw new RangeError('selection vector union arrangement node budget exceeded');
    const n={p,id:nodes.length};nodes.push(n);const key=cell.join(',');if(!cells.has(key))cells.set(key,[]);cells.get(key).push(n);return n;
  };
  const edges=[];
  for(const r of shapes)for(const ring of [...r.rings,...(r.clip||[])])for(let i=0;i<ring.length;i++) {
    const a=ring[i],b=ring[(i+1)%ring.length];if(a[0]!==b[0]||a[1]!==b[1])edges.push({a,b,splits:[{t:0,node:node(a)},{t:1,node:node(b)}],id:edges.length,bounds:bounds([a,b])});
  }
  if(edges.length>maxTotalEdges)throw new RangeError('selection vector union total edge budget exceeded');
  const edgeTree=tree([...edges]);
  const shapeTree=tree(shapes.map(shape=>({shape,bounds:bounds(shape.rings.flat())})));
  const parameter=(p,e)=>{const d=sub(e.b,e.a);return Math.abs(d[0])>Math.abs(d[1])?(p[0]-e.a[0])/d[0]:(p[1]-e.a[1])/d[1]};
  const add=(e,t,n)=>{if(t>=0&&t<=1)e.splits.push({t,node:n})};
  let intersections=0;
  for(const e of edges)visit(edgeTree,e.bounds,f=>{
    if(f.id<=e.id)return false;
    if(++intersections>maxIntersections)throw new RangeError('selection vector union local intersection budget exceeded');
    const u=sub(e.b,e.a),v=sub(f.b,f.a),w=sub(f.a,e.a),det=cross(u,v);
    if(det!==0) {
      const t=cross(w,v)/det,s=cross(w,u)/det;
      if(t>=0&&t<=1&&s>=0&&s<=1){
        const p=t===0?e.a:t===1?e.b:s===0?f.a:s===1?f.b:lerp(e.a,e.b,t);
        const n=node(p);add(e,t,n);add(f,s,n);
      }
    } else if(cross(w,u)===0){
      for(const n of [e.splits[0].node,e.splits[1].node,f.splits[0].node,f.splits[1].node]){add(e,parameter(n.p,e),n);add(f,parameter(n.p,f),n)}
    }
    return false;
  });
  const filled=p=>visit(shapeTree,[p[0],p[1],p[0],p[1]],x=>insideRegion(p,x.shape));
  const boundary=new Map();
  for(const e of edges) {
    e.splits.sort((a,b)=>a.t-b.t);
    for(let i=1;i<e.splits.length;i++) {
      let na=e.splits[i-1].node,nb=e.splits[i].node;if(na===nb)continue;
      let a=na.p,b=nb.p;const d=sub(b,a),l=Math.hypot(...d);if(l===0)continue;
      const m=lerp(a,b,.5);
      // Samples must stay in the two incident cells. Fixed offsets can cross
      // another edge of a narrow sliver and erase only half of its boundary.
      let delta=Math.min(1e-5,l*1e-4);
      const reach=[m[0]-delta,m[1]-delta,m[0]+delta,m[1]+delta];
      visit(edgeTree,reach,f=>{
        const u=sub(f.b,f.a),len=Math.hypot(...u);if(!len)return false;
        const t=Math.max(0,Math.min(1,((m[0]-f.a[0])*u[0]+(m[1]-f.a[1])*u[1])/(len*len)));
        const q=lerp(f.a,f.b,t),distance=Math.hypot(m[0]-q[0],m[1]-q[1]);
        const error=Math.min(EPS/16,128*Number.EPSILON*Math.max(1,Math.abs(m[0]),Math.abs(m[1])));
        if(distance>error)delta=Math.min(delta,distance/4);
        return false;
      });
      const n=[-d[1]*delta/l,d[0]*delta/l];
      const left=filled([m[0]+n[0],m[1]+n[1]]),right=filled([m[0]-n[0],m[1]-n[1]]);
      if(left===right)continue;if(!left){[a,b]=[b,a];[na,nb]=[nb,na]}
      boundary.set(na.id+'>'+nb.id,{a,b,start:na.id,end:nb.id});
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

// Rectangle intersection against the actual even-odd fill and optional clip.
// Test arrangement vertices, not geometry bounds: includes edge crossings,
// containment, holes and clip-created corners. Boundary contact counts.
export function regionIntersectsRectangle(region, rectangle) {
  const [x0,y0,x1,y1]=rectangle;
  if(rectangle.length!==4||!rectangle.every(Number.isFinite))throw TypeError('finite rectangle required');
  const left=Math.min(x0,x1),right=Math.max(x0,x1),top=Math.min(y0,y1),bottom=Math.max(y0,y1);
  if(left===right||top===bottom)return false;
  const rings=validateRings(region.rings),clip=region.clip&&validateRings(region.clip);
  const box=[[[left,top],[right,top],[right,bottom],[left,bottom]]];
  const edges=rs=>rs.flatMap(r=>r.map((a,i)=>[a,r[(i+1)%r.length]]));
  const on=(p,a,b)=>Math.abs(cross(sub(p,a),sub(b,a)))<=EPS*Math.max(1,Math.hypot(...sub(b,a)))&&p[0]>=Math.min(a[0],b[0])-EPS&&p[0]<=Math.max(a[0],b[0])+EPS&&p[1]>=Math.min(a[1],b[1])-EPS&&p[1]<=Math.max(a[1],b[1])+EPS;
  const contains=(p,rs,es,fillRule='evenodd')=>insideRings(p,rs,{fillRule})||es.some(([a,b])=>on(p,a,b));
  const re=edges(rings),ce=clip?edges(clip):[],be=edges(box);
  const hit=p=>p[0]>=left-EPS&&p[0]<=right+EPS&&p[1]>=top-EPS&&p[1]<=bottom+EPS&&contains(p,rings,re,region.fillRule??'evenodd')&&(!clip||contains(p,clip,ce));
  for(const r of [...rings,...(clip||[]),...box])for(const point of r)if(hit(point))return true;
  for(const [aa,bb] of [[re,be],[ce,be],[re,ce]])for(const [a,b]of aa)for(const [c,d]of bb){
    const u=sub(b,a),v=sub(d,c),w=sub(c,a),det=cross(u,v);
    if(Math.abs(det)>EPS){const t=cross(w,v)/det,s=cross(w,u)/det;if(t>=-EPS&&t<=1+EPS&&s>=-EPS&&s<=1+EPS&&hit(lerp(a,b,t)))return true;}
    else if(Math.abs(cross(w,u))<=EPS)for(const point of [a,b,c,d])if(on(point,a,b)&&on(point,c,d)&&hit(point))return true;
  }
  return false;
}
