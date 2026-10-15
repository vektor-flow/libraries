import {planTransition,transitionFrame} from './transitions.mjs';
import {typesetText} from './text-flow.mjs';
import {parseColor} from './colors.mjs';
import {typeset} from './typing-layout.mjs';
const $=id=>document.getElementById(id),input=$('expression'),canvas=$('math'),status=$('status');
const boot=performance.now();let revision=0,running=false,pending=null,ready=false;
window.mathGpuErrors=[];
const times=[];let cache=null;let animation=0,transitionPlan=null;let gpu,adapter,device,context,pipeline,bind,instances,uniform,data;
const examples={roots:'\\sqrt[3]{x}+\\sqrt{\\frac{a}{1+\\sqrt{b}}}+\\binom{n}{k}',notation:'\\boxed{\\operatorname*{argmax}_{x}f(x)}+a\\not\\subset B+x\\pmod{n}',equations:'\\begin{align}x&=y+1\\\\[3pt]z&=\\sqrt{x^2+y^2}\\end{align}',textstyles:'\\text{Regular \\textbf{bold} \\textit{italic} \\textsf{sans} \\texttt{mono} \\%}',basic:'x+\\alpha=\\beta',scripts:'x_i^2+a^{n+1}+e^{i\\pi}=0',fraction:'\\frac{x^2+\\alpha}{1+x_i}=\\frac{a}{b}',greek:'\\alpha+\\beta+\\gamma+\\omega+\\Gamma+\\Delta+\\Theta+\\Lambda+\\Xi+\\Pi+\\Sigma+\\Phi+\\Psi+\\Omega',operators:'\\sum_{x=0}^n x^2+\\prod_{k=1}^n k+\\oint_C f(x)\\,dx+\\oiint_S F\\cdot n\\,dS',matrix:'\\begin{pmatrix}a&b\\\\c&d\\end{pmatrix}\\begin{bmatrix}x\\\\y\\end{bmatrix}',cases:'f(x)=\\begin{cases}x^2&x>0\\\\-x&x\\leq0\\end{cases}',nested:'\\left\\langle\\frac{1}{\\left(1+x^{2^{n+1}}\\right)}\\right\\rangle',accents:'\\hat{x}+\\widehat{ABC}+\\tilde{x}+\\widetilde{abc}+\\vec{v}+\\dot{x}+\\ddot{x}+\\dddot{x}+\\check{x}',annotations:'\\overbrace{a+b+c}^{n}+\\underbrace{x+y}_{\\text{terms}}+\\overline{z}+\\underline{w}',arrows:'A\\xrightarrow[k]{n+1}B+\\overrightarrow{AB}+\\underleftarrow{xy}',units:'v=\\qty{9.81}{\\metre\\per\\second\\squared}+R=\\SI{1.2e3}{\\kilo\\ohm}+T=\\qty{20}{\\degreeCelsius}',alphabets:'\\mathcal{ABC}+\\mathscr{ABC}+\\mathfrak{Abc}+\\mathbb{RNCxyz012}+\\mathbf{Abc}+\\mathit{Abc}+\\mathsf{Abc}+\\mathtt{Abc}+\\boldsymbol{\\alpha}',lines:'x=1\\\\y=\\frac{a}{b}\\\\z=\\mathbb{R}',text:'This is regular Computer Modern text. Move the page-width slider to see natural word wrapping. Inline math such as $E=mc^2$ shares the same font family and baseline.\n\nDisplay math is separate:\n$$\\sum_{i=1}^n i=\\frac{n(n+1)}{2}$$\nThe same paragraph supports Swedish letters: å, ä, ö, Å, Ä and Ö.',colors:'E=\\textcolor{red}{m}\\textcolor{blue}{c^2}+\\textcolor{magenta}{\\frac{a}{b}}\\\\\\textcolor{cyan}{\\overbrace{x+y}^{n}}+\\textcolor{red}{\\hat{x}}+\\textcolor{blue}{\\mathbb{R}}',long:Array(90).fill('\\frac{x_i^2+\\alpha}{1+x}').join('+')};
function resize(){const rect=canvas.getBoundingClientRect(),dpr=Math.min(devicePixelRatio,2);const width=Math.max(1,Math.round(rect.width*dpr)),height=Math.max(1,Math.round(rect.height*dpr));if(canvas.width!==width)canvas.width=width;if(canvas.height!==height)canvas.height=height;}
function pack(box,appearance){
 const values=[],dpr=Math.min(devicePixelRatio,2),scale=appearance.fontSize/data.maps.display.em*dpr,cssScale=appearance.fontSize/data.maps.display.em;
 const maxWidth=(canvas.width-48*dpr)/scale;let extraY=0,offset=0,lastFlow=-1,lastLine=-1;
 for(const item of box.items){
  const line=item.flowLine??0;if(line!==lastLine){offset=0;lastFlow=-1;lastLine=line;}const lineBox=box.lines?.[line]??box;
  if(!box.document&&item.flowX!==lastFlow&&item.flowX+item.flowWidth-offset>maxWidth&&item.flowX>offset){offset=item.flowX;extraY+=lineBox.height+lineBox.depth+6;}
  lastFlow=item.flowX;
  const ox=24*dpr+(item.x-offset)*scale,oy=36*dpr+(box.height+item.y+extraY)*scale;
  const color=item.color??appearance.color,rgba=[...color.slice(0,3),(color[3]??1)*appearance.opacity];
  if(item.kind==='glyph'){
   const t=data.tiles[item.key];if(!t)throw Error('Missing prepared symbol');const p=t.plane,sy=item.sy??1,sx=item.sx??1;
   const lo=Math.max(p[1],item.crop?.[0]??p[1]),hi=Math.min(p[3],item.crop?.[1]??p[3]),left=Math.max(p[0],item.cropX?.[0]??p[0]),right=Math.min(p[2],item.cropX?.[1]??p[2]);
   const uv=[t.uv[0]+(left-p[0])/(p[2]-p[0])*(t.uv[2]-t.uv[0]),t.uv[1]+(lo-p[1])/(p[3]-p[1])*(t.uv[3]-t.uv[1]),t.uv[0]+(right-p[0])/(p[2]-p[0])*(t.uv[2]-t.uv[0]),t.uv[1]+(hi-p[1])/(p[3]-p[1])*(t.uv[3]-t.uv[1])];
   values.push(ox+left*sx*scale,oy+lo*sy*scale,(right-left)*sx*scale,(hi-lo)*sy*scale,...uv,...rgba,0,0,0,0);
  }else if(item.kind==='placeholder'){
   const w=item.width*scale,h=item.height*scale,edge=Math.max(1,dpr*.65);
   for(const [x,y,rw,rh] of [[0,0,w,edge],[0,h-edge,w,edge],[0,0,edge,h],[w-edge,0,edge,h]])values.push(ox+x-1,oy+y-1,rw+2,rh+2,0,0,0,0,...rgba.slice(0,3),rgba[3]*.45,1,rw,rh,0);
  }else values.push(ox-1,oy-1,item.width*scale+2,item.height*scale+2,0,0,0,0,...rgba,1,item.width*scale,item.height*scale,0);
 }
 const height=Math.min(2500,Math.max(matchMedia('(max-width:640px)').matches?200:260,72+(box.height+box.depth+extraY)*cssScale));
 if(Math.abs(canvas.getBoundingClientRect().height-height)>1){canvas.style.height=height+'px';canvas.height=Math.max(1,Math.round(height*dpr));}
 if(values.length>16*12000)throw Error('Draw limit exceeded');return new Float32Array(values);
}
async function update(){
 if(running||!ready)return;running=true;
 while(pending){const job=pending;pending=null;const start=performance.now();
  try{
   resize();const widthUnits=(canvas.getBoundingClientRect().width-48)/(job.appearance.fontSize/data.maps.display.em),key=JSON.stringify([job.source,job.mode,job.content,job.content==='text'?widthUnits:null]);
   const box=cache?.key===key?cache.box:job.content==='text'?typesetText(job.source,data.maps,{width:widthUnits}):typeset(job.source,data.maps,{mode:job.mode});cache={key,box};const layoutMs=performance.now()-start,packet=pack(box,job.appearance);
   drawPacket(packet);
   await device.queue.onSubmittedWorkDone();const total=performance.now()-job.start;
   if(job.revision!==revision)continue;
   times.push(total);if(times.length>120)times.shift();const sorted=[...times].sort((a,b)=>a-b);
   $('layout').textContent=layoutMs.toFixed(2)+' ms';$('latency').textContent=total.toFixed(2)+' ms';$('p95').textContent=sorted[Math.floor((sorted.length-1)*.95)].toFixed(2)+' / 10 ms';
   status.className='';status.textContent=`${box.atoms} atoms · ${packet.length/16} GPU instances · ${box.complete?'current expression':'current draft: '+box.diagnostics.join(' · ')}`;
   canvas.dataset.revision=String(job.revision);canvas.dataset.atoms=String(box.atoms);
   window.mathTyping={source:job.source,mode:job.mode,content:job.content,appearance:job.appearance,lines:box.lines?.length??1,revision:job.revision,layoutMs,queueMs:total,instances:packet.length/16,complete:box.complete,diagnostics:box.diagnostics,glyphKeys:box.items.filter(p=>p.kind==='glyph').map(p=>p.key),placeholders:box.items.filter(p=>p.kind==='placeholder').length};
   requestAnimationFrame(()=>{if(job.revision===revision)$('frame').textContent=(performance.now()-job.start).toFixed(2)+' ms';});
  }catch(error){if(job.revision===revision){const encoder=device.createCommandEncoder(),pass=encoder.beginRenderPass({colorAttachments:[{view:context.getCurrentTexture().createView(),clearValue:[1,1,1,1],loadOp:'clear',storeOp:'store'}]});pass.end();device.queue.submit([encoder.finish()]);canvas.dataset.revision=String(job.revision);status.className='error';status.textContent=error.message;window.mathTyping={source:job.source,error:error.message,revision:job.revision};}}
 }running=false;
}
function selectTab(name){for(const button of document.querySelectorAll('[data-tab]')){const active=button.dataset.tab===name;button.setAttribute('aria-selected',String(active));button.tabIndex=active?0:-1;$('panel-'+button.dataset.tab).hidden=!active;}}
for(const button of document.querySelectorAll('[data-tab]')){button.addEventListener('click',()=>selectTab(button.dataset.tab));button.addEventListener('keydown',event=>{const names=['equations','style','examples'],i=names.indexOf(button.dataset.tab);let next;if(event.key==='ArrowRight')next=(i+1)%3;else if(event.key==='ArrowLeft')next=(i+2)%3;else if(event.key==='Home')next=0;else if(event.key==='End')next=2;if(next!==undefined){event.preventDefault();selectTab(names[next]);$('tab-'+names[next]).focus();}});}
function drawPacket(packet){
 device.queue.writeBuffer(instances,0,packet);device.queue.writeBuffer(uniform,0,new Float32Array([canvas.width,canvas.height,0,0]));
 const encoder=device.createCommandEncoder(),pass=encoder.beginRenderPass({colorAttachments:[{view:context.getCurrentTexture().createView(),clearValue:[1,1,1,1],loadOp:'clear',storeOp:'store'}]});
 pass.setPipeline(pipeline);pass.setBindGroup(0,bind);pass.setVertexBuffer(0,instances);pass.draw(6,packet.length/16);pass.end();device.queue.submit([encoder.finish()]);
}
function stopTransition(){cancelAnimationFrame(animation);animation=0;transitionPlan=null;$('progress').value=0;$('progress-value').textContent='0%';if(window.mathTransition)window.mathTransition.running=false;}
function appearance(){return {fontSize:Number($('font-size').value),color:parseColor($('ink-color').value),opacity:Number($('opacity').value)/100,pageWidth:Number($('page-width').value)};}
function buildTransition(){
 resize();const look=appearance(),mode=document.querySelector('input[name=math-mode]:checked').value,content=document.querySelector('input[name=content-mode]:checked').value,width=(canvas.getBoundingClientRect().width-48)/(look.fontSize/data.maps.display.em);
 const layout=source=>content==='text'?typesetText(source,data.maps,{width}):typeset(source,data.maps,{mode});
 const a=layout(input.value),b=layout($('expression-b').value),from=pack(a,look),heightA=canvas.getBoundingClientRect().height,to=pack(b,look),heightB=canvas.getBoundingClientRect().height;
 canvas.style.height=Math.max(heightA,heightB)+'px';resize();
 transitionPlan=planTransition(from,to);window.mathTransition={from:input.value,to:$('expression-b').value,progress:0,running:false,matched:transitionPlan.matched,instances:transitionPlan.pairs.length,diagnostics:[...a.diagnostics,...b.diagnostics],frames:0};return transitionPlan;
}
function showTransition(progress){
 if(!ready)return;try{const plan=transitionPlan??buildTransition();drawPacket(transitionFrame(plan,progress));$('progress').value=Math.round(progress*1000);$('progress-value').textContent=Math.round(progress*100)+'%';window.mathTransition.progress=progress;window.mathTransition.frames++;status.className='';status.textContent=`${plan.matched} matching symbols · ${Math.round(progress*100)}% A → B`;}catch(error){status.className='error';status.textContent=error.message;}
}
async function transform(){
 if(!ready)return;cancelAnimationFrame(animation);const token=++revision;pending=null;
 // Let an earlier edit finish before claiming the canvas for animation.
 while(running)await new Promise(resolve=>requestAnimationFrame(resolve));
 if(token!==revision)return;
 transitionPlan=null;showTransition(0);if(!transitionPlan)return;
 const duration=matchMedia('(prefers-reduced-motion: reduce)').matches?0:Number($('duration').value),start=performance.now();window.mathTransition.running=duration>0;
 const tick=now=>{const p=duration?Math.min(1,(now-start)/duration):1;showTransition(p);if(p<1)animation=requestAnimationFrame(tick);else{animation=0;window.mathTransition.running=false;}};
 animation=requestAnimationFrame(tick);
}
$('transform').addEventListener('click',transform);
$('progress').addEventListener('input',async()=>{const p=Number($('progress').value)/1000;cancelAnimationFrame(animation);const token=++revision;pending=null;if(window.mathTransition)window.mathTransition.running=false;while(running)await new Promise(resolve=>requestAnimationFrame(resolve));if(token===revision)showTransition(p);});
$('duration').addEventListener('input',()=>{$('duration-value').textContent=(Number($('duration').value)/1000).toFixed(1)+' s';});
$('expression-b').addEventListener('input',enqueue);
$('transition-enabled').addEventListener('change',()=>{const enabled=$('transition-enabled').checked;$('target-editor').hidden=!enabled;$('transition-controls').hidden=!enabled;$('equations').classList.toggle('paired',enabled);enqueue();});
$('swap').addEventListener('click',()=>{[input.value,$('expression-b').value]=[$('expression-b').value,input.value];enqueue();});
for(const id of ['example-a','example-b']){
 for(const [key,source] of Object.entries(examples)){const option=document.createElement('option');option.value=key;option.textContent=document.querySelector(`[data-example="${key}"]`).textContent;$(id).append(option);}
 $(id).addEventListener('change',()=>{if(!$(id).value)return;$(id==='example-a'?'expression':'expression-b').value=examples[$(id).value];document.querySelector(`input[name=content-mode][value=${$(id).value==='text'?'text':'math'}]`).checked=true;enqueue();});
}
function enqueue(){stopTransition();const content=document.querySelector('input[name=content-mode]:checked').value;$('math-style').disabled=content==='text';$('expression-label').textContent=$('transition-enabled').checked?'Equation A':content==='text'?'Text with LaTeX math':'LaTeX expression';pending={content,appearance:appearance(),source:input.value,mode:document.querySelector('input[name=math-mode]:checked').value,start:performance.now(),revision:++revision};void update();}
input.addEventListener('input',enqueue);for(const control of document.querySelectorAll('input[name=math-mode],input[name=content-mode]'))control.addEventListener('change',enqueue);for(const b of document.querySelectorAll('[data-example]'))b.addEventListener('click',()=>{input.value=examples[b.dataset.example];document.querySelector(`input[name=content-mode][value=${b.dataset.example==='text'?'text':'math'}]`).checked=true;selectTab('equations');enqueue();input.focus();});
function appearanceChanged(){document.documentElement.style.setProperty('--page-width',$('page-width').value+'px');$('page-width-value').textContent=$('page-width').value+' px';$('font-size-value').textContent=$('font-size').value+' px';$('opacity-value').textContent=$('opacity').value+'%';for(const button of document.querySelectorAll('[data-color]'))button.setAttribute('aria-pressed',String(button.dataset.color===$('ink-color').value));enqueue();}
for(const id of ['page-width','font-size','opacity','ink-color'])$(id).addEventListener('input',appearanceChanged);
for(const button of document.querySelectorAll('[data-color]'))button.addEventListener('click',()=>{$('ink-color').value=button.dataset.color;appearanceChanged();});
let observedWidth=0;new ResizeObserver(entries=>{const width=entries[0].contentRect.width;if(Math.abs(width-observedWidth)>.5){observedWidth=width;if(ready){if(transitionPlan){const progress=window.mathTransition.progress;cancelAnimationFrame(animation);window.mathTransition.running=false;transitionPlan=null;showTransition(progress);}else enqueue();}}}).observe(canvas);
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
 $('backend').textContent+=` · initial preparation ${(performance.now()-boot).toFixed(0)} ms`;ready=true;$('transform').disabled=false;enqueue();
 device.lost.then(()=>{ready=false;status.className='error';status.textContent='WebGPU device lost. Reload to restart.';});
}catch(error){status.className='error';status.textContent=error.message;}
