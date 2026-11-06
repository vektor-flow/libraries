import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {pathToFileURL,fileURLToPath} from 'node:url';
const root=path.resolve(fileURLToPath(new URL('../..',import.meta.url))),compilerDir=process.argv[2];
if(!compilerDir)throw Error('Pass the exact current075 canonical compiler directory');
const dir=await fs.mkdtemp(path.join(os.tmpdir(),'vkf-geometric-measure-'));await fs.mkdir(dir+'/morphing');
const sources={};for(const file of['morphing/parallel.vkf','morphing/segment.vkf']){const bytes=await fs.readFile(root+'/'+file);await fs.writeFile(dir+'/'+file,bytes);sources[file]=createHash('sha256').update(bytes).digest('hex');}
const test=await fs.readFile(new URL('./geometric-measure.vkf',import.meta.url));await fs.writeFile(dir+'/main.vkf',test);
const {createProjectCompiler}=await import(pathToFileURL(compilerDir+'/package-tools/project.mjs')),compiler=await createProjectCompiler({compilerModule:compilerDir+'/compiler.mjs'}),compiled=await compiler.compileProject(dir),module=await WebAssembly.compile(compiled.wasm);
assert.deepEqual(WebAssembly.Module.imports(module),[]);
const {createSymbolicKernel}=await import(pathToFileURL('/home/viktor/Projects/Vektor Flow/.worktrees/native-state-colors-renderer-20261106/public/preview/0.7.5/vf-ui/vf-symbolic-kernel-runtime.mjs')),make=()=>createSymbolicKernel({instance:new WebAssembly.Instance(module,{}),manifest:compiled.result.manifest,diagnostics:true});
const start=performance.now();assert.equal(make().invokeValue('test',[]),true);const testMs=performance.now()-start;
const invalid={};for(const name of['invalid_storage','invalid_size','invalid_extent','invalid_cell']){try{make().invokeValue(name,[]);invalid[name]='ACCEPTED';}catch(error){invalid[name]=error.message;}}assert(Object.values(invalid).every(v=>v==='invalid geometric measure cell'));
const result={passed:true,compilerVersion:compiler.compilerVersion,compilerSourceBinding:compiler.sourceBinding,sources,testSha256:createHash('sha256').update(test).digest('hex'),wasmBytes:compiled.wasm.length,testMs,scope:{triangleSamples:125,permutationsPerSample:6,positiveScales:[1e-8,1e-4,1,1e4,1e8],cellCases:625,renderingOracle:'Existing native parallel.cell_triangles; area integrated in native VKF test only',zeroSemantics:'F>=0; all-zero triangle is filled; zero edge with negative remainder has zero area',measureModel:'Piecewise-linear nodal triangle clipping, established a--d diagonal; not true bilinear/curved-field area',integration:'New internal helpers only; active biological.raster/dispatch unchanged; no browser/GPU readiness claim',threeDimensional:'Not implemented/qualified in this bounded helper task'},invalid};
await fs.writeFile(new URL('./geometric-measure-qualification.json',import.meta.url),JSON.stringify(result,null,2)+'\n');await fs.writeFile('/tmp/vkf-geometric-measure.wasm',compiled.wasm);await fs.writeFile('/tmp/vkf-geometric-measure.json',JSON.stringify(compiled.result.manifest));console.log(JSON.stringify(result));
