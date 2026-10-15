import{mkdir,writeFile}from'node:fs/promises';
const{chromium}=await import(process.env.VKF_PLAYWRIGHT_MODULE??'playwright');
if(!process.env.VK_ICD_FILENAMES?.includes('swiftshader'))throw Error('Explicit software GPU required');
const[url,output]=process.argv.slice(2);await mkdir(output);
const browser=await chromium.launch({headless:false,executablePath:process.env.VKF_CHROMIUM,args:['--enable-unsafe-webgpu','--use-webgpu-adapter=swiftshader','--use-vulkan=swiftshader','--use-angle=vulkan','--enable-features=Vulkan','--disable-vulkan-surface']});
try{
 const page=await browser.newPage({viewport:{width:390,height:844},deviceScaleFactor:3,isMobile:true,hasTouch:true}),errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(url);await page.waitForFunction(()=>window.documentResult||window.documentInitError);if(await page.evaluate(()=>window.documentInitError))throw Error(await page.evaluate(()=>window.documentInitError));
 const checks=[];
 for(const [width,height]of [[390,844],[320,568],[430,932],[844,390]]){
  await page.setViewportSize({width,height});
  if(await page.locator('#editor').isHidden())await page.locator('#edit-toggle').click();
  const source=String.raw`\documentclass{article}\begin{document}Phone ${width}: $x^2+\frac{a}{b}=\alpha$\end{document}`;
  await page.locator('#document').fill(source);await page.locator('#render').click();
  await page.waitForFunction(s=>window.documentResult&&document.getElementById('document').value===s&&document.getElementById('editor').hidden,source);
  const result=await page.evaluate(()=>{const canvas=document.querySelector('canvas'),r=canvas.getBoundingClientRect(),head=document.querySelector('header').getBoundingClientRect();return{width:innerWidth,height:innerHeight,canvasTop:r.top,canvasWidth:r.width,headerBottom:head.bottom,editorHidden:document.getElementById('editor').hidden,active:document.activeElement.tagName,overflow:document.documentElement.scrollWidth>innerWidth,filesOpen:document.getElementById('files-panel').open,infoOpen:document.getElementById('render-info').open,pages:window.documentResult.pages.length,scale:window.documentScale,backingWidth:canvas.width};});
  if(result.overflow||!result.editorHidden||result.active==='TEXTAREA'||result.canvasTop<result.headerBottom-1||result.canvasTop>150||result.canvasWidth<Math.min(width-20,790)||result.filesOpen||result.infoOpen)throw Error('Phone preview failed '+JSON.stringify(result));
  checks.push(result);await page.screenshot({path:output+`/preview-${width}.png`});
 }
 await page.setViewportSize({width:390,height:844});await page.locator('#edit-toggle').click();if(!await page.locator('#document').isVisible())throw Error('Editor did not reopen');await page.screenshot({path:output+'/editor.png'});
 await page.locator('#files-panel summary').click();await page.screenshot({path:output+'/files.png'});await page.locator('#render').click();await page.waitForFunction(()=>document.getElementById('editor').hidden);
 const box=await page.locator('canvas').first().boundingBox(),before=await page.evaluate(()=>window.documentZoom);await page.mouse.move(box.x+100,box.y+100);await page.mouse.wheel(0,-120);await page.waitForFunction(before=>window.documentZoom>before,before);await page.screenshot({path:output+'/zoom.png'});await page.locator('#navigation summary').click();await page.locator('#reset-view').click();await page.waitForFunction(()=>window.documentResult?.zoom===1);
 await page.locator('#render-info summary').click();await page.screenshot({path:output+'/details.png'});await page.locator('#navigation summary').click();if(!await page.getByRole('link',{name:'Comparisons',exact:true}).isVisible())throw Error('Navigation inaccessible');
 const gpuErrors=await page.evaluate(()=>window.documentGpuErrors);if(errors.length||gpuErrors.length)throw Error('GPU/page errors');
 await writeFile(output+'/phone.json',JSON.stringify({checks,errors,gpuErrors,scope:'Touch phone viewports with DPR3 on explicit software WebGPU; no physical Safari/keyboard qualification.'},null,2));console.log(JSON.stringify({checks,errors,gpuErrors}));
}finally{await browser.close();}
