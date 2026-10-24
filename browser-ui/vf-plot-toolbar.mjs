import {readyPlotControlFont} from './vf-plot-control-font.mjs';
import {bindPlotDockGrip} from './vf-plot-docking.mjs';
import {plotToolbarSvg} from './vf-plot-toolbar-icons.mjs';
export const PLOT_TOOLBAR_API_VERSION='0.7.5-source.2';
const need=(value,code,status='FAIL')=>{if(!value)throw Object.assign(Error(code),{code,status});};
const copy=value=>structuredClone(value);

/** Retained view navigation only: first/last address the SAME bounded history
 * as previous/next. A new view after back drops the old forward branch.
 * No home extent, animation restart, or extra reset entry is created.
 */
export function createPlotViewHistory({limit=100}={}) {
 need(Number.isSafeInteger(limit)&&limit>=2&&limit<=10000,'PLOT_HISTORY_LIMIT');
 let entries=[],index=-1;const listeners=new Set();
 const state=()=>Object.freeze({index,length:entries.length,canBack:index>0,canForward:index>=0&&index<entries.length-1});
 const notify=()=>{for(const fn of listeners)fn(state());};
 function move(next){if(next<0||next>=entries.length||next===index)return null;index=next;notify();return copy(entries[index]);}
 return Object.freeze({
  reset(value){entries=[copy(value)];index=0;notify();return copy(value);},
  commit(value){const saved=copy(value);if(index>=0&&JSON.stringify(entries[index])===JSON.stringify(saved))return false;
   entries=entries.slice(0,index+1);entries.push(saved);if(entries.length>limit)entries=entries.slice(-limit);index=entries.length-1;notify();return true;},
  first:()=>move(0),back:()=>move(index-1),forward:()=>move(index+1),last:()=>move(entries.length-1),
  current:()=>index<0?null:copy(entries[index]),state,
  subscribe(fn){listeners.add(fn);return()=>listeners.delete(fn);}
 });
}

export function toolbarState({history,animation,capture}={}) {
 const h=history?.state?.()??{canBack:false,canForward:false};
 const timed=animation?.timed===true&&typeof animation.toggle==='function';
 const formats=Array.isArray(capture?.formats)?capture.formats:[];
 return Object.freeze({canBack:h.canBack===true,canForward:h.canForward===true,timed,
  playing:timed&&animation.playing!==false,speedVisible:timed&&typeof animation.setRate==='function',
  rate:animation?.rate??1,recording:capture?.video?.recording===true,
  pdf:formats.includes('pdf')&&typeof capture?.frame==='function',
  png:formats.includes('png')&&typeof capture?.frame==='function',
  video:typeof capture?.video?.start==='function'&&typeof capture?.video?.stop==='function'});
}
export function createPlotToolbarController({history,animation,capture,zoom,selection,onView=()=>{},onChange=()=>{}}={}) {
 let closed=false,tail=Promise.resolve();
 const state=()=>toolbarState({history,animation,capture});
 async function invoke(action) {
  need(!closed,'PLOT_TOOLBAR_CLOSED');
  const job=tail.then(async()=>{
   const s=state();let result;
   if(['first','back','forward','last'].includes(action)) {
    need(history&&typeof history[action]==='function','PLOT_HISTORY_MISSING','BLOCKED');
    if((['first','back'].includes(action)?s.canBack:s.canForward)){const value=history[action]();if(value!==null)await onView(value);}
   }else if(action==='select-mode'){need(selection&&typeof selection.setMode==='function','PLOT_SELECTION_DISABLED','BLOCKED');selection.setMode(selection.getMode()==='select'?'pan':'select');}
   else if(action==='play-pause'){need(s.timed,'PLOT_TIMED_ANIMATION_MISSING','BLOCKED');await animation.toggle();}
   else if(action==='zoom-in'||action==='zoom-out'){need(typeof zoom==='function','PLOT_ZOOM_MISSING','BLOCKED');await zoom(action==='zoom-in'?.8:1.25);}
   else if(action==='frame-pdf'||action==='frame-png') {
    const format=action.slice(6);need(s[format],'PLOT_CAPTURE_FORMAT_UNAVAILABLE','BLOCKED');
    const frame=await capture.frame();need(frame?.formats?.includes(format)&&typeof frame.save==='function','PLOT_CAPTURE_FRAME_CONTRACT');
    const bytes=await frame.save(format);need(bytes instanceof Uint8Array&&bytes.length>0,'PLOT_CAPTURE_EMPTY');
    result={format,bytes};if(capture.save)await capture.save(result);
   }else if(action==='capture-video') {
    need(s.video,'PLOT_VIDEO_CAPTURE_UNAVAILABLE','BLOCKED');
    result=s.recording?await capture.video.stop():await capture.video.start();
    need(result!==false&&result!==null,'PLOT_VIDEO_CAPTURE_FAILED');
   }else need(false,'PLOT_TOOLBAR_ACTION');
   onChange(state());return result;
  });tail=job.catch(()=>{});return job;
 }
 return Object.freeze({state,invoke,
  setRate(rate){need(!closed,'PLOT_TOOLBAR_CLOSED');const job=tail.then(async()=>{
   need(state().speedVisible,'PLOT_TIMED_ANIMATION_MISSING','BLOCKED');
   need(Number.isFinite(Number(rate))&&Number(rate)>=-4&&Number(rate)<=4&&Math.abs(Number(rate)*10-Math.round(Number(rate)*10))<1e-9,'PLOT_PLAYBACK_RATE');await animation.setRate(Number(rate));onChange(state());
  });tail=job.catch(()=>{});return job;},
  close(){if(closed)return tail;closed=true;return tail;}
 });
}

