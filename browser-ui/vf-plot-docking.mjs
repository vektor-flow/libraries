// No access to camera, history, animation, native data or capture.
const positions=['auto','top','bottom','left','right'];
export const coordinatePlacementForDock=Object.freeze({top:Object.freeze({edge:'right',align:'bottom'}),bottom:Object.freeze({edge:'right',align:'top'}),left:Object.freeze({edge:'top',align:'right'}),right:Object.freeze({edge:'top',align:'left'})});
export const coordinateCornerForDock=Object.freeze({top:'bottom-right',bottom:'top-right',left:'top-right',right:'top-left'});
export function createPlotDocking({position='auto',inset=true,phone=false,onChange=()=>{}}={}) {
 let selected,inside,isPhone=Boolean(phone);
 const valid=p=>{if(!positions.includes(p))throw TypeError('toolbarPosition must be auto|top|bottom|left|right');return p;};
 const boolean=v=>{if(typeof v!=='boolean')throw TypeError('inset must be boolean');return v;};
 selected=valid(position);inside=boolean(inset);
 const snapshot=()=>Object.freeze({position:selected,dock:selected==='auto'?(isPhone?'bottom':'top'):selected,inset:inside,
  coordinateCorner:coordinateCornerForDock[selected==='auto'?(isPhone?'bottom':'top'):selected],coordinatePlacement:coordinatePlacementForDock[selected==='auto'?(isPhone?'bottom':'top'):selected]});
 const changed=()=>{const s=snapshot();onChange(s);return s;};
 return Object.freeze({snapshot,setToolbarPosition(p){selected=valid(p);return changed();},setInset(v){inside=boolean(v);return changed();},
  setPhone(v){isPhone=Boolean(v);return changed();},resetToAuto(){selected='auto';return changed();},
  nearestEdge([x,y],rect){if(![x,y,rect.left,rect.top,rect.width,rect.height].every(Number.isFinite)||rect.width<=0||rect.height<=0)throw TypeError('finite frame rectangle required');
   const px=Math.max(0,Math.min(rect.width,x-rect.left)),py=Math.max(0,Math.min(rect.height,y-rect.top));
   return [['top',py],['bottom',rect.height-py],['left',px],['right',rect.width-px]].sort((a,b)=>a[1]-b[1])[0][0];}
 });
}
export function bindPlotDockGrip({grip,frame,docking,onPreview=()=>{},onGrab=()=>{}}) {
 if(!grip?.addEventListener||!frame?.getBoundingClientRect)throw TypeError('dock grip/frame required');
 let drag=null;const removals=[];const listen=(type,fn)=>{grip.addEventListener(type,fn);removals.push(()=>grip.removeEventListener(type,fn));};
 function finish(commit=false){if(!drag)return;const d=drag;drag=null;
  if(grip.hasPointerCapture?.(d.id))grip.releasePointerCapture(d.id);
  onPreview(null);grip.setAttribute('aria-grabbed','false');if(commit)docking.setToolbarPosition(d.target);onGrab(false);
 }
 listen('pointerdown',e=>{if(e.button!==0||drag)return;e.preventDefault();e.stopPropagation();
  drag={id:e.pointerId,target:docking.snapshot().dock};grip.setPointerCapture(e.pointerId);grip.focus?.({preventScroll:true});grip.setAttribute('aria-grabbed','true');onGrab(true);onPreview(drag.target);
 });
 listen('pointermove',e=>{if(!drag||e.pointerId!==drag.id)return;e.preventDefault();e.stopPropagation();drag.target=docking.nearestEdge([e.clientX,e.clientY],frame.getBoundingClientRect());onPreview(drag.target);});
 listen('pointerup',e=>{if(!drag||e.pointerId!==drag.id)return;e.preventDefault();e.stopPropagation();finish(true);});
 listen('pointercancel',()=>finish());listen('lostpointercapture',()=>finish());
 listen('keydown',e=>{const map={ArrowUp:'top',ArrowDown:'bottom',ArrowLeft:'left',ArrowRight:'right'};
  if(e.key==='Escape'&&drag){e.preventDefault();e.stopPropagation();finish();}
  else if(map[e.key]){e.preventDefault();e.stopPropagation();finish();docking.setToolbarPosition(map[e.key]);}
  else if(e.key==='Home'){e.preventDefault();e.stopPropagation();finish();docking.resetToAuto();}
 });
 return Object.freeze({get dragging(){return drag!==null;},cancel:()=>finish(),close(){finish();for(const remove of removals)remove();}});
}

/** HOST-verifiable rectangle contract, also used by browser acceptance. Inputs
 * are actual client box and measured toolbar size, never a guessed bar height.
 */
export function plotFrameRect({left=0,top=0,width,height,toolbarWidth=0,toolbarHeight=0,dock,inset=true}) {
 if(![left,top,width,height,toolbarWidth,toolbarHeight].every(Number.isFinite)||width<=0||height<=0||toolbarWidth<0||toolbarHeight<0||!['top','bottom','left','right'].includes(dock)||typeof inset!=='boolean')throw TypeError('invalid measured plot layout');
 const rect={left,top,width,height};if(!inset){if(dock==='top'){rect.top+=toolbarHeight;rect.height-=toolbarHeight;}if(dock==='bottom')rect.height-=toolbarHeight;
  if(dock==='left'){rect.left+=toolbarWidth;rect.width-=toolbarWidth;}if(dock==='right')rect.width-=toolbarWidth;}
 if(rect.width<=0||rect.height<=0)throw RangeError('toolbar consumes plot client area');return Object.freeze(rect);
}
export function inspectPlotLayout(host,plotFrame,toolbar,state,{tolerance=1}={}) {
 const h=host.getBoundingClientRect(),p=plotFrame.getBoundingClientRect(),t=toolbar?.getBoundingClientRect();
 const expected=plotFrameRect({left:h.left+(host.clientLeft??0),top:h.top+(host.clientTop??0),width:host.clientWidth??h.width,height:host.clientHeight??h.height,
  toolbarWidth:t?.width??0,toolbarHeight:t?.height??0,...state});
 const equal=['left','top','width','height'].every(k=>Math.abs(p[k]-expected[k])<=tolerance);
 return Object.freeze({expected,actual:{left:p.left,top:p.top,width:p.width,height:p.height},toolbar:t&&{left:t.left,top:t.top,width:t.width,height:t.height},equal,state});
}
