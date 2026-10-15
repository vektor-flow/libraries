import {MorphEngine} from './engine.mjs';
import {packScenes} from './endpoints.mjs';
import {typeset} from '../gpu-math-typing/typing-layout.mjs';
const $=id=>document.getElementById(id),status=$('status'),canvas=$('scene');
let engine,data,playing=false,busy=false,measuring=false,frame=0,lastTime=0,request=0,phase=0,startTime=0,editTimer,applying=false,applyPending=false;
let gpuTimes=[],wallTimes=[],cadences=[],pendingPhase=null;
const stats={bootMs:0,layoutMs:0,frames:0,fullSolvePerFrame:true,software:false,errors:[],sweep:[]};window.gpuMorph={stats,get engine(){return engine},get phase(){return phase},apply,render:renderPhase};
const percentile=(a,p)=>a.length?[...a].sort((a,b)=>a-b)[Math.max(0,Math.ceil(a.length*p)-1)]:null;
const ms=x=>x===null||x===undefined?'unavailable':x.toFixed(2)+' ms';
function error(e){stats.errors.push(String(e.message??e));status.textContent=e.message??String(e);status.className='error';stop();}
function resize(){const r=canvas.getBoundingClientRect(),dpr=Math.min(devicePixelRatio,2);canvas.width=Math.max(1,Math.round(r.width*dpr));canvas.height=Math.max(1,Math.round(r.height*dpr));}
function stop(){playing=false;cancelAnimationFrame(request);$('play').textContent='Play';lastTime=0;}
function metrics(sample){
 if(!sample)return;if(sample.gpuMs!==null){gpuTimes.push(sample.gpuMs);if(gpuTimes.length>120)gpuTimes.shift();}
 wallTimes.push(sample.wallMs);if(wallTimes.length>120)wallTimes.shift();stats.wallP95=percentile(wallTimes,.95);$('frame-wall').textContent=ms(stats.wallP95);stats.frames++;stats.lastFrame=sample;stats.gpuP95=percentile(gpuTimes,.95);stats.gpuMedian=percentile(gpuTimes,.5);
 $('frame-gpu').textContent=engine.software?'software test':ms(stats.gpuP95);
 $('budget').textContent=engine.software?'not hardware':stats.wallP95===null?'unavailable':(stats.wallP95/10).toFixed(2)+'×';
 if(cadences.length)$('fps').textContent=(1000/(cadences.reduce((a,b)=>a+b)/cadences.length)).toFixed(1)+' fps';
}
async function renderPhase(value,{measure=true}={}){
 if(!engine?.ready||busy){pendingPhase=value;return null;}
 busy=true;phase=Math.max(0,Math.min(1,value));$('phase').value=Math.round(phase*1000);$('progress').textContent=Math.round(phase*100)+'%';
 try{const sample=await engine.draw(phase,{measure});metrics(sample);return sample;}catch(e){error(e);return null;}finally{busy=false;}
}
async function tick(now){
 if(!playing||document.hidden)return;
 if(lastTime){cadences.push(now-lastTime);if(cadences.length>120)cadences.shift();}lastTime=now;
 const t=(now-startTime)/3000;await renderPhase((1-Math.cos(t*Math.PI))*.5,{measure:frame++%4===0});
 if(playing)request=requestAnimationFrame(tick);
}
function play(){if(!engine?.ready||measuring||applying)return;playing=true;startTime=performance.now()-Math.acos(1-2*phase)/Math.PI*3000;lastTime=0;$('play').textContent='Pause';request=requestAnimationFrame(tick);}
async function apply({resume=false}={}){
 if(!engine||measuring)return;if(applying){applyPending=true;return;}applying=true;const wasPlaying=playing||resume;stop();$('generate').disabled=true;$('sweep').disabled=true;
 try{
  await engine.device.queue.onSubmittedWorkDone();while(busy)await new Promise(r=>setTimeout(r,1));resize();
  const start=performance.now(),a=typeset($('source').value,data.maps),b=typeset($('target').value,data.maps),packet=packScenes(a,b,data,Number($('size').value));stats.layoutMs=performance.now()-start;
  const preparation=await engine.generate(packet.a,packet.b,{iterations:Number($('iterations').value)});stats.preparation=preparation;stats.count=packet.count;stats.endpointBytes=packet.a.byteLength+packet.b.byteLength;gpuTimes=[];wallTimes=[];cadences=[];
  $('prepare-wall').textContent=ms(preparation.wallMs+stats.layoutMs);$('phase').disabled=false;$('play').disabled=false;
  status.className='';status.textContent=`${packet.count} bodies · solving every frame · endpoint layout ${stats.layoutMs.toFixed(1)} ms`;
  await renderPhase(0);applying=false;if(wasPlaying)play();
 }catch(e){error(e);}finally{applying=false;$('generate').disabled=false;$('sweep').disabled=false;if(applyPending){applyPending=false;void apply({resume:wasPlaying});}}
}
async function sweep(){
 if(measuring||applying||!engine?.ready)return;clearTimeout(editTimer);stop();measuring=true;for(const id of ['source','target','size','iterations','play','phase'])$(id).disabled=true;$('sweep').disabled=true;$('generate').disabled=true;document.querySelector('main').classList.add('measuring');$('results').hidden=false;$('results').textContent='Bodies   GPU median/p95   Wall p95   ≤10ms\n';stats.sweep=[];
 try{
  while(busy)await new Promise(r=>setTimeout(r,1));resize();const a=typeset($('source').value,data.maps),b=typeset($('target').value,data.maps);
  for(const size of [64,128,256,512,1024]){
   const packet=packScenes(a,b,data,size);await engine.generate(packet.a,packet.b,{iterations:Number($('iterations').value)});const samples=[];
   for(let k=0;k<20;k++){
    status.textContent=`Measuring ${packet.count} bodies · ${k+1}/20 frames`;const sample=await engine.draw((k+.5)/20,{measure:true});if(k>=4)samples.push(sample);await new Promise(requestAnimationFrame);
   }
   const gpu=samples.map(x=>x.gpuMs).filter(x=>x!==null),wall=samples.map(x=>x.wallMs);const row={bodies:packet.count,gpuMedianMs:percentile(gpu,.5),gpuP95Ms:percentile(gpu,.95),wallP95Ms:percentile(wall,.95),samples:16,iterations:engine.iterations,grid:engine.grid,resolution:[canvas.width,canvas.height],software:engine.software};stats.sweep.push(row);
   $('results').textContent+=`${row.bodies}    ${engine.software?'software validation':ms(row.gpuMedianMs)+' / '+ms(row.gpuP95Ms)}    ${ms(row.wallP95Ms)}    ${engine.software?'—':row.wallP95Ms<=10?'yes':'NO'}\n`;
  }
  status.textContent=engine.software?'Validation only; software results are not GPU performance.':'Sweep complete. GPU includes fresh matching, flow solving and rendering for every frame.';
 }catch(e){error(e);}finally{measuring=false;for(const id of ['source','target','size','iterations','play','phase'])$(id).disabled=false;$('sweep').disabled=false;$('generate').disabled=false;document.querySelector('main').classList.remove('measuring');}
}
$('generate').onclick=()=>apply();$('play').onclick=()=>playing?stop():play();$('sweep').onclick=sweep;
$('phase').oninput=async()=>{if(measuring||applying)return;stop();pendingPhase=Number($('phase').value)/1000;if(busy)return;while(pendingPhase!==null){const p=pendingPhase;pendingPhase=null;await renderPhase(p);}};
for(const id of ['source','target','size','iterations'])$(id).addEventListener(id==='source'||id==='target'?'input':'change',()=>{clearTimeout(editTimer);editTimer=setTimeout(()=>apply(),350);});
document.addEventListener('visibilitychange',()=>{if(document.hidden)stop();});
new ResizeObserver(()=>{resize();if(engine?.ready&&!playing&&!busy&&!measuring)void renderPhase(phase);}).observe(canvas);
try{
 const boot=performance.now();const [mapping,blob,shader]=await Promise.all([fetch('../gpu-math-typing/typing-data.json').then(r=>r.json()),fetch('../gpu-math-typing/atlas.rgba.gz').then(async r=>new Response(r.body.pipeThrough(new DecompressionStream('gzip'))).arrayBuffer()),fetch('./morph.wgsl').then(r=>r.text())]);data=mapping;resize();
 engine=await MorphEngine.create(canvas,data,blob,shader,{validation:new URLSearchParams(location.search).has('validation')});stats.software=engine.software;stats.adapter={...Object.fromEntries(['vendor','architecture','description','isFallbackAdapter'].map(k=>[k,engine.info[k]]))};engine.onError=error;stats.bootMs=performance.now()-boot;
 $('backend').textContent=engine.software?'SOFTWARE VALIDATION — not GPU performance':`WebGPU · ${engine.info.description||engine.info.architecture||engine.info.vendor||'device'} · ${engine.timestamps?'GPU timers':'GPU timers unavailable'}`;
 $('generate').disabled=false;await apply({resume:!matchMedia('(prefers-reduced-motion: reduce)').matches});
}catch(e){error(e);}
