// Compare source-generated TikZ GPU paints against independently built native
// PDFs. Native compilation and reference rasterization are separate dev steps.
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {compileTikzPicture} from './tikz-layout.mjs';
const {chromium}=await import(process.env.VKF_PLAYWRIGHT_MODULE??'playwright');
if(!process.env.VK_ICD_FILENAMES?.includes('swiftshader'))throw Error('Explicit SwiftShader ICD required');
const [url,fixturesPath,output]=process.argv.slice(2),fixtures=JSON.parse(await readFile(fixturesPath,'utf8'));
await mkdir(output);const browser=await chromium.launch({headless:true,executablePath:process.env.VKF_CHROMIUM,args:['--enable-unsafe-webgpu','--use-webgpu-adapter=swiftshader','--use-vulkan=swiftshader','--use-angle=vulkan','--enable-features=Vulkan','--disable-vulkan-surface']});
try{
 const page=await browser.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));await page.goto(url);await page.waitForFunction(()=>window.documentReady||window.documentInitError);
 if(await page.evaluate(()=>window.documentInitError))throw Error(await page.evaluate(()=>window.documentInitError));
 const checks=[];
 for(const fixture of fixtures){
  const box=compileTikzPicture(fixture.source),source=String.raw`\documentclass[letterpaper]{article}\usepackage{tikz}\begin{document}\noindent\begin{tikzpicture}`+fixture.source+String.raw`\end{tikzpicture}\end{document}`;
  for(const zoom of [1,2,4,8,16,64]){
   const result=await page.evaluate(async({source,box,zoom})=>{
    await window.renderDocument(source,{scale:96/72,black:true});if(!window.documentResult.complete)throw Error(window.documentResult.diagnostics.join('\n'));
    const first=window.documentResult.pages[0].items.find(i=>i.tikz),left=first.x-box.items[0].x,baseline=first.y-box.items[0].y,pad=2*72/72.27,scale=zoom*96/72;
    const width=Math.min(2048,Math.ceil((box.width+2*pad)*scale)),height=Math.min(2048,Math.ceil((box.height+box.depth+2*pad)*scale));
    const bytes=await window.captureDocumentRegion(0,{scale,zoom:1,x:left-pad,y:baseline-box.height-pad,width,height});
    return{width,height,bytes,zoom,box:{width:box.width,height:box.height,depth:box.depth}};
   },{source,box,zoom});
   await writeFile(output+'/'+fixture.name+'-'+zoom+'.rgba',Buffer.from(result.bytes,'base64'));delete result.bytes;checks.push({name:fixture.name,...result});
  }
 }
 const gpuErrors=await page.evaluate(()=>window.documentGpuErrors);await writeFile(output+'/captures.json',JSON.stringify({checks,errors,gpuErrors},null,2));if(errors.length||gpuErrors.length)throw Error('Browser errors: '+[...errors,...gpuErrors].join('\n'));console.log(JSON.stringify({captures:checks.length,errors,gpuErrors}));
}finally{await browser.close();}
