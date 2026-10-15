import{mkdir,writeFile}from'node:fs/promises';
const{chromium}=await import(process.env.VKF_PLAYWRIGHT_MODULE??'playwright');
if(!process.env.VK_ICD_FILENAMES?.includes('swiftshader'))throw Error('Explicit software GPU required');
const[url,output]=process.argv.slice(2);await mkdir(output);
const browser=await chromium.launch({headless:false,executablePath:process.env.VKF_CHROMIUM,args:['--enable-unsafe-webgpu','--use-webgpu-adapter=swiftshader','--use-vulkan=swiftshader','--use-angle=vulkan','--enable-features=Vulkan','--disable-vulkan-surface']});
try{
 const page=await browser.newPage({viewport:{width:390,height:844},hasTouch:true,isMobile:true}),errors=[];page.on('pageerror',e=>errors.push(e.message));await page.goto(url);await page.waitForFunction(()=>window.documentResult||window.documentInitError);if(await page.evaluate(()=>window.documentInitError))throw Error(await page.evaluate(()=>window.documentInitError));
 await page.locator('#render').click();await page.waitForFunction(()=>document.getElementById('editor').hidden);
 await page.evaluate(()=>window.renderDocument(String.raw`\documentclass{article}\begin{document}H\end{document}`,{zoom:1,black:true}));
 await page.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));
 const canvas=page.locator('canvas').first(),box=await canvas.boundingBox();await canvas.evaluate(c=>window.gestureCanvas=c);
 const state=()=>page.evaluate(()=>({...window.documentViews[0],sameCanvas:window.gestureCanvas===document.querySelector('canvas'),scrollY,scrollX,viewportScale:visualViewport.scale,stageRect:document.getElementById('pages').getBoundingClientRect().toJSON(),canvasRect:document.querySelector('canvas:not([hidden])').getBoundingClientRect().toJSON(),headerTop:document.querySelector('header').getBoundingClientRect().top}));
 const settled=async()=>{await page.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));await page.evaluate(()=>window.documentViewReady);};
 const world=(view,x,y)=>[view.origin[0]+(x-box.x)*view.worldWidth/box.width,view.origin[1]+(y-box.y)*view.worldWidth/box.width];
 const near=(actual,expected,tolerance=.02)=>{if(Math.abs(actual-expected)>tolerance)throw Error('Gesture mismatch '+JSON.stringify({actual,expected}));};
 const checks=[];
 await canvas.screenshot({path:output+'/before-drag.png'});let before=await state();
 await page.mouse.move(box.x+140,box.y+120);await page.mouse.down();await page.mouse.move(box.x+190,box.y+155,{steps:5});await page.mouse.up();await settled();let after=await state();
 near((before.origin[0]-after.origin[0])*box.width/before.worldWidth,50);near((before.origin[1]-after.origin[1])*box.width/before.worldWidth,35);await canvas.screenshot({path:output+'/after-drag.png'});checks.push({name:'mouse drag at 1x',before,after});
 before=after;await page.mouse.move(box.x+60,box.y+60);await page.mouse.down();await page.mouse.move(box.x-20,box.y+80,{steps:4});await page.mouse.up();await settled();after=await state();near((before.origin[0]-after.origin[0])*box.width/before.worldWidth,-80);near((before.origin[1]-after.origin[1])*box.width/before.worldWidth,20);checks.push({name:'mouse capture beyond canvas edge',before,after});
 const x=box.x+170,y=box.y+180;before=after;let anchor=world(before,x,y);
 await page.mouse.move(x,y);await page.mouse.wheel(0,-240);await settled();after=await state();if(after.zoom<=before.zoom)throw Error('Wheel did not zoom');world(after,x,y).forEach((v,i)=>near(v,anchor[i]));checks.push({name:'cursor-anchored wheel',before,after});
 const cdp=await page.context().newCDPSession(page),touch=(type,points)=>cdp.send('Input.dispatchTouchEvent',{type,touchPoints:points.map(([id,x,y])=>({id,x,y,radiusX:2,radiusY:2,force:1}))});
 before=await state();await touch('touchStart',[[1,x-40,y],[2,x+40,y]]);anchor=world(before,x,y);
 await touch('touchMove',[[1,x-70+10,y+15],[2,x+70+10,y+15]]);await settled();after=await state();near(after.zoom/before.zoom,140/80);world(after,x+10,y+15).forEach((v,i)=>near(v,anchor[i]));near(after.scrollY,before.scrollY);near(after.viewportScale,before.viewportScale);checks.push({name:'two-touch pinch and translation',before,after});
 // Lifting one finger rebases the remaining finger; continuing to drag must not jump.
 await touch('touchEnd',[[2,x+80,y+15]]);await settled();before=await state();await touch('touchMove',[[1,x-30,y+35]]);await settled();after=await state();near((before.origin[0]-after.origin[0])*box.width/before.worldWidth,30);near((before.origin[1]-after.origin[1])*box.width/before.worldWidth,20);checks.push({name:'pinch to one-finger pan',before,after});await touch('touchEnd',[]);await settled();
 // A fresh single finger also pans, independently of mouse input.
 before=await state();await touch('touchStart',[[3,x,y]]);await touch('touchMove',[[3,x-25,y-30]]);await touch('touchEnd',[]);await settled();after=await state();near((before.origin[0]-after.origin[0])*box.width/before.worldWidth,-25);near((before.origin[1]-after.origin[1])*box.width/before.worldWidth,-30);checks.push({name:'single-touch pan',before,after});
 await touch('touchStart',[[4,x,y]]);await touch('touchCancel',[]);await settled();if(await page.locator('#pages').evaluate(e=>e.classList.contains('dragging')))throw Error('Cancelled touch stayed active');
 await page.mouse.move(x,y);await page.mouse.wheel(0,-100000);await settled();near((await state()).zoom,64);await page.mouse.wheel(0,100000);await settled();near((await state()).zoom,1);
 if(!checks.every(c=>c.after.sameCanvas))throw Error('Gesture replaced the canvas');
 await canvas.screenshot({path:output+'/gestures.png'});
 // Moving page 2 must preserve page 1's camera and canvas.
 await page.evaluate(()=>window.renderDocument(String.raw`\documentclass{article}\begin{document}First\newpage Second\end{document}`,{zoom:1}));
 const first=await page.evaluate(()=>JSON.stringify(window.documentViews[0]));await page.locator('#navigation summary').click();await page.locator('#document-page').selectOption('1');const secondBox=await page.locator('canvas').nth(1).boundingBox();await page.mouse.move(secondBox.x+100,secondBox.y+100);await page.mouse.wheel(0,-100);await settled();if(await page.evaluate(()=>JSON.stringify(window.documentViews[0]))!==first)throw Error('Page 2 moved page 1');if(await page.evaluate(()=>window.documentViews[1].zoom)<=1)throw Error('Page 2 did not zoom');
 for(const check of checks){near(check.after.scrollY,check.before.scrollY);near(check.after.scrollX,check.before.scrollX);near(check.after.headerTop,check.before.headerTop);for(const key of ['x','y','width','height'])near(check.after.stageRect[key],check.before.stageRect[key]);}
 const gpuErrors=await page.evaluate(()=>window.documentGpuErrors),overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth);if(errors.length||gpuErrors.length||overflow)throw Error('Page/GPU errors or overflow');if(await page.locator('input[type=range]').count())throw Error('Zoom slider remains');
 await writeFile(output+'/gestures.json',JSON.stringify({checks,errors,gpuErrors,overflow,multiPageIndependent:true,scope:'Real CDP touch input and Playwright mouse/wheel on explicit software WebGPU; not physical Safari qualification.'},null,2));console.log(JSON.stringify({checks:checks.map(c=>c.name),errors,gpuErrors,overflow}));
}finally{await browser.close();}
