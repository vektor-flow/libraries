import assert from 'node:assert/strict';
const {chromium}=await import(process.env.VKF_PLAYWRIGHT_MODULE??'playwright');
const base=process.env.VKF_SITE_URL??'http://127.0.0.1:8857';
const browser=await chromium.launch({executablePath:'/usr/bin/google-chrome',headless:true,args:['--use-angle=swiftshader','--enable-unsafe-swiftshader','--enable-unsafe-webgpu','--use-vulkan=swiftshader','--enable-features=Vulkan']});
try{
 const page=await browser.newPage({viewport:{width:390,height:844},reducedMotion:'reduce'});const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(base+'/previews/gpu-morph/?validation');
 await page.waitForFunction(()=>window.gpuMorph?.stats.frames>0||window.gpuMorph?.stats.errors.length,null,{timeout:120000});
 if(!base.includes('127.0.0.1')&&!base.includes('localhost')){
  assert((await page.locator('#status').innerText()).includes('requires a hardware GPU'));console.log('PASS public software rejection; no CPU fallback');
 }else{
  assert.deepEqual(await page.evaluate(()=>gpuMorph.stats.errors),[]);
  assert(await page.evaluate(()=>gpuMorph.stats.software));
  const assignment=await page.evaluate(()=>gpuMorph.engine.inspectAssignment());assert.equal(new Set(assignment).size,assignment.length);
  // Track API boundaries: endpoint data stays resident, only32bytes controls per frame.
  await page.evaluate(()=>{window.writes=[];window.solves=0;const e=gpuMorph.engine,w=e.device.queue.writeBuffer.bind(e.device.queue),s=e.encodeSolve.bind(e);e.device.queue.writeBuffer=(...args)=>{writes.push(args[2].byteLength);return w(...args)};e.encodeSolve=(...args)=>{solves++;return s(...args)};});
  const hashes=[];
  for(const phase of [0,.5,1,.5]){await page.evaluate(t=>gpuMorph.render(t),phase);hashes.push((await page.locator('canvas').screenshot()).toString('base64'));}
  assert.notEqual(hashes[0],hashes[1]);assert.notEqual(hashes[1],hashes[2]);assert.equal(hashes[1],hashes[3]);
  assert.deepEqual(await page.evaluate(()=>writes),[32,32,32,32]);assert.equal(await page.evaluate(()=>solves),4);
  for(const [width,height] of [[320,568],[844,390],[390,844]]){await page.setViewportSize({width,height});await page.waitForTimeout(150);assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));}
  await page.locator('#source').fill('h(x)=x^4+4x+7');await page.waitForTimeout(600);await page.waitForFunction(()=>gpuMorph.engine.ready);
  await page.locator('#sweep').click();await page.waitForFunction(()=>gpuMorph.stats.sweep.length===5||gpuMorph.stats.errors.length,null,{timeout:240000});
  assert.deepEqual(await page.evaluate(()=>gpuMorph.stats.errors),[]);const rows=await page.evaluate(()=>gpuMorph.stats.sweep);assert(rows[4].bodies>900);assert(rows.every(r=>r.software));assert.equal(new Set(rows.map(r=>JSON.stringify(r.resolution))).size,1);assert.deepEqual(errors,[]);
  console.log('PASS GPU shader validation, assignment permutation, arbitrary phase/reversal, per-frame32byte controls and fresh solve, responsive widths, edited scene, five-size sweep. SOFTWARE ONLY.');
  console.log(JSON.stringify(rows.map(r=>({bodies:r.bodies,grid:r.grid,iterations:r.iterations,resolution:r.resolution,samples:r.samples})),null,2));
 }
}finally{await browser.close();}
