import test from 'node:test';
import assert from 'node:assert/strict';
import {createSelectionController} from '../../browser-ui/vf-selection-controller.mjs';
import {createRetainedPlotView} from '../../browser-ui/vf-retained-plot-view.mjs';
import {unionOutlines} from '../../browser-ui/vf-selection-outline.mjs';
import {textSelectionObjects} from '../../browser-ui/vf-selection-adapters.mjs';
const box=(x=0,y=0)=>[[x,y],[x+7,y],[x+7,y+12],[x,y+12]];
const scene={selectionContour(){}};
const count=c=>c.preparationStats().unionComputations;
const setup=()=>{const regions=[{rings:[box()]}],details=[{rings:[box(20)]}];let size=0;
 const c=createSelectionController();const object={id:'text',regions:()=>regions,detailRegions:()=>details,detailSize:()=>size,hitTest:()=>true};
 c.replace('scope',[object]);c.selectAt([0,0]);return {c,regions,details,object,size:v=>size=v}};
test('content verification, clipping, snapshots, DPR and immutable style configuration',()=>{
 const {c,regions}=setup();const first=c.outlines(),n=count(c);first[0][0][0]=99999;first.push([[0,0]]);
 assert.deepEqual(c.outlines(),unionOutlines(regions,{padding:4}));assert.equal(count(c),n);
 regions[0].rings[0][0][0]=-3;assert.deepEqual(c.outlines(),unionOutlines(regions,{padding:4}));assert.equal(count(c),n+1);
 regions[0].clip=[box(2)];c.outlines();assert.equal(count(c),n+2);
 regions[0].clip[0][0][0]=3;c.outlines();assert.equal(count(c),n+3);
 regions[0].rings[0][0][0]=NaN;assert.throws(()=>c.outlines(),/finite polygon/);regions[0].rings[0][0][0]=-3;
 c.render(scene);const before=count(c);c.render(scene);assert.equal(count(c),before);c.render(scene,{pixelRatio:2});assert.equal(count(c),before+2);
 let emitted; c.render({selectionContour(...args){emitted=args;args[2][0][0]=[-999,-999]}},{pixelRatio:2});
 assert.equal(emitted[4],2);assert.deepEqual(c.outlines(),unionOutlines(regions,{padding:4}));
 const layers=c.layerPaths(),saved=structuredClone(layers);layers.outerPaths[0][0][0]=-999;layers.innerPaths.length=0;assert.deepEqual(c.layerPaths(),saved);
 const red=createSelectionController({selectionColor:'red',selectionRadius:6,ringWidth:3});red.replace('s',[{id:'x',regions:()=>regions,hitTest:()=>true}]);red.selectAt([0,0]);let color;red.render({selectionContour(...a){color=a[3]}});assert.equal(color,'red');assert.deepEqual(red.outlines(),unionOutlines(regions,{padding:6}));
});
test('zoom hysteresis, detail mutation, group replacement, deselection, disable and disposal',()=>{
 const {c,object,details,size}=setup();size(55);c.render(scene);assert.equal(c.presentation()[0].detail,false);
 size(56);c.render(scene);assert.equal(c.presentation()[0].detail,true);let n=count(c);
 size(42);c.render(scene);assert.equal(count(c),n);details[0].rings[0][0][0]=18;c.render(scene);assert.equal(count(c),n+1);
 size(40);c.render(scene);assert.equal(c.presentation()[0].detail,false);n=count(c);
 size(48);c.render(scene);assert.equal(count(c),n);
 c.replace('scope',[{...object,parentId:'group',clickTargets:['text','group']},{id:'group',regions:object.regions}]);c.render(scene);assert.ok(count(c)>n);
 c.selectAt([0,0],{clicks:2});c.render(scene);assert.deepEqual(c.selection(),['group']);
 c.clearSelection();assert.equal(c.preparationStats().entries,0);assert.deepEqual(c.outlines(),[]);
 c.selectAt([0,0]);c.setEnabled(false);assert.deepEqual(c.outlines(),[]);c.setEnabled(true);c.selectAt([0,0]);c.render(scene);
 c.replace('scope',[]);assert.deepEqual(c.outlines(),[]);c.dispose();assert.equal(c.preparationStats().entries,0);assert.throws(()=>c.outlines(),/disposed/);
});
test('authentic adapter projection is re-evaluated through mutable transform',()=>{
 let zoom=1,pan=0;const coordinates={worldToScreen:p=>[p[0]*zoom+pan,p[1]*zoom]};
 const c=createSelectionController();c.replace('text',textSelectionObjects({elementId:'e',coordinates,clusters:[{id:'c',rings:[box()],source:{id:'s',text:'a',offsetUnit:'utf16',start:0,end:1}}]}));c.selectAt([2,2]);
 c.outlines();let n=count(c);c.outlines();assert.equal(count(c),n);zoom=5;c.outlines();assert.equal(count(c),n+1);pan=20;c.outlines();assert.equal(count(c),n+2);
});
for(const kind of ['glyph','graph'])test(`1000 ${kind}: repeated actual retained frames and layers avoid unions`,()=>{
 let shift=0;const regions=Array.from({length:1000},(_,i)=>({rings:[kind==='glyph'?box(i*9):[[i*5,0],[i*5+10,5],[i*5,10]]]}));
 let packed;const v=createRetainedPlotView({coordinates:{worldToScreen:p=>p},renderer:{setPackedVertices:p=>packed=p}}),c=v.selectionController;
 c.replace(kind,[{id:kind,regions:()=>shift?regions.map(r=>({rings:r.rings.map(ring=>ring.map(([x,y])=>[x*1.01+shift,y*1.01]))})):regions,hitTest:()=>true}]);c.selectAt([0,0]);
 const timed=fn=>{const start=performance.now();fn();return performance.now()-start};
 const initial=timed(()=>v.render()),n=count(c),first=Array.from(packed),steady=[];
 for(let i=0;i<5;i++){steady.push(timed(()=>v.render()));assert.equal(count(c),n);assert.deepEqual(Array.from(packed),first)}
 const layerInitial=timed(()=>c.layerPaths()),ln=count(c),layerSteady=[];
 for(let i=0;i<5;i++){layerSteady.push(timed(()=>c.layerPaths()));assert.equal(count(c),ln)}
 shift=1;const changed=timed(()=>v.render());assert.ok(count(c)>ln);assert.notDeepEqual(Array.from(packed),first);
 console.log(JSON.stringify({kind,initialMs:initial,steadyMs:steady,layerInitialMs:layerInitial,layerSteadyMs:layerSteady,changedZoomMs:changed,initialUnions:n,steadyAdditionalUnions:0,layerInitialAdditionalUnions:ln-n,changedUnions:count(c)-ln,stats:c.preparationStats()}));v.dispose();
});
