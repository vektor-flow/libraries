import {createPlotDocking} from './vf-plot-docking.mjs';
import {mountPlotToolbar,createPlotViewHistory} from './vf-plot-toolbar.mjs';
import {mountNativePlotCoordinates,createNativePlotLabelLayer} from './vf-native-plot-label-layer.mjs';

/** Composable VKF chrome for an existing application-owned plot surface.
 * Applications supply state/action contracts, never a second toolbar/readout.
 * Geometry/camera/physics ownership is unchanged by mounting or docking chrome.
 */
export async function mountPlotChrome(root, {
  plotFrame = root, history = null, getView = null, animation, capture, zoom, selection, onView = () => {},
  nativeTypography = null, labelCoordinates = null, onLabelsChanged = () => {}, dimensions = 2, coords = true, values = Array(dimensions).fill(0),
  toolbarPosition = 'auto', inset = true, onError = () => {}, onDockChange = () => {},
  onDockGrab = () => {}, onDockPreview = () => {}
} = {}) {
  if (!root?.ownerDocument || !root.append) throw TypeError('Plot chrome DOM host required');
  if (typeof coords !== 'boolean') throw TypeError('coords must be boolean');
  if (![2,3].includes(dimensions)) throw TypeError('Native coordinates require two or three dimensions');
  const doc = root.ownerDocument;
  let labels = null;
  let panel = null, toolbar = null, closing = null, closed = false;
  const ownedHistory = history ?? (getView ? createPlotViewHistory() : null);
  if(!history && getView)ownedHistory.reset(getView());
  let viewTimer=null,queuedView=null,restoring=false,lastView=getView?JSON.stringify(getView()):null;
  function flushView(){
    if(viewTimer!==null)clearTimeout(viewTimer);viewTimer=null;
    if(queuedView){ownedHistory?.commit(queuedView);queuedView=null;}
  }
  const viewHistory=ownedHistory&&Object.freeze({...ownedHistory,...Object.fromEntries(
    ['first','back','forward','last'].map(name=>[name,()=>{flushView();return ownedHistory[name]();}]))});
  function commitView(){
    if(closed||restoring||!getView)return false;
    const next=getView(),key=JSON.stringify(next);if(key===lastView)return false;
    lastView=key;queuedView=structuredClone(next);
    if(viewTimer!==null)clearTimeout(viewTimer);viewTimer=setTimeout(flushView,140);return true;
  }
  const prior = {dock:root.dataset.toolbarDock,inset:root.dataset.toolbarInset};
  let currentValues = [...values], visible = coords;
  const media = doc.defaultView.matchMedia?.('(max-width:480px)');
  const docking = createPlotDocking({position:toolbarPosition,inset,phone:media?.matches === true,
    onChange(state) {
      root.dataset.toolbarDock = state.dock;
      root.dataset.toolbarInset = String(state.inset);
      toolbar?.element.setAttribute('aria-orientation', ['left','right'].includes(state.dock)?'vertical':'horizontal');
      panel?.setPlacement(state.coordinatePlacement);
      onDockChange(state);
    }
  });
  const phoneChange = event => docking.setPhone(event.matches);
  const coordinateButton = doc.createElement('button');
  coordinateButton.type = 'button';
  coordinateButton.className = 'vf-plot-toolbar__button';
  coordinateButton.dataset.vfCoordsToggle = '1';
  coordinateButton.textContent = 'Coords';
  const unavailable = !nativeTypography;
  coordinateButton.disabled = unavailable;
  coordinateButton.title = unavailable ? 'Native coordinates unavailable: VKF typography provider required' : 'Pointer coordinates';
  coordinateButton.setAttribute('aria-label', unavailable ? coordinateButton.title : 'Hide coordinates');
  async function setCoordsVisible(value) {
    if (closed) throw Error('Plot chrome is closed');
    if (typeof value !== 'boolean') throw TypeError('coords must be boolean');
    if (value && unavailable) throw Object.assign(Error('PLOT_NATIVE_TYPOGRAPHY_REQUIRED'),{status:'BLOCKED'});
    visible = value;
    if (panel) panel.setVisible(value);
    coordinateButton.setAttribute('aria-pressed',String(value && !!panel));
    coordinateButton.setAttribute('aria-label',value?'Hide coordinates':'Show coordinates');
    return value;
  }
  const toggle = () => setCoordsVisible(!visible).catch(onError);
  try {
    toolbar = mountPlotToolbar(root,{history:viewHistory,animation,capture,
      zoom:typeof zoom==='function'?async factor=>{flushView();await zoom(factor);if(getView){const view=getView();lastView=JSON.stringify(view);ownedHistory?.commit(view);}}:undefined,
      selection,async onView(view){restoring=true;try{await onView(view);}finally{restoring=false;if(getView)lastView=JSON.stringify(getView());}},docking,
      onDockGrab,onDockPreview,onError});
    coordinateButton.addEventListener('click',toggle);
    toolbar.element.querySelector('.vf-plot-toolbar__controls').append(coordinateButton);
    if (!unavailable) {
      if(labelCoordinates)labels=createNativePlotLabelLayer({typography:nativeTypography,coordinates:labelCoordinates});
      panel = await mountNativePlotCoordinates(plotFrame,{typography:nativeTypography,dimensions,visible:coords,onError});
      panel.setPlacement(docking.snapshot().coordinatePlacement);
      panel.update(currentValues);
      if(coords) await panel.ready;
    }
    coordinateButton.setAttribute('aria-pressed',String(coords && !!panel));
    media?.addEventListener?.('change',phoneChange);
    await toolbar.fontReady;
    docking.setToolbarPosition(toolbarPosition);
  } catch (error) {
    try {await panel?.close();await labels?.close();} finally {await toolbar?.close();}
    if(prior.dock===undefined)delete root.dataset.toolbarDock;else root.dataset.toolbarDock=prior.dock;
    if(prior.inset===undefined)delete root.dataset.toolbarInset;else root.dataset.toolbarInset=prior.inset;
    throw error;
  }
  return Object.freeze({toolbar,docking,coordinates:panel,history:viewHistory,commitView,
    get coordinatesAvailable(){return !!panel;},
    updateCoordinates(next){
      if(closed)return;
      if(!Array.isArray(next)||next.length!==dimensions||!next.every(Number.isFinite))throw TypeError('Finite coordinate vector required');
      currentValues=[...next];panel?.update(currentValues);
    },
    async setLabels(specs){if(!labels||closed)return false;await labels.setLabels(specs);if(!closed)onLabelsChanged();return !closed;},
    renderLabels(scene,frame,{pixelRatio=1}={}){
      if(!labels||closed)return;
      if(!Number.isFinite(pixelRatio)||pixelRatio<=0)throw TypeError('Positive pixel ratio required');
      for(const item of labels.geometry())for(const [i,primitive]of item.triangles.entries())
        scene.primitive(frame,item.elementId+':native:'+i,{...primitive,points:primitive.points.map(point=>point.map(v=>v*pixelRatio))});
    },
    refresh:toolbar.refresh,setCoordsVisible,
    setToolbarPosition:docking.setToolbarPosition,setInset:docking.setInset,resetToAuto:docking.resetToAuto,
    close(){
      if(closing)return closing;closed=true;
      if(viewTimer!==null)clearTimeout(viewTimer);viewTimer=null;queuedView=null;
      closing=(async()=>{
        media?.removeEventListener?.('change',phoneChange);
        coordinateButton.removeEventListener('click',toggle);
        const errors=[];
        for(const close of [()=>toolbar.close(),()=>capture?.video?.recording?capture.video.stop():undefined,()=>panel?.close(),()=>labels?.close()])try{await close();}catch(error){errors.push(error);}
        if(prior.dock===undefined)delete root.dataset.toolbarDock;else root.dataset.toolbarDock=prior.dock;
        if(prior.inset===undefined)delete root.dataset.toolbarInset;else root.dataset.toolbarInset=prior.inset;
        if(errors.length)throw new AggregateError(errors,'Plot chrome cleanup failed');
      })();return closing;
    }
  });
}
