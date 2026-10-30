import {createAntialiasedScreenSpaceRenderer} from './vf-antialiased-screen-renderer.mjs';
import {STROKE_CONTRACT_VERSION} from './vf-stroke-contract.mjs';
// Actual @vektor-flow/ui retained renderer adapter. No seed/VfDisplay dependency.
import {buildScreenSpaceSimplexVertices} from 'vektor-flow/screen-simplex-renderer';
import {need,finite,freeze,identity} from './vf-plot-pdf-commands.mjs';
import {createPlotVectorCapture,freezePlotFrame} from './vf-plot-vector-capture.mjs';
const equalColor=(a,b)=>a.every((v,i)=>Object.is(v,b[i]));
/** Accepted Float32 vertex positions/colors, in the renderer's shader viewport
 * coordinates. Preserve upload ordering, triangle winding and alpha blending.
 * No curve projection, camera fitting, axis layout or font selection occurs.
 */
export function packedPlotPaths(vertices,{bufferWidth,bufferHeight,cssWidth,cssHeight}){
 need(vertices instanceof Float32Array&&vertices.length%18===0&&vertices.length/18<=50000,'PLOT_LIBRARY_PACKED_TRIANGLES');
 need([bufferWidth,bufferHeight,cssWidth,cssHeight].every(n=>finite(n)&&n>0),'PLOT_LIBRARY_VIEWPORT');
 const scaleX=bufferWidth/Math.fround(cssWidth),scaleY=bufferHeight/Math.fround(cssHeight),paths=[];
 for(let at=0;at<vertices.length;at+=18){const triangle=[];let paint;
  for(let v=0;v<3;v++){const i=at+v*6,x=vertices[i],y=vertices[i+1],c=Array.from(vertices.subarray(i+2,i+6));
   need([x,y,...c].every(finite)&&c.every(n=>n>=0&&n<=1),'PLOT_LIBRARY_VERTEX');
   if(paint)need(equalColor(paint,c),'PLOT_LIBRARY_INTERPOLATED_COLOR_UNSUPPORTED');else paint=c;
   triangle.push([v===0?'M':'L',x*scaleX,y*scaleY]);
  }
  triangle.push(['Z']);paths.push({kind:'plotpath',commands:triangle,matrix:identity.slice(),clips:[],fillRule:'nonzero',fill:paint,stroke:null});
 }
 return paths;
}
const pngBytes=url=>{need(typeof url==='string'&&url.startsWith('data:image/png;base64,'),'PLOT_LIBRARY_PNG_READBACK');const raw=atob(url.slice(url.indexOf(',')+1));return Uint8Array.from(raw,c=>c.charCodeAt(0));};
/** Wrap this mount's existing renderer BEFORE createRetainedPlotView. Each
 * accepted render owns an immutable uploaded payload, camera and shader size.
 * pairedCapture is the genuine929 async factory contract, with dynamic formats.
 */
