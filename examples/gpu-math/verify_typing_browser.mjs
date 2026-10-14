import {mkdir,writeFile} from 'node:fs/promises';
const {chromium}=await import(process.env.VKF_PLAYWRIGHT_MODULE??'playwright');
const executablePath=process.env.VKF_CHROMIUM;if(!executablePath||!process.env.VK_ICD_FILENAMES?.includes('swiftshader'))throw Error('Explicit software Chromium/ICD required');
const url=process.argv[2],output=process.argv[3];await mkdir(output);
const browser=await chromium.launch({headless:process.env.VKF_HEADLESS!=='false',executablePath,args:['--enable-unsafe-webgpu','--use-webgpu-adapter=swiftshader','--use-vulkan=swiftshader','--use-angle=vulkan','--enable-features=Vulkan','--disable-vulkan-surface']});
let page;try{
 page=await browser.newPage({viewport:{width:1100,height:900}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(url);await page.waitForFunction(()=>window.mathTyping?.queueMs!==undefined,{timeout:30000});
 const backend=await page.locator('#backend').textContent();if(!/swiftshader/i.test(backend))throw Error('Non-software adapter');
 const initial=await page.evaluate(()=>window.mathTyping);await page.screenshot({path:`${output}/fraction.png`});await page.locator('canvas').screenshot({path:`${output}/canvas.png`});
 const field=page.locator('#expression');await field.fill('');await field.pressSequentially('x_i^2+\\alpha=y',{delay:40});
 await page.waitForFunction(()=>window.mathTyping?.source==='x_i^2+\\alpha=y');const typed=await page.evaluate(()=>window.mathTyping);
 await field.fill('\\frac{x}{');await page.waitForFunction(()=>window.mathTyping?.source==='\\frac{x}{');const incomplete=await page.evaluate(()=>window.mathTyping);if(incomplete.complete||!incomplete.placeholders)throw Error('Incomplete source did not render a current draft');
 await field.fill('\\sum_x^n');await page.waitForFunction(()=>window.mathTyping?.source==='\\sum_x^n');await field.press('End');await field.press('Backspace');await page.waitForFunction(()=>window.mathTyping?.source==='\\sum_x^');const deletion=await page.evaluate(()=>window.mathTyping);if(deletion.glyphKeys.includes('script/n')||!deletion.placeholders)throw Error('Deleted exponent remained visible');
 const features=[];for(const name of ['Greek','Sums & integrals','Matrices & vectors','Cases','Nested scopes']){await page.getByRole('button',{name,exact:true}).click();await page.waitForFunction(()=>window.mathTyping?.source===document.getElementById('expression').value&&window.mathTyping?.complete);features.push({name,current:await page.evaluate(()=>window.mathTyping)});await page.locator('canvas').screenshot({path:`${output}/feature-${features.length}.png`});}
 await field.fill('\\sum_{i=0}^n\\frac{a}{b}');await page.waitForFunction(()=>window.mathTyping?.source==='\\sum_{i=0}^n\\frac{a}{b}');const display=await page.evaluate(()=>window.mathTyping);await page.getByRole('radio',{name:'Inline',exact:true}).check();await page.waitForFunction(()=>window.mathTyping?.mode==='inline');const inline=await page.evaluate(()=>window.mathTyping);if(!inline.glyphKeys.includes('text/\\sum')||!display.glyphKeys.includes('display/\\sum'))throw Error('Math style did not change');await page.locator('canvas').screenshot({path:`${output}/inline.png`});await page.getByRole('radio',{name:'Display',exact:true}).check();await page.waitForFunction(()=>window.mathTyping?.mode==='display');
 await field.fill('\\frac{x}{y}');await page.waitForFunction(()=>window.mathTyping?.source==='\\frac{x}{y}');
 await page.getByRole('button',{name:'Long expression',exact:true}).click();await page.waitForFunction(()=>window.mathTyping?.source?.length>500);const long=await page.evaluate(()=>window.mathTyping);await page.screenshot({path:`${output}/long.png`,fullPage:true});
 const timings=[];for(let i=0;i<60;i++){
  const source=`x_i^${i%10}+\\frac{a+${i%10}}{b}=\\alpha`;
  await field.fill(source);await page.waitForFunction(s=>window.mathTyping?.source===s,source);timings.push(await page.evaluate(()=>window.mathTyping.queueMs));
 }
 timings.sort((a,b)=>a-b);
 await page.setViewportSize({width:390,height:844});await page.waitForTimeout(150);await page.screenshot({path:`${output}/phone.png`,fullPage:true});
 const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth);
 const result={browser:browser.version(),backend,initial,typed,incomplete,deletion,features,display,inline,long,warmEdits:{count:60,p50ms:timings[30],p95ms:timings[57],maxms:timings.at(-1)},errors,gpuErrors:await page.evaluate(()=>window.mathGpuErrors),phoneOverflow:overflow,
  scope:'Real DOM input and WebGPU canvas on forced SwiftShader. Queue completion measured, not physical screen presentation or native VKF integration.'};
 await writeFile(`${output}/typing-browser-verification.json`,JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result));
 if(errors.length||result.gpuErrors.length||overflow)throw Error('Browser check failed');
}catch(error){if(page){await writeFile(`${output}/failure.json`,JSON.stringify(await page.evaluate(()=>({status:document.getElementById('status')?.textContent,input:document.getElementById('expression')?.value,current:window.mathTyping,gpuErrors:window.mathGpuErrors})),null,2));}throw error;}finally{await browser.close();}
