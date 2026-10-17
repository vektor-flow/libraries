import {prepareTikzConsumer} from './tikz-analytic-consumer.mjs';
import {glyphPaintItems} from './glyph-paints.mjs';
import {pdfPngImage} from './pdf-images.mjs';
import {requestedFontProfile,validateFontProfile} from './font-profile.mjs';
import {isVectorPrimitive,vectorPaintItems,vectorPacket,vectorBounds} from './vector-packets.mjs';
import {attachDocumentGestures} from './document-gestures.mjs';
import {pdfTextPositions} from './pdf-text-positions.mjs';
import {pngPhysicalSize,projectPath} from './document-project.mjs';
import {typesetDocument} from './document-layout.mjs';
import {exportVectorPdf,verifyVectorMapping,preparePdfCompression} from './vector-pdf.mjs';
const $=id=>document.getElementById(id),assets={},files={},assetTextures=new Map(),errors=[];window.documentGpuErrors=errors;
let baseData,baseFontBind;const fontProfiles=new Map();
let data,device,pipeline,fontBind,uniform,instances,gpu,format,atlas,pageDraws=[],revision=0,cachedLayout=null,cachedSource=null,assetRevision=0,cachedAssetRevision=-1,cachedBuildContext=null,currentBuildContext={};
const ink=[.078,.188,.149,1];
const sourceImages=new Map(),sourceVectors=new Map();
let mappingBytes;const pdfFontResources=new Map(),pdfMappings=new Map();
async function documentFontProfile(source,buildContext){
 const name=await requestedFontProfile(source,{files,buildContext});if(!name)return{mapping:baseData,bind:baseFontBind};
 if(!fontProfiles.has(name))fontProfiles.set(name,(async()=>{
  const folder='./font-profiles/'+encodeURIComponent(name)+'/',response=await fetch(folder+'typing-data.json');if(!response.ok)throw Error('Native font profile is unavailable: '+name);const mapping=validateFontProfile(name,await response.json(),device.limits.maxTextureDimension2D),atlasResponse=await fetch(folder+'atlas.rgba.gz');if(!atlasResponse.ok)throw Error('Native font atlas is unavailable: '+name);let raw=await atlasResponse.arrayBuffer();if(new Uint8Array(raw)[0]===31)raw=await new Response(new Blob([raw]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer();if(raw.byteLength!==mapping.atlasSize[0]*mapping.atlasSize[1]*4)throw Error('Font profile atlas byte length differs');const texture=device.createTexture({size:mapping.atlasSize,format:'rgba8unorm',usage:GPUTextureUsage.TEXTURE_BINDING|GPUTextureUsage.COPY_DST});device.queue.writeTexture({texture},raw,{bytesPerRow:mapping.atlasSize[0]*4},mapping.atlasSize);return{mapping,texture,bind:bind(texture)};
 })().catch(error=>{fontProfiles.delete(name);throw error;}));return fontProfiles.get(name);
}

async function pdfMapping(name=null){
 if(!name)return{mapping:baseData,bytes:mappingBytes};
 if(!pdfMappings.has(name))pdfMappings.set(name,(async()=>{
  const response=await fetch('./font-profiles/'+encodeURIComponent(name)+'/pdf-metrics.json.gz');if(!response.ok)throw Error('Native PDF font profile is unavailable: '+name);
  const compressed=await response.arrayBuffer(),bytes=await new Response(new Blob([compressed]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer(),mapping=validateFontProfile(name,JSON.parse(new TextDecoder().decode(bytes)));return{mapping,bytes};
 })().catch(error=>{pdfMappings.delete(name);throw error;}));
 return pdfMappings.get(name);
}
async function pdfVectors(name=null){
 const key=name??'base';if(!pdfFontResources.has(key))pdfFontResources.set(key,(async()=>{
  const folder=name?'./font-profiles/'+encodeURIComponent(name)+'/':'./';
  const mapping=pdfMapping(name),response=await fetch(folder+'pdf-vectors.json.gz');if(!response.ok)throw Error('PDF vector fonts could not be loaded'+(name?': '+name:''));
  const raw=await response.arrayBuffer(),bytes=new Uint8Array(raw);
  let text;if(bytes[0]===31){const stream=new DecompressionStream('gzip'),writer=stream.writable.getWriter(),output=new Response(stream.readable).text();await writer.write(bytes);await writer.close();text=await output;}else text=new TextDecoder().decode(bytes);
  const vectors=JSON.parse(text),data=await mapping;
  await verifyVectorMapping(name?{...vectors,mappingSha256:vectors.pdfMappingSha256}:vectors,data.bytes);return{mapping:data.mapping,vectors};
 })().catch(error=>{pdfFontResources.delete(key);throw error;}));
 return pdfFontResources.get(key);
}
// This API also works when WebGPU is unavailable. It reads current source and
// project inputs, independently of the preview's camera, atlas and GPU state.
window.exportDocumentPdf=async(source=$('document').value,{buildContext=currentBuildContext,profile=false}={})=>{
 const exportStart=performance.now(),timings={};let checkpoint=exportStart;const stage=name=>{const now=performance.now();timings[name]=now-checkpoint;checkpoint=now;};
 if(!data)throw Error('Native font mapping is still loading');
 const requestedProfile=await requestedFontProfile(source,{files,buildContext});
 preparePdfCompression();
 const exportMapping=mapping=>{const result={...mapping,tiles:{...mapping.tiles}};for(const material of assetTextures.values())for(const key of material.keys??[])result.tiles[key]=data.tiles[key];return result;};
 stage('inputPreparationMs');let resources,result;
 [resources,result]=await Promise.all([pdfVectors(requestedProfile),(async()=>{
  const {mapping}=await pdfMapping(requestedProfile);stage('fontMappingMs');
  return typesetDocument(source,exportMapping(mapping),{assets,files,buildContext});
 })()]);stage('layoutAndFontLoadMs');
 const base=resources.vectors;
 const vectors={...base,keys:{...base.keys},paths:{...base.paths}},images={};
 for(const [material,paths]of sourceVectors)for(const [key,path]of Object.entries(paths??{})){
  const name=material+'/'+key;vectors.keys[name]=name;vectors.paths[name]=path;
 }
 stage('vectorResourcesMs');
 const needed=new Set(result.pages.flatMap(page=>page.items.filter(item=>item.kind==='image').map(item=>item.asset)));
 for(const name of needed){
  const blob=sourceImages.get(name)??sourceImages.get(name.replace(/\.[^.]+$/,''));if(!blob)throw Error('Missing original illustration: '+name);
  const png=new Uint8Array(await blob.arrayBuffer());if(pdfPngImage(png)){images[name]={png};continue;}
  const bitmap=await createImageBitmap(blob);
  try{const canvas=new OffscreenCanvas(bitmap.width,bitmap.height),context=canvas.getContext('2d');context.drawImage(bitmap,0,0);images[name]={width:bitmap.width,height:bitmap.height,rgba:context.getImageData(0,0,bitmap.width,bitmap.height).data};}finally{bitmap.close();}
 }
 stage('imageDecodeMs');const metrics=profile?{}:null;
 const bytes=await exportVectorPdf(result,vectors,{images,metrics});stage('pdfCoreMs');timings.totalMs=performance.now()-exportStart;
 return{bytes,pages:result.pages.length,diagnostics:result.diagnostics,layout:result,timings,...(profile?{pdfMetrics:metrics}:{})};
};
$('export-pdf').addEventListener('click',async()=>{
 const button=$('export-pdf');button.disabled=true;$('notice').textContent='Preparing vector PDF…';
 try{const result=await window.exportDocumentPdf(),url=URL.createObjectURL(new Blob([result.bytes],{type:'application/pdf'})),a=document.createElement('a');
 a.href=url;a.download=(currentBuildContext.jobName??'document')+'.pdf';a.click();setTimeout(()=>URL.revokeObjectURL(url),30000);
 $('navigation').open=false;$('notice').textContent=`Vector PDF exported · ${result.pages} pages${result.diagnostics.length?' · '+result.diagnostics.length+' compatibility issues (see details)':''}`;
 $('diagnostics').textContent=result.diagnostics.join('\n');
 }catch(error){$('notice').textContent='PDF export failed: '+error.message;}finally{button.disabled=false;}
});
function packet(item,scale,pdfPixels,zoom=1,origin=[0,0],pixelAlign=true){
 const color=item.color??ink;
 if(isVectorPrimitive(item))return vectorPacket(item,color);
 if(item.kind==='link'&&item.borderWidth===0)return[0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0];
 if(item.kind==='link')return[item.x-1.5,item.y-1.5,item.width+3,item.height+3,0,0,0,0,...color,1,item.width+1,item.height+1,pdfPixels?-1:1];
 if(item.kind==='image')return[item.x,item.y,item.width,item.height,0,0,1,1,1,1,1,1,2,0,0,0];
 if(item.kind==='glyph'||item.kind==='field'){if(pixelAlign&&!pdfPixels){const pixels=scale*zoom;item={...item,x:origin[0]+Math.floor((item.x-origin[0])*pixels*4)/(pixels*4),y:origin[1]+Math.floor((item.y-origin[1])*pixels)/pixels};}if(pdfPixels){item={...item,x:item.pdfX??item.x,y:item.pdfY??item.y};}const phases=pdfPixels&&Math.abs(scale-96/72)<1e-8&&!item.crop&&!item.cropX&&Math.abs((item.sx??1)-(data.coverage96Metrics?.[item.key]?.scale??1))<1e-8&&Math.abs((item.sy??1)-(data.coverage96Metrics?.[item.key]?.scale??1))<1e-8?data.coverage96?.[item.key]:null;if(phases){const phasePosition=Math.floor((item.pdfPixelX??item.x*scale)*4+.5),phase=((phasePosition%4)+4)%4,yPhases=data.coverage96Metrics?.[item.key]?.yPhases??1,yPosition=Math.floor((item.pdfPixelY??item.y*scale)*yPhases+.5),yPhase=((yPosition%yPhases)+yPhases)%yPhases,tile=phases[yPhase*4+phase];if(tile){const r=tile.rect;return[(Math.floor(phasePosition/4)+r[0])/scale,(Math.floor(yPosition/yPhases)+r[1])/scale,r[2]/scale,r[3]/scale,...tile.uv,...color,3,0,0,0];}}const t=data.tiles[item.key];if(!t)throw Error('Missing native tile: '+item.key);const p=t.plane,lo=Math.max(p[1],item.crop?.[0]??p[1]),hi=Math.min(p[3],item.crop?.[1]??p[3]),left=Math.max(p[0],item.cropX?.[0]??p[0]),right=Math.min(p[2],item.cropX?.[1]??p[2]),sx=item.sx??1,sy=item.sy??1;return[item.x+left*sx,item.y+lo*sy,(right-left)*sx,(hi-lo)*sy,t.uv[0]+(left-p[0])/(p[2]-p[0])*(t.uv[2]-t.uv[0]),t.uv[1]+(lo-p[1])/(p[3]-p[1])*(t.uv[3]-t.uv[1]),t.uv[0]+(right-p[0])/(p[2]-p[0])*(t.uv[2]-t.uv[0]),t.uv[1]+(hi-p[1])/(p[3]-p[1])*(t.uv[3]-t.uv[1]),...color,0,0,0,0];}
 return[item.x-1,item.y-1,item.width+2,item.height+2,0,0,0,0,...color,1,item.width,item.height,0];
}
function bind(texture,{image=false}={}){return device.createBindGroup({layout:pipeline.getBindGroupLayout(0),entries:[{binding:0,resource:{buffer:uniform}},{binding:1,resource:texture.createView()},{binding:2,resource:device.createSampler({minFilter:'linear',magFilter:image?'nearest':'linear'})}]});}
async function addAsset(name,blob){
 name=projectPath(name);const bytes=new Uint8Array(await blob.arrayBuffer()),bitmap=await createImageBitmap(blob);
 try{
  if(bitmap.width*bitmap.height>16777216||(device&&(bitmap.width>device.limits.maxTextureDimension2D||bitmap.height>device.limits.maxTextureDimension2D)))throw Error('Image exceeds device/image memory limit');
  const physical=pngPhysicalSize(bytes,bitmap.width,bitmap.height);
  if(device){const texture=device.createTexture({size:[bitmap.width,bitmap.height],format:'rgba8unorm',usage:GPUTextureUsage.TEXTURE_BINDING|GPUTextureUsage.COPY_DST|GPUTextureUsage.RENDER_ATTACHMENT});device.queue.copyExternalImageToTexture({source:bitmap},{texture},[bitmap.width,bitmap.height]);assetTextures.get(name)?.texture.destroy();assetTextures.set(name,{texture,bind:bind(texture,{image:true})});}
  assets[name]={width:bitmap.width,height:bitmap.height,...physical};sourceImages.set(name,blob);assetRevision++;
 }finally{bitmap.close();}
}
window.addDocumentAsset=async(name,base64,mime='image/png')=>{const bytes=Uint8Array.from(atob(base64),c=>c.charCodeAt(0));await addAsset(name,new Blob([bytes],{type:mime}));};
window.addDocumentFile=(name,text)=>{if(typeof text!=='string'||text.length>1000000)throw Error('Invalid project text file');files[projectPath(name)]=text;assetRevision++;};
window.addDocumentVectorAsset=async(name,spec,base64)=>{
 name=projectPath(name);if(spec.schema!=='vkf.document-vector-asset/1'||!Array.isArray(spec.items)||spec.items.length>5000||Object.keys(spec.tiles??{}).length>2000)throw Error('Invalid vector asset');
 const [w,h]=spec.atlasSize??[];if(![w,h].every(n=>Number.isInteger(n)&&n>0&&n<=(device?.limits.maxTextureDimension2D??8192))||w*h>33554432||![spec.widthBp,spec.heightBp].every(n=>Number.isFinite(n)&&n>0))throw Error('Vector asset dimensions exceed limits');
 let texture;if(device){const compressed=Uint8Array.from(atob(base64),c=>c.charCodeAt(0)),raw=await new Response(new Blob([compressed]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer();if(raw.byteLength!==w*h*4)throw Error('Vector asset atlas byte count mismatch');texture=device.createTexture({size:[w,h],format:'rgba8unorm',usage:GPUTextureUsage.TEXTURE_BINDING|GPUTextureUsage.COPY_DST});device.queue.writeTexture({texture},raw,{bytesPerRow:w*4},[w,h]);}
 const material='vector:'+name,prefix=material+'/',keys=[];
 for(const [key,tile]of Object.entries(spec.tiles)){if(!Array.isArray(tile.uv)||tile.uv.length!==4||!Array.isArray(tile.plane)||tile.plane.length!==4||![...tile.uv,...tile.plane].every(Number.isFinite)||tile.uv.some(n=>n<0||n>1)||tile.plane[2]<=tile.plane[0]||tile.plane[3]<=tile.plane[1])throw Error('Invalid vector field');}
 for(const [key,phases]of Object.entries(spec.coverage96??{})){const metric=spec.coverage96Metrics?.[key];if(!spec.tiles[key]||!metric||!Number.isFinite(metric.scale)||metric.scale<=0||!Array.isArray(phases)||phases.length!==4||phases.some(tile=>tile&&(!Array.isArray(tile.uv)||tile.uv.length!==4||tile.uv.some(n=>!Number.isFinite(n)||n<0||n>1)||!Array.isArray(tile.rect)||tile.rect.length!==4||!tile.rect.every(Number.isFinite)||tile.rect[2]<=0||tile.rect[3]<=0)))throw Error('Invalid vector font coverage');}
 const items=spec.items.map(item=>{if(!['glyph','field'].includes(item.kind)||!spec.tiles[item.key]||![item.x,item.y,...(item.color??[])].every(Number.isFinite))throw Error('Invalid vector asset item');return{...item,key:prefix+item.key,material};});
 const previous=assetTextures.get(material);previous?.texture?.destroy();for(const key of previous?.keys??[]){delete data.tiles[key];delete data.coverage96?.[key];delete data.coverage96Metrics?.[key];}
 for(const [key,tile]of Object.entries(spec.tiles)){data.tiles[prefix+key]=tile;keys.push(prefix+key);}for(const [key,phases]of Object.entries(spec.coverage96??{})){data.coverage96??={};data.coverage96Metrics??={};data.coverage96[prefix+key]=phases;data.coverage96Metrics[prefix+key]=spec.coverage96Metrics[key];}assetTextures.set(material,{texture,bind:texture?bind(texture):null,keys});sourceVectors.set(material,spec.vectors);assets[name]={widthBp:spec.widthBp,heightBp:spec.heightBp,items,source:spec.source};assetRevision++;
};
window.clearDocumentProject=()=>{for(const material of assetTextures.values()){material.texture?.destroy();for(const key of material.keys??[]){delete data.tiles[key];delete data.coverage96?.[key];delete data.coverage96Metrics?.[key];}}assetTextures.clear();sourceImages.clear();sourceVectors.clear();for(const key of Object.keys(assets))delete assets[key];for(const key of Object.keys(files))delete files[key];assetRevision++;};
function encodePage(draw,zoom,origin){
 const {canvas,context,page,scale,values}=draw,drawItems=draw.drawItems??page.items;
 const analytic=prepareTikzConsumer(values,{scale,zoom,origin,width:canvas.width,height:canvas.height});
 device.queue.writeBuffer(instances,0,values);
 device.queue.writeBuffer(uniform,0,new Float32Array([canvas.width/(scale*zoom),canvas.height/(scale*zoom),...origin]));
 const target=context.getCurrentTexture(),encoder=device.createCommandEncoder(),pass=encoder.beginRenderPass({colorAttachments:[{view:target.createView(),clearValue:[1,1,1,1],loadOp:'clear',storeOp:'store'}]});
 pass.setPipeline(pipeline);pass.setVertexBuffer(0,instances);pass.setBindGroup(0,fontBind);
 for(let i=0;i<drawItems.length;){if(analytic.get(i)?.visible===false){i++;continue;}const item=drawItems[i];if(item.kind==='image'){const material=assetTextures.get(item.asset)??assetTextures.get(item.asset.replace(/\.[^.]+$/,''));if(material){pass.setBindGroup(0,material.bind);pass.draw(6,1,0,i);pass.setBindGroup(0,fontBind);}i++;}else{let end=i+1;while(end<drawItems.length&&analytic.get(end)?.visible!==false&&drawItems[end].kind!=='image'&&drawItems[end].material===item.material)end++;pass.setBindGroup(0,item.material?assetTextures.get(item.material).bind:fontBind);pass.draw(6,end-i,0,i);i=end;}}
 pass.end();return{encoder,target};
}
function zoomLabel(zoom){$('zoom-value').textContent=zoom.toFixed(1)+'×';}
window.updateDocumentView=(number,{zoom,origin})=>{
 const draw=pageDraws[number];if(!draw)return;
 zoom=Math.max(1,Math.min(64,zoom));if(!Number.isFinite(zoom)||!origin.every(Number.isFinite))return;
 if(draw.pdfPixels){draw.drawItems=glyphPaintItems(vectorPaintItems(draw.page.items),data);draw.values=new Float32Array(draw.drawItems.flatMap(item=>packet({...item,...(draw.black&&!item.color?{color:[0,0,0,1]}:{})},draw.scale,false,1,[0,0],false)));draw.pdfPixels=false;}
 const {encoder}=encodePage(draw,zoom,origin);device.queue.submit([encoder.finish()]);
 window.documentViews[number]={origin:[...origin],zoom,worldWidth:draw.canvas.width/(draw.scale*zoom),worldHeight:draw.canvas.height/(draw.scale*zoom)};
 window.documentZoom=zoom;if(window.documentResult){window.documentResult.zoom=zoom;window.documentResult.pixelMode='MTSDF';}
 zoomLabel(zoom);window.documentViewReady=device.queue.onSubmittedWorkDone();
};
// Untimed validation readback, reusing the live renderer's packets and draw path.
let tileCapture=null;
window.captureDocumentRegion=async(number,{zoom=1,x=0,y=0,width=1024,height=1024,scale=96/72}={})=>{
 const draw=pageDraws[number];if(!draw)throw Error('Missing GPU page '+number);
 if(!Number.isInteger(width)||!Number.isInteger(height)||width<1||height<1||width>4096||height>4096||![zoom,x,y,scale].every(Number.isFinite)||zoom<1||zoom>64||scale<=0)throw Error('Invalid capture region');
 if(!tileCapture||tileCapture.canvas.width!==width||tileCapture.canvas.height!==height){tileCapture?.context.unconfigure();tileCapture?.buffer.destroy();const canvas=document.createElement('canvas');canvas.width=width;canvas.height=height;const context=canvas.getContext('webgpu');context.configure({device,format,alphaMode:'opaque',usage:GPUTextureUsage.RENDER_ATTACHMENT|GPUTextureUsage.COPY_SRC});const rowBytes=Math.ceil(width*4/256)*256;tileCapture={canvas,context,rowBytes,buffer:device.createBuffer({size:rowBytes*height,usage:GPUBufferUsage.COPY_DST|GPUBufferUsage.MAP_READ})};}
 const captureDraw=draw.pdfPixels&&Math.abs(scale*zoom-96/72)>1e-8?{...draw,drawItems:glyphPaintItems(vectorPaintItems(draw.page.items),data)}:draw;if(captureDraw!==draw)captureDraw.values=new Float32Array(captureDraw.drawItems.flatMap(item=>packet({...item,...(draw.black&&!item.color?{color:[0,0,0,1]}:{})},draw.scale,false,1,[0,0],false)));
 const {canvas,context,rowBytes,buffer}=tileCapture,{encoder,target}=encodePage({...captureDraw,canvas,context,scale},zoom,[x,y]);encoder.copyTextureToBuffer({texture:target},{buffer,bytesPerRow:rowBytes},[width,height]);device.queue.submit([encoder.finish()]);await buffer.mapAsync(GPUMapMode.READ);const raw=new Uint8Array(buffer.getMappedRange()),rgba=new Uint8Array(width*height*4);for(let row=0;row<height;row++)rgba.set(raw.subarray(row*rowBytes,row*rowBytes+width*4),row*width*4);if(format.startsWith('bgra'))for(let i=0;i<rgba.length;i+=4){const value=rgba[i];rgba[i]=rgba[i+2];rgba[i+2]=value;}buffer.unmap();let binary='';for(let i=0;i<rgba.length;i+=32768)binary+=String.fromCharCode(...rgba.subarray(i,i+32768));return btoa(binary);
};
attachDocumentGestures($('pages'),{getView:number=>{const canvas=pageDraws[number]?.canvas,view=window.documentViews?.[number];return canvas&&view?{...view,bounds:canvas.getBoundingClientRect()}:null;},setView:window.updateDocumentView});
let resizeFrame=0;
function resizeViewport(){
 const number=Number($('document-page').value||0),draw=pageDraws[number];if(!draw?.viewportMode)return;
 const width=Math.max(1,Math.ceil($('pages').clientWidth*(devicePixelRatio||1))),height=Math.max(1,Math.ceil($('pages').clientHeight*(devicePixelRatio||1)));
 draw.canvas.width=width;draw.canvas.height=height;draw.scale=Math.min(96/72,$('pages').clientWidth/draw.page.width)*(devicePixelRatio||1);window.documentScale=draw.scale;
 const view=window.documentViews[number];if(view)window.updateDocumentView(number,{zoom:view.zoom,origin:view.origin});
}
new ResizeObserver(()=>{cancelAnimationFrame(resizeFrame);resizeFrame=requestAnimationFrame(resizeViewport);}).observe($('pages'));
// Safari can still rubber-band ancestors unless touch defaults are explicitly
// cancelled on this surface; editing/controls keep their normal touch behavior.
$('pages').addEventListener('touchmove',event=>event.preventDefault(),{passive:false});
$('pages').addEventListener('gesturestart',event=>event.preventDefault(),{passive:false});
$('pages').addEventListener('gesturechange',event=>event.preventDefault(),{passive:false});
function contentBounds(page){const rects=page.items.map(item=>{if(item.kind==='glyph'||item.kind==='field'){const p=data.tiles[item.key]?.plane;if(!p)return null;return[item.x+p[0]*(item.sx??1),item.y+p[1]*(item.sy??1),item.x+p[2]*(item.sx??1),item.y+p[3]*(item.sy??1)];}return isVectorPrimitive(item)?vectorBounds(item):[item.x,item.y,item.x+item.width,item.y+item.height];}).filter(r=>r&&r.every(Number.isFinite));return rects.length?[Math.min(...rects.map(r=>r[0])),Math.min(...rects.map(r=>r[1])),Math.max(...rects.map(r=>r[2])),Math.max(...rects.map(r=>r[3]))]:[0,0,page.width,page.height];}
window.renderDocument=async(source,{scale=null,black=false,capture=false,pdfPixels=false,zoom=1,pan=null,pixelAlign=false,forceLayout=false,fitContent=false,buildContext=currentBuildContext}={})=>{
 const viewportMode=scale===null;const token=++revision,start=performance.now(),profile=await documentFontProfile(source,buildContext);if(token!==revision)return null;if(data!==profile.mapping){for(const material of assetTextures.values())for(const key of material.keys??[])profile.mapping.tiles[key]=data.tiles[key];data=profile.mapping;fontBind=profile.bind;cachedLayout=null;cachedSource=null;}const result=!forceLayout&&cachedSource===source&&cachedAssetRevision===assetRevision&&cachedBuildContext===JSON.stringify(buildContext)?cachedLayout:await typesetDocument(source,data,{assets,files,buildContext});cachedLayout=result;cachedSource=source;cachedAssetRevision=assetRevision;cachedBuildContext=JSON.stringify(buildContext);if(scale===null)scale=Math.min(96/72,($('pages').clientWidth||innerWidth-24)/(result.pages[0]?.width??595.276))*(devicePixelRatio||1);if(!Number.isFinite(scale)||scale<=0)throw Error('Invalid raster scale');if(fitContent){const bounds=result.pages.map(contentBounds),left=Math.min(...bounds.map(b=>b[0])),right=Math.max(...bounds.map(b=>b[2]));zoom=(result.pages[0]?.width??595.276)/Math.max(1,right-left+20);}zoom=Math.max(1,Math.min(64,zoom));window.documentZoom=zoom;window.documentScale=scale;window.documentViews=[];if(token!==revision)return null;
 $('document').value=source;for(const canvas of $('pages').querySelectorAll('canvas'))canvas.getContext('webgpu').unconfigure();$('pages').replaceChildren();pageDraws=[];const layoutMs=performance.now()-start;window.documentPixels=[];
 if(result.pages.length>100)throw Error('Document limit: 100 pages');
 for(const [number,page]of result.pages.entries()){if(token!==revision)return null;
  const canvas=document.createElement('canvas');canvas.width=Math.max(1,Math.ceil(page.width*scale));canvas.height=Math.max(1,Math.ceil(page.height*scale));if(viewportMode){canvas.width=Math.max(1,Math.ceil($('pages').clientWidth*(devicePixelRatio||1)));canvas.height=Math.max(1,Math.ceil($('pages').clientHeight*(devicePixelRatio||1)));}if(canvas.width>device.limits.maxTextureDimension2D||canvas.height>device.limits.maxTextureDimension2D)throw Error('Page backing texture exceeds the device limit; use camera zoom');canvas.style.width=viewportMode?'100%':`min(100%,${page.width*96/72}px)`;canvas.style.height=viewportMode?'100%':'auto';canvas.hidden=number!==0;canvas.style.touchAction='none';canvas.setAttribute('aria-label','Document page '+(number+1));$('pages').append(canvas);
  const firstInk=page.items.find(item=>item.kind==='glyph')??{x:0,y:0},firstTile=data.tiles[firstInk.key],bounds=fitContent?contentBounds(page):null,origin=pan??(bounds?[bounds[0]-10,bounds[1]-10]:zoom===1?[0,0]:[firstInk.x+(firstTile?.plane[0]??0)*(firstInk.sx??1)-2/zoom,firstInk.y+(firstTile?.plane[1]??-8)*(firstInk.sy??1)-2/zoom]);canvas.dataset.page=number;window.documentViews.push({origin,zoom,worldWidth:canvas.width/(scale*zoom),worldHeight:canvas.height/(scale*zoom)});const context=canvas.getContext('webgpu');context.configure({device,format,alphaMode:'opaque',usage:GPUTextureUsage.RENDER_ATTACHMENT|GPUTextureUsage.COPY_SRC});const drawItems=glyphPaintItems(vectorPaintItems(pdfPixels&&zoom===1?pdfTextPositions(page.items.flatMap(item=>{const parts=Math.abs(scale-96/72)<1e-8&&!item.crop&&!item.cropX&&item.kind==='glyph'&&(item.sx??1)===1&&(item.sy??1)===1?data.coverage96Parts?.[item.key]:null;return parts?parts.map(part=>({...item,key:part.key,x:item.x+part.x,y:item.y+part.y})):item;}),data,{pageHeight:page.height,fontWidthDigits:data.coverage96Rasterizer==='mupdf'?3:4}):page.items),data,{bitmap:!(pdfPixels&&zoom===1&&Math.abs(scale-96/72)<1e-8)});const list=drawItems.map(item=>packet({...item,...(black&&!item.color?{color:[0,0,0,1]}:{})},scale,pdfPixels&&zoom===1,zoom,origin,pixelAlign));if(list.length>50000)throw Error('Page draw limit: 50000 instances');const values=new Float32Array(list.flat());pageDraws[number]={canvas,context,page,scale,values,drawItems,black,viewportMode,pdfPixels:pdfPixels&&zoom===1};
  const {encoder,target}=encodePage(pageDraws[number],zoom,origin);let readback,rowBytes;if(capture){rowBytes=Math.ceil(canvas.width*4/256)*256;readback=device.createBuffer({size:rowBytes*canvas.height,usage:GPUBufferUsage.COPY_DST|GPUBufferUsage.MAP_READ});encoder.copyTextureToBuffer({texture:target},{buffer:readback,bytesPerRow:rowBytes},[canvas.width,canvas.height]);}device.queue.submit([encoder.finish()]);await device.queue.onSubmittedWorkDone();if(capture){await readback.mapAsync(GPUMapMode.READ);const raw=new Uint8Array(readback.getMappedRange()),rgba=new Uint8Array(canvas.width*canvas.height*4);for(let y=0;y<canvas.height;y++)rgba.set(raw.subarray(y*rowBytes,y*rowBytes+canvas.width*4),y*canvas.width*4);if(format.startsWith('bgra'))for(let j=0;j<rgba.length;j+=4){const r=rgba[j];rgba[j]=rgba[j+2];rgba[j+2]=r;}readback.unmap();readback.destroy();window.documentPixels.push({width:canvas.width,height:canvas.height,bytes:rgba});}
 }
 if(token!==revision)return null;const gpuCompleteMs=performance.now()-start;window.documentResult={...result,pixelMode:pdfPixels&&zoom===1?'96dpi font coverage cache with MTSDF fallback':'MTSDF',pixelAlign,zoom,layoutMs,gpuCompleteMs,backend:$('backend')?.textContent??window.documentBackend};$('timing').textContent=`${result.pages.length} pages · layout ${layoutMs.toFixed(1)} ms · GPU complete ${gpuCompleteMs.toFixed(1)} ms`;$('status').textContent=result.complete?'Preview rendered · page layout remains experimental':result.diagnostics.length+' compatibility issues';$('diagnostics').textContent=result.diagnostics.join('\n');$('render-summary').textContent=`${result.pages.length} ${result.pages.length===1?'page':'pages'} · ${gpuCompleteMs.toFixed(0)} ms${result.complete?'':' · issues'}`;$('notice').textContent='';zoomLabel(zoom);$('page-nav').hidden=result.pages.length<2;$('document-page').replaceChildren(...result.pages.map((_,i)=>new Option(`Page ${i+1} of ${result.pages.length}`,i)));return window.documentResult;
};
function setEditor(open){$('editor').hidden=!open;$('edit-toggle').textContent=open?'Hide editor':'Edit';$('edit-toggle').setAttribute('aria-expanded',String(open));}
$('edit-toggle').addEventListener('click',()=>{const open=$('editor').hidden;setEditor(open);if(open){$('document').focus({preventScroll:true});window.scrollTo({top:0,behavior:'instant'});}});
async function render({focusPreview=false}={}){if(!device)return;try{const result=await window.renderDocument($('document').value,{zoom:window.documentZoom??1,fitContent:focusPreview&&matchMedia('(max-width:600px)').matches});if(result&&focusPreview){document.activeElement?.blur();setEditor(false);for(const id of ['files-panel','render-info','navigation'])$(id).open=false;requestAnimationFrame(()=>window.scrollTo({top:0,behavior:'instant'}));}return result;}catch(error){$('status').textContent=error.message;$('notice').textContent=error.message;$('render-summary').textContent='Render failed';}}
$('render').addEventListener('click',()=>render({focusPreview:true}));$('document').addEventListener('keydown',event=>{if((event.ctrlKey||event.metaKey)&&event.key==='Enter'){event.preventDefault();render({focusPreview:true});}});
$('document-page').addEventListener('change',()=>{const number=Number($('document-page').value);for(const [i,draw]of pageDraws.entries())draw.canvas.hidden=i!==number;resizeViewport();zoomLabel(window.documentViews[number]?.zoom??1);$('navigation').open=false;});
$('fit-text').addEventListener('click',async()=>{try{await window.renderDocument($('document').value,{fitContent:true});$('navigation').open=false;}catch(error){$('notice').textContent=error.message;}});
$('reset-view').addEventListener('click',async()=>{try{await window.renderDocument($('document').value,{zoom:1});$('navigation').open=false;}catch(error){$('notice').textContent=error.message;}});
$('tex-file').addEventListener('change',async e=>{const file=e.target.files[0];if(file){currentBuildContext={entry:file.name,jobName:file.name.replace(/\.[^.]+$/,'')};$('document').value=await file.text();await render({focusPreview:true});}});$('image-files').addEventListener('change',async e=>{for(const file of e.target.files){if(/\.(?:tex|bbl|bib|m|txt)$/i.test(file.name))window.addDocumentFile(file.name,await file.text());else await addAsset(file.name,file);}await render({focusPreview:true});});
try{
 const mappingResponse=await fetch('./typing-data.json');if(!mappingResponse.ok)throw Error('Native font mapping could not be loaded');mappingBytes=await mappingResponse.arrayBuffer();data=JSON.parse(new TextDecoder().decode(mappingBytes));baseData=data;$('export-pdf').disabled=false;
 gpu=navigator.gpu;if(!gpu)throw Error('WebGPU unavailable');const adapter=await gpu.requestAdapter();if(!adapter)throw Error('WebGPU adapter unavailable');device=await adapter.requestDevice();device.lost.then(()=>{window.documentReady=false;$('render').disabled=true;$('status').textContent='WebGPU device lost. Reload to restart.';$('notice').textContent=$('status').textContent;});window.documentBackend=adapter.info.description||adapter.info.architecture||adapter.info.vendor;device.addEventListener('uncapturederror',e=>{errors.push(e.error.message);$('status').textContent=e.error.message;});
 const [raw,shader]=await Promise.all([fetch('./atlas.rgba.gz').then(async r=>{const raw=await r.arrayBuffer();return new Uint8Array(raw)[0]===31?new Response(new Blob([raw]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer():raw;}),fetch('./draw.wgsl').then(r=>r.text())]);atlas=device.createTexture({size:data.atlasSize,format:'rgba8unorm',usage:GPUTextureUsage.TEXTURE_BINDING|GPUTextureUsage.COPY_DST});device.queue.writeTexture({texture:atlas},raw,{bytesPerRow:data.atlasSize[0]*4},data.atlasSize);format=gpu.getPreferredCanvasFormat();const module=device.createShaderModule({code:shader});const info=await module.getCompilationInfo();if(info.messages.some(m=>m.type==='error'))throw Error(info.messages.map(m=>m.message).join('\n'));pipeline=await device.createRenderPipelineAsync({layout:'auto',vertex:{module,entryPoint:'vs',buffers:[{arrayStride:64,stepMode:'instance',attributes:[0,1,2,3].map(i=>({shaderLocation:i,offset:i*16,format:'float32x4'}))}]},fragment:{module,entryPoint:'fs',targets:[{format,blend:{color:{srcFactor:'one',dstFactor:'one-minus-src-alpha'},alpha:{srcFactor:'one',dstFactor:'one-minus-src-alpha'}}}]},primitive:{topology:'triangle-list'}});uniform=device.createBuffer({size:16,usage:GPUBufferUsage.UNIFORM|GPUBufferUsage.COPY_DST});instances=device.createBuffer({size:50000*64,usage:GPUBufferUsage.VERTEX|GPUBufferUsage.COPY_DST});fontBind=bind(atlas);baseFontBind=fontBind;$('render').disabled=false;window.documentReady=true;await render();
}catch(error){$('status').textContent=error.message;$('notice').textContent=error.message;$('render-summary').textContent='Unavailable';window.documentInitError=error.message;}
