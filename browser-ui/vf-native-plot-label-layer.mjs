import {prepareNativeLabelGeometry,createNativeCoordinateUpdater,formatNativePlotNumber} from './vf-native-plot-labels.mjs';
import {createAntialiasedScreenSpaceRenderer} from './vf-antialiased-screen-renderer.mjs';
const need=(v,c)=>{if(!v)throw Object.assign(Error(c),{code:c,status:'FAIL'});};
const kinds=['axis','tick','label','legend','title','annotation','coordinates'];
export function createNativePlotLabelLayer({typography,coordinates,pixelRatio=globalThis.devicePixelRatio||1}={}) {
 need(typography?.prepare&&coordinates?.worldToScreen,'PLOT_LABEL_LAYER_DEPENDENCIES');
 let labels=[],closed=false,generation=0,tail=Promise.resolve();
 function matrix(spec){const scale=spec.scale??1,anchor=spec.anchor;
  if(spec.sizeSpace==='css')return [scale,0,0,scale,anchor[0],anchor[1]];
  const project=(x,y)=>coordinates.worldToScreen([anchor[0]+x*scale,anchor[1]-y*scale,...anchor.slice(2)]).slice(0,2);
  const o=project(0,0),x=project(1,0),y=project(0,1);return [x[0]-o[0],x[1]-o[1],y[0]-o[0],y[1]-o[1],...o];
 }
 function geometry(label){const m=matrix(label.spec),key=JSON.stringify([m,pixelRatio]);
  if(label.key!==key){label.geometry=prepareNativeLabelGeometry(label.lease,typography.vectors,m,{elementId:label.spec.id,sourceId:label.spec.sourceId??label.spec.id,
   color:label.spec.color??[0,0,0,1],pixelRatio});label.key=key;}return label.geometry;
 }
 return Object.freeze({
  setLabels(specs){need(!closed&&Array.isArray(specs)&&specs.length<=64,'PLOT_LABEL_SET');const serial=++generation;
   const owned=structuredClone(specs),ids=new Set();for(const s of owned){need(typeof s.id==='string'&&s.id&&!ids.has(s.id)&&kinds.includes(s.category??'label'),'PLOT_LABEL_SPEC_ID');ids.add(s.id);
    need(Array.isArray(s.anchor)&&[2,3].includes(s.anchor.length)&&s.anchor.every(Number.isFinite)&&Number.isFinite(s.scale??1)&&(s.scale??1)>0&&['world','css'].includes(s.sizeSpace??'world'),'PLOT_LABEL_PLACEMENT');
    s.sizeSpace??='world';}
   const job=tail.then(async()=>{if(closed||serial!==generation)return false;const next=[];try{for(const spec of owned)next.push({spec,lease:await typography.prepare(spec),key:null});
    if(closed||serial!==generation){for(const label of next)label.lease.release();return false;}
    const previous=labels;labels=next;for(const l of previous)l.lease.release();return true;
   }catch(e){for(const l of next)l.lease.release();throw e;}});tail=job.catch(()=>{});return job;
  },
  render(scene,frame){for(const label of labels)for(const [i,primitive]of geometry(label).triangles.entries())scene.primitive(frame,label.spec.id+':native:'+i,primitive);},
  selectionObjects(){return labels.filter(l=>l.spec.selectable!==false).flatMap(l=>geometry(l).objects);},
  geometry(){return labels.map(l=>geometry(l));},
  glyphOrigins(){return labels.map(l=>({elementId:l.spec.id,run:l.lease.run,bounds:[...geometry(l).bounds],baseline:[...geometry(l).baseline],provenance:l.lease.prepared.provenance,resourceIdentity:typography.resourceIdentity,engineIdentity:typography.engineIdentity,
    clusterScope:geometry(l).nativeUtf16ClusterScope,parts:geometry(l).parts.map(p=>({id:p.id,nativeKey:p.nativeKey,nativeItemIndex:p.nativeItemIndex,source:p.source}))}));},
  setPixelRatio(value){need(Number.isFinite(value)&&value>0,'PLOT_LABEL_DPR');pixelRatio=value;},
  close(){closed=true;generation++;return tail.then(()=>{for(const l of labels)l.lease.release();labels=[];return {joined:true};});}
 });
}
/** Titles/legend/annotations use the exact same concrete layer as numeric axes.
 * Bounds and tick values come from the compiler/caller; no reference positions.
 */
