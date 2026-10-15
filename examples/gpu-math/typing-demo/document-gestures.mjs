// Camera-only input. World coordinates stay under the drag point / pinch centre.
export function attachDocumentGestures(container,{getView,setView}){
 const pointers=new Map();let gesture=null,frame=0,pending=null;
 const clamp=value=>Math.max(1,Math.min(64,value));
 function commit(page,zoom,origin){
  pending={page,zoom,origin};
  if(!frame)frame=requestAnimationFrame(()=>{frame=0;const next=pending;pending=null;setView(next.page,{zoom:next.zoom,origin:next.origin});});
 }
 function current(page){const view=getView(page);return view&&pending?.page===page?{...view,zoom:pending.zoom,origin:pending.origin,worldWidth:view.worldWidth*view.zoom/pending.zoom}:view;}
 function rebase(){
  const points=[...pointers.values()];container.classList.toggle('dragging',points.length>0);
  if(!points.length){gesture=null;return;}
  const page=points[0].page,view=current(page);if(!view){gesture=null;return;}
  const a=points[0],b=points[1]??a,x=(a.x+b.x)/2,y=(a.y+b.y)/2,ratio=view.worldWidth/view.bounds.width;
  gesture={page,zoom:view.zoom,ratio,distance:points.length>1?Math.hypot(b.x-a.x,b.y-a.y):0,anchor:[view.origin[0]+(x-view.bounds.left)*ratio,view.origin[1]+(y-view.bounds.top)*ratio]};
 }
 function down(event){
  if(event.pointerType==='mouse'&&event.button!==0)return;
  const canvas=event.target.closest('canvas');if(!canvas)return;
  const page=Number(canvas.dataset.page);if(!getView(page)||pointers.size&&[...pointers.values()][0].page!==page)return;
  event.preventDefault();pointers.set(event.pointerId,{page,x:event.clientX,y:event.clientY});container.setPointerCapture(event.pointerId);rebase();
 }
 function move(event){
  const point=pointers.get(event.pointerId);if(!point||!gesture)return;
  event.preventDefault();point.x=event.clientX;point.y=event.clientY;
  const points=[...pointers.values()],a=points[0],b=points[1]??a,view=getView(gesture.page);if(!view)return;
  const x=(a.x+b.x)/2,y=(a.y+b.y)/2,distance=Math.hypot(b.x-a.x,b.y-a.y),zoom=clamp(gesture.distance>0?gesture.zoom*distance/gesture.distance:gesture.zoom),ratio=gesture.ratio*gesture.zoom/zoom;
  commit(gesture.page,zoom,[gesture.anchor[0]-(x-view.bounds.left)*ratio,gesture.anchor[1]-(y-view.bounds.top)*ratio]);
 }
 function up(event){if(!pointers.delete(event.pointerId))return;rebase();}
 function wheel(event){
  const canvas=event.target.closest('canvas');if(!canvas||pointers.size)return;
  const page=Number(canvas.dataset.page),view=current(page);if(!view)return;
  event.preventDefault();const delta=event.deltaY*(event.deltaMode===1?16:event.deltaMode===2?view.bounds.height:1),zoom=clamp(view.zoom*Math.exp(-delta*(event.ctrlKey ? .01 : .002))),ratio=view.worldWidth/view.bounds.width,x=event.clientX-view.bounds.left,y=event.clientY-view.bounds.top;
  commit(page,zoom,[view.origin[0]+x*ratio*(1-view.zoom/zoom),view.origin[1]+y*ratio*(1-view.zoom/zoom)]);
 }
 container.addEventListener('pointerdown',down);container.addEventListener('pointermove',move);for(const name of ['pointerup','pointercancel','lostpointercapture'])container.addEventListener(name,up);container.addEventListener('wheel',wheel,{passive:false});
 return()=>{cancelAnimationFrame(frame);pointers.clear();container.classList.remove('dragging');container.removeEventListener('pointerdown',down);container.removeEventListener('pointermove',move);for(const name of ['pointerup','pointercancel','lostpointercapture'])container.removeEventListener(name,up);container.removeEventListener('wheel',wheel);};
}
