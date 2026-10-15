const {chromium}=await import(process.env.VKF_PLAYWRIGHT_MODULE??'playwright');
import {fileURLToPath} from 'node:url';import path from 'node:path';
import fs from 'node:fs';import assert from 'node:assert/strict';
const source=path.dirname(fileURLToPath(import.meta.url)),reference=source+'/reference';
const out=process.env.VKF_RESULTS_DIR??'/tmp/vkf-gpu-morph-validation-'+Date.now();fs.mkdirSync(out,{recursive:true});
const base=process.env.VKF_PREVIEW_URL??'http://127.0.0.1:8857/previews/gpu-morph/';
function health(){} // This harness never runs on physical hardware.
const browser=await chromium.launch({executablePath:'/usr/bin/google-chrome',headless:true,args:['--use-angle=swiftshader','--use-vulkan=swiftshader','--enable-features=Vulkan','--enable-unsafe-webgpu','--enable-unsafe-swiftshader'],ignoreDefaultArgs:['--enable-unsafe-swiftshader']});const results=[];
try{
 const p=await browser.newPage({viewport:{width:1280,height:1100},reducedMotion:'reduce'});p.on('console',m=>{if(m.type()==='error')console.log('browser',m.text())});p.on('pageerror',e=>console.log('pageerror',e.message));
 await p.route('**/optimized-engine.mjs',r=>r.fulfill({contentType:'text/javascript',body:fs.readFileSync(source+'/engine.mjs','utf8').replace("subgroups=adapter.features.has('subgroups')",process.env.NO_SUBGROUPS?'subgroups=false':"subgroups=adapter.features.has('subgroups')").replace('GPUBufferUsage.STORAGE|GPUBufferUsage.COPY_DST|extra','GPUBufferUsage.STORAGE|GPUBufferUsage.COPY_DST|GPUBufferUsage.COPY_SRC|extra')}));
 await p.route('**/engine.mjs',r=>r.fulfill({contentType:'text/javascript',body:fs.readFileSync(reference+'/engine.mjs','utf8').replace('GPUBufferUsage.STORAGE|GPUBufferUsage.COPY_DST|extra','GPUBufferUsage.STORAGE|GPUBufferUsage.COPY_DST|GPUBufferUsage.COPY_SRC|extra')}));
 await p.route('**/morph.wgsl',r=>r.fulfill({contentType:'text/plain',body:fs.readFileSync(reference+'/morph.wgsl','utf8')}));
 await p.route('**/optimized.wgsl',r=>r.fulfill({contentType:'text/plain',body:fs.readFileSync(source+'/morph.wgsl','utf8')}));
 await p.goto(base+'?validation');await p.waitForFunction(()=>gpuMorph.stats.frames||gpuMorph.stats.errors.length,null,{timeout:120000});assert.deepEqual(await p.evaluate(()=>gpuMorph.stats.errors),[]);assert.equal(await p.evaluate(()=>gpuMorph.stats.software),true);health();
 await p.evaluate(async()=>{
 window.data=await fetch('../gpu-math-typing/typing-data.json').then(r=>r.json());window.pack=(await import('./endpoints.mjs')).packScenes;window.typeset=(await import('../gpu-math-typing/typing-layout.mjs')).typeset;
 const blob=await fetch('../gpu-math-typing/atlas.rgba.gz').then(r=>new Response(r.body.pipeThrough(new DecompressionStream('gzip'))).arrayBuffer()),shader=await fetch('./optimized.wgsl').then(r=>r.text());const canvas=document.createElement('canvas');canvas.width=1200;canvas.height=760;const {MorphEngine}=await import('./optimized-engine.mjs');window.optimized=await MorphEngine.create(canvas,data,blob,shader,{validation:true});window.baseline=gpuMorph.engine;
 window.read=async(e,buf)=>{const d=e.device,b=d.createBuffer({size:buf.size,usage:GPUBufferUsage.MAP_READ|GPUBufferUsage.COPY_DST}),c=d.createCommandEncoder();c.copyBufferToBuffer(buf,0,b,0,buf.size);d.queue.submit([c.finish()]);await b.mapAsync(GPUMapMode.READ);const a=new Float32Array(b.getMappedRange().slice(0));b.unmap();b.destroy();return a;};
 window.pixels=async e=>{const d=e.device,w=1200,h=760,row=4864,t=d.createTexture({size:[w,h],format:navigator.gpu.getPreferredCanvasFormat(),usage:GPUTextureUsage.RENDER_ATTACHMENT|GPUTextureUsage.COPY_SRC}),b=d.createBuffer({size:row*h,usage:GPUBufferUsage.COPY_DST|GPUBufferUsage.MAP_READ}),c=d.createCommandEncoder(),p=c.beginRenderPass({colorAttachments:[{view:t.createView(),clearValue:[.035,.055,.065,1],loadOp:'clear',storeOp:'store'}]});p.setPipeline(e.renderPipeline);p.setBindGroup(0,e.bind);p.draw(6,e.n);p.end();c.copyTextureToBuffer({texture:t},{buffer:b,bytesPerRow:row},[w,h]);d.queue.submit([c.finish()]);await b.mapAsync(GPUMapMode.READ);const a=new Uint8Array(b.getMappedRange().slice(0));b.unmap();b.destroy();t.destroy();return a;};
 });console.log('Software validation only; not hardware performance');health();
 const invalid=await p.evaluate(async()=>{let rejected=0;for(const options of [{grid:0},{grid:33},{iterations:0},{iterations:33}]){try{await optimized.generate(new Float32Array(16),new Float32Array(16),options);}catch{rejected++;}}const invalid=new Float32Array(16);invalid[0]=NaN;try{await optimized.generate(invalid,invalid);}catch{rejected++;}return rejected;});assert.equal(invalid,5);
 const matching=await p.evaluate(async()=>{
 let cases=0;for(const n of [1,17,63,64,65,127,256,1024]){
 const packet=new Float32Array(n*16);for(let i=0;i<n;i++)packet.set([10+i,10,20,20,0,0,0,0,1,1,1,1,4,0,0,0],i*16);
 for(const e of [baseline,optimized])await e.generate(packet,packet,{grid:32,iterations:1});
 for(const mode of ['ties','random','quantized','unique','chain','close']){
 let state=17;const random=()=>{state=(Math.imul(state,1664525)+1013904223)>>>0;return state/4294967296;};const costs=new Float32Array(n*n);
 for(let i=0;i<n;i++)for(let j=0;j<n;j++){let c=0;if(mode==='random')c=random()*100;if(mode==='quantized')c=Math.floor(random()*5);if(mode==='unique')c=j===n-1-i?0:10+j;if(mode==='chain')c=j;if(mode==='close')c=1+Math.floor(random()*8)*2**-23;costs[i*n+j]=c;}
 const used=new Set(),oracle=[];for(let i=0;i<n;i++){let best=-1;for(let j=0;j<n;j++)if(!used.has(j)&&(best<0||costs[i*n+j]<costs[i*n+best]))best=j;used.add(best);oracle.push(best);}
 for(const e of [baseline,optimized]){const buffer=e.costs??e.buffers[2];e.device.queue.writeBuffer(buffer,0,costs);const enc=e.device.createCommandEncoder(),pass=enc.beginComputePass();pass.setBindGroup(0,e.computeBinds[0]);if(e.encodeMatching)e.encodeMatching(pass,n);else{pass.setPipeline(e.compute.assign_pairs);pass.dispatchWorkgroups(1);}pass.end();e.device.queue.submit([enc.finish()]);const actual=await e.inspectAssignment();if(actual.some((x,i)=>x!==oracle[i]))throw Error(`cost oracle mismatch ${n} ${mode}`);}
 cases++;
 }}return {cases,oracle:'independent CPU reference, test-only',subgroups:optimized.subgroups};});health();console.log('MATCHING',JSON.stringify(matching));
 const flowChecks=await p.evaluate(async()=>{
 let seed=103;const rand=()=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed/4294967296;};let checks=0,maxFlowError=0,maxPixelError=0;
 for(const [grid,iterations] of [[16,1],[16,7],[32,1],[32,4],[32,12],[32,32]]){
 const packet=pack(typeset('a+b+c+2x=7',data.maps),typeset('f(x)=x^3-4x',data.maps),data,65);
 for(let i=0;i<packet.a.length;i+=16){packet.a[i]+=rand()*100;packet.b[i+1]+=rand()*100;packet.a[i+2]*=.5+rand();packet.b[i+3]*=.5+rand();if(i%48===0){packet.a[i+12]=4;packet.b[i+12]=5;}}
 for(const e of [baseline,optimized]){e.canvas.width=1200;e.canvas.height=760;await e.generate(packet.a,packet.b,{grid,iterations});}
 for(const phase of [0,.17,.5,.83,1,.17]){
 let a,b,pixA,pixB;await baseline.draw(phase);a=await read(baseline,baseline.flows[iterations%2]);pixA=await pixels(baseline);await optimized.draw(phase);b=await read(optimized,optimized.flows[iterations%2]);pixB=await pixels(optimized);
 for(let i=0;i<a.length;i++)maxFlowError=Math.max(maxFlowError,Math.abs(a[i]-b[i]));for(let i=0;i<pixA.length;i++)maxPixelError=Math.max(maxPixelError,Math.abs(pixA[i]-pixB[i]));checks++;
 }}return {checks,maxFlowError,maxPixelError};});health();console.log('FLOW',JSON.stringify(flowChecks));assert(flowChecks.maxFlowError<1e-5);assert(flowChecks.maxPixelError<=1);fs.writeFileSync(out+'/quality.json',JSON.stringify({matching,flowChecks},null,2));
}finally{await browser.close();health();}
