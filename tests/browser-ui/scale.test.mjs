import test from 'node:test';
import assert from 'node:assert/strict';
import {unionOutlines,insideRings} from '../../browser-ui/vf-selection-outline.mjs';
import {unionOutlines as previous} from './selection-f331-oracle.mjs';
import {createSelectionController} from '../../browser-ui/vf-selection-controller.mjs';
import {createRetainedPlotView} from '../../browser-ui/vf-retained-plot-view.mjs';
const box=(x,y,w=7,h=12)=>[[x,y],[x+w,y],[x+w,y+h],[x,y+h]];
const glyphs=n=>Array.from({length:n},(_,i)=>({rings:[box(i*9,0)]}));
const measure=(name,fn)=>{const start=performance.now(),result=fn();console.log(JSON.stringify({name,ms:performance.now()-start,vertices:Array.isArray(result)?result.reduce((n,p)=>n+p.length,0):null}));return result};
test('exact F331 forty glyph default-padding rejection reproduced',()=>assert.throws(()=>previous(glyphs(40),{padding:4}),/edge budget/));
for(const n of [40,200,1000])test(`${n} glyphs: union and actual retained rendering; global layer geometry`,()=>{
 const regions=glyphs(n);const paths=measure(`union-${n}`,()=>unionOutlines(regions,{padding:4}));
 assert.equal(paths.length,1);assert.ok(paths[0].length<40*n);
 for(let i=0;i<n;i++){assert.equal(insideRings([i*9+3,6],paths),true);assert.equal(insideRings([i*9+3,-5],paths),false)}
 const c=createSelectionController();c.replace('text',[{id:'whole',regions:()=>regions,hitTest:()=>true}]);c.selectAt([0,0]);
 const layer=measure(`layer-${n}`,()=>c.layerPaths());assert.equal(layer.outerPaths.length,1);assert.equal(layer.innerPaths.length,1);
 assert.equal(insideRings([3,-4.5],layer.outerPaths),true);assert.equal(insideRings([3,-4.5],layer.innerPaths),false);
 let packed;const v=createRetainedPlotView({coordinates:{worldToScreen:p=>p},renderer:{setPackedVertices:p=>packed=p}});
 v.selectionController.replace('text',[{id:'whole',regions:()=>regions,hitTest:()=>true}]);v.selectionController.selectAt([0,0]);
 measure(`retained-${n}`,()=>v.render());assert.ok(packed.length>0);assert.ok(packed.length<5000*n);
 v.selectionController.setEnabled(false);v.render();assert.equal(packed.length,0);
 v.selectionController.setEnabled(true);v.selectionController.selectAt([0,0]);v.invalidate();v.render();assert.ok(packed.length>0);
 v.selectionController.replace('text',[]);v.render();assert.equal(packed.length,0);v.dispose();
});
test('dense overlap, duplicates, multi-line text, holes, disconnected clipping and diagonal graph',()=>{
 const dense=Array.from({length:1000},(_,i)=>({rings:[box((i%10)*.3,Math.floor(i/10)%10*.3)]}));
 const p=measure('dense-1000',()=>unionOutlines(dense,{padding:4}));assert.equal(p.length,1);assert.equal(insideRings([6,6],p),true);
 const rows=Array.from({length:1000},(_,i)=>({rings:[box((i%40)*9,Math.floor(i/40)*30)]}));
 const lines=measure('rows-1000',()=>unionOutlines(rows,{padding:4}));assert.equal(lines.length,25);
 const hole={rings:[box(0,0,50,50),box(10,10,30,30)],clip:[box(-20,-20,42,100),box(28,-20,42,100)]};
 const clipped=unionOutlines([hole],{padding:4});assert.equal(insideRings([25,3],clipped),false);assert.equal(insideRings([20,25],clipped),false);assert.equal(insideRings([5,25],clipped),true);assert.equal(insideRings([45,25],clipped),true);
 const graph=Array.from({length:1000},(_,i)=>({rings:[[[i*5,0],[i*5+10,5],[i*5,10]]]}));
 const g=measure('graph-1000',()=>unionOutlines(graph,{padding:4}));assert.equal(g.length,1);assert.equal(insideRings([3,-10],g),false);
});
