// Browser orchestration only. JSON here records test evidence, not draw data.
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {readFile,writeFile} from 'node:fs/promises';
import {extname,resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
import {parseArgs} from 'node:util';

const {values}=parseArgs({options:{artifacts:{type:'string'},playwright:{type:'string'},chromium:{type:'string'},software:{type:'boolean',default:false}}});
for(const name of ['artifacts','playwright','chromium'])assert.ok(values[name],`Missing --${name}`);
const root=resolve(values.artifacts),{chromium}=await import(pathToFileURL(resolve(values.playwright)));
const server=createServer(async(req,res)=>{
 try{
  const url=new URL(req.url,'http://localhost');
  if(url.pathname==='/favicon.ico'){res.writeHead(204);res.end();return;}
  const path=resolve(root,'.'+url.pathname);
  if(!path.startsWith(root+'/'))throw Error('Invalid test asset path');
  const body=path===root+'/index.html'?Buffer.from('<!doctype html><title>Typed VKF GPU buffer qualification</title>'):await readFile(path);
  res.setHeader('Content-Type',({'.mjs':'text/javascript','.wasm':'application/wasm','.json':'application/json','.html':'text/html'})[extname(path)]??'text/plain');res.end(body);
 }catch(error){res.writeHead(404);res.end(error.message);}
});
await new Promise(r=>server.listen(0,'127.0.0.1',r));
let browser;const report={passed:false,fullRendererQualified:false,softwareRequested:values.software};
try{
 const args=['--no-sandbox','--enable-unsafe-webgpu'];
 if(values.software)args.push('--enable-features=Vulkan','--use-webgpu-adapter=swiftshader','--use-vulkan=swiftshader','--use-angle=swiftshader','--enable-unsafe-swiftshader','--enable-vulkan','--disable-vulkan-surface');
 browser=await chromium.launch({headless:true,executablePath:values.chromium,args});
 const page=await browser.newPage();page.on('console',x=>(report.notes??=[]).push(x.text()));
 await page.goto('http://127.0.0.1:'+server.address().port+'/index.html');
 Object.assign(report,await page.evaluate(async software=>{
  const adapter=await navigator.gpu?.requestAdapter({forceFallbackAdapter:software});if(!adapter)throw Error('No WebGPU adapter');
  const info={vendor:adapter.info.vendor,architecture:adapter.info.architecture,device:adapter.info.device,description:adapter.info.description,isFallbackAdapter:adapter.info.isFallbackAdapter};
  const isSoftware=adapter.info.isFallbackAdapter||/swiftshader|llvmpipe|software/i.test(JSON.stringify(info));
  if(isSoftware!==software)throw Error('Requested adapter class differs: '+JSON.stringify(info));
  const device=await adapter.requestDevice(),errors=[];device.addEventListener('uncapturederror',x=>errors.push(x.error.message));
  const [{createDocumentGpuArena},manifest,bytes,shader,draw,expected,many]=await Promise.all([
   import('./document_gpu_arena.mjs'),fetch('./kernel/manifest.json').then(r=>r.json()),fetch('./kernel/kernel.wasm').then(r=>r.arrayBuffer()),
   fetch('./document_gpu_arena.wgsl').then(r=>r.text()),fetch('./draw.wgsl').then(r=>r.text()),fetch('./expected.json').then(r=>r.json()),fetch('./expected-many.json').then(r=>r.json())
  ]);
  const {instance}=await WebAssembly.instantiate(bytes),arena=await createDocumentGpuArena({device,instance,manifest,shader});
  const fail=message=>{throw Error(message);};
  const readback=async(buffer,size)=>{
   const copy=device.createBuffer({size:Math.max(4,size),usage:GPUBufferUsage.COPY_DST|GPUBufferUsage.MAP_READ}),encoder=device.createCommandEncoder();
   encoder.copyBufferToBuffer(buffer,0,copy,0,Math.max(4,size));device.queue.submit([encoder.finish()]);await copy.mapAsync(GPUMapMode.READ);
   const values=new Uint32Array(copy.getMappedRange()).slice();copy.unmap();copy.destroy();return [...values];
  };
  let prior,packet;const checks=[];
  for(const [entry,revision,target] of [
   ['transport',0,expected[0]],['transport',2,expected[1]],['transport_many',2,many],['transport_empty',3,{rows:[]}],['transport',3,expected[2]]
  ]){
   const heap=instance.exports.vkf_vm_heap_ptr(),before={...arena.metrics};packet=arena.commit(entry,[revision]);
   if(instance.exports.vkf_vm_heap_ptr()!==heap)fail('Transient VKF heap was not restored');
   if(packet.count!==target.rows.length||packet.stride!==64||packet.revision!==revision)fail('GPU header differs from VKF output');
   if(prior&&packet.count<=prior.count&&prior.buffer!==packet.buffer)fail('Shrinking or empty edit replaced the resident buffer');
   if(prior&&packet.count<=prior.count&&before.allocations!==arena.metrics.allocations)fail('Shrinking or empty edit allocated new resources');
   if(prior?.count===4&&packet.count===4&&prior.buffer!==packet.buffer)fail('Small edit replaced the resident buffer');
   await device.queue.onSubmittedWorkDone();
   if((await readback(packet.errorBuffer,4))[0]!==0)fail('GPU tagged numeric ABI validation failed');
   const got=packet.count?await readback(packet.buffer,packet.count*packet.stride):[],want=new Uint32Array(new Float32Array(target.rows.flat()).buffer);
   if(got.length!==want.length||got.some((x,i)=>x!==want[i]))fail('GPU numeric conversion differs at '+got.findIndex((x,i)=>x!==want[i]));
   checks.push({entry,revision,count:packet.count,values:got.length,exactFloat32:true,heapRestored:true,bufferReused:prior?prior.buffer===packet.buffer:false,allocations:arena.metrics.allocations});prior=packet;
  }
  const heap=instance.exports.vkf_vm_heap_ptr(),metrics={...arena.metrics};
  for(const [entry,args] of [['missing',[]],['transport',[]],['transport',[null]]]){
   let rejected=false;try{arena.commit(entry,args);}catch{rejected=true;}
   if(!rejected||instance.exports.vkf_vm_heap_ptr()!==heap||JSON.stringify(metrics)!==JSON.stringify(arena.metrics))fail('Invalid call changed arena state');
  }
  // Use the actual preview shader and its four vec4 attributes, not a test shader.
  const module=device.createShaderModule({code:draw}),compilation=await module.getCompilationInfo();
  if(compilation.messages.some(x=>x.type==='error'))fail(compilation.messages.map(x=>x.message).join('\n'));
  const pipeline=await device.createRenderPipelineAsync({layout:'auto',vertex:{module,entryPoint:'vs',buffers:[{arrayStride:64,stepMode:'instance',attributes:[0,1,2,3].map(i=>({shaderLocation:i,offset:i*16,format:'float32x4'}))}]},fragment:{module,entryPoint:'fs',targets:[{format:'rgba8unorm'}]}});
  const uniform=device.createBuffer({size:16,usage:GPUBufferUsage.UNIFORM|GPUBufferUsage.COPY_DST});device.queue.writeBuffer(uniform,0,new Float32Array([64,16,0,0]));
  const atlas=device.createTexture({size:[1,1],format:'rgba8unorm',usage:GPUTextureUsage.TEXTURE_BINDING|GPUTextureUsage.COPY_DST});
  device.queue.writeTexture({texture:atlas},new Uint8Array([255,255,255,255]),{bytesPerRow:4},[1,1]);
  const binding=device.createBindGroup({layout:pipeline.getBindGroupLayout(0),entries:[{binding:0,resource:{buffer:uniform}},{binding:1,resource:atlas.createView()},{binding:2,resource:device.createSampler()}]});
  const texture=device.createTexture({size:[64,16],format:'rgba8unorm',usage:GPUTextureUsage.RENDER_ATTACHMENT|GPUTextureUsage.COPY_SRC});
  for(let frame=0;frame<10;frame++){
   const encoder=device.createCommandEncoder(),pass=encoder.beginRenderPass({colorAttachments:[{view:texture.createView(),loadOp:'clear',storeOp:'store',clearValue:[0,0,0,1]}]});
   pass.setPipeline(pipeline);pass.setBindGroup(0,binding);pass.setVertexBuffer(0,packet.buffer);
   for(const row of [0,2,3])pass.draw(6,1,0,row);pass.end();device.queue.submit([encoder.finish()]);
  }
  await device.queue.onSubmittedWorkDone();if(JSON.stringify(metrics)!==JSON.stringify(arena.metrics))fail('Drawing resident frames changed or uploaded instance data');
  const pix=device.createBuffer({size:256*16,usage:GPUBufferUsage.COPY_DST|GPUBufferUsage.MAP_READ}),commands=device.createCommandEncoder();commands.copyTextureToBuffer({texture},{buffer:pix,bytesPerRow:256},[64,16]);device.queue.submit([commands.finish()]);await pix.mapAsync(GPUMapMode.READ);
  const pixels=new Uint8Array(pix.getMappedRange()),sample=x=>[...pixels.slice((4*64+x)*4,(4*64+x)*4+4)],red=sample(4),green=sample(20),blue=sample(36),background=sample(48);
  if(red.join()!=='255,0,0,255'||green.join()!=='0,255,0,255'||blue.join()!=='0,0,255,255'||background.join()!=='0,0,0,255')fail('Production shader draw differs: '+JSON.stringify({red,green,blue,background}));
  pix.unmap();pix.destroy();texture.destroy();atlas.destroy();uniform.destroy();arena.dispose();arena.dispose();
  let rejected=false;try{arena.commit('transport',[0]);}catch{rejected=true;}if(!rejected)fail('Disposed arena accepted an edit');
  await device.queue.onSubmittedWorkDone();if(errors.length)fail(errors.join('\n'));device.destroy();
  return {passed:true,physicalGpu:!isSoftware,softwareWebGpu:isSoftware,adapter:info,checks,invalidCallsRejected:3,disposeIdempotent:true,productionShader:true,drawFramesWithoutUpload:10,pixels:{red,green,blue,background},metrics,shaderErrors:errors};
 },values.software));
}catch(error){report.error=String(error);process.exitCode=1;}
finally{await writeFile(root+'/gpu-verification.json',JSON.stringify(report,null,2)+'\n');await browser?.close();await new Promise(r=>server.close(r));}
assert.equal(report.passed,true,report.error);console.log(JSON.stringify(report));
