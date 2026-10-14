import {mkdir,writeFile} from 'node:fs/promises';
const {chromium}=await import(process.env.VKF_PLAYWRIGHT_MODULE??'playwright');
if(!process.env.VK_ICD_FILENAMES?.includes('swiftshader'))throw Error('Explicit software adapter required');
const [url,output]=process.argv.slice(2);await mkdir(output);
const browser=await chromium.launch({headless:false,executablePath:process.env.VKF_CHROMIUM,args:['--enable-unsafe-webgpu','--use-webgpu-adapter=swiftshader','--use-vulkan=swiftshader','--use-angle=vulkan','--enable-features=Vulkan','--disable-vulkan-surface']});
try{
 const page=await browser.newPage({viewport:{width:390,height:844},isMobile:true,hasTouch:true,deviceScaleFactor:2}),errors=[];page.on('pageerror',e=>errors.push(e.message));await page.goto(url);await page.waitForFunction(()=>window.mathTyping?.queueMs!==undefined,{timeout:30000});
 await page.locator('#example-a').selectOption('basic');await page.locator('#example-b').selectOption('fraction');await page.getByRole('button',{name:'Transform A → B',exact:true}).tap();await page.waitForFunction(()=>window.mathTransition?.progress===1);
 await page.locator('#progress').evaluate(e=>{e.value=500;e.dispatchEvent(new Event('input',{bubbles:true}));});await page.waitForFunction(()=>window.mathTransition?.progress===.5);
 await page.screenshot({path:output+'/phone-compact.png'});
 const phone=await page.evaluate(()=>({width:innerWidth,overflow:document.documentElement.scrollWidth>innerWidth,canvasBottom:document.getElementById('math').getBoundingClientRect().bottom,transformBottom:document.getElementById('transform').getBoundingClientRect().bottom,viewport:innerHeight,transition:window.mathTransition}));
 await page.getByRole('tab',{name:'Style',exact:true}).tap();await page.getByRole('button',{name:'Red ink',exact:true}).tap();await page.waitForFunction(()=>window.mathTyping?.appearance.color[0]>.9);await page.screenshot({path:output+'/phone-style.png'});
 await page.getByRole('tab',{name:'Examples',exact:true}).tap();await page.getByRole('button',{name:'Greek',exact:true}).tap();await page.waitForFunction(()=>window.mathTyping?.complete&&document.getElementById('tab-equations').getAttribute('aria-selected')==='true');
 const result={phone,errors,gpuErrors:await page.evaluate(()=>window.mathGpuErrors),backend:await page.locator('#backend').textContent(),scope:'Touch-enabled Chromium phone viewport on forced SwiftShader; not physical phone qualification.'};await writeFile(output+'/phone-verification.json',JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result));if(errors.length||result.gpuErrors.length||phone.overflow||phone.canvasBottom>phone.viewport||phone.transformBottom>phone.viewport)throw Error('Compact phone flow failed');
}finally{await browser.close();}
