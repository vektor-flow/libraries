import{mkdir,writeFile}from'node:fs/promises';
const{chromium}=await import(process.env.VKF_PLAYWRIGHT_MODULE??'playwright');
if(!process.env.VK_ICD_FILENAMES?.includes('swiftshader'))throw Error('Explicit software GPU required');
const[url,output]=process.argv.slice(2);await mkdir(output);
const browser=await chromium.launch({headless:false,executablePath:process.env.VKF_CHROMIUM,args:['--enable-unsafe-webgpu','--use-webgpu-adapter=swiftshader','--use-vulkan=swiftshader','--use-angle=vulkan','--enable-features=Vulkan','--disable-vulkan-surface']});
try{
 const page=await browser.newPage({viewport:{width:390,height:844},deviceScaleFactor:3,isMobile:true,hasTouch:true}),errors=[];page.on('pageerror',e=>errors.push(e.message));await page.goto(url);await page.waitForFunction(()=>window.documentResult||window.documentInitError);if(await page.evaluate(()=>window.documentInitError))throw Error(await page.evaluate(()=>window.documentInitError));
 await page.locator('#render').click();await page.waitForFunction(()=>document.getElementById('editor').hidden);
 const checks=[];
 const fixtures=[['sqrt',String.raw`\sqrt{x^2}`,'y'],['fraction',String.raw`\frac{a}{b}`,'y'],['overline',String.raw`\overline{x}`,'y'],['array',String.raw`\begin{array}{|c|}\hline x\\\hline\end{array}`,'y'],['isolated-horizontal',String.raw`\overline{\phantom{xxxx}}`,'y',true],['isolated-vertical',String.raw`\begin{array}{|c|}\phantom{x}\end{array}`,'x',true]];
 for(const [name,body,axis,isolated=false]of fixtures){
  const source=String.raw`\documentclass{article}\begin{document}$`+body+String.raw`$\end{document}`;
  for(const zoom of [1,4,16,28.6,64]){
   const result=await page.evaluate(async({source,zoom,axis})=>{
    await window.renderDocument(source,{scale:96/72,black:true});const rule=window.documentResult.pages[0].items.find(i=>i.kind==='rule'&&(axis==='y'?i.width>i.height:i.height>i.width));if(!rule)throw Error('No '+axis+' rule');
    const pan=[rule.x-2/zoom,rule.y-2/zoom];await window.renderDocument(source,{scale:96/72,zoom,pan,black:true,capture:true});const p=window.documentPixels[0],scale=window.documentScale*zoom;
    const sample=Math.floor((axis==='y'?rule.x-pan[0]+Math.min(rule.width*.65,6):rule.y-pan[1]+Math.min(rule.height*.65,6))*scale),top=(axis==='y'?rule.y-pan[1]:rule.x-pan[0])*scale,bottom=top+(axis==='y'?rule.height:rule.width)*scale;
    // At 1x adjacent fraction glyphs can merge into the same profile; isolated
    // phantom fixtures check subpixel rules without that neighbouring ink.
    let runs=[],run=0,ink=0,maxDarkness=0;const start=Math.max(0,Math.floor(top-2*scale)),end=Math.min((axis==='y'?p.height:p.width)-1,Math.ceil(bottom+2*scale));
    for(let n=start;n<=end;n++){const x=axis==='y'?sample:n,y=axis==='y'?n:sample,value=p.bytes[(y*p.width+x)*4];maxDarkness=Math.max(maxDarkness,255-value);if(value<250)ink++;if(value>5&&value<250)run++;else if(run){runs.push(run);run=0;}}if(run)runs.push(run);
    return{zoom,rule,top,bottom,expectedThickness:(axis==='y'?rule.height:rule.width)*scale,maxPartialCoverageRun:Math.max(0,...runs),partialCoverageRuns:runs,inkPixels:ink,maxDarkness,pixelMode:window.documentResult.pixelMode};
   },{source,zoom,axis});checks.push({name,axis,edgeCheck:zoom>1||isolated,...result});await page.locator('canvas').first().screenshot({path:output+`/${name}-${zoom}.png`});
  }
 }
 const gpuErrors=await page.evaluate(()=>window.documentGpuErrors);await writeFile(output+'/rules.json',JSON.stringify({checks,errors,gpuErrors,scope:'Horizontal/vertical native rule coverage from software WebGPU RGBA readback; 390px DPR3 phone viewport, explicit96dpi capture. Physical Safari remains unqualified.'},null,2));
 if(errors.length||gpuErrors.length||checks.some(c=>(c.edgeCheck&&c.maxPartialCoverageRun>2)||!c.inkPixels||c.pixelMode!=='MTSDF'))throw Error('Rule edge softens with zoom or disappears');console.log(JSON.stringify(checks.map(c=>({name:c.name,zoom:c.zoom,partial:c.maxPartialCoverageRun,ink:c.inkPixels}))));
}finally{await browser.close();}