export function createLibraryPlotVectorCapture({renderer,canvas,frameId,getFrameId=()=>frameId,getState,getNativeGlyphOrigins=()=>[],getCaptureOverlay=()=>null,captureBackground=[1,1,1,1],whenCaptureReady=async()=>{},writePdf,pdfPolicy={}}={}){
 need(typeof renderer?.setPackedVertices==='function'&&typeof renderer?.capturePNG==='function'&&canvas&&typeof getState==='function','PLOT_LIBRARY_RENDERER_MISSING','BLOCKED');
 const output=canvas.ownerDocument.createElement('canvas');
 const documentRenderer=createAntialiasedScreenSpaceRenderer(output);let documentInitialized=false,accepted=null;
 let revision=0,snapshot=null,failure=null,closed=false,cssWidth=null,cssHeight=null,viewportRect=null;
 function accept(vertices,dirtyRange){
  need(!closed,'PLOT_LIBRARY_CAPTURE_CLOSED');snapshot=null;failure=null;let owned;
  try{need(vertices instanceof Float32Array,'PLOT_LIBRARY_PACKED_TRIANGLES');owned=vertices.slice();accepted=owned;renderer.setPackedVertices(owned,dirtyRange);}catch(error){failure=error;throw error;}revision++;
  try{need(cssWidth!==null&&cssHeight!==null,'PLOT_LIBRARY_VIEWPORT_MISSING','BLOCKED');const viewport={width:canvas.width,height:canvas.height};const primitives=packedPlotPaths(owned,{bufferWidth:viewport.width,bufferHeight:viewport.height,cssWidth,cssHeight});
   snapshot=freezePlotFrame({schema:'vf-plot-vector-frame/1',frameId:getFrameId(),revision,viewport,state:{strokeContract:STROKE_CONTRACT_VERSION,coverage:renderer.coveragePolicy?.()??null,coordinates:getState(),shaderViewport:{width:cssWidth,height:cssHeight}},primitives,nativeGlyphOrigins:getNativeGlyphOrigins(),complete:true});
   viewportRect=canvas.getBoundingClientRect?.();
  }catch(error){failure=error;}
 }
 const captureRenderer={
  plotVectorCaptureStatus(){const rect=canvas.getBoundingClientRect?.();const ready=!closed&&snapshot!==null&&canvas.width===snapshot.viewport.width&&canvas.height===snapshot.viewport.height&&(!rect||!viewportRect||rect.width===viewportRect.width&&rect.height===viewportRect.height)&&JSON.stringify(getState())===JSON.stringify(snapshot.state.coordinates);
   return freeze({ready,status:ready?'READY':failure?.status??'BLOCKED',code:ready?'PLOT_FRAME_READY':failure?.code??'PLOT_LIBRARY_COMMITTED_FRAME_MISSING'});},
  capturePlotVectorFrame(){const status=this.plotVectorCaptureStatus();need(status.ready,status.code,status.status);
   // Existing929 renderer redraws its last accepted private payload and reads
   // synchronously. No awaits permit producer/camera/resize changes in between.
   const background=buildScreenSpaceSimplexVertices({primitives:[{kind:'face',points:[[0,0],[cssWidth,0],[cssWidth,cssHeight]],color:captureBackground},{kind:'face',points:[[0,0],[cssWidth,cssHeight],[0,cssHeight]],color:captureBackground}]});
   const overlay=getCaptureOverlay(),extra=overlay?buildScreenSpaceSimplexVertices({primitives:overlay.primitives}):new Float32Array();
   const combined=new Float32Array(background.length+accepted.length+extra.length);combined.set(background);combined.set(accepted,background.length);combined.set(extra,background.length+accepted.length);
   const viewport={...snapshot.viewport};
   const documentSnapshot=freezePlotFrame({...snapshot,state:{...snapshot.state,captureBackground:[...captureBackground],coordinatesOverlay:overlay?.origin??null,coords:!!overlay},
    primitives:packedPlotPaths(combined,{bufferWidth:viewport.width,bufferHeight:viewport.height,cssWidth,cssHeight}),
    nativeGlyphOrigins:[...getNativeGlyphOrigins(),...(overlay?[overlay.origin]:[])]});
   need(documentInitialized,'PLOT_DOCUMENT_RENDERER_UNINITIALIZED','BLOCKED');
   documentRenderer.resize(cssWidth,cssHeight);documentRenderer.setPackedVertices(combined);
   const png=pngBytes(documentRenderer.capturePNG());return Object.freeze({snapshot:documentSnapshot,png});}
 };
 const capture=createPlotVectorCapture({renderer:captureRenderer,frameId,writePdf,pdfPolicy});
 const pairedCapture=async()=>{await whenCaptureReady();return capture.frame();};Object.defineProperty(pairedCapture,'formats',{get:()=>capture.formats});
 const facade=Object.freeze({...renderer,
  get backend(){return renderer.backend;},
  async initialize(){const result=await renderer.initialize();await documentRenderer.initialize();documentInitialized=true;return result;},
  async capturePNG(){await whenCaptureReady();return "data:image/png;base64,"+(()=>{const bytes=captureRenderer.capturePlotVectorFrame().png;let raw="";for(let i=0;i<bytes.length;i+=8192)raw+=String.fromCharCode(...bytes.subarray(i,i+8192));return btoa(raw);})();},
  setPackedVertices:accept,
  setScene(scene){snapshot=null;failure=null;try{need(Array.isArray(scene?.primitives)&&scene.primitives.every(p=>['face','edge','vertex'].includes(p?.kind)),'PLOT_LIBRARY_SCENE_PRIMITIVE_UNSUPPORTED');accept(buildScreenSpaceSimplexVertices(scene));}catch(error){failure=error;throw error;}},
  resize(width,height){snapshot=null;failure=null;cssWidth=width;cssHeight=height;return renderer.resize(width,height);},
  destroy(){closed=true;snapshot=null;documentRenderer.destroy();return renderer.destroy();}
 });
 return Object.freeze({renderer:facade,pairedCapture,frame:pairedCapture,get formats(){return capture.formats;},status:()=>captureRenderer.plotVectorCaptureStatus()});
}
