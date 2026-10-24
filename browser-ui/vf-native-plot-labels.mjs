import {nativeOutlineCommands} from './vf-plot-pdf-commands.mjs';
import {textSelectionObjects} from './vf-selection-adapters.mjs';
const fail=(code,status='FAIL')=>Object.assign(Error(code),{code,status});
const need=(v,c,s)=>{if(!v)throw fail(c,s);};
const freeze=v=>{if(v&&typeof v==='object'){for(const x of Object.values(v))freeze(x);Object.freeze(v);}return v;};
export const NATIVE_PLOT_TYPOGRAPHY_VERSION='native075-plot-outlines/1';
export function nativeLabelRun({kind='text',source,display=false,role='roman'}) {
 need(typeof source==='string'&&source.length<=4096&&!/[\r\n\0]/u.test(source),'PLOT_LABEL_SOURCE');
 need(kind==='text'||kind==='math','PLOT_LABEL_KIND');need(typeof display==='boolean','PLOT_LABEL_DISPLAY');
 need(role==='roman','PLOT_LABEL_FONT_ROLE');
 return kind==='text'?{kind,text:source,role}:{kind,source,display};
}
/** Own one cache for the lifetime of one genuine native075 provider. The provider
 * is constructed by the admitted application, never from document label data.
 * Existing adapter preserves raw/frame receipts, exact font queries and order.
 */
export function createNativePlotTypography({provider,vectors,engineIdentity,resourceIdentity=provider?.resourceIdentity,
 presentationIdentity=provider?.presentationIdentity,maxEntries=128,maxItems=4096,ownProvider=false}={}) {
 need(typeof provider?.prepare==='function'&&typeof provider?.release==='function'&&vectors?.schema==='vkf.pdf-vectors/1','PLOT_NATIVE_LABEL_PROVIDER_MISSING','BLOCKED');
 need(/^e914-native075:[a-f0-9]{64}$/u.test(engineIdentity)&&resourceIdentity===provider.resourceIdentity&&resourceIdentity&&
  JSON.stringify(presentationIdentity)===JSON.stringify(provider.presentationIdentity),'PLOT_NATIVE_LABEL_IDENTITY');
 need(Number.isSafeInteger(maxEntries)&&maxEntries>0&&maxEntries<=256&&Number.isSafeInteger(maxItems)&&maxItems>0&&maxItems<=4096,'PLOT_LABEL_CACHE_LIMIT');
 const cache=new Map(),pending=new Map();let closed=false,closing,clock=0;
 const key=run=>JSON.stringify([NATIVE_PLOT_TYPOGRAPHY_VERSION,engineIdentity,resourceIdentity,presentationIdentity,run]);
 function evict(){while(cache.size>=maxEntries){const victim=[...cache].filter(([,v])=>v.refs===0).sort((a,b)=>a[1].used-b[1].used)[0];
  need(victim,'PLOT_LABEL_CACHE_PINNED');cache.delete(victim[0]);provider.release(victim[1].prepared);}}
 function lease(entry){entry.refs++;entry.used=++clock;let released=false;
  return Object.freeze({run:entry.run,prepared:entry.prepared,box:entry.prepared.box,
   release(){if(released)return;released=true;entry.refs--;}});}
 async function prepare(spec){need(!closed,'PLOT_LABELS_CLOSED');const run=nativeLabelRun(spec),k=key(run);
  let entry=cache.get(k);
  if(!entry){let job=pending.get(k);if(!job){need(pending.size<32,'PLOT_LABEL_QUEUE_LIMIT');
    job=(async()=>{const prepared=await provider.prepare(run);let retained=false;
     try {need(prepared?.box?.complete===true&&Array.isArray(prepared.box.items)&&prepared.box.items.length<=maxItems,'PLOT_LABEL_INCOMPLETE');
      need(prepared.provenance?.kind==='native075-io-component'&&prepared.provenance.resourceIdentity===resourceIdentity,'PLOT_LABEL_NATIVE_PROVENANCE');
      for(const item of prepared.box.items)if(item.kind==='glyph')need(vectors.paths?.[vectors.keys?.[item.key]],'PLOT_LABEL_MISSING_PHYSICAL_GLYPH');
      else need(item.kind==='rule','PLOT_LABEL_UNSUPPORTED_ITEM');
      evict();const e={run:freeze(run),prepared,refs:0,used:++clock};cache.set(k,e);retained=true;return e;
     }finally{if(!retained)provider.release(prepared);}
    })();pending.set(k,job);job.finally(()=>pending.delete(k)).catch(()=>{});
   }entry=await job;
  }
  need(!closed,'PLOT_LABELS_CLOSED');return lease(entry);
 }
 return Object.freeze({prepare,vectors,engineIdentity,resourceIdentity,presentationIdentity,
  stats:()=>({entries:cache.size,pending:pending.size,leases:[...cache.values()].reduce((n,e)=>n+e.refs,0),maxEntries,maxItems}),
  close(){if(closing)return closing;closed=true;closing=(async()=>{await Promise.allSettled([...pending.values()]);
   const errors=[];if([...cache.values()].some(e=>e.refs))errors.push(fail('PLOT_LABEL_LEASES_NOT_RELEASED'));for(const e of cache.values())try{provider.release(e.prepared);}catch(e){errors.push(e);}cache.clear();if(ownProvider)try{await provider.close();}catch(e){errors.push(e);}if(errors.length)throw new AggregateError(errors,'Native label cache cleanup failed');return {joined:true};})();return closing;}
 });
}
const point=(m,p)=>[m[0]*p[0]+m[2]*p[1]+m[4],m[1]*p[0]+m[3]*p[1]+m[5]];
const distance=(p,a,b)=>{const dx=b[0]-a[0],dy=b[1]-a[1];return Math.hypot(dx,dy)?Math.abs(dx*(a[1]-p[1])-(a[0]-p[0])*dy)/Math.hypot(dx,dy):Math.hypot(p[0]-a[0],p[1]-a[1]);};
/** Adaptive physical outlines; tolerance is in projected DEVICE pixels. Native
 * positions/scales/holes are never replaced by text bounds. Same rings feed GPU
 * filled faces, PDF capture and the existing shared selection adapter/kernel.
 */