const handledSpace=new WeakSet();
export function handlePlotSpace(event,{root,state,toggle}={}) {
 if(!event||handledSpace.has(event)||event.defaultPrevented||!(event.code==='Space'||event.key===' ')||
  event.altKey||event.ctrlKey||event.metaKey||event.shiftKey||event.isComposing||state?.timed!==true)return false;
 const path=event.composedPath?.()??[event.target];
 const focused=root?.ownerDocument?.activeElement;
 if(!root||!focused||!root.contains(focused))return false;
 for(const item of path) {
  const tag=item?.tagName?.toLowerCase();
  const contenteditable=item?.getAttribute?.('contenteditable');
  if(['input','textarea','select','button','a','option'].includes(tag)||item?.isContentEditable||
    contenteditable!==null&&contenteditable!==undefined&&contenteditable!=='false'||
    ['textbox','combobox','button','menuitem'].includes(item?.getAttribute?.('role')))return false;
  if(item!==root&&item?.dataset?.vfPlotToolbarRoot==='1')return false;
  if(item===root)break;
 }
 handledSpace.add(event);event.preventDefault();event.stopPropagation();
 if(!event.repeat)toggle();return true;
}

let nextToolbar=0;
/** Browser DOM mount; importing this file never opens a window or renderer.
 * Native buttons/menuitems retain their normal keyboard semantics. Space on a
 * focused plot surface uses the same toggle path exactly once, without scrolling.
 */
