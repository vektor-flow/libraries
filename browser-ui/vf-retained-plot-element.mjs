import {createPlotDocking,inspectPlotLayout} from './vf-plot-docking.mjs';
import {readyPlotControlFont} from './vf-plot-control-font.mjs';
import {createNativePlotLabelLayer,mountNativePlotCoordinates,nativeAxisLabelSpecs} from './vf-native-plot-label-layer.mjs';
import {createPlotViewHistory,mountPlotToolbar} from './vf-plot-toolbar.mjs';
import {createLibraryPlotVectorCapture} from './vf-library-plot-vector-capture.mjs';
import {createSceneMediaCapture} from './vf-media-capture.mjs';
import {mountSelectionMarquee} from './vf-selection-marquee.mjs';
import {bindSelectionInput} from './vf-selection-controller.mjs';
import {createAntialiasedScreenSpaceRenderer} from './vf-antialiased-screen-renderer.mjs';
import {createCoordinateView} from './vf-coordinate-view.mjs';
import {createCoordinateView3d} from './vf-coordinate-view-3d.mjs';
import {createRetainedPlotView} from './vf-retained-plot-view.mjs';

// A bounded native presentation for compiler-produced retained field geometry.
// The caller owns compilation, timed execution and authored source. Toolbar is a reusable075 library mount, with real optional capture providers.
export async function mountRetainedPlot(container, packet, {
  dimensions = null, bounds, selectionEnabled = false, selectionMode = 'pan', selectionToolbar = false, selectionStroke = null, selectionColor = '#00ffff', onSelectionChange = () => {},
  interaction = null, onInteractionChange = () => {}, onDockInteraction = () => {},
  toolbar = true, toolbarPosition='auto', inset=true, nativeTypography=null, nativeCoordinates=true, coords=true, plotLabels=null, animation = null, pairedCapture = null, vectorCapture = false, pdfPolicy = {}, onToolbarError = () => {}, elapsedSeconds = 0, layerTimeOffsets = {}
} = {}) {
  if(typeof selectionEnabled!=='boolean'||typeof selectionToolbar!=='boolean')throw TypeError('selection flags must be boolean');
  if(!['pan','select'].includes(selectionMode)||!selectionEnabled&&selectionMode!=='pan')throw TypeError('select mode requires enabled selection');
  if(typeof coords!=='boolean')throw TypeError('coords must be boolean');
  if(typeof vectorCapture!=='boolean')throw TypeError('vectorCapture must be a boolean');
  if(pairedCapture!==null&&typeof pairedCapture!=='function')throw TypeError('pairedCapture must be an actual paired frame provider');
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
  if((nativeCoordinates||plotLabels?.length)&&!nativeTypography)throw Object.assign(Error('PLOT_NATIVE_TYPOGRAPHY_REQUIRED'),{status:'BLOCKED'});
  const docking=createPlotDocking({position:toolbarPosition,inset,phone:container.ownerDocument.defaultView.matchMedia?.('(max-width:480px)')?.matches===true,onChange:state=>applyDock(state)});
  const originalHostClass=container.classList.contains('vf-plot-host');container.classList.add('vf-plot-host');
  const plotFrame=container.ownerDocument.createElement('div');plotFrame.className='vf-plot-frame';container.append(plotFrame);
  const canvas=container.ownerDocument.createElement('canvas');
  canvas.style.cssText='display:block;width:100%;height:100%;touch-action:none';
  canvas.tabIndex=0;
  canvas.setAttribute('aria-label','Plot');
  plotFrame.append(canvas);
  const baseRenderer=createAntialiasedScreenSpaceRenderer(canvas);
  const coordinates=dimensions===3 ? createCoordinateView3d({bounds}) : createCoordinateView({bounds});
  let captureFrameId=packet.metadata.scene.frame;
  const plotVectorCapture=vectorCapture?createLibraryPlotVectorCapture({renderer:baseRenderer,canvas,
    frameId:captureFrameId,getFrameId:()=>captureFrameId,getState:()=>coordinates.snapshot(),getNativeGlyphOrigins:()=>nativeLabelLayer?.glyphOrigins()??[],getCaptureOverlay:()=>nativeCoordinatePanel?.captureGeometry()??null,whenCaptureReady:async()=>{if(nativeCoordinatePanel?.visible)await nativeCoordinatePanel.whenIdle();},pdfPolicy}):null;
  const renderer=plotVectorCapture?.renderer??baseRenderer;
  const pairedProvider=pairedCapture??plotVectorCapture?.pairedCapture;
  let disposed=false, active=null,toolbarHandle=null,historyTimer=null,disposePromise=null,unsubscribeAnimation=()=>{},nativeCoordinatePanel=null,nativeLabelLayer=null,phoneMedia=null,layoutReady=false;
  let coordsVisible=coords,pointerValues=Array(dimensions).fill(0),coordinateCreation=null;
  const originalDock={dock:container.dataset.toolbarDock,inset:container.dataset.toolbarInset};
  const layoutListeners=[];
  async function setCoordsVisible(value){
    if(disposed)throw Error('plot view is disposed');
    if(typeof value!=='boolean')throw TypeError('coords visibility must be boolean');
    if(value&&!nativeCoordinates)throw Object.assign(Error('PLOT_COORDINATE_CAPABILITY_DISABLED'),{status:'BLOCKED'});
    coordsVisible=value;
    const toggle=toolbarHandle?.element.querySelector('[data-vf-coords-toggle]');toggle?.setAttribute('aria-pressed',String(value));toggle?.setAttribute('aria-label',value?'Hide coordinates':'Show coordinates');
    if(!value){nativeCoordinatePanel?.setVisible(false);return false;}
    if(!nativeCoordinatePanel){
      coordinateCreation??=(async()=>{const panel=await mountNativePlotCoordinates(plotFrame,{typography:nativeTypography,dimensions,visible:coordsVisible,onError:onToolbarError});if(disposed){await panel.close();throw Error('plot view is disposed');}nativeCoordinatePanel=panel;panel.setPlacement(docking.snapshot().coordinatePlacement);panel.update(pointerValues);await panel.ready;return panel;})();
      await coordinateCreation;
    }else{nativeCoordinatePanel.setVisible(true);nativeCoordinatePanel.update(pointerValues);await nativeCoordinatePanel.whenIdle();}
    nativeCoordinatePanel.setVisible(coordsVisible);
    if(coordsVisible&&nativeCoordinatePanel.snapshot().status!=='ready')throw Object.assign(Error('PLOT_COORDINATE_CAPTURE_NOT_READY'),{status:'FAIL'});
    toolbarHandle?.element.querySelector('[data-vf-coords-toggle]')?.setAttribute('aria-pressed',String(coordsVisible));
    return coordsVisible;
  }
  function applyDock(state){container.dataset.toolbarDock=state.dock;container.dataset.toolbarInset=String(state.inset);
    nativeCoordinatePanel?.setPlacement(state.coordinatePlacement);toolbarHandle?.element.setAttribute('aria-orientation',['left','right'].includes(state.dock)?'vertical':'horizontal');
    if(layoutReady)resize();
  }
  const retainedHistory=createPlotViewHistory();
  // Flush a pending wheel view BEFORE navigation chooses its target. Animation
  // packets and elapsed time never enter these real coordinate snapshots.
  const history=Object.freeze({...retainedHistory,...Object.fromEntries(
    ['first','back','forward','last'].map(name=>[name,()=>{flushView();return retainedHistory[name]();}]))});
  const media=createSceneMediaCapture({fallbackCanvas:()=>canvas,
    captureRendererFrame:()=>renderer.capturePNG(),document:container.ownerDocument,
    MediaRecorderClass:container.ownerDocument.defaultView.MediaRecorder});
  const view=createRetainedPlotView({coordinates,renderer,selectionColor,selectionStroke});
  view.selectionController.setEnabled(selectionEnabled);
  const marquee=mountSelectionMarquee(canvas,{color:selectionColor});
  const getInteractionMode=()=>unbindSelection.getMode?.()??selectionMode;
  const setInteractionMode=mode=>{cancel();const result=unbindSelection.setMode(mode);toolbarHandle?.refresh();return result;};
  const local=event=>{const rect=canvas.getBoundingClientRect();return[event.clientX-rect.left,event.clientY-rect.top]};
  const render=()=>{if(!disposed){view.render();toolbarHandle?.refresh();}};
  const commitView=()=>{if(!disposed)history.commit(coordinates.snapshot());};
  const flushView=()=>{if(historyTimer!==null){clearTimeout(historyTimer);historyTimer=null;commitView();}};
  const scheduleView=()=>{if(historyTimer!==null)clearTimeout(historyTimer);historyTimer=setTimeout(()=>{historyTimer=null;commitView();},140);};
  async function saveCapture({format,bytes}) {
    const doc=container.ownerDocument,url=doc.defaultView.URL.createObjectURL(new Blob([bytes],{type:format==='pdf'?'application/pdf':format==='webm'?'video/webm':'image/png'}));
    try{const link=doc.createElement('a');link.href=url;link.download='vektor-flow-plot.'+format;link.click();}
    finally{doc.defaultView.setTimeout(()=>doc.defaultView.URL.revokeObjectURL(url),0);}
  }
  function attachToolbar() {
    if(!toolbar)return;
    const video=typeof canvas.captureStream==='function'&&typeof container.ownerDocument.defaultView.MediaRecorder==='function'?{
      get recording(){return media.recording;},start:()=>media.startMovie(),async stop(){const blob=await media.stopMovie();
        if(!blob)throw Object.assign(Error('PLOT_VIDEO_CAPTURE_EMPTY'),{status:'FAIL'});await saveCapture({format:'webm',bytes:new Uint8Array(await blob.arrayBuffer())});return blob;}}:null;
    const capture={get formats(){return pairedProvider&&(pairedProvider.formats??['pdf','png']).includes('pdf')?['pdf','png']:typeof canvas.toBlob==='function'?['png']:[];},video,save:saveCapture,
      async frame(){if(pairedProvider&&(pairedProvider.formats??['pdf','png']).includes('pdf'))return pairedProvider();
        const url=await renderer.capturePNG();
        const bytes=Uint8Array.from(container.ownerDocument.defaultView.atob(url.split(',')[1]),c=>c.charCodeAt(0));return{formats:['png'],save(format){if(format!=='png')throw Object.assign(Error('PLOT_PDF_CAPTURE_UNAVAILABLE'),{status:'BLOCKED'});return bytes.slice();}};}};
    toolbarHandle=mountPlotToolbar(container,{history,animation,capture,docking,selection:selectionEnabled&&selectionToolbar?{getMode:getInteractionMode,setMode:setInteractionMode}:null,
      onDockGrab:grabbing=>{cancel();if(grabbing)unbindSelection.cancel?.();onDockInteraction(grabbing);},onDockPreview:edge=>{if(edge)container.dataset.dockPreview=edge;else delete container.dataset.dockPreview;},onError:onToolbarError,
      onView:snapshot=>{cancel();unbindSelection.cancel?.();interaction?.cancel();coordinates.restore(snapshot);const rect=canvas.getBoundingClientRect();coordinates.resize(rect.width,rect.height);view.invalidate();render();},
      zoom:factor=>{unbindSelection.cancel?.();flushView();const s=coordinates.snapshot(),vp=s.viewport;coordinates.zoomAt([vp.width/2,vp.height/2],factor<1?-100:100);view.invalidate();render();commitView();}});
    const coordsToggle=container.ownerDocument.createElement('button');coordsToggle.type='button';coordsToggle.className='vf-plot-toolbar__button';coordsToggle.dataset.vfCoordsToggle='1';coordsToggle.textContent='Coords';coordsToggle.setAttribute('aria-label',coordsVisible?'Hide coordinates':'Show coordinates');coordsToggle.setAttribute('aria-pressed',String(coordsVisible));coordsToggle.addEventListener('click',()=>{setCoordsVisible(!coordsVisible).catch(onToolbarError);coordsToggle.setAttribute('aria-pressed',String(coordsVisible));});toolbarHandle.element.querySelector('.vf-plot-toolbar__controls')?.append(coordsToggle);
    container.insertBefore(toolbarHandle.element,plotFrame);
  }
  const resize=()=>{
    if(disposed)return;
    unbindSelection.cancel?.();
    const rect=canvas.getBoundingClientRect();
    coordinates.resize(rect.width,rect.height);
    renderer.resize(rect.width,rect.height);
    view.invalidate();render();
  };
  const down=event=>{
    if(event.button!==0||event.isPrimary===false||active||getInteractionMode()==='select')return;
    flushView();canvas.focus({preventScroll:true});
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
    interaction?.end();
    if(active.dragged&&!active.objectDrag)commitView();
    if(canvas.hasPointerCapture(event.pointerId))canvas.releasePointerCapture(event.pointerId);
    active=null;
  };
  const cancel=()=>{interaction?.cancel();
    if(active&&canvas.hasPointerCapture(active.id))canvas.releasePointerCapture(active.id);
    active=null;};
  const hover=event=>{const point=coordinates.screenToWorld(local(event));pointerValues=point.slice(0,dimensions);if(coordsVisible)nativeCoordinatePanel?.update(pointerValues);};
  const wheel=event=>{unbindSelection.cancel?.();event.preventDefault();coordinates.zoomAt(local(event),event.deltaY);render();scheduleView()};
  let unbindSelection=()=>{};
  let observer;
  try {
    if(toolbar)await readyPlotControlFont(container.ownerDocument);
    await renderer.initialize();
    if(nativeTypography){nativeLabelLayer=createNativePlotLabelLayer({typography:nativeTypography,coordinates});
      const specs=plotLabels??(dimensions===2&&bounds?.x&&bounds?.y?nativeAxisLabelSpecs({bounds}):[]);
      await nativeLabelLayer.setLabels(specs);view.setNativeLabelLayer(nativeLabelLayer);}
    if(nativeCoordinates&&coordsVisible)await setCoordsVisible(true);
    applyDock(docking.snapshot());
    view.replaceArena(packet,{elapsedSeconds,layerTimeOffsets});
    canvas.addEventListener('pointerdown',down);
    canvas.addEventListener('pointermove',move);
    canvas.addEventListener('pointermove',hover);
    canvas.addEventListener('pointerup',up);
    canvas.addEventListener('pointercancel',cancel);
    canvas.addEventListener('lostpointercapture',cancel);
    canvas.addEventListener('wheel',wheel,{passive:false});
    unbindSelection=bindSelectionInput(canvas,view.selectionController,{local,enabled:selectionEnabled,mode:selectionMode,onMarquee:marquee.show,onChange:ids=>{try{render()}finally{onSelectionChange(ids)}}});
    observer=new container.ownerDocument.defaultView.ResizeObserver(resize);
    observer.observe(plotFrame);
    phoneMedia=container.ownerDocument.defaultView.matchMedia?.('(max-width:480px)');
    if(phoneMedia){const change=e=>docking.setPhone(e.matches);phoneMedia.addEventListener('change',change);layoutListeners.push(()=>phoneMedia.removeEventListener('change',change));}
    attachToolbar();applyDock(docking.snapshot());layoutReady=true;resize();history.reset(coordinates.snapshot());
    // The caller owns the existing timed executor; subscribe only to its state.
    // No local animation clock, sample, or restart is introduced by the mount.
    const unsubscribe=animation?.subscribe?.(()=>toolbarHandle?.refresh())??(()=>{});
    if(typeof unsubscribe!=='function')throw TypeError('animation subscription must return an unsubscribe function');
    unsubscribeAnimation=unsubscribe;
  } catch(error) {
    const errors=[error];
    for(const cleanup of [()=>unsubscribeAnimation(),()=>toolbarHandle?.close(),()=>nativeCoordinatePanel?.close(),()=>nativeLabelLayer?.close(),()=>media.cancel(),()=>observer?.disconnect(),()=>unbindSelection(),()=>marquee.close(),()=>view.dispose(),()=>renderer.destroy(),()=>canvas.remove(),()=>plotFrame.remove(),()=>{for(const release of layoutListeners)release();delete container.dataset.dockPreview;if(originalDock.dock===undefined)delete container.dataset.toolbarDock;else container.dataset.toolbarDock=originalDock.dock;if(originalDock.inset===undefined)delete container.dataset.toolbarInset;else container.dataset.toolbarInset=originalDock.inset;},()=>{if(!originalHostClass)container.classList.remove('vf-plot-host');}]) {
      try{await cleanup();}catch(cleanupError){errors.push(cleanupError);}
    }
    if(errors.length>1)throw new AggregateError(errors,'Plot initialization and cleanup failed');throw error;
  }
  return Object.freeze({
    canvas,plotFrame,coordinates,history,toolbar:toolbarHandle,capture:plotVectorCapture,get nativeCoordinates(){return nativeCoordinatePanel;},nativeLabels:nativeLabelLayer,
    setCoordsVisible,get coords(){return coordsVisible&&!!nativeCoordinatePanel?.visible;},
    docking,setToolbarPosition:docking.setToolbarPosition,setInset:docking.setInset,resetToAuto:docking.resetToAuto,
    inspectLayout:()=>inspectPlotLayout(container,plotFrame,toolbarHandle?.element,docking.snapshot()),
    selection:view.selection,
    registerSelectionObjects(key,objects){const remove=view.registerSelectionObjects(key,objects);render();return()=>{remove();if(!disposed)render()};},strokeContext:view.strokeContext,getInteractionMode,setInteractionMode,cancelSelection:()=>unbindSelection.cancel?.(),
    update(next,{elapsedSeconds=0,layerTimeOffsets={}}={}){if(disposed)throw new Error('plot view is disposed');unbindSelection.cancel?.();const before=view.selection();view.replaceArena(next,{elapsedSeconds,layerTimeOffsets});captureFrameId=next.metadata.scene.frame;render();toolbarHandle?.refresh();if(JSON.stringify(before)!==JSON.stringify(view.selection()))onSelectionChange(view.selection())},
    dispose(){
      if(disposePromise)return disposePromise;
      disposePromise=(async()=>{
      disposed=true;
      const closeErrors=[];
      try{await coordinateCreation;}catch(error){closeErrors.push(error);}
      for(const release of [()=>interaction?.cancel(),()=>observer.disconnect(),()=>unsubscribeAnimation()])
        try{await release();}catch(error){closeErrors.push(error);}
      if(active&&canvas.hasPointerCapture(active.id))canvas.releasePointerCapture(active.id);
      active=null;
      if(historyTimer!==null){clearTimeout(historyTimer);historyTimer=null;}
      // Join accepted toolbar work and the real recorder before renderer teardown.
      try{await toolbarHandle?.close();}catch(error){closeErrors.push(error);}
      for(const close of [()=>nativeCoordinatePanel?.close(),()=>nativeLabelLayer?.close()])try{await close();}catch(error){closeErrors.push(error);}
      try{if(media.recording)await media.stopMovie();}catch(error){closeErrors.push(error);}
      for(const [name,handler] of [['pointerdown',down],['pointermove',move],['pointermove',hover],['pointerup',up],['pointercancel',cancel],['lostpointercapture',cancel],['wheel',wheel]])canvas.removeEventListener(name,handler);
      for(const cleanup of [unbindSelection,()=>marquee.close(),()=>view.dispose(),()=>renderer.destroy(),()=>canvas.remove(),()=>plotFrame.remove(),()=>{for(const release of layoutListeners)release();delete container.dataset.dockPreview;if(originalDock.dock===undefined)delete container.dataset.toolbarDock;else container.dataset.toolbarDock=originalDock.dock;if(originalDock.inset===undefined)delete container.dataset.toolbarInset;else container.dataset.toolbarInset=originalDock.inset;},()=>{if(!originalHostClass)container.classList.remove('vf-plot-host');}])try{await cleanup();}catch(error){closeErrors.push(error);}
      if(closeErrors.length)throw new AggregateError(closeErrors,"Plot capture cleanup failed");
      })();return disposePromise;
    }
  });
}