export function nativeOutlineRings(commands,matrix,{tolerance=.125,maxDepth=18,maxPoints=65536}={}) {
 need(matrix?.length===6&&matrix.every(Number.isFinite)&&tolerance>0,'PLOT_LABEL_TRANSFORM');
 const rings=[];let ring,current,origin,count=0;
 const add=p=>{need(++count<=maxPoints,'PLOT_LABEL_OUTLINE_LIMIT');if(!ring.length||Math.hypot(p[0]-ring.at(-1)[0],p[1]-ring.at(-1)[1])>1e-12)ring.push(p);};
 function curve(a,b,c,d,depth=0){if(Math.max(distance(b,a,d),distance(c,a,d))<=tolerance){add(d);return;}
  need(depth<maxDepth,'PLOT_LABEL_CURVE_PRECISION');const mid=(x,y)=>[(x[0]+y[0])/2,(x[1]+y[1])/2],ab=mid(a,b),bc=mid(b,c),cd=mid(c,d),abc=mid(ab,bc),bcd=mid(bc,cd),m=mid(abc,bcd);
  curve(a,ab,abc,m,depth+1);curve(m,bcd,cd,d,depth+1);}
 for(const c of commands){if(c[0]==='M'){if(ring?.length>2)rings.push(ring);ring=[];current=point(matrix,c.slice(1));origin=current;add(current);}
  else if(c[0]==='L'){need(ring,'PLOT_LABEL_PATH');current=point(matrix,c.slice(1));add(current);}
  else if(c[0]==='C'){need(ring,'PLOT_LABEL_PATH');const end=point(matrix,c.slice(5));curve(current,point(matrix,c.slice(1,3)),point(matrix,c.slice(3,5)),end);current=end;}
  else if(c[0]==='Z'){need(ring,'PLOT_LABEL_PATH');if(ring.length>2){if(Math.hypot(ring.at(-1)[0]-origin[0],ring.at(-1)[1]-origin[1])<=1e-12)ring.pop();rings.push(ring);}ring=null;current=origin;}
  else throw fail('PLOT_LABEL_PATH_OPERATOR');}
 if(ring?.length>2)rings.push(ring);return rings;
}
/** Nonzero winding scan conversion of physical contours into filled triangles.
 * Horizontal slabs include every native contour vertex; holes remain empty.
 * No stencil/font/shaper or dependency on a reference raster is involved.
 */
