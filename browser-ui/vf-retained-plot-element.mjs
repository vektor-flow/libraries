import {createAntialiasedScreenSpaceRenderer} from './vf-antialiased-screen-renderer.mjs';
import {createCoordinateView} from './vf-coordinate-view.mjs';
import {createCoordinateView3d} from './vf-coordinate-view-3d.mjs';
import {createRetainedPlotView} from './vf-retained-plot-view.mjs';

// A bounded native presentation for compiler-produced retained field geometry.
// The caller owns compilation, World execution, toolbar and authored source.
export async function mountRetainedPlot(container, packet, {
  dimensions = null, bounds, selectionColor = '#00ffff', onSelectionChange = () => {},
  interaction = null, onInteractionChange = () => {}
} = {}) {
  if (!container?.ownerDocument || typeof container.append !== 'function') throw new TypeError('plot container must be a DOM element');
  const meshes=packet?.metadata?.scene?.meshes || [];
  dimensions ??= meshes.some(mesh=>mesh.mode3d===true) ? 3 : 2;
  if(dimensions!==2 && dimensions!==3)throw new RangeError('plot presentation requires two or three dimensions');
  if(!bounds) {
    const ranges={};
    for(const axis of ['x','y','z']) {
      const spans=meshes.map(mesh=>[mesh.axis_ticks?.[axis+'_min'],mesh.axis_ticks?.[axis+'_max']])
        .filter(([min,max])=>Number.isFinite(min) && Number.isFinite(max) && max>min);
      if(spans.length)ranges[axis]=[Math.min(...spans.map(span=>span[0])),Math.max(...spans.map(span=>span[1]))];
    }
    if(Object.keys(ranges).length)bounds=ranges;
  }
  const canvas=container.ownerDocument.createElement('canvas');
  canvas.style.cssText='display:block;width:100%;height:100%;touch-action:none';
  canvas.tabIndex=0;
  canvas.setAttribute('aria-label','Plot');
  container.append(canvas);
  const renderer=createAntialiasedScreenSpaceRenderer(canvas);
  const coordinates=dimensions===3 ? createCoordinateView3d({bounds}) : createCoordinateView({bounds});
  let disposed=false, active=null;
  const view=createRetainedPlotView({coordinates,renderer,selectionColor});
  const local=event=>{const rect=canvas.getBoundingClientRect();return[event.clientX-rect.left,event.clientY-rect.top]};
  const render=()=>{if(!disposed)view.render()};
  const resize=()=>{
    if(disposed)return;
    const rect=canvas.getBoundingClientRect();
    coordinates.resize(rect.width,rect.height);
    renderer.resize(rect.width,rect.height);
    view.invalidate();render();
  };
  const down=event=>{
    if(event.button!==0)return;
    interaction?.cancel();
    const point=local(event),hit=view.hitTest(point,{capability:'draggable'});
    const objectDrag=Boolean(hit && interaction?.begin(hit.id,point,coordinates,{dimensions}));
    active={id:event.pointerId,origin:point,last:point,dragged:false,objectDrag};
    canvas.setPointerCapture(event.pointerId);
  };
  const move=event=>{
    if(!active || event.pointerId!==active.id)return;
    const point=local(event);
    if(Math.hypot(point[0]-active.origin[0],point[1]-active.origin[1])>=4)active.dragged=true;
    if(active.dragged){
      if(active.objectDrag){const update=interaction.move(point);if(update)onInteractionChange(update)}
      else coordinates.pan(active.last,point);
      render();
    }
    active.last=point;
  };
  const up=event=>{
    if(!active || event.pointerId!==active.id)return;
    if(!active.dragged){view.selectAt(local(event),{additive:event.shiftKey});render();onSelectionChange(view.selection())}
    interaction?.end();
    if(canvas.hasPointerCapture(event.pointerId))canvas.releasePointerCapture(event.pointerId);
    active=null;
  };
  const cancel=()=>{interaction?.cancel();active=null};
  const wheel=event=>{event.preventDefault();coordinates.zoomAt(local(event),event.deltaY);render()};
  const key=event=>{if(event.key==='Escape'){view.clearSelection();render();onSelectionChange(view.selection())}};
  let observer;
  try {
    await renderer.initialize();
    view.replaceArena(packet);
    canvas.addEventListener('pointerdown',down);
    canvas.addEventListener('pointermove',move);
    canvas.addEventListener('pointerup',up);
    canvas.addEventListener('pointercancel',cancel);
    canvas.addEventListener('wheel',wheel,{passive:false});
    canvas.addEventListener('keydown',key);
    observer=new container.ownerDocument.defaultView.ResizeObserver(resize);
    observer.observe(container);
    resize();
  } catch(error) {renderer.destroy();canvas.remove();throw error}
  return Object.freeze({
    canvas,coordinates,
    selection:view.selection,
    update(next){if(disposed)throw new Error('plot view is disposed');view.replaceArena(next);render()},
    dispose(){
      if(disposed)return;
      disposed=true;interaction?.cancel();active=null;observer.disconnect();
      for(const [name,handler] of [['pointerdown',down],['pointermove',move],['pointerup',up],['pointercancel',cancel],['wheel',wheel],['keydown',key]])canvas.removeEventListener(name,handler);
      renderer.destroy();canvas.remove();
    }
  });
}
