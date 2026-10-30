import {strokeContext,resolveStroke,DEFAULT_PLOT_STROKE} from './vf-stroke-contract.mjs';
import {renderMergedSelectionLayer} from './vf-selection-presentation.mjs';
import {unionOutlines,validateRings,regionIntersectsRectangle} from './vf-selection-outline.mjs';

// Object adapters own stable IDs, explicit click targets, hit geometry and
// projected regions. This controller owns interaction and presentation only.
export function createSelectionController({enabled=true,detailThreshold=48,hysteresis=8,
  selectionColor='#00ffff',selectionRadius=DEFAULT_PLOT_STROKE.gap+DEFAULT_PLOT_STROKE.width/2,ringWidth=DEFAULT_PLOT_STROKE.width,stroke=null,getStrokeContext=()=>strokeContext()}={}) {
  if(![detailThreshold,hysteresis,selectionRadius,ringWidth].every(Number.isFinite)||detailThreshold<=0||hysteresis<0||hysteresis>=detailThreshold||selectionRadius<0||ringWidth<=0)throw new RangeError('invalid selection metrics');
  let objects=new Map(),scope=null,selected=new Set(),detailed=new Map(),disposed=false,revision=0;
  // Bounded, private prepared geometry. Adapters may return mutable arrays and
  // have no authentic revision token: verify projected content on every frame.
  // No identity-only or caller-promised immutability shortcut is safe here.
  // Explicit external native-label groups survive compiler mesh publications.
  // Values must use the same scope/coordinates; every publication cancels an
  // in-progress gesture rather than mixing two native coordinate packets.
  let baseObjects=[],baseScope=null;const externalGroups=new Map();
  const revisionListeners=new Set();
  const advanceRevision=()=>{revision++;for(const fn of revisionListeners)fn(revision)};
  const prepared=new Map();let unionComputations=0,cacheHits=0;
  const copyPaths=paths=>paths.map(r=>r.map(p=>[...p]));
  const invalidate=()=>prepared.clear();
  function prepare(slot,regions,padding,context,tolerance=.125) {
    const content=regions.map(r=>({rings:copyPaths(validateRings(r.rings)),
      clip:r.clip?copyPaths(validateRings(r.clip)):null,fillRule:r.fillRule??'evenodd'}));
    const key=JSON.stringify([scope,[...selected],selectionColor,ringWidth,padding,context,content]);
    const previous=prepared.get(slot);
    if(previous?.key===key){cacheHits++;return previous.paths}
    unionComputations++;
    const paths=unionOutlines(content,{padding,tolerance});
    prepared.set(slot,{key,paths});return paths;
  }
  function collect() {
    const regions=[];
    for(const id of selected){const object=objects.get(id);regions.push(...object.regions());
      const size=object.detailSize?.()??0,prior=detailed.get(id)===true;
      detailed.set(id,prior?size>detailThreshold-hysteresis:size>=detailThreshold+hysteresis);
    }
    return regions;
  }
  const detailState=()=>[...selected].map(id=>[id,detailed.get(id)===true]);
  const live=()=>{if(disposed)throw new Error('selection controller is disposed')};
  const selection=()=>Object.freeze([...selected]);
  function replace(nextScope,values) {live();if(!Array.isArray(values))throw TypeError('selection objects required');const owned=[...values];install(nextScope,[...owned,...[...externalGroups.values()].flat()]);baseScope=nextScope;baseObjects=owned;}
  function registerObjects(key,values){live();if(typeof key!=='string'||!key||!Array.isArray(values))throw TypeError('issued selection group and objects required');
    const prior=externalGroups.get(key),owned=[...values];externalGroups.set(key,owned);
    try{if(baseScope!==null)install(baseScope,[...baseObjects,...[...externalGroups.values()].flat()]);}
    catch(error){if(prior)externalGroups.set(key,prior);else externalGroups.delete(key);throw error;}
    return()=>{if(!disposed&&externalGroups.get(key)===owned)removeObjects(key)};
  }
  function removeObjects(key){live();if(externalGroups.delete(key)&&baseScope!==null)install(baseScope,[...baseObjects,...[...externalGroups.values()].flat()]);}
  function metrics(){const context=getStrokeContext();
    if(stroke){const m=resolveStroke(typeof stroke==='function'?stroke():stroke,context);return {radius:m.selectionCenterOffset,width:m.cssWidth,tolerance:m.tessellationToleranceCss,contract:m};}
    // Existing UI selection is an explicitly cosmetic CSS-pixel policy. Consumers
    // selecting PDF/world rules supply stroke:{units:'world',width,gap}.
    const m=resolveStroke({units:'css-pixel',width:ringWidth,gap:Math.max(0,selectionRadius-ringWidth/2)},context);
    return {radius:selectionRadius,width:ringWidth,tolerance:m.tessellationToleranceCss,contract:m};
  }
  function install(nextScope,values) {
    live();if(typeof nextScope!=='string'||!nextScope||!Array.isArray(values))throw new TypeError('selection scope and objects required');
    const next=new Map();
    for(const value of values){
      if(typeof value.id!=='string'||!value.id||next.has(value.id)||typeof value.regions!=='function'||value.hitTest!=null&&typeof value.hitTest!=='function')throw new TypeError('invalid or duplicate selection object');
      next.set(value.id,Object.freeze({...value,clickTargets:value.clickTargets&&Object.freeze([...value.clickTargets])}));
    }
    for(const value of next.values()) {
      for(const id of [value.parentId,...(value.clickTargets||[])].filter(x=>x!=null))if(!next.has(id))throw new TypeError('unknown selection parent/target');
      const seen=new Set([value.id]);let p=value.parentId;
      while(p!=null){if(seen.has(p))throw new TypeError('cyclic selection hierarchy');seen.add(p);p=next.get(p).parentId}
    }
    if(scope!==nextScope){selected.clear();detailed.clear()}
    advanceRevision();invalidate();scope=nextScope;objects=next;selected=new Set([...selected].filter(id=>next.has(id)&&next.get(id).selectable!==false));
    detailed=new Map([...detailed].filter(([id])=>selected.has(id)));
  }
  function selectAt(point,{additive=false,clicks=1,...options}={}) {
    live();if(!enabled)return selection();
    if(!Array.isArray(point)||point.length!==2||!point.every(Number.isFinite)||!Number.isInteger(clicks)||clicks<1)throw new TypeError('finite screen point and positive click count required');
    let hit=null;
    for(const object of objects.values())if(object.pickable!==false&&object.selectable!==false&&object.hitTest?.(point,options))hit=object;
    const target=hit&&(hit.clickTargets?.[Math.min(clicks,hit.clickTargets.length)-1]??hit.id);
    if(!additive)selected.clear();if(target&&objects.get(target).selectable!==false)selected.add(target);
    return selection();
  }
  function selectRectangle(rectangle,{additive=false}={}) {
    live();if(!enabled)return selection();
    if(!Array.isArray(rectangle)||rectangle.length!==4||!rectangle.every(Number.isFinite))throw TypeError('finite rectangle required');
    // A zero-area gesture has no selection effect, including replacement.
    if(rectangle[0]===rectangle[2]||rectangle[1]===rectangle[3])return selection();
    const hits=[];
    for(const object of objects.values())if(object.pickable!==false&&object.selectable!==false&&object.regions().some(region=>regionIntersectsRectangle(region,rectangle)))hits.push(object.id);
    if(!additive)selected.clear();for(const id of hits)selected.add(id);
    invalidate();return selection();
  }
  function outlines() {
    live();const regions=collect();
    const m=metrics();return copyPaths(prepare('outline',regions,m.radius,[m,detailState()],m.tolerance));
  }
  function render(scene,{pixelRatio=1,coordinateSpace='device-pixel'}={}) {
    if(!Number.isFinite(pixelRatio)||pixelRatio<=0)throw new RangeError('positive pixel ratio required');
    if(!['css-pixel','device-pixel'].includes(coordinateSpace))throw TypeError('selection coordinate space');
    const outputRatio=coordinateSpace==='css-pixel'?1:pixelRatio;
    live();const regions=collect();
    const m=metrics();const paths=copyPaths(prepare('outline',regions,m.radius,[pixelRatio,m,detailState()],m.tolerance));
    paths.forEach((path,i)=>scene.selectionContour(scope,`selection-union:${i}`,path.map(p=>p.map(x=>x*outputRatio)),selectionColor,outputRatio,{selectionRadius:0,ringWidth:m.width,coveragePixelRatio:pixelRatio}));
    const details=[...selected].filter(id=>detailed.get(id)).flatMap(id=>objects.get(id).detailRegions?.()??[]);
    prepare('detail',details,0,[pixelRatio,detailState()]).forEach((path,i)=>scene.selectionContour(scope,`selection-detail:${i}`,path.map(p=>p.map(x=>x*outputRatio)),selectionColor,outputRatio,{selectionRadius:0,ringWidth:m.width,coveragePixelRatio:pixelRatio}));
    return paths;
  }
  function layerPaths(){
    live();const m=metrics();if(m.radius<m.width/2)throw new RangeError('merged canvas ring requires padding >= half ring width');
    const regions=collect(),context=detailState();
    return {outerPaths:copyPaths(prepare('outer',regions,m.radius+m.width/2,[context,m],m.tolerance)),innerPaths:copyPaths(prepare('inner',regions,m.radius-m.width/2,[context,m],m.tolerance))};
  }
  function clearSelection(){live();selected.clear();detailed.clear();invalidate()}
  return Object.freeze({replace,registerObjects,removeObjects,invalidateCoordinates(){live();advanceRevision();invalidate()},strokeMetrics:metrics,selectAt,selectRectangle,revision:()=>revision,subscribeRevision(fn){live();if(typeof fn!=='function')throw TypeError('revision listener required');revisionListeners.add(fn);return()=>revisionListeners.delete(fn)},isEnabled:()=>enabled,selection,clearSelection,outlines,render,layerPaths,renderLayer:(context,options={})=>renderMergedSelectionLayer(context,{...options,...layerPaths(),color:selectionColor}),
    preparationStats(){return Object.freeze({unionComputations,cacheHits,entries:prepared.size})},
    presentation(){return Object.freeze([...selected].map(id=>Object.freeze({id,detail:detailed.get(id)===true})))},
    setEnabled(value){live();advanceRevision();enabled=Boolean(value);if(!enabled)clearSelection()},
    dispose(){if(disposed)return;advanceRevision();clearSelection();objects.clear();externalGroups.clear();baseObjects=[];revisionListeners.clear();disposed=true}});
}

