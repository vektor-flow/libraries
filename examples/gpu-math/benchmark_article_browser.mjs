// Explicit software-browser, real file-cache-cold / warm / changed-source runs.
import {readFile,writeFile,mkdir,readdir} from 'node:fs/promises';
import {join,resolve,dirname} from 'node:path';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
const {chromium}=await import(process.env.VKF_PLAYWRIGHT_MODULE??'playwright');
if(!process.env.VK_ICD_FILENAMES?.includes('swiftshader'))throw Error('Explicit SwiftShader ICD required');
const [url,projectArg,entry,snapshotArg,cacheHelper,editPath,output]=process.argv.slice(2);
if(!output)throw Error('Usage: url project-root entry.tex served-snapshot cache-helper.py edit.json output');
const project=resolve(projectArg),snapshot=resolve(snapshotArg),edit=JSON.parse(await readFile(editPath,'utf8')),trials=Number(process.env.VKF_DOCUMENT_TRIALS??3);
if(!Number.isInteger(trials)||trials<1||trials>10)throw Error('Invalid trial count');
await mkdir(output);const paths=[];
for(const p of await readdir(snapshot,{recursive:true}))if(/\.(mjs|json|gz|wgsl|html)$/.test(p))paths.push(join(snapshot,p));
for(const p of await readdir(project,{recursive:true}))if(/\.(tex|bib|sty|cls)$/.test(p))paths.push(join(project,p));
const chromeRoot=dirname(process.env.VKF_CHROMIUM);for(const p of await readdir(chromeRoot,{recursive:true,withFileTypes:true}))if(p.isFile())paths.push(join(p.parentPath,p.name));
await writeFile(join(output,'input-paths.json'),JSON.stringify(paths));const hash=s=>createHash('sha256').update(s).digest('hex'),results=[];
for(let trial=1;trial<=trials;trial++){
 const cache=JSON.parse(execFileSync('sudo',['-n','/usr/bin/python3',cacheHelper,join(output,'input-paths.json')],{encoding:'utf8',maxBuffer:16*1024*1024}));
 await writeFile(join(output,'cache-'+trial+'.json'),JSON.stringify(cache));
 const resident=Object.values(cache.after).reduce((n,p)=>n+p.resident,0);if(resident)throw Error('Measured input data still resident before launch');
 const start=performance.now(),browser=await chromium.launch({headless:true,executablePath:process.env.VKF_CHROMIUM,args:['--enable-unsafe-webgpu','--use-webgpu-adapter=swiftshader','--use-vulkan=swiftshader','--use-angle=vulkan','--enable-features=Vulkan','--disable-vulkan-surface']});
 try{
  const browserLaunchMs=performance.now()-start,page=await browser.newPage({viewport:{width:1100,height:900}}),errors=[];page.on('pageerror',e=>errors.push(e.message));await page.goto(url);await page.waitForFunction(()=>window.documentReady||window.documentInitError,{timeout:60000});if(await page.evaluate(()=>window.documentInitError))throw Error(await page.evaluate(()=>window.documentInitError));const appReadyMs=performance.now()-start;
  const files={};for(const p of await readdir(project,{recursive:true}))if(/\.(tex|bib|sty|cls)$/.test(p))files[p]=await readFile(join(project,p),'utf8');const source=files[entry];if(typeof source!=='string'||source.split(edit.before).length!==2)throw Error('Edit location must be unique');const changed=source.replace(edit.before,edit.after);if(changed===source)throw Error('Edit does not change source');
  await page.evaluate(files=>{window.clearDocumentProject();for(const [n,t]of Object.entries(files))window.addDocumentFile(n,t);},files);const inputsReadyMs=performance.now()-start;
  const measure=async source=>page.evaluate(async({source,entry})=>{const r=await window.renderDocument(source,{scale:96/72,black:true,pdfPixels:true,forceLayout:true,buildContext:{entry}});return{pages:r.pages.length,complete:r.complete,diagnostics:r.diagnostics,layoutMs:r.layoutMs,gpuCompleteMs:r.gpuCompleteMs,glyphs:r.pages.reduce((n,p)=>n+p.items.filter(i=>i.kind==='glyph').length,0),backend:r.backend};},{source,entry});
  const cold=await measure(source),totalColdMs=performance.now()-start;
  const digest=()=>page.evaluate(async()=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(JSON.stringify(window.documentResult.pages.map(p=>p.items))))),b=>b.toString(16).padStart(2,'0')).join(''));
  const baselineDigest=await digest(),warm=[],edits=[];
  for(let i=0;i<3;i++)warm.push(await measure(source));
  for(let i=0;i<3;i++){const text=i%2===0?changed:source,r=await measure(text),layoutSha256=await digest();if((i%2===0)===(layoutSha256===baselineDigest))throw Error('Visible edit output was not changed/reverted');edits.push({...r,sourceSha256:hash(text),layoutSha256,changed:i%2===0});}
  const gpuErrors=await page.evaluate(()=>window.documentGpuErrors),row={trial,browserLaunchMs,appReadyMs,inputsReadyMs,totalColdMs,cold,warm,edits,sourceSha256:hash(source),editedSourceSha256:hash(changed),baselineLayoutSha256:baselineDigest,inputDataCachePages:Object.values(cache.after).reduce((n,p)=>n+p.pages,0),inputResidentPages:resident,errors,gpuErrors};
  if([cold,...warm,...edits].some(r=>!r.complete||r.pages!==cold.pages)||errors.length||gpuErrors.length)throw Error('Incomplete/invalid timed output');results.push(row);await writeFile(join(output,'trial-'+trial+'.json'),JSON.stringify(row,null,2));console.log(JSON.stringify({trial,totalColdMs,cold,warm:warm.map(r=>r.gpuCompleteMs),edits:edits.map(r=>r.gpuCompleteMs)}));
 }finally{await browser.close();}
}
const median=xs=>{xs=[...xs].sort((a,b)=>a-b);return xs[Math.floor(xs.length/2)];};const summary={trials:results,medianColdTotalMs:median(results.map(r=>r.totalColdMs)),medianColdDocumentMs:median(results.map(r=>r.cold.gpuCompleteMs)),medianWarmDocumentMs:median(results.flatMap(r=>r.warm.map(r=>r.gpuCompleteMs))),medianSmallEditDocumentMs:median(results.flatMap(r=>r.edits.map(r=>r.gpuCompleteMs))),medianWarmLayoutMs:median(results.flatMap(r=>r.warm.map(r=>r.layoutMs))),scope:'Source-to-completed all-page WebGPU submissions on explicit SwiftShader. Three fresh Chromium processes/profiles after Linux sync/drop_caches=3 and root mincore verifies all recorded source/runtime/font assets and Chromium executable/resource files nonresident. Cold total includes browser launch, navigation, base app/font/pipeline initialization, source/.bib read and transfer, optical font fetch/decompression/upload, independent layout and every page submission. Cold document measures optical-font load onward. Warm and edits force fresh full layout and page draws; no document-layout cache. Edits really add/remove configured title punctuation, verified by source and placed-item hashes. Offline reusable font preparation, installation, reference rendering, framebuffer readback, PDF generation, file saving and controller verification are excluded. OS shared executable/library pages, hardware caches and browser-independent server-process startup are not reset.'};await writeFile(join(output,'summary.json'),JSON.stringify(summary,null,2));console.log(JSON.stringify(Object.fromEntries(Object.entries(summary).filter(([k])=>k.startsWith('median')))));
