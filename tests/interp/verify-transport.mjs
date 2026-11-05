import {pathToFileURL} from 'node:url';
import {mkdtemp,cp,writeFile,readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
import path from 'node:path';
const base=process.env.VKF_CANONICAL || '/home/viktor/Projects/Tesseracs/.worktrees/platonic-phone-web-20261104/public/vkf-0.7.5/playground/canonical';
const {createProjectCompiler}=await import(pathToFileURL(path.join(base,'package-tools/project.mjs'))),dir=await mkdtemp('/tmp/vkf-ink-transport-');
for(const name of ['Interp.vkf','Morphing.vkf','morphing'])await cp(name,path.join(dir,name),{recursive:true});
await writeFile(path.join(dir,'main.vkf'),await readFile('Interp.vkf','utf8')+'\n::1\n');
const c=await createProjectCompiler({compilerModule:path.join(base,'compiler.mjs'),compilerOptions:{printErr:()=>{}}}),compiled=await c.compileProject(dir);
const {createSymbolicKernel}=await import(pathToFileURL(process.env.VKF_RUNTIME || '/home/viktor/Projects/Vektor Flow/.worktrees/pp-text-modes-renderer-20261105/public/preview/0.7.5/vf-ui/vf-symbolic-kernel-runtime.mjs'));
const kernel=createSymbolicKernel({instance:new WebAssembly.Instance(await WebAssembly.compile(compiled.wasm),{}),manifest:compiled.result.manifest,diagnostics:true});
const settings=kernel.invokeValue('evaporate',[1,.35,.65,17,4,.54,.32,false]);
const source=[.1,.4,1,0,0,1,2,.2,.4,1,0,0,.5,2],destination=[.6,.2,0,1,1,1,2,.7,.2,0,1,1,1,2,.8,.2,0,1,1,.5,2,.9,.2,0,1,1,1,2],glyphs=[.6,.2,0,0,1,1,1,.8,.2,1,0,1,1,1];
const plan=kernel.invokeValue('prepare_vapor_transport',[settings,source,destination,glyphs]);assert.equal(plan.material.carriers,4);assert.equal(plan.material.weights.reduce((a,b)=>a+b),1);
const frames=[];for(const q of [0,.1,.25,.4,.6,.8,1]){const front=kernel.invokeValue('vapor_front',[settings,q,1.5]),frame=kernel.invokeValue('sample_vapor_transport',[plan,q,front]);assert(Math.abs(frame.ledger.reduce((a,b)=>a+b)-1)<1e-12);assert.equal(frame.gas.length,36);frames.push({q,front,frame});}
const first=frames[0].frame,last=frames.at(-1).frame;assert.equal(first.source_alpha,1);assert.equal(last.source_alpha,0);assert.deepEqual(last.ledger,[0,0,1]);
for(let i=0;i<4;i++){const a=plan.material.owners[i],b=plan.material.owners[4+i];assert.equal(first.gas[9*i],source[7*a]);assert.equal(first.gas[9*i+1],source[7*a+1]);assert.equal(last.gas[9*i],destination[7*b]);assert.equal(last.gas[9*i+1],destination[7*b+1]);assert.deepEqual(last.gas.slice(9*i+4,9*i+7),[0,1,1]);assert.equal(last.gas[9*i+2],0);}
assert(frames.some(({frame})=>frame.ledger[1]>0));assert(frames.some(({frame})=>frame.gas.some((v,i)=>i%9===4&&v>0&&v<1)),'source→target color interpolation');assert(frames[2].frame.gas[1]>source[1],'upward dissolved phase');
for(const {frame} of frames)for(let i=0;i<4;i++){if(frame.gas[9*i+8]>0){const b=plan.material.owners[4+i];assert.equal(frame.gas[9*i],destination[7*b]);assert.equal(frame.gas[9*i+1],destination[7*b+1]);}}
const replay=kernel.invokeValue('sample_vapor_transport',[plan,.4,frames[3].front]);assert.deepEqual(replay,frames[3].frame);
assert.throws(()=>kernel.invokeValue('prepare_vapor_transport',[settings,[],destination,glyphs]));assert.throws(()=>kernel.invokeValue('prepare_vapor_transport',[settings,source,[],glyphs]));
const report={passed:true,version:c.compilerVersion,binding:c.sourceBinding,scope:'native conserved dyadic carrier ledger, actual endpoint positions/colors, lifted seekable paths, arrival-front coupling, explicit empty endpoint rejection',sourceHashes:{'Interp.vkf':createHash('sha256').update(await readFile('Interp.vkf')).digest('hex')},frames,dir};
await writeFile('tests/interp/evidence/transport-qualification.json',JSON.stringify(report,null,2)+'\n');console.log('PASS material transport endpoints/color/ledger/front/seek/empty rejection');
