import {typeset} from './typing-layout.mjs';
const $=id=>document.getElementById(id),input=$('expression'),canvas=$('math'),status=$('status');
const boot=performance.now();let revision=0,running=false,pending=null,ready=false;
window.mathGpuErrors=[];
const times=[];let gpu,adapter,device,context,pipeline,bind,instances,uniform,data;
const examples={basic:'x+\\alpha=\\beta',scripts:'x_i^2+a^{n+1}+e^{i\\pi}=0',fraction:'\\frac{x^2+\\alpha}{1+x_i}=\\frac{a}{b}',long:Array(90).fill('\\frac{x_i^2+\\alpha}{1+x}').join('+')};
function resize(){const rect=canvas.getBoundingClientRect(),dpr=Math.min(devicePixelRatio,2);const width=Math.max(1,Math.round(rect.width*dpr)),height=Math.max(1,Math.round(rect.height*dpr));if(canvas.width!==width)canvas.width=width;if(canvas.height!==height)canvas.height=height;}
function pack(box){
 const values=[],dpr=canvas.width/canvas.getBoundingClientRect().width,scale=3*dpr;
 const maxWidth=(canvas.width-48*dpr)/scale;let row=0,offset=0,lastFlow=-1;
 for(const item of box.items){
  if(item.flowX!==lastFlow && item.flowX+item.flowWidth-offset>maxWidth && item.flowX>offset){offset=item.flowX;row++;}
  lastFlow=item.flowX;
  const ox=24*dpr+(item.x-offset)*scale,oy=36*dpr+(box.height+item.y+row*(box.height+box.depth+6))*scale;
  if(item.kind==='glyph'){
   const t=data.tiles[item.key];if(!t)throw Error('Missing prepared symbol');const p=t.plane;
   values.push(ox+p[0]*scale,oy+p[1]*scale,(p[2]-p[0])*scale,(p[3]-p[1])*scale,...t.uv,.08,.19,.15,1,0,0,0,0);
  }else values.push(ox-1,oy-1,item.width*scale+2,item.height*scale+2,0,0,0,0,.08,.19,.15,1,1,item.width*scale,item.height*scale,0);
 }
 const height=Math.min(2500,Math.max(330,72+(box.height+box.depth+row*(box.height+box.depth+6))*3));
 if(Math.abs(canvas.getBoundingClientRect().height-height)>1){canvas.style.height=height+'px';canvas.height=Math.round(height*dpr);}
 if(values.length>16*12000)throw Error('Draw limit exceeded');return new Float32Array(values);
}
async function update(){
 if(running||!ready)return;running=true;
 while(pending){const job=pending;pending=null;const start=performance.now();
  try{
   const box=typeset(job.source,data.maps),layoutMs=performance.now()-start;resize();const packet=pack(box);
   device.queue.writeBuffer(instances,0,packet);device.queue.writeBuffer(uniform,0,new Float32Array([canvas.width,canvas.height,0,0]));
   const encoder=device.createCommandEncoder(),pass=encoder.beginRenderPass({colorAttachments:[{view:context.getCurrentTexture().createView(),clearValue:[1,1,1,1],loadOp:'clear',storeOp:'store'}]});
   pass.setPipeline(pipeline);pass.setBindGroup(0,bind);pass.setVertexBuffer(0,instances);pass.draw(6,packet.length/16);pass.end();device.queue.submit([encoder.finish()]);
   await device.queue.onSubmittedWorkDone();const total=performance.now()-job.start;
   if(job.revision!==revision)continue;
   times.push(total);if(times.length>120)times.shift();const sorted=[...times].sort((a,b)=>a-b);
   $('layout').textContent=layoutMs.toFixed(2)+' ms';$('latency').textContent=total.toFixed(2)+' ms';$('p95').textContent=sorted[Math.floor((sorted.length-1)*.95)].toFixed(2)+' / 10 ms';
   status.className='';status.textContent=`${box.atoms} atoms · ${packet.length/16} GPU instances · last valid expression shown`;
   canvas.dataset.revision=String(job.revision);canvas.dataset.atoms=String(box.atoms);
   window.mathTyping={source:job.source,revision:job.revision,layoutMs,queueMs:total,instances:packet.length/16};
   requestAnimationFrame(()=>{if(job.revision===revision)$('frame').textContent=(performance.now()-job.start).toFixed(2)+' ms';});
  }catch(error){if(job.revision===revision){status.className='error';status.textContent=error.message;window.mathTyping={error:error.message,revision:job.revision};}}
 }running=false;
}
function enqueue(){pending={source:input.value,start:performance.now(),revision:++revision};void update();}
input.addEventListener('input',enqueue);for(const b of document.querySelectorAll('[data-example]'))b.addEventListener('click',()=>{input.value=examples[b.dataset.example];enqueue();input.focus();});
let observedWidth=0;new ResizeObserver(entries=>{const width=entries[0].contentRect.width;if(Math.abs(width-observedWidth)>.5){observedWidth=width;if(ready)enqueue();}}).observe(canvas);
try{
 gpu=navigator.gpu;
 if(!gpu)throw Error('WebGPU is unavailable. Open this test in a browser with WebGPU enabled.');
 adapter=await gpu.requestAdapter({forceFallbackAdapter:new URLSearchParams(location.search).has('software')});if(!adapter)throw Error('No WebGPU adapter available');
 device=await adapter.requestDevice();const info=adapter.info;
 $('backend').textContent=`WebGPU · ${info.description||info.architecture||info.vendor||'adapter identity not provided'} · ${info.isFallbackAdapter?'software fallback':'device adapter'}`;
 device.addEventListener('uncapturederror',e=>{window.mathGpuErrors.push(e.error.message);ready=false;status.className='error';status.textContent=e.error.message;});
 const [mapping,blob,shader]=await Promise.all([fetch('./typing-data.json').then(r=>r.json()),fetch('./atlas.rgba.gz').then(async r=>{const bytes=await r.arrayBuffer(),head=new Uint8Array(bytes);return head[0]===31&&head[1]===139?new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer():bytes;}),fetch('./draw.wgsl').then(r=>r.text())]);data=mapping;
 const atlas=device.createTexture({size:[2048,2048],format:'rgba8unorm',usage:GPUTextureUsage.TEXTURE_BINDING|GPUTextureUsage.COPY_DST});
 device.queue.writeTexture({texture:atlas},blob,{bytesPerRow:8192},[2048,2048]);
 const module=device.createShaderModule({code:shader}),messages=await module.getCompilationInfo();if(messages.messages.some(m=>m.type==='error'))throw Error(messages.messages.map(m=>m.message).join('\n'));
 const format=gpu.getPreferredCanvasFormat();context=canvas.getContext('webgpu');context.configure({device,format,alphaMode:'opaque'});
 pipeline=await device.createRenderPipelineAsync({layout:'auto',vertex:{module,entryPoint:'vs',buffers:[{arrayStride:64,stepMode:'instance',attributes:[0,1,2,3].map(i=>({shaderLocation:i,offset:i*16,format:'float32x4'}))}]},fragment:{module,entryPoint:'fs',targets:[{format,blend:{color:{srcFactor:'one',dstFactor:'one-minus-src-alpha'},alpha:{srcFactor:'one',dstFactor:'one-minus-src-alpha'}}}]},primitive:{topology:'triangle-list'}});
 uniform=device.createBuffer({size:16,usage:GPUBufferUsage.UNIFORM|GPUBufferUsage.COPY_DST});instances=device.createBuffer({size:12000*64,usage:GPUBufferUsage.VERTEX|GPUBufferUsage.COPY_DST});
 bind=device.createBindGroup({layout:pipeline.getBindGroupLayout(0),entries:[{binding:0,resource:{buffer:uniform}},{binding:1,resource:atlas.createView()},{binding:2,resource:device.createSampler({minFilter:'linear',magFilter:'linear'})}]});
 $('backend').textContent+=` · initial preparation ${(performance.now()-boot).toFixed(0)} ms`;ready=true;enqueue();
 device.lost.then(()=>{ready=false;status.className='error';status.textContent='WebGPU device lost. Reload to restart.';});
}catch(error){status.className='error';status.textContent=error.message;}
