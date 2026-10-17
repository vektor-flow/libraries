import assert from 'node:assert/strict';
import {curveContract,projectCurves,contractFromTikzPacket,drawCurves} from '../../browser-ui/vf-analytic-curves.mjs';
import {createRetainedPlotView} from '../../browser-ui/vf-retained-plot-view.mjs';
import {createRetainedGeometryScene} from '../../browser-ui/vf-retained-geometry-scene.mjs';
import {compileTikzPicture} from '../../examples/gpu-math/tikz-layout.mjs';
import {vectorPacket} from '../../examples/gpu-math/vector-packets.mjs';
const item=compileTikzPicture(String.raw`\draw (0,0) to[out=45,in=180] (2,1);`).items[0];
const packet=vectorPacket(item,item.color),tikz=contractFromTikzPacket(packet);
const quadratic=curveContract({version:1,branches:[{id:'q',controls:[[0,0,0],[1,2,0],[2,0,0]],color:[1,0,0,1]}]});
const observations=[];
const vertex=p=>[...p,0,0,1,1,0,0,1];
function evaluate(c,t){while(c.length>1)c=c.slice(1).map((p,i)=>p.map((v,j)=>c[i][j]*(1-t)+v*t));return c[0];}
function dist(p,a,b){const d=[b[0]-a[0],b[1]-a[1]],l=d[0]**2+d[1]**2,t=l?Math.max(0,Math.min(1,((p[0]-a[0])*d[0]+(p[1]-a[1])*d[1])/l)):0;return Math.hypot(p[0]-a[0]-t*d[0],p[1]-a[1]-t*d[1]);}
for(const zoom of [.001,1,100,10000])for(const dpr of [1,1.5,3])for(const curve of [quadratic,tikz]){
 const matrix=[zoom,0,0,0,0,-zoom,0,0],projection={matrix,pixelRatio:dpr};
 const paths=projectCurves(curve,projection),b=curve.branches[0],points=paths[0].points;
 const tr=p=>[p[0]*zoom*dpr||0,-p[1]*zoom*dpr||0];
 assert.deepEqual(points[0],tr(b.controls[0]));assert.deepEqual(points.at(-1),tr(b.controls.at(-1)));
 let error=0;for(let i=0;i<=200;i++){const p=tr(evaluate(b.controls,i/200));error=Math.max(error,Math.min(...points.slice(1).map((v,j)=>dist(p,points[j],v))));}assert(error<=.25000001);
 let actual;const coordinates={worldToScreen:p=>[p[0]*zoom,-p[1]*zoom],affineWorldToScreen:()=>matrix};
 const view=createRetainedPlotView({coordinates,pixelRatio:dpr,renderer:{setPackedVertices:p=>actual=Array.from(p)}});
 const mesh={id:'mesh',type:'field_mesh',topology:'line-strip',vertices:[...vertex(b.controls[0]),...vertex(b.controls.at(-1))],indices:[0,1],edge_width:2,analytic_curve:curve};
 view.replace({frame:'f',meshes:[mesh]});view.render();assert(actual.length>0);
 let expected;const scene=createRetainedGeometryScene();scene.beginFrame();drawCurves(scene,'f','mesh',curve,projection,2*dpr);scene.commit({setPackedVertices:p=>expected=Array.from(p)});assert.deepEqual(actual,expected);
 // Fixed sample fallback and selection methods remain executable and unchanged.
 view.replace({frame:'f',meshes:[{...mesh,analytic_curve:undefined}]});view.render();assert(actual.length>0);
 assert.throws(()=>view.replace({frame:'f',meshes:[{...mesh,selectable:true}]}),/interaction/);
 observations.push({zoom,dpr,curve:b.id,segments:points.length-1,maxSampleError:error});view.dispose();
}
const clipped=curveContract({version:1,branches:[{...quadratic.branches[0],id:'left',domain:[0,.25]},{...quadratic.branches[0],id:'right',domain:[.75,1]}]});
const paths=projectCurves(clipped,{matrix:[1,0,0,0,0,1,0,0]});assert.equal(paths.length,2);assert.deepEqual(paths[0].points.at(-1),evaluate(quadratic.branches[0].controls,.25).slice(0,2));assert(paths[0].points.at(-1)[0]<paths[1].points[0][0]);
const connected=curveContract({version:1,branches:[{...quadratic.branches[0],id:'a',domain:[0,.5]},{...quadratic.branches[0],id:'b',domain:[.5,1]}]});const joins=projectCurves(connected,{matrix:[1,0,0,0,0,1,0,0]});assert.deepEqual(joins[0].points.at(-1),joins[1].points[0]);
assert.throws(()=>curveContract({version:1,branches:[{...quadratic.branches[0],controls:[[0,0,0],[NaN,0,0]]}]}),/finite/);
assert.throws(()=>projectCurves(quadratic,{matrix:[Infinity,0,0,0,0,1,0,0]}),/finite/);
assert.throws(()=>projectCurves(quadratic,{matrix:[1e200,0,0,0,0,1,0,0]}),/range/);
assert.throws(()=>projectCurves(quadratic,{matrix:[100,0,0,0,0,100,0,0],maxSegments:1}),/budget/);
assert.throws(()=>curveContract({version:1,branches:[{...quadratic.branches[0],domain:[0,Infinity]}]}),/domain/);
console.log(JSON.stringify({pass:true,observations,actualTikzCompilerAndVectorPacket:true,actualF333PlotAndGeometryBackend:true,clippedBranches:true,connectedEndpoints:true,finiteAndBudgetGuards:true,nativeCompilerQualification:false,browserPixels:false},null,2));
