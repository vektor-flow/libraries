import test from 'node:test';
import assert from 'node:assert/strict';
import {unionOutlines,insideRings,strokeRegions} from '../../browser-ui/vf-selection-outline.mjs';
import {createSelectionController,bindSelectionInput} from '../../browser-ui/vf-selection-controller.mjs';
import {textSelectionObjects,imageSelectionObject,nativeGeometrySelectionObject} from '../../browser-ui/vf-selection-adapters.mjs';
import {buildFaceSelectionBoundaryPaths,buildEdgeSelectionPaths} from '../../browser-ui/vf-selection-contours.mjs';
import {createSelectionContourMetrics,createSelectionLayerPasses,renderSelectionLayer,renderMergedSelectionLayer} from '../../browser-ui/vf-selection-presentation.mjs';
import {createRetainedPlotView} from '../../browser-ui/vf-retained-plot-view.mjs';
const box=(x,y,w,h)=>[[x,y],[x+w,y],[x+w,y+h],[x,y+h]];
const region=(...rings)=>({rings});
const area=paths=>paths.reduce((sum,path)=>sum+path.reduce((a,p,i)=>{const q=path[(i+1)%path.length];return a+(p[0]*q[1]-p[1]*q[0])/2},0),0);
const coords={scale:1,dx:0,dy:0,worldToScreen(p){return[p[0]*this.scale+this.dx,p[1]*this.scale+this.dy]}};
const controller=()=>createSelectionController({selectionRadius:0,detailThreshold:20,hysteresis:3});
const source={id:'source:owner',text:'𝛼fi∫(x)',offsetUnit:'utf16',start:0,end:4};
function textObjects(){return textSelectionObjects({elementId:'text:owner',coordinates:coords,groups:[{id:'word:owner',kind:'word'},{id:'integral:owner',kind:'math'},{id:'delimiter:owner',kind:'math'}],clusters:[
 {id:'cluster:ligature',groupId:'word:owner',source,rings:[box(0,0,10,10),box(3,3,4,4)]},
 {id:'cluster:ligature',groupId:'word:owner',source,rings:[box(10,0,2,10)]},
 {id:'cluster:i',groupId:'integral:owner',source,rings:[box(20,0,2,10)]},
 {id:'cluster:i',groupId:'integral:owner',source,rings:[box(20,10,2,5)]},
 {id:'cluster:d',groupId:'delimiter:owner',source,rings:[box(30,0,2,10)]},
 {id:'cluster:unknown',source,rings:[box(40,0,2,10)]}
]})}
test('Platonic transferred topology removes shared face diagonal; preserves branches',()=>{
 assert.deepEqual(buildFaceSelectionBoundaryPaths([[0,1,2],[2,1,3]]),[[0,1,3,2,0]]);
 assert.deepEqual(buildEdgeSelectionPaths([{a:0,b:1},{a:1,b:2},{a:1,b:3}]),[[0,1],[1,2],[1,3]]);
});
test('Platonic transferred metrics and original source-over then destination-out',()=>{
 const m=createSelectionContourMetrics({vertexRadius:7});assert.equal(m.selectionRadius,12);assert.equal(m.outerRadius,13);
 assert.deepEqual(createSelectionLayerPasses('face',m).map(x=>x.composite),['source-over','destination-out','destination-out']);
 const calls=[],ctx={save(){},restore(){},beginPath(){},stroke(){calls.push([this.globalCompositeOperation,this.lineWidth])}};
 renderSelectionLayer(ctx,{geometry:'edge',metrics:m,trace(){},pixelRatio:2});assert.deepEqual(calls,[['source-over',52],['destination-out',44]]);
});
for(const [name,regions,expectedArea,count]of [
 ['overlap',[region(box(0,0,10,10)),region(box(5,0,10,10))],150,1],
 ['containment',[region(box(0,0,10,10)),region(box(2,2,2,2))],100,1],
 ['touching edge',[region(box(0,0,10,10)),region(box(10,0,10,10))],200,1],
 ['disconnected',[region(box(0,0,10,10)),region(box(20,0,10,10))],200,2],
 ['hole',[region(box(0,0,10,10),box(2,2,6,6))],64,2],
 ['duplicate boundaries',[region(box(0,0,10,10)),region(box(0,0,10,10))],100,1],
 ['corner touch',[region(box(0,0,10,10)),region(box(10,10,10,10))],200,2]
])test('global union '+name,()=>{const p=unionOutlines(regions);assert.equal(p.length,count);assert.ok(Math.abs(area(p)-expectedArea)<1e-5);for(const path of p)assert.deepEqual(path[0],path.at(-1));
 // Midpoint oracle: no boundary segment may have filled material on both sides.
 for(const path of p)for(let i=1;i<path.length;i++){const a=path[i-1],b=path[i],d=[b[0]-a[0],b[1]-a[1]],l=Math.hypot(...d),m=[(a[0]+b[0])/2,(a[1]+b[1])/2],n=[-d[1]/l*1e-4,d[0]/l*1e-4];assert.notEqual(regions.some(r=>insideRings([m[0]+n[0],m[1]+n[1]],r.rings)),regions.some(r=>insideRings([m[0]-n[0],m[1]-n[1]],r.rings)))}
});
test('clipping and nonrectangular stroke envelope',()=>{
 const p=unionOutlines([{rings:[box(0,0,10,10)],clip:[box(0,0,5,10)]}]);assert.equal(area(p),50);
 const stroke=unionOutlines(strokeRegions([[0,0],[10,10]],1));assert.equal(insideRings([0,10],stroke),false);assert.equal(insideRings([5,5],stroke),true);
});
test('padding merges close regions, preserves sufficiently large holes',()=>{
 const p=unionOutlines([region(box(0,0,10,10)),region(box(11,0,10,10))],{padding:1});assert.equal(p.length,1);
 const hole=unionOutlines([region(box(0,0,20,20),box(4,4,12,12))],{padding:1});assert.equal(hole.length,2);assert.equal(insideRings([10,10],hole),false);
});
test('click 1/2/3 and constructed math, delimiter, unknown-scope fallback',()=>{
 coords.scale=1;const c=controller();c.replace('owner',textObjects());
 for(const [p,one,two]of [[[1,1],'cluster:ligature','word:owner'],[[21,12],'cluster:i','integral:owner'],[[31,2],'cluster:d','delimiter:owner'],[[41,2],'cluster:unknown','cluster:unknown']]){
  assert.deepEqual(c.selectAt(p),[one]);assert.deepEqual(c.selectAt(p,{clicks:2}),[two]);assert.deepEqual(c.selectAt(p,{clicks:3}),['text:owner']);}
});
test('glyph holes, ligature origins and source units retained; no bbox hits',()=>{
 const c=controller(),values=textObjects();c.replace('owner',values);assert.deepEqual(c.selectAt([5,5]),[]);assert.deepEqual(c.selectAt([11,1]),['cluster:ligature']);
 assert.equal(values.find(v=>v.id==='cluster:ligature').origins[0].text,source.text);assert.equal(values.find(v=>v.id==='cluster:ligature').origins[0].end,4);
});
test('cross-type union with image, glyph and native triangle; stable IDs and topmost overlap',()=>{
 const c=controller();const image=imageSelectionObject({imageId:'image:owner',boundary:box(8,0,10,10),coordinates:coords});
 const native=nativeGeometrySelectionObject({objectId:'native:owner',points:[[17,0],[25,0],[17,10]],indices:[0,1,2],topology:'triangle-list',coordinates:coords});
 c.replace('owner',[...textObjects(),image,native]);c.selectAt([1,1]);c.selectAt([15,1],{additive:true});c.selectAt([18,1],{additive:true});
 assert.deepEqual(c.selection(),['cluster:ligature','image:owner','native:owner']);const p=c.outlines();assert.equal(p.length,2); // exterior plus glyph hole
 assert.equal(insideRings([20,9],p),false);assert.equal(insideRings([15,5],p),true);
});
test('image transform and explicit alpha hole, zoom never reselects; hysteresis',()=>{
 const c=controller();c.replace('owner',textObjects());c.selectAt([1,1],{clicks:2});const ids=c.selection();
 coords.scale=2.4;c.outlines();assert.equal(c.presentation()[0].detail,true);coords.scale=1.9;c.outlines();assert.equal(c.presentation()[0].detail,true);coords.scale=1.6;c.outlines();assert.equal(c.presentation()[0].detail,false);assert.deepEqual(c.selection(),ids);
 coords.scale=2;coords.dx=5;const image=imageSelectionObject({imageId:'image',boundary:box(0,0,10,10),alphaRegions:[box(0,0,10,10),box(3,3,4,4)],coordinates:coords});
 assert.equal(image.hitTest([15,10]),false);assert.equal(image.hitTest([7,2]),true);coords.scale=1;coords.dx=0;
});
test('atomic replacement, disabled, Shift-additive, removed IDs and disposal',()=>{
 const c=controller();c.replace('owner',textObjects());c.selectAt([1,1]);c.selectAt([21,1],{additive:true});assert.equal(c.selection().length,2);
 assert.throws(()=>c.replace('owner',[{id:'bad',regions(){return[]},parentId:'absent'}]));assert.equal(c.selection().length,2);
 c.replace('owner',textObjects());assert.equal(c.selection().length,2);c.replace('new-owner',textObjects());assert.deepEqual(c.selection(),[]);
 c.setEnabled(false);assert.deepEqual(c.selectAt([1,1]),[]);c.setEnabled(true);c.selectAt([1,1]);c.replace('new-owner',[]);assert.deepEqual(c.selection(),[]);c.dispose();c.dispose();assert.throws(()=>c.selectAt([0,0]),/disposed/);
});
test('pointer drag is not click, cancel, native click counts, Shift/Escape and unbind',()=>{
 const handlers=new Map(),el={addEventListener(n,f){handlers.set(n,f)},removeEventListener(n){handlers.delete(n)},getBoundingClientRect(){return{left:100,top:50}}};
 const c=controller();c.replace('owner',textObjects());const unbind=bindSelectionInput(el,c);
 const send=(n,x=101,y=51,more={})=>handlers.get(n)?.({button:0,pointerId:7,clientX:x,clientY:y,detail:1,...more});
 send('pointerdown');send('pointermove',110,51);send('pointerup',101,51);send('click');assert.deepEqual(c.selection(),[]);
 send('pointerdown');send('pointerup');send('lostpointercapture');send('click',101,51,{detail:2});assert.deepEqual(c.selection(),['word:owner']);
 send('pointerdown',121,51);send('pointerup',121,51);send('click',121,51,{shiftKey:true});assert.deepEqual(c.selection(),['word:owner','cluster:i']);
 send('keydown',0,0,{key:'Escape'});assert.deepEqual(c.selection(),[]);send('pointerdown');send('pointercancel');send('click');assert.deepEqual(c.selection(),[]);unbind();assert.equal(handlers.size,0);
});
test('DPR applies once and high zoom details use same scene contour interface',()=>{
 const c=controller();c.replace('owner',textObjects());c.selectAt([1,1],{clicks:2});const calls=[];coords.scale=3;
 c.render({selectionContour(...args){calls.push(args)}},{pixelRatio:2});assert.ok(calls.some(a=>a[1].startsWith('selection-detail')));assert.ok(calls.every(a=>a[4]===2&&a[5].selectionRadius===0));assert.equal(Math.max(...calls[0][2].map(p=>p[0])),72);coords.scale=1;
});
test('one combined canvas outer pass before one combined clear pass, holes use evenodd',()=>{
 const c=createSelectionController({selectionRadius:2,ringWidth:2});c.replace('owner',[imageSelectionObject({imageId:'a',boundary:box(0,0,10,10),coordinates:coords}),imageSelectionObject({imageId:'b',boundary:box(5,0,10,10),coordinates:coords})]);c.selectAt([1,1]);c.selectAt([14,1],{additive:true});
 const layers=c.layerPaths();assert.equal(layers.outerPaths.length,1);assert.equal(layers.innerPaths.length,1);assert.ok(area(layers.outerPaths)>area(layers.innerPaths));
 const calls=[],ctx={save(){},restore(){},beginPath(){},moveTo(){},lineTo(){},closePath(){},fill(rule){calls.push([this.globalCompositeOperation,rule])}};c.renderLayer(ctx);assert.deepEqual(calls,[['source-over','evenodd'],['destination-out','evenodd']]);
});
test('existing retained mesh consumes common selection, merged faces and disabled behavior',()=>{
 let packed;const view=createRetainedPlotView({coordinates:coords,renderer:{setPackedVertices(v){packed=v}},pixelRatio:2,selectionRadius:1});
 const mesh=(id,x,selectable=true)=>({id,type:'field_mesh',selectable,topology:'triangle-list',vertices:[x,0,0,0,0,1,1,0,0,1,x+10,0,0,0,0,1,1,0,0,1,x,10,0,0,0,1,1,0,0,1],indices:[0,1,2]});
 view.replace({frame:'f',meshes:[mesh('a',0),mesh('b',5)]});view.selectAt([1,1],{tolerance:0});view.selectAt([6,1],{tolerance:0,additive:true});assert.deepEqual(view.selection(),['a','b']);assert.equal(view.selectionController.outlines().length,1);view.render();assert.ok(packed.length>0);
 view.replace({frame:'f',meshes:[mesh('a',0,false),mesh('b',5)]});assert.deepEqual(view.selection(),['b']);view.replace({frame:'other',meshes:[]});assert.deepEqual(view.selection(),[]);view.dispose();
});
test('unsupported precision/edge budget rejects explicitly',()=>{assert.throws(()=>unionOutlines([region(box(0,0,10,10))],{maxEdges:3}),/budget/);assert.throws(()=>unionOutlines([region(box(Infinity,0,10,10))]),/finite/)});
