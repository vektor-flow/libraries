import {typeset} from './typing-layout.mjs';
const $=id=>document.getElementById(id),input=$('expression'),canvas=$('math'),status=$('status');
const boot=performance.now();let revision=0,running=false,pending=null,ready=false;
window.mathGpuErrors=[];
const times=[];let gpu,adapter,device,context,pipeline,bind,instances,uniform,data;
const examples={basic:'x+\\alpha=\\beta',scripts:'x_i^2+a^{n+1}+e^{i\\pi}=0',fraction:'\\frac{x^2+\\alpha}{1+x_i}=\\frac{a}{b}',greek:'\\alpha+\\beta+\\gamma+\\omega+\\Gamma+\\Delta+\\Theta+\\Lambda+\\Xi+\\Pi+\\Sigma+\\Phi+\\Psi+\\Omega',operators:'\\sum_{x=0}^n x^2+\\prod_{k=1}^n k+\\oint_C f(x)\\,dx+\\oiint_S F\\cdot n\\,dS',matrix:'\\begin{pmatrix}a&b\\\\c&d\\end{pmatrix}\\begin{bmatrix}x\\\\y\\end{bmatrix}',cases:'f(x)=\\begin{cases}x^2&x>0\\\\-x&x\\leq0\\end{cases}',nested:'\\left\\langle\\frac{1}{\\left(1+x^{2^{n+1}}\\right)}\\right\\rangle',long:Array(90).fill('\\frac{x_i^2+\\alpha}{1+x}').join('+')};
function resize(){const rect=canvas.getBoundingClientRect(),dpr=Math.min(devicePixelRatio,2);const width=Math.max(1,Math.round(rect.width*dpr)),height=Math.max(1,Math.round(rect.height*dpr));if(canvas.width!==width)canvas.width=width;if(canvas.height!==height)canvas.height=height;}
function pack(box){
 const values=[],dpr=canvas.width/canvas.getBoundingClientRect().width,scale=3*dpr;
 const maxWidth=(canvas.width-48*dpr)/scale;let row=0,offset=0,lastFlow=-1;
 for(const item of box.items){
  if(item.flowX!==lastFlow && item.flowX+item.flowWidth-offset>maxWidth && item.flowX>offset){offset=item.flowX;row++;}
  lastFlow=item.flowX;
  const ox=24*dpr+(item.x-offset)*scale,oy=36*dpr+(box.height+item.y+row*(box.height+box.depth+6))*scale;
  if(item.kind==='glyph'){
   const t=data.tiles[item.key];if(!t)throw Error('Missing prepared symbol');const p=t.plane,sy=item.sy??1;
   const lo=Math.max(p[1],item.crop?.[0]??p[1]),hi=Math.min(p[3],item.crop?.[1]??p[3]);
   const v0=t.uv[1]+(lo-p[1])/(p[3]-p[1])*(t.uv[3]-t.uv[1]),v1=t.uv[1]+(hi-p[1])/(p[3]-p[1])*(t.uv[3]-t.uv[1]);
   values.push(ox+p[0]*scale,oy+lo*sy*scale,(p[2]-p[0])*scale,(hi-lo)*sy*scale,t.uv[0],v0,t.uv[2],v1,.08,.19,.15,1,0,0,0,0);
  }else if(item.kind==='placeholder'){
   const w=item.width*scale,h=item.height*scale,edge=Math.max(1,dpr*.65);
   for(const [x,y,rw,rh] of [[0,0,w,edge],[0,h-edge,w,edge],[0,0,edge,h],[w-edge,0,edge,h]])values.push(ox+x-1,oy+y-1,rw+2,rh+2,0,0,0,0,.35,.48,.42,.45,1,rw,rh,0);
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
   const box=typeset(job.source,data.maps,{mode:job.mode}),layoutMs=performance.now()-start;resize();const packet=pack(box);
   device.queue.writeBuffer(instances,0,packet);device.queue.writeBuffer(uniform,0,new Float32Array([canvas.width,canvas.height,0,0]));
   const encoder=device.createCommandEncoder(),pass=encoder.beginRenderPass({colorAttachments:[{view:context.getCurrentTexture().createView(),clearValue:[1,1,1,1],loadOp:'clear',storeOp:'store'}]});
   pass.setPipeline(pipeline);pass.setBindGroup(0,bind);pass.setVertexBuffer(0,instances);pass.draw(6,packet.length/16);pass.end();device.queue.submit([encoder.finish()]);
   await device.queue.onSubmittedWorkDone();const total=performance.now()-job.start;
   if(job.revision!==revision)continue;
   times.push(total);if(times.length>120)times.shift();const sorted=[...times].sort((a,b)=>a-b);
   $('layout').textContent=layoutMs.toFixed(2)+' ms';$('latency').textContent=total.toFixed(2)+' ms';$('p95').textContent=sorted[Math.floor((sorted.length-1)*.95)].toFixed(2)+' / 10 ms';
   status.className='';status.textContent=`${box.atoms} atoms · ${packet.length/16} GPU instances · ${box.complete?'current expression':'current draft: '+box.diagnostics.join(' · ')}`;
   canvas.dataset.revision=String(job.revision);canvas.dataset.atoms=String(box.atoms);
   window.mathTyping={source:job.source,mode:job.mode,revision:job.revision,layoutMs,queueMs:total,instances:packet.length/16,complete:box.complete,diagnostics:box.diagnostics,glyphKeys:box.items.filter(p=>p.kind==='glyph').map(p=>p.key),placeholders:box.items.filter(p=>p.kind==='placeholder').length};
   requestAnimationFrame(()=>{if(job.revision===revision)$('frame').textContent=(performance.now()-job.start).toFixed(2)+' ms';});
  }catch(error){if(job.revision===revision){const encoder=device.createCommandEncoder(),pass=encoder.beginRenderPass({colorAttachments:[{view:context.getCurrentTexture().createView(),clearValue:[1,1,1,1],loadOp:'clear',storeOp:'store'}]});pass.end();device.queue.submit([encoder.finish()]);canvas.dataset.revision=String(job.revision);status.className='error';status.textContent=error.message;window.mathTyping={source:job.source,error:error.message,revision:job.revision};}}
 }running=false;
}
function enqueue(){pending={source:input.value,mode:document.querySelector('input[name=math-mode]:checked').value,start:performance.now(),revision:++revision};void update();}
input.addEventListener('input',enqueue);for(const control of document.querySelectorAll('input[name=math-mode]'))control.addEventListener('change',enqueue);for(const b of document.querySelectorAll('[data-example]'))b.addEventListener('click',()=>{input.value=examples[b.dataset.example];enqueue();input.focus();});
let observedWidth=0;new ResizeObserver(entries=>{const width=entries[0].contentRect.width;if(Math.abs(width-observedWidth)>.5){observedWidth=width;if(ready)enqueue();}}).observe(canvas);
try{
 gpu=navigator.gpu;
 if(!gpu)throw Error('WebGPU is unavailable. Open this test in a browser with WebGPU enabled.');
 adapter=await gpu.requestAdapter({forceFallbackAdapter:new URLSearchParams(location.search).has('software')});if(!adapter)throw Error('No WebGPU adapter available');
 device=await adapter.requestDevice();const info=adapter.info;
 $('backend').textContent=`WebGPU · ${info.description||info.architecture||info.vendor||'adapter identity not provided'} · ${info.isFallbackAdapter?'software fallback':'device adapter'}`;
 device.addEventListener('uncapturederror',e=>{window.mathGpuErrors.push(e.error.message);ready=false;status.className='error';status.textContent=e.error.message;});
 const [mapping,blob,shader]=await Promise.all([fetch('./typing-data.json').then(r=>r.json()),fetch('./atlas.rgba.gz').then(async r=>{const bytes=await r.arrayBuffer(),head=new Uint8Array(bytes);return head[0]===31&&head[1]===139?new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer():bytes;}),fetch('./draw.wgsl').then(r=>r.text())]);data=mapping;
 const [atlasWidth,atlasHeight]=data.atlasSize;if(blob.byteLength!==atlasWidth*atlasHeight*4)throw Error('Atlas byte length mismatch');
 const atlas=device.createTexture({size:[atlasWidth,atlasHeight],format:'rgba8unorm',usage:GPUTextureUsage.TEXTURE_BINDING|GPUTextureUsage.COPY_DST});
 device.queue.writeTexture({texture:atlas},blob,{bytesPerRow:atlasWidth*4},[atlasWidth,atlasHeight]);
 const module=device.createShaderModule({code:shader}),messages=await module.getCompilationInfo();if(messages.messages.some(m=>m.type==='error'))throw Error(messages.messages.map(m=>m.message).join('\n'));
 const format=gpu.getPreferredCanvasFormat();context=canvas.getContext('webgpu');context.configure({device,format,alphaMode:'opaque'});
 pipeline=await device.createRenderPipelineAsync({layout:'auto',vertex:{module,entryPoint:'vs',buffers:[{arrayStride:64,stepMode:'instance',attributes:[0,1,2,3].map(i=>({shaderLocation:i,offset:i*16,format:'float32x4'}))}]},fragment:{module,entryPoint:'fs',targets:[{format,blend:{color:{srcFactor:'one',dstFactor:'one-minus-src-alpha'},alpha:{srcFactor:'one',dstFactor:'one-minus-src-alpha'}}}]},primitive:{topology:'triangle-list'}});
 uniform=device.createBuffer({size:16,usage:GPUBufferUsage.UNIFORM|GPUBufferUsage.COPY_DST});instances=device.createBuffer({size:12000*64,usage:GPUBufferUsage.VERTEX|GPUBufferUsage.COPY_DST});
 bind=device.createBindGroup({layout:pipeline.getBindGroupLayout(0),entries:[{binding:0,resource:{buffer:uniform}},{binding:1,resource:atlas.createView()},{binding:2,resource:device.createSampler({minFilter:'linear',magFilter:'linear'})}]});
 $('backend').textContent+=` · initial preparation ${(performance.now()-boot).toFixed(0)} ms`;ready=true;enqueue();
 device.lost.then(()=>{ready=false;status.className='error';status.textContent='WebGPU device lost. Reload to restart.';});
}catch(error){status.className='error';status.textContent=error.message;}