// Backwards-compatible callable cleanup with an explicit mode API. All points
// are canvas-local CSS pixels; adapters apply the live camera, never DPR twice.
export function bindSelectionInput(element,controller,{onChange=()=>{},onMarquee=()=>{},onModeChange=()=>{},mode='pan',enabled=true,
  local=e=>{const r=element.getBoundingClientRect();return[e.clientX-r.left,e.clientY-r.top]}}={}) {
  let active=null,allowClick=false,disposed=false;
  const validMode=value=>{if(!['pan','select'].includes(value))throw TypeError('selection mode must be pan or select');return value};
  validMode(mode);
  const usable=()=>enabled&&controller.isEnabled();
  const release=id=>{if(element.hasPointerCapture?.(id))element.releasePointerCapture(id)};
  function cancel(){const old=active;active=null;allowClick=false;try{if(old?.box)release(old.id)}finally{onMarquee(null)}}
  const unsubscribeRevision=controller.subscribeRevision?.(cancel)??(()=>{});
  const priorCursor=element.style?.cursor;
  const cursor=()=>{if(element.style)element.style.cursor=mode==='select'&&enabled?'crosshair':priorCursor??''};
  cursor();
  const stale=()=>active&&active.revision!==controller.revision();
  const boxPoint=e=>{const point=local(e),r=element.getBoundingClientRect();return[Math.max(0,Math.min(r.width,point[0])),Math.max(0,Math.min(r.height,point[1]))]};
  const down=e=>{
    if(disposed||active||e.button!==0||e.isPrimary===false||!usable())return;
    allowClick=false;const box=mode==='select';
    active={id:e.pointerId,start:box?boxPoint(e):local(e),end:box?boxPoint(e):local(e),dragged:false,box,additive:e.shiftKey===true,revision:controller.revision()};
    if(box){element.focus?.({preventScroll:true});try{element.setPointerCapture(e.pointerId)}catch(error){cancel();throw error}e.preventDefault?.();}
  };
  const move=e=>{
    if(active?.id!==e.pointerId)return;if(stale()){cancel();return;}
    active.end=active.box?boxPoint(e):local(e);if(Math.hypot(...active.end.map((v,i)=>v-active.start[i]))>=4)active.dragged=true;
    if(active.box&&active.dragged){e.preventDefault?.();onMarquee([...active.start,...active.end]);}
  };
  const up=e=>{
    if(active?.id!==e.pointerId)return;move(e);if(!active)return;
    const current=active;active=null;allowClick=!current.dragged;
    try{if(current.box&&current.dragged&&current.start[0]!==current.end[0]&&current.start[1]!==current.end[1]){controller.selectRectangle([...current.start,...current.end],{additive:current.additive});onChange(controller.selection());e.preventDefault?.();}}
    finally{try{if(current.box)release(current.id)}finally{onMarquee(null)}}
  };
  const click=e=>{if(!usable()||!allowClick||e.button!==0)return;allowClick=false;controller.selectAt(local(e),{clicks:Math.max(1,e.detail||1),additive:e.shiftKey});onChange(controller.selection())};
  const key=e=>{if(e.key!=='Escape'||!usable())return;e.preventDefault?.();if(active){cancel();return;}controller.clearSelection();onChange(controller.selection())};
  const pointercancel=e=>{if(active?.id===e.pointerId)cancel()};
  const window=element.ownerDocument?.defaultView;
  window?.addEventListener?.('scroll',cancel,true);
  window?.addEventListener?.('blur',cancel);
  window?.addEventListener?.('resize',cancel);
  const events={pointerdown:down,pointermove:move,pointerup:up,pointercancel,lostpointercapture:pointercancel,click,keydown:key};
  for(const [name,fn]of Object.entries(events))element.addEventListener(name,fn);
  const close=()=>{if(disposed)return;disposed=true;try{cancel()}finally{unsubscribeRevision();if(element.style)element.style.cursor=priorCursor??'';window?.removeEventListener?.('scroll',cancel,true);window?.removeEventListener?.('blur',cancel);window?.removeEventListener?.('resize',cancel);for(const [name,fn]of Object.entries(events))element.removeEventListener(name,fn)}};
  return Object.freeze(Object.assign(close,{cancel,getMode:()=>mode,
    setMode(value){if(disposed)throw Error('selection input is disposed');validMode(value);if(value==='select'&&!usable())throw Error('selection capability is disabled');if(value!==mode){cancel();mode=value;cursor();onModeChange(mode)}return mode},
    setEnabled(value){cancel();enabled=Boolean(value);if(!enabled&&mode!=='pan'){mode='pan';cursor();onModeChange(mode)}},
    active:()=>active?.box===true}));
}
