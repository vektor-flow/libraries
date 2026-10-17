// Development-only full article and zoom capture. Runtime receives source files,
// never a reference PDF or reference page coordinates.
import {readFile,writeFile,mkdir,readdir} from 'node:fs/promises';
import {resolve,relative,join} from 'node:path';
const {chromium}=await import(process.env.VKF_PLAYWRIGHT_MODULE??'playwright');
if(!process.env.VK_ICD_FILENAMES?.includes('swiftshader'))throw Error('Explicit SwiftShader ICD required');
const [url,rootArg,entry,output]=process.argv.slice(2);if(!url||!rootArg||!entry||!output)throw Error('Usage: url project-root entry.tex output');
const root=resolve(rootArg),source=await readFile(join(root,entry),'utf8'),files={};
for(const path of await readdir(root,{recursive:true}))if(/\.(tex|bib|sty|cls)$/.test(path))files[path]=await readFile(join(root,path),'utf8');
await mkdir(output);const browser=await chromium.launch({headless:true,executablePath:process.env.VKF_CHROMIUM,args:['--enable-unsafe-webgpu','--use-webgpu-adapter=swiftshader','--use-vulkan=swiftshader','--use-angle=vulkan','--enable-features=Vulkan','--disable-vulkan-surface']});
try{
 const page=await browser.newPage({viewport:{width:1100,height:900}}),errors=[];page.on('pageerror',e=>errors.push(e.message));await page.goto(url);await page.waitForFunction(()=>window.documentReady||window.documentInitError,{timeout:60000});if(await page.evaluate(()=>window.documentInitError))throw Error(await page.evaluate(()=>window.documentInitError));
 await page.evaluate(files=>{window.clearDocumentProject();for(const [name,text]of Object.entries(files))window.addDocumentFile(name,text);},files);
 const modes=[];
 for(const pdfPixels of (process.env.VKF_CAPTURE_MODES==='coverage'?[true]:[false,true])){
  const name=pdfPixels?'coverage':'mtsdf',folder=join(output,name);await mkdir(folder);
  const result=await page.evaluate(async({source,entry,pdfPixels})=>{const r=await window.renderDocument(source,{scale:96/72,black:true,capture:true,pdfPixels,forceLayout:true,buildContext:{entry}});return{...r,layoutMs:r.layoutMs,gpuCompleteMs:r.gpuCompleteMs};},{source,entry,pdfPixels});
  await writeFile(join(folder,'layout.json'),JSON.stringify(result));
  const sizes=await page.evaluate(()=>window.documentPixels.map(({width,height})=>({width,height})));await writeFile(join(folder,'pixel-sizes.json'),JSON.stringify(sizes));
  const selected=process.env.VKF_CAPTURE_PAGES?.split(',').map(Number);
  for(let i=0;i<sizes.length;i++){if(selected&&!selected.includes(i+1))continue;const raw=await page.evaluate(i=>{const bytes=window.documentPixels[i].bytes;let s='';for(let at=0;at<bytes.length;at+=16384)s+=String.fromCharCode(...bytes.subarray(at,at+16384));return btoa(s);},i);await writeFile(join(folder,'page-'+String(i+1).padStart(2,'0')+'.rgba'),Buffer.from(raw,'base64'));}
  modes.push({name,pages:result.pages.length,complete:result.complete,diagnostics:result.diagnostics,layoutMs:result.layoutMs,gpuCompleteMs:result.gpuCompleteMs});
 }
 const zooms=[];
 // Exercise text, math, BBM and native vector paths from arbitrary source.
 const targets=await page.evaluate(()=>{const out=[],seen=new Set();for(const [page,p]of window.documentResult.pages.entries())for(const i of p.items){const family=i.kind==='glyph'?(i.key.includes('mathbbm')?'bbm':i.key.includes('@document:roman')?'roman':i.key.startsWith('script/')?'script':null):i.kind==='bezier'?'bezier':null;if(family&&!seen.has(family)){seen.add(family);out.push({family,page,x:i.x,y:i.y});}}return out;});
 await page.evaluate(async()=>{window.updateDocumentView(0,{zoom:1,origin:[0,0]});await window.documentViewReady;});
 for(const target of targets)for(const zoom of [1,2,4,8,16,64]){
  const scale=zoom*96/72,x=Math.floor((target.x-3)*scale)/scale,y=Math.floor((target.y-12)*scale)/scale,width=Math.min(768,Math.ceil(36*scale)),height=Math.min(768,Math.ceil(28*scale)),raw=await page.evaluate(async({page,x,y,width,height,scale})=>window.captureDocumentRegion(page,{x,y,width,height,scale,zoom:1}),{...target,x,y,width,height,scale});const name=target.family+'-'+zoom;await writeFile(join(output,name+'.rgba'),Buffer.from(raw,'base64'));zooms.push({...target,name,zoom,scale,x,y,width,height});
 }
 const gpuErrors=await page.evaluate(()=>window.documentGpuErrors);await writeFile(join(output,'receipt.json'),JSON.stringify({url,entry,modes,zooms,errors,gpuErrors},null,2));console.log(JSON.stringify({modes,zoomCaptures:zooms.length,errors,gpuErrors}));if(errors.length||gpuErrors.length||modes.some(m=>!m.complete))throw Error('Incomplete browser output');
}finally{await browser.close();}
