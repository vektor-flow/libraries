/** Software-only real WebGPU codegen/readback/render benchmark. */
import {writeFile,mkdir} from 'node:fs/promises';
const {chromium}=await import(process.env.VKF_PLAYWRIGHT_MODULE ?? 'playwright');
const executablePath=process.env.VKF_CHROMIUM;
if(!executablePath || !process.env.VK_ICD_FILENAMES?.includes('swiftshader')) throw Error('Explicit Chromium and SwiftShader ICD required');
const base=process.argv[2],output=process.argv[3];
if(!base || !output)throw Error('Usage: verify_webgpu.mjs http://loopback/artifact-root fresh-output');
await mkdir(output); // Preserve earlier receipts.
const browser=await chromium.launch({headless:true,executablePath,args:[
 '--enable-unsafe-webgpu','--use-webgpu-adapter=swiftshader','--use-vulkan=swiftshader','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
try {
 const page=await browser.newPage();const pageErrors=[];
 page.on('pageerror',e=>pageErrors.push(e.message));
 await page.goto(base);
 const results=[];
 for(const name of ['fraction','long']) {
  const result=await page.evaluate(async({name,assetDir})=>{
   const adapter=await navigator.gpu.requestAdapter({forceFallbackAdapter:true});
   if(!adapter)throw Error('No software WebGPU adapter');
   const info={vendor:adapter.info.vendor,architecture:adapter.info.architecture,description:adapter.info.description,isFallbackAdapter:adapter.info.isFallbackAdapter};
   if(!/swiftshader/i.test(JSON.stringify(info)))throw Error('Refusing non-SwiftShader adapter');
   const device=await adapter.requestDevice();const errors=[];
   device.addEventListener('uncapturederror',e=>errors.push(e.error.message));
   const {create}=await import(`./${assetDir}/${name}/expression.gpu.mjs`);
   const coldStart=performance.now();const expression=await create(device);const coldMs=performance.now()-coldStart;
   const [w,h]=expression.metadata.texture.size;
   async function read(texture,width,height) {
    const pitch=Math.ceil(width*4/256)*256;
    const buffer=device.createBuffer({size:pitch*height,usage:GPUBufferUsage.COPY_DST|GPUBufferUsage.MAP_READ});
    const encoder=device.createCommandEncoder();encoder.copyTextureToBuffer({texture},{buffer,bytesPerRow:pitch},[width,height]);
    device.queue.submit([encoder.finish()]);await buffer.mapAsync(GPUMapMode.READ);
    const padded=new Uint8Array(buffer.getMappedRange()),bytes=new Uint8Array(width*height*4);
    for(let y=0;y<height;y++)bytes.set(padded.subarray(y*pitch,y*pitch+width*4),y*width*4);
    buffer.unmap();buffer.destroy();return bytes;
   }
   const field=await read(expression.texture,w,h);
   const viewport=[800,800];
   const target=device.createTexture({size:viewport,format:'rgba8unorm',usage:GPUTextureUsage.RENDER_ATTACHMENT|GPUTextureUsage.COPY_SRC});
   const times=[];
   for(let frame=0;frame<130;frame++) {
    const start=performance.now();const encoder=device.createCommandEncoder();
    const pass=encoder.beginRenderPass({colorAttachments:[{view:target.createView(),clearValue:[0,0,0,0],loadOp:'clear',storeOp:'store'}]});
    expression.draw(pass,{viewport,x:16,y:16,unitsToPixels:2});pass.end();
    device.queue.submit([encoder.finish()]);await device.queue.onSubmittedWorkDone();
    if(frame>=10)times.push(performance.now()-start);
   }
   const rendered=await read(target,...viewport);
   const referencePacket=await (await fetch(name==='long'?'./independent-long-packet.json':'./direct-latex-pinned/fraction/path-packet.json')).json();
   const canvas=document.createElement('canvas');canvas.width=viewport[0]*4;canvas.height=viewport[1]*4;
   const ctx=canvas.getContext('2d');
   for(const primitive of referencePacket.primitives) {
    const t=primitive.transform;
    ctx.setTransform(8*t[0],8*t[1],8*t[2],8*t[3],64+8*t[4],64+8*t[5]);
    ctx.fill(new Path2D(referencePacket.outlines[primitive.outline].svgPath),'nonzero');
   }
   const high=ctx.getImageData(0,0,canvas.width,canvas.height).data;
   const reference=new Uint8Array(viewport[0]*viewport[1]*4);
   for(let y=0;y<viewport[1];y++)for(let x=0;x<viewport[0];x++) {
    let sum=0;for(let dy=0;dy<4;dy++)for(let dx=0;dx<4;dx++)sum+=high[((y*4+dy)*canvas.width+x*4+dx)*4+3];
    reference[(y*viewport[0]+x)*4+3]=Math.round(sum/16);
   }
   let intersection=0,union=0,alphaDifference=0,softUnion=0;
   for(let i=3;i<reference.length;i+=4) {
    const a=rendered[i],b=reference[i];
    if(a>=128&&b>=128)intersection++;
    if(a>=128||b>=128)union++;
    alphaDifference+=Math.abs(a-b)/255;softUnion+=Math.max(a,b)/255;
   }
   const fidelity={thresholdIoU:intersection/union,relativeAlphaDifference:alphaDifference/softUnion,
    reference:'Independent Path2D vector rasterization at 4x with area downsampling; no font lookup'};
   times.sort((a,b)=>a-b);
   const timing={frames:times.length,p50ms:times[60],p95ms:times[114],maxms:times.at(-1)};
   expression.dispose();target.destroy();device.destroy();
   function encode(bytes) {
    let text='';for(let i=0;i<bytes.length;i+=8192)text+=String.fromCharCode(...bytes.subarray(i,i+8192));
    return btoa(text);
   }
   return {name,info,errors,coldMs,timing,fidelity,fieldSize:[w,h],field:encode(field),viewport,rendered:encode(rendered),metadata:expression.metadata};
  },{name,assetDir:process.env.VKF_CODEGEN_DIR ?? 'gpu-codegen-binned'});
  const {field,rendered,...receipt}=result;
  await writeFile(`${output}/${name}-field.rgba`,Buffer.from(field,'base64'));
  await writeFile(`${output}/${name}-render.rgba`,Buffer.from(rendered,'base64'));
  results.push(receipt);
 }
 const receipt={acceptance:{relativeAlphaDifferenceMax:0.05,reason:'Antialiased area error is the quality gate at small text sizes; threshold IoU is recorded as a diagnostic because pixels near half coverage flip its binary classification.'},browser:browser.version(),results,pageErrors,scope:'Forced SwiftShader software WebGPU; completed submission wall times include synchronization. No physical GPU, native VKF integration or cold source-to-pixels target qualification.'};
 await writeFile(`${output}/webgpu-verification.json`,JSON.stringify(receipt,null,2)+'\n');
 if(pageErrors.length || results.some(r=>r.errors.length || r.fidelity.relativeAlphaDifference>.05))throw Error('WebGPU validation failed; inspect receipt');
 console.log(JSON.stringify(results.map(r=>({case:r.name,coldMs:r.coldMs,...r.timing}))));
} finally {await browser.close();}
