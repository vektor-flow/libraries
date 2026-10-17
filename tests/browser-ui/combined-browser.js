import {bindSelectionInput} from '../../browser-ui/vf-selection-controller.mjs';
import {createRetainedPlotView} from '../../browser-ui/vf-retained-plot-view.mjs';
const checks=[];const check=(name,pass)=>{checks.push({name,pass:!!pass});if(!pass)throw Error(name)};
try{
for(const zoom of [1,1.5])for(const dpr of [1,2]){
const vertex=(x,y,color)=>[x,y,0,0,0,1,...color];let packed=[];
const red=[1,0,0,1],green=[0,1,0,1];
const curve={id:'curve',type:'field_mesh',topology:'line-strip',vertices:[...vertex(20,80,red),...vertex(100,80,red)],indices:[0,1],edge_width:3,analytic_curve:{version:1,branches:[{id:'arch',controls:[[20,80,0],[60,0,0],[100,80,0]],color:red}]}};
const line={id:'line',type:'field_mesh',topology:'line-strip',vertices:[...vertex(130,30,green),...vertex(180,30,green)],indices:[0,1],edge_width:3,selectable:true};
const coordinates={worldToScreen:p=>[p[0]*zoom,p[1]*zoom],affineWorldToScreen:()=>[zoom,0,0,0,0,zoom,0,0]};
const view=createRetainedPlotView({coordinates,pixelRatio:dpr,renderer:{setPackedVertices:p=>packed=Array.from(p)}});
view.replace({frame:'frame',meshes:[curve]});view.render();const analytic=packed.slice();
view.replace({frame:'frame',meshes:[{...curve,analytic_curve:undefined}]});view.render();check('analytic differs from endpoint fallback',JSON.stringify(packed)!==JSON.stringify(analytic));
view.replace({frame:'frame',meshes:[curve,line]});view.render();const baseline=packed.slice();
check('analytic geometry retained with selectable neighbor',baseline.length>analytic.length);
check('analytic curve has no sampled hit fallback',view.hitTest([60*zoom,80*zoom])===null);
view.selectAt([150*zoom,30*zoom]);check('neighbor selectable',view.selection().join()==='line');view.render();check('selected outline added',packed.length>baseline.length);
view.clearSelection();view.render();check('clear restores exact geometry',JSON.stringify(packed)===JSON.stringify(baseline));
view.selectionController.setEnabled(false);view.render();check('disable preserves exact geometry',JSON.stringify(packed)===JSON.stringify(baseline));view.selectionController.setEnabled(true);
const canvas=document.querySelector('canvas');let changes=0;

const unbind=bindSelectionInput(canvas,view.selectionController,{onChange:()=>changes++,local:e=>[e.clientX,e.clientY]});
view.selectAt([150*zoom,30*zoom]);canvas.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape'}));view.render();check('Escape preserves exact geometry',view.selection().length===0&&JSON.stringify(packed)===JSON.stringify(baseline));
unbind();canvas.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape'}));check('unbind joined listeners',changes===1);
for(const capability of ['selectable','draggable']){let rejected=false;try{view.replace({frame:'changed',meshes:[{...curve,[capability]:true}]})}catch(e){rejected=/interaction/.test(String(e))}check('explicit analytic '+capability+' rejection',rejected);view.render();check('rejected replace preserves geometry',JSON.stringify(packed)===JSON.stringify(baseline));}
view.replace({frame:'next',meshes:[curve,line]});view.render();check('frame replacement preserves analytic geometry',JSON.stringify(packed)===JSON.stringify(baseline));
view.dispose();let rejected=false;try{view.selectAt([0,0])}catch{rejected=true}check('dispose closes controller',rejected&&view.selection().length===0);
}
document.querySelector('#result').textContent=JSON.stringify({pass:true,checks,scope:'real software browser combined retained geometry and selection lifecycle; packed geometry assertions, no native transport or analytic pixels claim'});
}catch(e){document.querySelector('#result').textContent=JSON.stringify({pass:false,checks,error:String(e),stack:e.stack})}
