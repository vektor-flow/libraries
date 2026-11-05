// Independent endpoint/small-value and exact-polynomial conditioning checks.
import {pathToFileURL} from 'node:url';
import {mkdtemp,cp,writeFile,readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import path from 'node:path';
const base=process.env.VKF_CANONICAL || '/home/viktor/Projects/Tesseracs/.worktrees/platonic-phone-web-20261104/public/vkf-0.7.5/playground/canonical';
const {createProjectCompiler}=await import(pathToFileURL(path.join(base,'package-tools/project.mjs')));
const dir=await mkdtemp('/tmp/vkf-growth-positive-');await cp('morphing',path.join(dir,'morphing'),{recursive:true});
const alphas=[0,Number.MIN_VALUE,Number.MIN_VALUE*2,2**-1000,2**-500,2**-100,2**-50,2**-25,.001,.1,.5,.9,1],coefficients=[0,.25,4,16];
const source='u:.morphing.unfold\ngrowth(a:num,coefficient:num)->num:u.growth(a,coefficient)\ncoefficient(overshoot:num)->num:u.back_coefficient(overshoot)\n::1\n';
await writeFile(path.join(dir,'main.vkf'),source);
const c=await createProjectCompiler({compilerModule:path.join(base,'compiler.mjs'),compilerOptions:{printErr:()=>{}}}),compiled=await c.compileProject(dir);
const {createSymbolicKernel}=await import(pathToFileURL(process.env.VKF_RUNTIME || '/home/viktor/Projects/Vektor Flow/.worktrees/pp-text-modes-renderer-20261105/public/preview/0.7.5/vf-ui/vf-symbolic-kernel-runtime.mjs'));
const module=await WebAssembly.compile(compiled.wasm),kernel=createSymbolicKernel({instance:new WebAssembly.Instance(module,{}),manifest:compiled.result.manifest,diagnostics:true});
coefficients.push(kernel.invokeValue('coefficient',[.32]));let checks=0,maxRelativeError=0;
for(const a of alphas)for(const s of coefficients){
 const actual=kernel.invokeValue('growth',[a,s]),expected=a*(3-3*a+a*a+s*(1-2*a+a*a));
 if(a>0){if(!(actual>0))throw Error('nonpositive tiny native growth '+a);checks++;}
 if(a===0||a===1){if(actual!==a)throw Error('inexact endpoint');checks++;}
 else {const relative=Math.abs(actual/expected-1);maxRelativeError=Math.max(maxRelativeError,relative);if(relative>2e-14)throw Error('relative polynomial mismatch');checks++;}
}
for(const amount of [0,.01,.1,.32,.5]){const coefficient=kernel.invokeValue('coefficient',[amount]),peak=amount===0?1:1-2*coefficient/(3*(coefficient+1));if(Math.abs(kernel.invokeValue('growth',[peak,coefficient])-(1+amount))>1e-8)throw Error('requested overshoot changed');checks++;}
for(const s of coefficients){if(kernel.invokeValue('growth',[-1,s])!==0||kernel.invokeValue('growth',[2,s])!==1)throw Error('clamp semantics changed');checks+=2;}
const report={passed:true,version:c.compilerVersion,binding:c.sourceBinding,checks,maxRelativeError,unfoldSourceSha256:createHash('sha256').update(await readFile(path.join(dir,'morphing/unfold.vkf'))).digest('hex'),scope:'actual native WASM positive tiny-alpha growth and endpoint/relative same-polynomial checks; no physical GPU claim',sourceSha256:createHash('sha256').update(source).digest('hex'),dir,priorAttempt:'Constant-expanded assertions compiled for56s; stopped own process and moved test values to runtime arguments. No native source semantics changed for this test adaptation.'};
await writeFile('tests/interp/evidence/growth-qualification.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));
