// This asset is converted from the EXACT native CMR10 physical program/TFM.
// Ordinary HTML controls use CSS/browser text by explicit product policy.
// A successful load is never reported as native plot-layout certification.
export const PLOT_CONTROL_FONT=Object.freeze({family:'Vektor Flow CMR',sha256:'28bcd14b587b230324f69ef20d338e8ee90233ba4ad574d24b79e7404fd35212',bytes:15128,
 url:new URL('./fonts/vf-cmr10.otf',import.meta.url).href});
const documents=new WeakMap();
export function readyPlotControlFont(doc,{fetchAsset=globalThis.fetch,FontFaceClass=doc?.defaultView?.FontFace}={}) {
 if(documents.has(doc))return documents.get(doc);
 const ready=(async()=>{if(!doc?.fonts||typeof FontFaceClass!=='function'||typeof fetchAsset!=='function')throw Object.assign(Error('PLOT_CONTROL_FONT_API_MISSING'),{status:'BLOCKED'});
  const response=await fetchAsset(PLOT_CONTROL_FONT.url,{credentials:'omit',redirect:'error',cache:'force-cache'});
  if(!response.ok)throw Object.assign(Error('PLOT_CONTROL_FONT_ASSET_MISSING'),{status:'BLOCKED'});
  const bytes=await response.arrayBuffer();if(bytes.byteLength!==PLOT_CONTROL_FONT.bytes)throw Error('PLOT_CONTROL_FONT_SIZE');
  const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),n=>n.toString(16).padStart(2,'0')).join('');
  if(digest!==PLOT_CONTROL_FONT.sha256)throw Error('PLOT_CONTROL_FONT_DIGEST');
  const face=new FontFaceClass(PLOT_CONTROL_FONT.family,bytes,{style:'normal',weight:'400',display:'block'});await face.load();doc.fonts.add(face);
  const loaded=await doc.fonts.load('13px "'+PLOT_CONTROL_FONT.family+'"','-4 -3 -2 -1 0 +1 +2 +3 +4 0.1x');
  if(!loaded.includes(face)||!doc.fonts.check('13px "'+PLOT_CONTROL_FONT.family+'"'))throw Error('PLOT_CONTROL_FONT_NOT_READY');
  return Object.freeze({family:PLOT_CONTROL_FONT.family,sha256:digest,loaded:true,nativePlotProof:false});
 })();documents.set(doc,ready);return ready;
}
