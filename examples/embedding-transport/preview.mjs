import {createEmbeddingTransport,orderedMassCoupling,sampleEmbeddingTransport,sampleEmbeddingKinematics} from '../../browser-ui/vf-embedding-transport.mjs';
import {fixture} from './fixtures.mjs';
import {createBranchingCopies,sampleBranchingCopies} from '../../browser-ui/vf-branching-transport.mjs';
import {createVisualProperties,sampleVisualProperties,linearRgbToCss} from '../../browser-ui/vf-visual-properties.mjs';
const canvas=document.querySelector('#view'),ctx=canvas.getContext('2d');
const select=document.querySelector('#example'),slider=document.querySelector('#time'),play=document.querySelector('#play');
let model,plan,baseline,properties,playing=false,last=0,frame=0;
function load(){
  properties=null;
  if(select.value==='branch'){
    model={kind:'copies',title:'One → two',note:'The connected shape moves and opens into two full-size copies. Constructed visual duplication, not a proven minimum-cost branching solution.'};
    plan=createBranchingCopies({source:[0,-.9],targets:[{id:'left',position:[-.8,.75]},{id:'right',position:[.8,.75]}],radius:.24});baseline=null;
    document.querySelector('#note').textContent=model.note;draw();return;
  }
  model=fixture(select.value);
  const coupling=model.coupling??orderedMassCoupling(model.source,model.target);
  plan=createEmbeddingTransport(model.source,model.target,coupling,{motion:'affine-2d'});
  baseline=createEmbeddingTransport(model.source,model.target,coupling,{motion:'linear'});
  if(model.kind==='material'){
    baseline=null;
    properties=createVisualProperties({mass:1,coverage:.2,opacity:.8,color:[1,1,1]},{mass:2,coverage:.6,opacity:1,color:[.45,.1,.9]});
  }
  document.querySelector('#note').textContent=model.note;draw();
}
function draw(){
  const rect=canvas.getBoundingClientRect(),dpr=devicePixelRatio||1;
  canvas.width=Math.round(rect.width*dpr);canvas.height=Math.round(rect.height*dpr);
  ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,rect.width,rect.height);
  const scale=Math.min(rect.width/4.2,rect.height/3.2);
  const point=p=>[rect.width/2+p[0]*scale,rect.height/2-p[1]*scale];
  const t=Number(slider.value)/1000;
  document.querySelector('#time-label').textContent=t.toFixed(3);
  const samples=model.kind==='copies'?sampleBranchingCopies(plan,t,4):sampleEmbeddingKinematics(plan,t,4);
  const attributes=properties?sampleVisualProperties(properties,t,4):null;
  document.querySelector('.gold').hidden=!baseline;
  document.querySelector('#speed').textContent=`${model.kind==='copies'?'moving split':plan.pose.fit.kind} · Peak speed: ${Math.max(...samples.map(p=>Math.hypot(...p.velocity))).toFixed(3)} units/s · 4 seconds`;
  if(attributes)document.querySelector('#speed').textContent+=` · mass ${attributes.mass.value.toFixed(3)} · area ${attributes.coverage.value.toFixed(3)}`;
  function paint(points,color,filled){
    ctx.strokeStyle=color;ctx.fillStyle=color;ctx.lineWidth=2;ctx.setLineDash(filled?[]:[5,5]);
    if(model.kind==='material'){
      ctx.fillStyle=linearRgbToCss(attributes.color.map(c=>c.value));ctx.globalAlpha=attributes.opacity.value;
      const [x,y]=point(points[0].position);ctx.beginPath();ctx.arc(x,y,Math.sqrt(attributes.coverage.value/Math.PI)*scale,0,2*Math.PI);ctx.fill();ctx.globalAlpha=1;
    }else if(model.kind==='copies'){
      // One union fill: coincident copies recover the source without opacity
      // jumps. Silhouette topology changes when the moving disks separate.
      ctx.beginPath();for(const p of points){const [x,y]=point(p.position);ctx.moveTo(x+p.radius*scale,y);ctx.arc(x,y,p.radius*scale,0,2*Math.PI);}
      ctx.fill();
    }else if(model.rings){
      let offset=0;ctx.beginPath();
      for(const count of model.rings){
        points.slice(offset,offset+count).forEach((p,i)=>{const [x,y]=point(p.position);if(!i)ctx.moveTo(x,y);else ctx.lineTo(x,y);});ctx.closePath();offset+=count;
      }
      if(filled){ctx.globalAlpha=.32;ctx.fill('evenodd');ctx.globalAlpha=1;}ctx.stroke();
    }else{
      // Add continuous density kernels before compositing. Aggregating coincident
      // disk radii only at exact endpoints would create a visible size jump.
      const buffer=document.createElement('canvas');buffer.width=Math.min(200,Math.ceil(rect.width));buffer.height=Math.round(buffer.width*rect.height/rect.width);
      const bctx=buffer.getContext('2d'),pixels=bctx.createImageData(buffer.width,buffer.height);
      const rgb=filled?[137,228,177]:[228,185,103],sigma=.14;
      for(let y=0;y<buffer.height;y++)for(let x=0;x<buffer.width;x++){
        const X=((x+.5)*rect.width/buffer.width-rect.width/2)/scale,Y=(rect.height/2-(y+.5)*rect.height/buffer.height)/scale;
        const density=points.reduce((sum,p)=>sum+p.weight*Math.exp(-((X-p.position[0])**2+(Y-p.position[1])**2)/(2*sigma*sigma)),0);
        const index=4*(y*buffer.width+x);pixels.data.set(rgb,index);pixels.data[index+3]=255*(1-Math.exp(-8*density));
      }
      bctx.putImageData(pixels,0,0);ctx.drawImage(buffer,0,0,rect.width,rect.height);
    }
  }
  if(baseline)paint(sampleEmbeddingTransport(baseline,t),'#e4b967',false);
  paint(samples,'#89e4b1',true);
  if(document.querySelector('#vectors').checked){
    ctx.strokeStyle='#eaf6ee';ctx.lineWidth=1;ctx.setLineDash([]);
    samples.filter((_,i)=>i%Math.max(1,Math.floor(samples.length/16))===0).forEach(p=>{
      const a=point(p.position),b=point(p.position.map((x,k)=>x+.25*p.velocity[k]));
      ctx.beginPath();ctx.moveTo(...a);ctx.lineTo(...b);ctx.stroke();
      if(Math.hypot(...p.velocity)>1e-6){ctx.beginPath();ctx.arc(...b,2,0,2*Math.PI);ctx.fillStyle='#eaf6ee';ctx.fill();}
    });
  }
  canvas.setAttribute('aria-label',`${model.title}, progress ${Math.round(t*100)} percent`);
  // Read-only browser evidence: exact samples used by the displayed frame.
  globalThis.embeddingPreview=Object.freeze({example:select.value,t,samples,attributes,pose:plan.pose,kind:model.kind});
}
function stop(){playing=false;cancelAnimationFrame(frame);play.textContent='Play';}
function tick(now){
  if(!playing)return;
  slider.value=String(Math.min(1000,Number(slider.value)+(now-last)/4));last=now;draw();
  if(Number(slider.value)>=1000)stop();else frame=requestAnimationFrame(tick);
}
play.addEventListener('click',()=>{if(playing)return stop();if(Number(slider.value)>=1000)slider.value='0';playing=true;play.textContent='Pause';last=performance.now();frame=requestAnimationFrame(tick);});
slider.addEventListener('input',()=>{stop();draw();});select.addEventListener('change',()=>{stop();load();});
document.querySelector('#vectors').addEventListener('change',draw);
document.addEventListener('visibilitychange',()=>{if(document.hidden)stop();});
new ResizeObserver(draw).observe(canvas);load();
