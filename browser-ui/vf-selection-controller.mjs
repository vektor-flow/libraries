import {renderMergedSelectionLayer} from './vf-selection-presentation.mjs';
import {unionOutlines,validateRings} from './vf-selection-outline.mjs';

// Object adapters own stable IDs, explicit click targets, hit geometry and
// projected regions. This controller owns interaction and presentation only.
export function createSelectionController({enabled=true,detailThreshold=48,hysteresis=8,
  selectionColor='#00ffff',selectionRadius=4,ringWidth=2}={}) {
  if(![detailThreshold,hysteresis,selectionRadius,ringWidth].every(Number.isFinite)||detailThreshold<=0||hysteresis<0||hysteresis>=detailThreshold||selectionRadius<0||ringWidth<=0)throw new RangeError('invalid selection metrics');
  let objects=new Map(),scope=null,selected=new Set(),detailed=new Map(),disposed=false;
  // Bounded, private prepared geometry. Adapters may return mutable arrays and
  // have no authentic revision token: verify projected content on every frame.
  // No identity-only or caller-promised immutability shortcut is safe here.
  const prepared=new Map();let unionComputations=0,cacheHits=0;
  const copyPaths=paths=>paths.map(r=>r.map(p=>[...p]));
  const invalidate=()=>prepared.clear();
  function prepare(slot,regions,padding,context) {
    const content=regions.map(r=>({rings:copyPaths(validateRings(r.rings)),
      clip:r.clip?copyPaths(validateRings(r.clip)):null}));
    const key=JSON.stringify([scope,[...selected],selectionColor,ringWidth,padding,context,content]);
    const previous=prepared.get(slot);
    if(previous?.key===key){cacheHits++;return previous.paths}
    unionComputations++;
    const paths=unionOutlines(content,{padding});
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
  function replace(nextScope,values) {
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
    invalidate();scope=nextScope;objects=next;selected=new Set([...selected].filter(id=>next.has(id)&&next.get(id).selectable!==false));
    detailed=new Map([...detailed].filter(([id])=>selected.has(id)));
  }
  function selectAt(point,{additive=false,clicks=1,...options}={}) {
    live();if(!enabled)return selection();
    if(!Array.isArray(point)||point.length!==2||!point.every(Number.isFinite)||!Number.isInteger(clicks)||clicks<1)throw new TypeError('finite screen point and positive click count required');
    let hit=null;
    for(const object of objects.values())if(object.selectable!==false&&object.hitTest?.(point,options))hit=object;
    const target=hit&&(hit.clickTargets?.[Math.min(clicks,hit.clickTargets.length)-1]??hit.id);
    if(!additive)selected.clear();if(target&&objects.get(target).selectable!==false)selected.add(target);
    return selection();
  }
  function outlines() {
    live();const regions=collect();
    return copyPaths(prepare('outline',regions,selectionRadius,[1,detailState()]));
  }
  function render(scene,{pixelRatio=1}={}) {
    if(!Number.isFinite(pixelRatio)||pixelRatio<=0)throw new RangeError('positive pixel ratio required');
    live();const regions=collect();
    const paths=copyPaths(prepare('outline',regions,selectionRadius,[pixelRatio,detailState()]));
    paths.forEach((path,i)=>scene.selectionContour(scope,`selection-union:${i}`,path.map(p=>p.map(x=>x*pixelRatio)),selectionColor,pixelRatio,{selectionRadius:0,ringWidth}));
    const details=[...selected].filter(id=>detailed.get(id)).flatMap(id=>objects.get(id).detailRegions?.()??[]);
    prepare('detail',details,0,[pixelRatio,detailState()]).forEach((path,i)=>scene.selectionContour(scope,`selection-detail:${i}`,path.map(p=>p.map(x=>x*pixelRatio)),selectionColor,pixelRatio,{selectionRadius:0,ringWidth}));
    return paths;
  }
  function layerPaths(){
    live();if(selectionRadius<ringWidth/2)throw new RangeError('merged canvas ring requires padding >= half ring width');
    const regions=collect(),context=detailState();
    return {outerPaths:copyPaths(prepare('outer',regions,selectionRadius+ringWidth/2,context)),innerPaths:copyPaths(prepare('inner',regions,selectionRadius-ringWidth/2,context))};
  }
  function clearSelection(){live();selected.clear();detailed.clear();invalidate()}
  return Object.freeze({replace,selectAt,selection,clearSelection,outlines,render,layerPaths,renderLayer:(context,options={})=>renderMergedSelectionLayer(context,{...options,...layerPaths(),color:selectionColor}),
    preparationStats(){return Object.freeze({unionComputations,cacheHits,entries:prepared.size})},
    presentation(){return Object.freeze([...selected].map(id=>Object.freeze({id,detail:detailed.get(id)===true})))},
    setEnabled(value){live();enabled=Boolean(value);if(!enabled)clearSelection()},
    dispose(){if(disposed)return;clearSelection();objects.clear();disposed=true}});
}

// DOM click.detail supplies native multi-click timing/accessibility conventions.
// Pointer movement uses the retained plot's 4 CSS pixel pan threshold.
export function bindSelectionInput(element,controller,{onChange=()=>{},local=e=>{const r=element.getBoundingClientRect();return[e.clientX-r.left,e.clientY-r.top]}}={}) {
  let active=null,allowClick=false;
  const down=e=>{allowClick=false;if(e.button===0)active={id:e.pointerId,start:local(e),dragged:false}};
  const move=e=>{if(active?.id===e.pointerId&&Math.hypot(...local(e).map((v,i)=>v-active.start[i]))>=4)active.dragged=true};
  const up=e=>{if(active?.id!==e.pointerId)return;move(e);allowClick=!active.dragged;active=null};
  const cancel=()=>{active=null;allowClick=false};
  const click=e=>{if(!allowClick||e.button!==0)return;allowClick=false;controller.selectAt(local(e),{clicks:Math.max(1,e.detail||1),additive:e.shiftKey});onChange(controller.selection())};
  const key=e=>{if(e.key==='Escape'){controller.clearSelection();onChange(controller.selection())}};
  const events={pointerdown:down,pointermove:move,pointerup:up,pointercancel:cancel,lostpointercapture:()=>{if(active)cancel()},click,keydown:key};
  for(const [name,fn]of Object.entries(events))element.addEventListener(name,fn);
  return ()=>{cancel();for(const [name,fn]of Object.entries(events))element.removeEventListener(name,fn)};
}
