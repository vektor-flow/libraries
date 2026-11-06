import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
const root=path.resolve(fileURLToPath(new URL('../..',import.meta.url))),compilerDir=process.argv[2];
if(!compilerDir)throw Error('Pass exact075 canonical compiler directory');
const {createProjectCompiler}=await import(pathToFileURL(compilerDir+'/package-tools/project.mjs'));
const compiler=await createProjectCompiler({compilerModule:compilerDir+'/compiler.mjs'});
const {createSymbolicKernel}=await import(pathToFileURL('/home/viktor/Projects/Vektor Flow/.worktrees/native-dense-material-renderer-20261105/public/preview/0.7.5/vf-ui/vf-symbolic-kernel-runtime.mjs'));
const source=String.raw`b:.morphing.biological
Curve:(knots:[num],values:[num],second:[num],count:int,width:int,mode:int)
Plan:(curve:Curve,dimension:int,size:int,cells:int,carriers:int,stride:int,smooth_start:bit,smooth_end:bit,join:num)
contour_field(vertices:[num],rings:[int],size:int)->[num]:b.polygon_field(vertices,rings,size,true)
geometry(knots:[num],offsets:[int],owners:[int],carriers:int,centers:[num],extents:[num],fields:[num],size:int,dimension:int,mode:int)->Plan:
    @:b.prepare(knots,offsets,owners,carriers,centers,extents,fields,size,dimension,mode,false,false,0)
attributes(plan:Plan,offsets:[int],owners:[int],values:[num],width:int)->Plan:
    @:b.attributes(plan,offsets,owners,values,width)
`;
async function build(baseline){
 const dir=await fs.mkdtemp(path.join(os.tmpdir(),'vkf-packing-'));await fs.mkdir(dir+'/morphing');
 for(const file of (await fs.readdir(root+'/morphing')).filter(n=>n.endsWith('.vkf'))){let bytes=await fs.readFile(root+'/morphing/'+file);if(baseline&&file==='biological.vkf')bytes=execFileSync('git',['show','32aceb6:morphing/biological.vkf'],{cwd:root});await fs.writeFile(dir+'/morphing/'+file,bytes);}
 await fs.writeFile(dir+'/main.vkf',source);const compiled=await compiler.compileProject(dir),module=await WebAssembly.compile(compiled.wasm);
 return()=>createSymbolicKernel({instance:new WebAssembly.Instance(module,{}),manifest:compiled.result.manifest,diagnostics:true});
}
const make=await build(false),old=await build(true),parity=[];
for(const dimension of [2,3])for(const mode of [0,1]){
 const size=3,cells=size**dimension,objects=4,offsets=[0,1,3,4],owners=[0,0,0,1,0,0],centers=Array.from({length:objects*dimension},(_,i)=>(i%dimension)*.1+Math.floor(i/dimension)*.03),extents=centers.map(()=>1),fields=Array.from({length:objects*cells},(_,i)=>i%cells===Math.floor(cells/2)?.6:-1),args=[[0,.3,1],offsets,owners,2,centers,extents,fields,size,dimension,mode];
 console.log(JSON.stringify({stage:'parity',dimension,mode}));const before=old().invokeValue('geometry',args),after=make().invokeValue('geometry',args);assert.deepEqual(after,before);
 for(const width of [1,4,64]){const values=Array.from({length:objects*width},(_,i)=>i/11),a=old().invokeValue('attributes',[before,offsets,owners,values,width]),b=make().invokeValue('attributes',[after,offsets,owners,values,width]);assert.deepEqual(b,a);}
 parity.push({dimension,mode,attributeWidths:[1,4,64],allPlanValuesAndCoefficientsExact:true});
}
const gcFixture=JSON.parse(await fs.readFile(new URL('./packing-gc-fixture.json',import.meta.url))),gcArgs=gcFixture.geometry.slice(0,10),oldGeometry=old().invokeValue('geometry',gcArgs),freshGeometry=make().invokeValue('geometry',gcArgs);assert.deepEqual(freshGeometry,oldGeometry);let sharedError=null;const shared=make();shared.invokeValue('contour_field',gcFixture.contour);try{shared.invokeValue('geometry',gcArgs);}catch(error){sharedError=error.message;}assert.equal(sharedError,'unreachable','Pinned075 shared-arena reproduction changed; reassess the explicit ownership gap');let fieldKernel=make();fieldKernel.invokeValue('contour_field',gcFixture.contour);fieldKernel=null;const scopedGeometry=make().invokeValue('geometry',gcArgs);assert.deepEqual(scopedGeometry,oldGeometry);const gcRegression={fixtureSha256:createHash('sha256').update(await fs.readFile(new URL('./packing-gc-fixture.json',import.meta.url))).digest('hex'),carriers:gcFixture.geometry[3],sharedArenaStatus:'RED: nativeGC allocation-header trap after contour then geometry; reset is not a repair',sharedArenaError:sharedError,scopedArenaStatus:'GREEN: native contour and geometry use separate detached instances of same cachedmodule',allScopedGeometryValuesAndCoefficientsExact:true};console.log(JSON.stringify({stage:'actual-contour-geometry-ownership-regression',...gcRegression}));
const carriers=27,size=65,dimension=2,cells=size*size,objects=carriers+1,offsets=[0,1,objects],owners=[...Array(carriers).fill(0),...Array.from({length:carriers},(_,i)=>i)],centers=Array.from({length:objects*dimension},(_,i)=>(i%2)*.1+Math.floor(i/2)*.001),extents=centers.map(()=>1),fields=Array.from({length:objects*cells},(_,i)=>{const j=i%cells,x=j%size,y=Math.floor(j/size);return x===0||y===0||x===size-1||y===size-1?-1: .5+j/(cells*10);}),args=[[0,1],offsets,owners,carriers,centers,extents,fields,size,dimension,0];
console.log(JSON.stringify({stage:'large-geometry'}));let t=performance.now();const geometry=make().invokeValue('geometry',args),geometryMs=performance.now()-t,rgba=Array.from({length:objects*4},(_,i)=>(i%4)/3);
console.log(JSON.stringify({stage:'large-attributes',geometryMs}));t=performance.now();const colored=make().invokeValue('attributes',[geometry,offsets,owners,rgba,4]),attributesMs=performance.now()-t;
for(let state=0;state<2;state++)for(let k=0;k<carriers;k++){const owner=offsets[state]+owners[state*carriers+k],base=(state*carriers+k)*geometry.stride,colorBase=(state*carriers+k)*colored.stride;for(let j=0;j<dimension;j++){assert.equal(geometry.curve.values[base+j],centers[owner*dimension+j]);assert.equal(geometry.curve.values[base+dimension+j],extents[owner*dimension+j]);}for(let j=0;j<cells;j++)assert.equal(geometry.curve.values[base+2*dimension+j],fields[owner*cells+j]);for(let j=0;j<geometry.stride;j++)assert.equal(colored.curve.values[colorBase+j],geometry.curve.values[base+j]);for(let j=0;j<4;j++)assert.equal(colored.curve.values[colorBase+geometry.stride+j],rgba[owner*4+j]);}
assert(geometry.curve.second.every(v=>v===0)&&colored.curve.second.every(v=>v===0));
const result={passed:true,compilerSourceBinding:compiler.sourceBinding,sourceSha256:createHash('sha256').update(await fs.readFile(root+'/morphing/biological.vkf')).digest('hex'),baseline:'32aceb6f7aa7cece078482c75af7533a51c21f09',gcRegression,parity,large:{carriers,size,values:geometry.curve.values.length,geometryMs,attributesMs,exactLayout:true,scope:'One current client WASM invocation, includes input marshal and output decoding; no GPU compute claim.'}};
await fs.writeFile(new URL('./packing-qualification.json',import.meta.url),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result));