export function mountPlotToolbar(root,options={}) {
 need(root?.ownerDocument&&root.append,'PLOT_TOOLBAR_HOST','BLOCKED');
 const doc=root.ownerDocument,toolbar=doc.createElement('div'),controls=doc.createElement('div'),menu=doc.createElement('div');
 const listeners=[],buttons=new Map();let disposed=false,menuOpen=false,unsubscribe=()=>{};
 const listen=(target,type,fn,opts)=>{target.addEventListener(type,fn,opts);listeners.push(()=>target.removeEventListener(type,fn,opts));};
 const previousRootMarker=root.dataset.vfPlotToolbarRoot;root.dataset.vfPlotToolbarRoot='1';
 toolbar.className='vf-plot-toolbar';toolbar.setAttribute('role','toolbar');toolbar.setAttribute('data-vf-frame-chrome','1');toolbar.setAttribute('aria-label','Plot view controls');
 controls.className='vf-plot-toolbar__controls';toolbar.append(controls);
 const status=doc.createElement('span');status.className='vf-plot-toolbar__status';status.setAttribute('role','status');
 const report=error=>{status.textContent=error.status==='BLOCKED'?'Unavailable: '+error.message:error.message;options.onError?.(error);};
 const controller=createPlotToolbarController({...options,onChange:()=>refresh()});
 const action=name=>controller.invoke(name).catch(report);
 function button(actionName,label,icon,parent=controls) {
  const b=doc.createElement('button');b.type='button';b.className='vf-plot-toolbar__button';b.dataset.vfToolbarAction=actionName;
  b.setAttribute('aria-label',label);b.title=label;b.innerHTML=plotToolbarSvg(icon);parent.append(b);buttons.set(actionName,b);
  listen(b,'click',event=>{event.preventDefault();event.stopPropagation();action(actionName);if(parent===menu){setMenu(false);captureButton.focus();}});return b;
 }
 button('first','First view','first');button('back','Previous view','back');button('forward','Next view','forward');button('last','Last view','last');
 const zout=button('zoom-out','Zoom out','zoom-out'),zin=button('zoom-in','Zoom in','zoom-in');zout.disabled=zin.disabled=typeof options.zoom!=='function';
 const select=options.selection?button('select-mode','Select objects','select'):null;
 const captureWrap=doc.createElement('div');captureWrap.className='vf-plot-toolbar__capture';controls.append(captureWrap);
 const captureButton=doc.createElement('button');captureButton.type='button';captureButton.className='vf-plot-toolbar__button';
 captureButton.dataset.vfToolbarAction='capture';captureButton.setAttribute('aria-label','Capture');captureButton.title='Capture frame or record video';
 captureButton.innerHTML=plotToolbarSvg('capture');captureButton.setAttribute('aria-haspopup','menu');captureButton.setAttribute('aria-expanded','false');
 captureWrap.append(captureButton);menu.id='vf-plot-capture-'+(++nextToolbar);menu.className='vf-plot-toolbar__menu';menu.setAttribute('role','menu');
 menu.setAttribute('aria-label','Capture');menu.hidden=true;captureButton.setAttribute('aria-controls',menu.id);captureWrap.append(menu);
 for(const [name,label,icon]of [['frame-pdf','Frame shot (PDF)','pdf'],['frame-png','Frame shot (PNG)','png'],['capture-video','Start video recording','video']]) {
  const b=button(name,label,icon,menu);b.setAttribute('role','menuitem');const text=doc.createElement('span');text.textContent=label;b.append(text);
 }
 const play=button('play-pause','Pause animation','pause');play.setAttribute('aria-keyshortcuts','Space');
 const speedControl=doc.createElement('div'),speed=doc.createElement('input'),speedValue=doc.createElement('output'),speedTicks=doc.createElement('div'),tickList=doc.createElement('datalist');
 speedControl.className='vf-plot-toolbar__rate';speed.className='vf-plot-toolbar__speed';speed.type='range';speed.min='-4';speed.max='4';speed.step='0.1';speed.setAttribute('aria-label','Playback rate');speed.title='Playback rate: negative reverses, zero holds';
 speedValue.className='vf-plot-toolbar__rate-value';speedValue.setAttribute('aria-live','off');
 speedTicks.className='vf-plot-toolbar__rate-ticks';speedTicks.setAttribute('aria-hidden','true');tickList.id='vf-rate-ticks-'+nextToolbar;speed.setAttribute('list',tickList.id);
 for(const value of [-4,-3,-2,-1,0,1,2,3,4]){const label=doc.createElement('span');label.textContent=(value>0?'+':'')+value;label.style.left=((value+4)/8*100)+'%';speedTicks.append(label);const opt=doc.createElement('option');opt.value=String(value);tickList.append(opt);}
 speedControl.append(speed,speedValue,speedTicks,tickList);controls.append(speedControl);
 // Coordinates are a separate native pmatrix surface on the actual plot frame.
 toolbar.append(status);
 const grip=doc.createElement('button');grip.type='button';grip.className='vf-plot-toolbar__grip';
 grip.setAttribute('aria-label','Move toolbar. Drag to an edge; arrow keys dock; Home resets automatic position.');
 grip.title='Move toolbar';grip.setAttribute('aria-grabbed','false');
 grip.innerHTML='<svg viewBox="0 0 12 24" aria-hidden="true" fill="currentColor"><circle cx="4" cy="6" r="1"/><circle cx="8" cy="6" r="1"/><circle cx="4" cy="12" r="1"/><circle cx="8" cy="12" r="1"/><circle cx="4" cy="18" r="1"/><circle cx="8" cy="18" r="1"/></svg>';
 if(options.docking)controls.insertBefore(grip,controls.firstChild);
 const gripBinding=options.docking?bindPlotDockGrip({grip,frame:root,docking:options.docking,
  onGrab:options.onDockGrab,onPreview:options.onDockPreview}):null;
 toolbar.dataset.fontStatus='pending';
 const fontReady=readyPlotControlFont(doc).then(proof=>{if(!disposed)toolbar.dataset.fontStatus='ready';return proof;},error=>{if(!disposed){toolbar.dataset.fontStatus='FAIL';report(error);}throw error;});fontReady.catch(()=>{});
 function setMenu(open,focus=false){menuOpen=open;menu.hidden=!open;captureButton.setAttribute('aria-expanded',String(open));
  if(open&&focus)[...menu.children].find(b=>!b.disabled)?.focus();}
 function refresh(){const s=controller.state();
  if(select){const active=options.selection.getMode()==='select';select.setAttribute('aria-pressed',String(active));select.title=active?'Select objects (switch to pan)':'Pan (switch to select objects)';}
  for(const n of ['first','back'])buttons.get(n).disabled=!s.canBack;
  for(const n of ['forward','last'])buttons.get(n).disabled=!s.canForward;
  play.hidden=!s.timed;play.innerHTML=plotToolbarSvg(s.playing?'pause':'play');play.setAttribute('aria-label',s.playing?'Pause animation':'Play animation');play.title=(s.playing?'Pause':'Play')+' animation (Space)';
  speedControl.hidden=!s.speedVisible;speed.value=String(s.rate);
  const signed=(s.rate>0?'+':'')+Number(s.rate).toFixed(1)+'x';
  speedValue.textContent=signed;speed.setAttribute('aria-valuetext',signed+(s.rate<0?' reverse':s.rate===0?' hold':' forward'));
  for(const [name,available]of [['frame-pdf',s.pdf],['frame-png',s.png],['capture-video',s.video]]) {
   const b=buttons.get(name);b.disabled=!available;
   const label=name==='capture-video'?(s.recording?'Stop video recording':'Start video recording'):name==='frame-pdf'?'Frame shot (PDF)':'Frame shot (PNG)';
   b.setAttribute('aria-label',label);b.title=available?label:label+' unavailable: no qualified provider';
   b.innerHTML=plotToolbarSvg(name==='capture-video'?(s.recording?'stop':'video'):name.slice(6));const text=doc.createElement('span');text.textContent=label;b.append(text);
  }
  toolbar.dataset.recording=String(s.recording);
 }
 listen(captureButton,'click',event=>{event.stopPropagation();setMenu(!menuOpen,true);});
 listen(captureButton,'keydown',event=>{if(event.key==='ArrowDown'){event.preventDefault();event.stopPropagation();setMenu(true,true);}else if(event.key==='Escape'&&menuOpen){event.preventDefault();event.stopPropagation();setMenu(false);}});
 listen(menu,'click',event=>{if(event.target.closest?.('button')&&!event.target.closest('button').disabled){setMenu(false);captureButton.focus();}});
 listen(menu,'keydown',event=>{
  const items=[...menu.children].filter(b=>!b.disabled),at=items.indexOf(doc.activeElement);let next;
  if(event.key==='Escape'){setMenu(false);captureButton.focus();}
  else if(event.key==='ArrowDown')next=(at+1)%items.length;
  else if(event.key==='ArrowUp')next=(at-1+items.length)%items.length;
  else if(event.key==='Home')next=0;else if(event.key==='End')next=items.length-1;
  else if(event.key==='Tab'){setMenu(false);return;}else return;
  event.preventDefault();event.stopPropagation();if(next!==undefined)items[next]?.focus();
 });
 listen(doc,'pointerdown',event=>{if(menuOpen&&!captureWrap.contains(event.target))setMenu(false);});
 listen(speed,'input',()=>controller.setRate(Number(speed.value)).catch(report));
 listen(root,'keydown',event=>handlePlotSpace(event,{root,state:controller.state(),toggle:()=>action('play-pause')}));
 unsubscribe=options.history?.subscribe?.(()=>refresh())??(()=>{});
 refresh();root.append(toolbar);
 return Object.freeze({element:toolbar,controller,refresh,fontReady,grip,
  cancelDockDrag:()=>gripBinding?.cancel(),
  async close(){if(disposed)return controller.close();disposed=true;gripBinding?.close();unsubscribe();for(const remove of listeners)remove();toolbar.remove();
   if(previousRootMarker===undefined)delete root.dataset.vfPlotToolbarRoot;else root.dataset.vfPlotToolbarRoot=previousRootMarker;
   await controller.close();}
 });
}
