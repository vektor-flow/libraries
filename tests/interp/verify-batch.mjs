import {pathToFileURL} from 'node:url';
import {mkdtemp,cp,writeFile,readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import os from 'node:os';
import path from 'node:path';
const base=process.env.VKF_CANONICAL || '/home/viktor/Projects/Tesseracs/.worktrees/platonic-phone-web-20261104/public/vkf-0.7.5/playground/canonical';
const {createProjectCompiler}=await import(pathToFileURL(path.join(base,'package-tools/project.mjs')));
const dir=await mkdtemp(path.join(os.tmpdir(),'vkf-interp-batch-'));
for(const name of ['Morphing.vkf','Interpolation.vkf','Interp.vkf','morphing','interpolation'])await cp(name,path.join(dir,name),{recursive:true});
const source=`i:.Interpolation
check()->bit:
    gas:i.vapor_interp(seed:127)
    reveal:i.spectral_interp(grow:false)
    ink:[0,0,1,0.5,-0.25,0.5]
    reading:[0,0.25]
    first:i.text_frame(gas,0,ink,reading,0)
    last:i.text_frame(gas,1,ink,reading,2)
    middle:i.text_frame(gas,0.5,ink,reading,0.3)
    repeat:i.text_frame(gas,0.5,ink,reading,0.3)
    simple:i.text_frame(reveal,0.5,[],reading,0.3)
    empty:i.text_frame(gas,0.5,[],[],0)
    (first.source_alpha=1 /\\ last.source_alpha=0)?! "exact source endpoint"
    (empty.gas.length()=0 /\\ empty.target.length()=0 /\\ simple.gas.length()=0)?! "empty and reveal layouts"
    (middle.gas.length()=8 /\\ middle.target.length()=10)?! "packed strides"
    j:0
    j<2?>
        (first.gas.(4*j+2)=0 /\\ last.gas.(4*j+2)=0)?! "gas endpoint absent"
        (first.target.(5*j)=0 /\\ last.target.(5*j)=1)?! "target endpoint exact"
        (last.target.(5*j+1)=1 /\\ last.target.(5*j+2)=1 /\\ last.target.(5*j+3)=1 /\\ last.target.(5*j+4)=1)?! "target growth/color finish"
        (simple.target.(5*j+1)=1)?! "grow false batch"
        (|middle.gas.(4*j)-(ink.(3*j)+i.vapor_channel(gas,0.5,j,0))|<0.000000001)?! "batch dx matches scalar"
        (|middle.gas.(4*j+1)-(ink.(3*j+1)+i.vapor_channel(gas,0.5,j,1))|<0.000000001)?! "batch dy matches scalar"
        (|middle.gas.(4*j+2)-ink.(3*j+2)*i.vapor_channel(gas,0.5,j,2)|<0.000000001)?! "batch alpha preserves ink coverage"
        (middle.gas.(4*j+3)=i.vapor_channel(gas,0.5,j,3))?! "batch size matches scalar"
        ch:0
        ch<5?>
            (middle.target.(5*j+ch)=i.reveal_channel(gas,0.3-reading.(j),ch))?! "batch reveal matches native unfold"
            .ch:ch+1
        .j:j+1
    .j:0
    j<8?>
        (middle.gas.(j)=repeat.gas.(j))?! "seek deterministic packet"
        .j:j+1
    @:true
::check()
`;
await writeFile(path.join(dir,'main.vkf'),source);
const c=await createProjectCompiler({compilerModule:path.join(base,'compiler.mjs'),compilerOptions:{printErr:()=>{}}});
const start=Date.now();const result=await c.runProject(dir);
if(result.stdout.trim()!=='true')throw Error(result.stdout);
await writeFile(path.join(dir,'batch.wasm'),result.wasm);
const sourceHashes={};for(const name of ['Interp.vkf','Interpolation.vkf'])sourceHashes[name]=createHash('sha256').update(await readFile(name)).digest('hex');
const report={passed:true,version:c.compilerVersion,binding:c.sourceBinding,sourceHashes,sourceSha256:createHash('sha256').update(source).digest('hex'),ms:Date.now()-start,stdout:result.stdout,dir,scope:'actual client canonical WASM batch output: exact endpoints, empty inputs, scalar parity, native coverage and seek determinism; no GPU/renderer performance claim'};
await writeFile('tests/interp/evidence/batch-qualification.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));
