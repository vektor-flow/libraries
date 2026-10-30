import {need,finite,freeze,matrix,identity,multiply,validatePlotPath} from './vf-plot-pdf-commands.mjs';
const clone=v=>structuredClone(v);
export function freezePlotFrame(value){
 need(value?.schema==='vf-plot-vector-frame/1'&&typeof value.frameId==='string'&&value.frameId&&Number.isSafeInteger(value.revision)&&value.revision>0,'PLOT_FRAME_IDENTITY');
 const v=value.viewport;need(v&&[v.width,v.height].every(n=>finite(n)&&n>0)&&v.width*v.height<=16777216,'PLOT_VIEWPORT');
 need(Array.isArray(value.primitives)&&value.primitives.length<=50000,'PLOT_PRIMITIVES');
 const copied=clone(value);for(const p of copied.primitives)validatePlotPath(p);
 need(copied.complete===true,'PLOT_FRAME_INCOMPLETE');return freeze(copied);
}
/** Export page policy never feeds renderer layout, camera, animation or PNG. */
export function plotPdfLayout(frame,policy={}){
 frame=freezePlotFrame(frame);need(policy&&Object.keys(policy).every(k=>['paper','margins','scale'].includes(k)),'PLOT_PDF_POLICY');
 const scale=policy.scale??1;need(finite(scale)&&scale>0,'PLOT_PDF_SCALE');
 const {width,height}=frame.viewport;let pageWidth=width*scale,pageHeight=height*scale,left=0,top=0;
 if(policy.paper){need(Object.keys(policy.paper).every(k=>['width','height'].includes(k)),'PLOT_PAPER_FIELDS');({width:pageWidth,height:pageHeight}=policy.paper);
  need([pageWidth,pageHeight].every(n=>finite(n)&&n>0),'PLOT_PAPER');
  const m=policy.margins??{};need(Object.keys(m).every(k=>['left','right','top','bottom'].includes(k)),'PLOT_MARGIN_FIELDS');
  left=m.left??0;top=m.top??0;const right=m.right??0,bottom=m.bottom??0;
  need([left,top,right,bottom].every(n=>finite(n)&&n>=0)&&left+width*scale+right<=pageWidth&&top+height*scale+bottom<=pageHeight,'PLOT_PAPER_FIT');
 }else need(!policy.margins,'PLOT_MARGINS_REQUIRE_PAPER');
 const placement=[scale,0,0,scale,left,top],viewportClip={commands:[['M',0,0],['L',width,0],['L',width,height],['L',0,height],['Z']],matrix:placement,rule:'nonzero'};
 const items=frame.primitives.map(p=>({...p,x:0,y:0,matrix:multiply(placement,p.matrix??identity),clips:[viewportClip,...(p.clips??[]).map(c=>({...c,matrix:multiply(placement,c.matrix??identity)}))]}));
 return freeze({pages:[{width:pageWidth,height:pageHeight,items}]});
}
const realWriter=async(layout,vectors,options)=>(await import('./text-math-vendor/vector-pdf.mjs')).exportVectorPdf(layout,vectors,options);
/** Renderer takes one synchronous ownership snapshot, including PNG bytes/promise.
 * Waiting for PNG encoding never rereads the renderer. No export asks for layout.
 */
export function createPlotVectorCapture({renderer,frameId,writePdf=realWriter,pdfPolicy={}}={}){
 const available=()=>typeof renderer?.capturePlotVectorFrame==='function'&&typeof renderer?.plotVectorCaptureStatus==='function'&&renderer.plotVectorCaptureStatus(frameId)?.ready===true;
 return Object.freeze({get formats(){return available()?Object.freeze(['pdf','png']):Object.freeze([]);},
  async frame(){need(typeof renderer?.capturePlotVectorFrame==='function','PLOT_VECTOR_PROVIDER_MISSING','BLOCKED');
   const held=renderer.capturePlotVectorFrame(frameId);need(held&&typeof held.then!=='function','PLOT_CAPTURE_MUST_FREEZE_SYNCHRONOUSLY');
   const snapshot=freezePlotFrame(held.snapshot),layout=plotPdfLayout(snapshot,clone(pdfPolicy));
   need(held.png instanceof Uint8Array||typeof held.png?.then==='function','PLOT_PNG_SNAPSHOT_MISSING','BLOCKED');
   const png=Promise.resolve(held.png).then(bytes=>{need(bytes instanceof Uint8Array&&bytes.length>8,'PLOT_PNG_CAPTURE_EMPTY');return bytes.slice();});png.catch(()=>{});
   let pdf;
   const saved=Object.freeze({formats:Object.freeze(['pdf','png']),snapshot,
    async save(format){need(['pdf','png'].includes(format),'PLOT_CAPTURE_FORMAT_UNSUPPORTED');
     if(format==='png')return (await png).slice();
     // Existing project vector writer. Empty glyph bundle is intentional: native
     // outlines are already frozen plot paths, no second shaping/font selection.
     pdf??=Promise.resolve().then(()=>writePdf(layout,{schema:'vkf.pdf-vectors/1',keys:{},paths:{}},{compressionWorker:false}));pdf.catch(()=>{});
     const bytes=await pdf;need(bytes instanceof Uint8Array&&bytes.length>0,'PLOT_PDF_CAPTURE_EMPTY');return bytes.slice();}
   });return saved;
  }
 });
}