export function nativeAxisLabelSpecs({bounds,ticks={},axisNames={x:'x',y:'y'},scale=.025,id='plot:axes'}={}) {
 const specs=[];for(const [axis,index]of [['x',0],['y',1]]){const span=bounds?.[axis];need(span?.length===2&&span.every(Number.isFinite)&&span[1]>span[0],'PLOT_NATIVE_AXIS_BOUNDS');
  const values=ticks[axis]??Array.from({length:5},(_,i)=>span[0]+(span[1]-span[0])*i/4);need(values.length<=32&&values.every(Number.isFinite),'PLOT_NATIVE_AXIS_TICKS');
  for(const [i,v]of values.entries()){const anchor=index===0?[v,bounds.y[0]]:[bounds.x[0],v];
   specs.push({id:id+':'+axis+':tick:'+i,category:'tick',kind:'math',source:formatNativePlotNumber(v,{digits:6}),anchor,scale,sizeSpace:'world'});}
  specs.push({id:id+':'+axis+':label',category:'axis',kind:'text',source:axisNames[axis],anchor:index===0?[span[1],bounds.y[0]]:[bounds.x[0],span[1]],scale,sizeSpace:'world'});
 }return specs;
}
export async function mountNativePlotCoordinates(frame,{typography,dimensions=2,onError=()=>{},pixelRatio=globalThis.devicePixelRatio||1,
 createRenderer=createAntialiasedScreenSpaceRenderer,visible=true}={}) {
 need(frame?.ownerDocument&&[2,3].includes(dimensions),'PLOT_COORDINATE_FRAME');
 const doc=frame.ownerDocument,panel=doc.createElement('div'),canvas=doc.createElement('canvas');
 panel.className='vf-plot-native-coordinates';panel.dataset.vfFrameChrome='1';panel.dataset.coordinateEdge='right';panel.dataset.coordinateAlign='bottom';
 panel.setAttribute('role','img');panel.setAttribute('aria-label','Pointer coordinates');canvas.setAttribute('aria-hidden','true');panel.append(canvas);frame.append(panel);
 const renderer=createRenderer(canvas);let closed=false,lastLease=null,currentValues=null,currentGeometry=null,resolveReady,rejectReady;
 const ready=new Promise((resolve,reject)=>{resolveReady=resolve;rejectReady=reject;});ready.catch(()=>{});
 function draw(lease,values){const scale=1.25;const first=prepareNativeLabelGeometry(lease,typography.vectors,[scale,0,0,scale,0,0],{elementId:'plot:coordinate-pmatrix',pixelRatio});
  const [l,t,r,b]=first.bounds,pad=4,w=r-l+2*pad,h=b-t+2*pad;
  need(w<=140&&h<=140,'PLOT_COORDINATE_CONTENT_LIMIT');panel.style.width=w+'px';panel.style.height=h+'px';canvas.style.width=w+'px';canvas.style.height=h+'px';
  renderer.resize(w,h);const geometry=prepareNativeLabelGeometry(lease,typography.vectors,[scale,0,0,scale,pad-l,pad-t],{elementId:'plot:coordinate-pmatrix',pixelRatio});
  renderer.setScene({primitives:geometry.triangles});canvas.hidden=false;panel.dataset.nativeStatus='ready';panel.setAttribute('aria-label','Pointer coordinates column vector: '+values.join(', '));
  currentGeometry=geometry;currentValues=[...values];
 }
 try{await renderer.initialize();}catch(e){panel.remove();renderer.destroy();throw e;}
 panel.hidden=!visible;
 const updater=createNativeCoordinateUpdater({typography,onLabel(lease,values){if(closed)return;
   // Cache keeps this entry alive while the updater lease exists; hold a second
   // independently releasable lease for DPR redraw/lifetime, without re-shaping.
   return typography.prepare({kind:'math',source:lease.run.source}).then(held=>{if(closed){held.release();return;}try{draw(held,values);resolveReady({nativeGeometry:true,engineIdentity:typography.engineIdentity,resourceIdentity:typography.resourceIdentity});}catch(e){held.release();throw e;}lastLease?.release();lastLease=held;});
  },onError(error){canvas.hidden=true;rejectReady(error);panel.dataset.nativeStatus=error.status??'FAIL';panel.setAttribute('aria-label','Native coordinates unavailable: '+error.message);onError(error);}});
 return Object.freeze({element:panel,ready,update:values=>updater.update(values),whenIdle:()=>updater.whenIdle(),
  get visible(){return !panel.hidden;},setVisible(value){if(typeof value!=='boolean')throw TypeError('coords visibility must be boolean');panel.hidden=!value;},
  captureGeometry(){if(panel.hidden)return null;need(currentGeometry&&panel.dataset.nativeStatus==='ready','PLOT_COORDINATE_CAPTURE_NOT_READY');const p=panel.getBoundingClientRect(),f=frame.getBoundingClientRect(),dx=p.left-f.left,dy=p.top-f.top;const plate=[{kind:'face',points:[[dx,dy],[dx+p.width,dy],[dx+p.width,dy+p.height]],color:[1,1,1,1]},{kind:'face',points:[[dx,dy],[dx+p.width,dy+p.height],[dx,dy+p.height]],color:[1,1,1,1]}];return {primitives:[...plate,...currentGeometry.triangles.map(t=>({...t,points:t.points.map(([x,y])=>[x+dx,y+dy])}))],origin:{kind:'coordinate-pmatrix',source:lastLease.run.source,values:[...currentValues],provenance:lastLease.prepared.provenance,engineIdentity:typography.engineIdentity,resourceIdentity:typography.resourceIdentity},visible:true};},
  snapshot:()=>Object.freeze({visible:!panel.hidden,status:panel.dataset.nativeStatus,source:lastLease?.run.source,values:currentValues&&Object.freeze([...currentValues]),bounds:currentGeometry&&Object.freeze([...currentGeometry.bounds]),baseline:currentGeometry&&Object.freeze([...currentGeometry.baseline]),provenance:lastLease?.prepared.provenance}),
  setPlacement({edge,align}){need(['right','top'].includes(edge)&&['top','bottom','left','right'].includes(align),'PLOT_COORDINATE_PLACEMENT');panel.dataset.coordinateEdge=edge;panel.dataset.coordinateAlign=align;},
  setPixelRatio(value){need(Number.isFinite(value)&&value>0,'PLOT_COORDINATE_DPR');pixelRatio=value;if(lastLease)draw(lastLease,currentValues);},
  async close(){if(closed)return;closed=true;rejectReady(Object.assign(Error('PLOT_COORDINATES_CLOSED'),{status:'BLOCKED'}));await updater.close();lastLease?.release();renderer.destroy();panel.remove();}
 });
}