export function triangulateNativeRings(rings) {
 const edges=[],ys=[];for(const ring of rings)for(let i=0;i<ring.length;i++){const a=ring[i],b=ring[(i+1)%ring.length];ys.push(a[1]);if(a[1]!==b[1])edges.push({a,b,w:b[1]>a[1]?1:-1});}
 const levels=[...new Set(ys)].sort((a,b)=>a-b),triangles=[];
 const x=(e,y)=>e.a[0]+(e.b[0]-e.a[0])*(y-e.a[1])/(e.b[1]-e.a[1]);
 for(let i=1;i<levels.length;i++){const lo=levels[i-1],hi=levels[i];if(hi-lo<1e-12)continue;const mid=(lo+hi)/2;
  const active=edges.filter(e=>mid>Math.min(e.a[1],e.b[1])&&mid<Math.max(e.a[1],e.b[1])).sort((a,b)=>x(a,mid)-x(b,mid));
  let winding=0,left;
  for(const e of active){const old=winding;winding+=e.w;if(old===0&&winding!==0)left=e;
   if(old!==0&&winding===0){const a=[x(left,lo),lo],b=[x(e,lo),lo],c=[x(e,hi),hi],d=[x(left,hi),hi];
    if(Math.abs(b[0]-a[0])>1e-12)triangles.push([a,b,c]);if(Math.abs(c[0]-d[0])>1e-12)triangles.push([a,c,d]);}}
  need(winding===0,'PLOT_LABEL_UNCLOSED_WINDING');need(triangles.length<=50000,'PLOT_LABEL_TRIANGLE_LIMIT');
 }return triangles;
}
export function prepareNativeLabelGeometry(lease,vectors,matrix,{elementId,sourceId=elementId,color=[0,0,0,1],pixelRatio=1,tolerance=.125}={}) {
 need(typeof elementId==='string'&&elementId&&typeof sourceId==='string'&&sourceId&&pixelRatio>0,'PLOT_LABEL_ID');
 const source=lease.run.kind==='text'?lease.run.text:lease.run.source,parts=[],triangles=[];
 const items=lease.box.items;
 for(let index=0;index<items.length;index++){const item=items[index];need(!item.clip&&!item.crop,'PLOT_LABEL_CLIPPING_UNSUPPORTED');let commands;
  if(item.kind==='glyph'){const path=vectors.paths?.[vectors.keys?.[item.key]];need(path,'PLOT_LABEL_MISSING_PHYSICAL_GLYPH');commands=nativeOutlineCommands(path.operators);}
  else {need(item.kind==='rule'&&[item.width,item.height].every(n=>Number.isFinite(n)&&n>=0),'PLOT_LABEL_RULE');commands=[['M',0,0],['L',item.width,0],['L',item.width,item.height],['L',0,item.height],['Z']];}
  const sx=item.sx??1,sy=item.sy??1,m=[matrix[0]*sx,matrix[1]*sx,matrix[2]*sy,matrix[3]*sy,
   matrix[0]*item.x+matrix[2]*item.y+matrix[4],matrix[1]*item.x+matrix[3]*item.y+matrix[5]];
  const device=m.map((v)=>v*pixelRatio),deviceRings=nativeOutlineRings(commands,device,{tolerance}),rings=deviceRings.map(r=>r.map(p=>p.map(v=>v/pixelRatio)));
  const text=lease.run.kind==='text';need(!text||(Number.isSafeInteger(item.start)&&Number.isSafeInteger(item.stop)),'PLOT_LABEL_NATIVE_UTF16_CLUSTER_MISSING');
  // Math075 has no exposed per-glyph origin. Keep one honest whole-run math
  // cluster instead of guessing character positions from glyphs or source.
  const start=text?item.start:0,end=text?item.stop:source.length;
  if(rings.length)parts.push({id:elementId+':cluster:'+start+':'+end,groupId:text?null:elementId+':math',rings,nativeKey:item.key??null,nativeItemIndex:index,
   source:{id:sourceId,text:source,offsetUnit:'utf16',start,end}});
  for(const points of triangulateNativeRings(rings))triangles.push({kind:'face',points,color:item.color??color});
 }
 const groups=lease.run.kind==='math'?[{id:elementId+':math',kind:'math'}]:[];
 const objects=textSelectionObjects({elementId,clusters:parts,groups,coordinates:{worldToScreen:p=>p}});
 const [a,b,c,d,e,f]=matrix,box=lease.box;
 const logical=[[0,-box.height],[box.width,-box.height],[box.width,box.depth],[0,box.depth]].map(p=>point(matrix,p));
 const all=[...logical,...parts.flatMap(p=>p.rings.flat())],bounds=[Math.min(...all.map(p=>p[0])),Math.min(...all.map(p=>p[1])),Math.max(...all.map(p=>p[0])),Math.max(...all.map(p=>p[1]))];
 return {elementId,parts,objects,triangles,bounds,baseline:point(matrix,[0,0]),provenance:lease.prepared.provenance,
  nativeUtf16ClusterScope:lease.run.kind==='text'?'native literal clusters':'whole math run; per-glyph native origins unavailable'};
}
export function formatNativePlotNumber(n,{digits=4}={}) {
 need(Number.isFinite(n)&&Number.isInteger(digits)&&digits>=1&&digits<=6,'PLOT_NATIVE_NUMBER');
 const rounded=Number(n.toPrecision(digits));const s=Number.isFinite(rounded)?rounded.toString():n.toExponential(digits-1);if(!/[eE]/.test(s))return s==='0'?'0':s;
 const [m,e]=s.toLowerCase().split('e');return m+'\\times 10^{'+Number(e)+'}';
}
export function coordinatePmatrixSource(values,options={}) {
 need(Array.isArray(values)&&[2,3].includes(values.length)&&values.every(Number.isFinite),'PLOT_COORDINATES');
 return '\\begin{pmatrix}'+values.map(v=>formatNativePlotNumber(v,options)).join('\\\\')+'\\end{pmatrix}';
}
/** Single native request in flight, one replaceable latest value, bounded cache.
 * No process creation, compiler, file hash, font acquisition or shaper here.
 */
export function createNativeCoordinateUpdater({typography,onLabel,onError=()=>{},interval=50}) {
 let latest=null,active=null,closed=false,tail=Promise.resolve(),timer=null;
 function pump(){if(active||closed||!latest)return;const values=latest;latest=null;
  active=(async()=>{let lease;try{lease=await typography.prepare({kind:'math',source:coordinatePmatrixSource(values)});if(!closed)await onLabel(lease,values);}
   catch(e){if(!closed)onError(e);}finally{lease?.release();}})();
  tail=active.finally(()=>{active=null;if(latest&&!closed)timer=setTimeout(()=>{timer=null;pump();},interval);});tail.catch(()=>{});
 }
 return Object.freeze({update(values){need(!closed,'PLOT_COORDINATES_CLOSED');coordinatePmatrixSource(values);latest=[...values];pump();},
  async whenIdle(){while(active||latest||timer){if(timer){clearTimeout(timer);timer=null;}if(!active)pump();await tail;}},
  async close(){closed=true;latest=null;clearTimeout(timer);timer=null;await tail;return {joined:true};}});
}
