"""Observe QED evaluation order using actual JS glyph metric getters.

The VKF observer executes scheduler actions, not a replacement geometry engine.
JS observations distinguish skipped capture bodies, repeated evaluation, nested
push/pop side effects and execution-time font/style selection.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
if sys.version_info[:2]!=(3,14):raise SystemExit('Reference checks require Python 3.14')
p=argparse.ArgumentParser(description=__doc__)
for name in ['compiler','wasm-compiler','wasm-runtime','fonts','metrics','output']:p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
root=Path(__file__).resolve().parent
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
report=dict(passed=False,completeRendererPort=False,performanceValidated=False,compilerSha256=sha(a.compiler),wasmCompilerSha256=sha(a.wasm_compiler),wasmRuntimeSha256=sha(a.wasm_runtime),catalogSha256=sha(a.fonts),metricsSha256=sha(a.metrics),referenceSha256=sha(root.parent/'typing-layout.mjs'),sourceHashes={s.name:sha(s) for s in root.glob('math_qed*.vkf')})
def run(command,input=None,timeout=240):
    result=subprocess.run(list(map(str,command)),input=input,text=True,capture_output=True,timeout=timeout)
    if result.returncode:
        report['failure']=dict(command=list(map(str,command)),stdout=result.stdout,stderr=result.stderr,exitCode=result.returncode)
        raise RuntimeError(result.stderr or result.stdout)
    return result.stdout
def projection(value):
    assert value['depth']==0,value
    return {k:value[k] for k in ['events','diagnostics']}
try:
    sources=[r'\pushQED{a}',r'\pushQED{a}\qedhere\qedhere\popQED',r'\pushQED{a}\popQED',
             r'\pushQED{a}\pushQED{\popQED}\popQED',r'\pushQED{\pushQED{b}}\qedhere\popQED\popQED',
             r'\pushQED{a}\pushQED{\qedhere}\popQED',r'\pushQED{\popQED}\qedhere',
             r'\pushQED{\qed a}\qedhere',r'\qed a',r'\qedhere\qedhere',
             r'\pushQED{a}\scriptstyle\qedhere\scriptscriptstyle\qedhere',
             r'\pushQED{a}\mathbf{\qedhere}\qedhere',r'\pushQED{\mathbf{a}}\qedhere\qedhere',
             r'\pushQED{a}x_{\qedhere}\popQED',r'\pushQED{a}x^{\qedhere}_{\qedhere}\popQED',
             r'\pushQED{a}_b^x\qedhere_b^x',r'\pushQED{\scriptstyle a}\qedhere\qedhere',
             r'{\pushQED{a}}b\qedhere',r'\pushQED{a}{\qedhere}b\popQED',
             r'\pushQED{\qed}\mathbf{\qedhere}\qedhere',
             r'\pushQED{a}\widehat{\mathrm{A\popQED V}}',
             r'\pushQED{a}\xrightarrow[\popQED]{x\popQED b}',
             r'\pushQED{a}\left(\mathrm{A\popQED V}\middle|b\right)']
    cases=[]
    for source in sources:
        for style in range(4):
            styled=source
            if style==2:styled=r'\scriptstyle '+source
            if style==3:styled=r'\scriptscriptstyle '+source
            for display in [True,False]:cases.append(dict(source=styled,inline=style==1,display=display))
    (a.output/'cases.json').write_text(json.dumps(cases,indent=2)+'\n')
    oracle=a.output/'reference.mjs'
    oracle.write_text('''import {readFile,writeFile} from 'node:fs/promises';import {pathToFileURL} from 'node:url';
const {typeset}=await import(pathToFileURL(process.argv[2]));const amsthm=await import(pathToFileURL(process.argv[3]));const data=JSON.parse(await readFile(process.argv[4])),cases=JSON.parse(await readFile(process.argv[5]));let events=[];const maps={};const observed=new Set(['a','b','x','A','V','\\\\square']);for(const [style,map] of Object.entries(data.maps)){const symbols={};for(const [token,metric] of Object.entries(map.symbols)){const value={...metric};Object.defineProperty(value,'width',{enumerable:true,get(){if(observed.has(token.replace(/^@font:[^:]+:/,'')))events.push(style+'/'+token);return metric.width;}});symbols[token]=value;}maps[style]={...map,symbols};}maps.text.qedSymbol='\\\\square';const result=cases.map(c=>{events=[];const q=typeset(c.source,maps,{mode:c.inline?'inline':'display',displayEnvironment:c.display,nativeSemantics:true,packages:['amsthm'],extensions:[amsthm]});return{events:[...events],diagnostics:q.diagnostics};});
events=[];const bare=typeset('\\\\qed a',maps,{displayEnvironment:true,nativeSemantics:true,extensions:[amsthm]});const nested=typeset('\\\\pushQED{\\\\qed a}\\\\qedhere',maps,{displayEnvironment:true,nativeSemantics:true,extensions:[amsthm]});const glyph=maps.text.symbols['\\\\square'],body=maps.display.symbols.a;if(Math.abs(nested.items.find(i=>i.equationTag).tagWidth-(glyph.width+body.width))>1e-9)throw Error('Captured bareQED must participate inline in tag width');if(!bare.items.some(i=>i.equationTag&&i.key==='text/\\\\square'))throw Error('Bare displayQED must be tagged');await writeFile(process.argv[6],JSON.stringify(result));''')
    run(['node',oracle,root.parent/'typing-layout.mjs',root.parent/'latex-modules/packages/amsthm.mjs',a.metrics,a.output/'cases.json',a.output/'reference.json'])
    expected=json.loads((a.output/'reference.json').read_text())
    native=a.output/'qed_action_dump'
    build=run([a.compiler,'-b',root/'math_qed_action_dump.vkf','-o',native,'--diagnostics'])
    (a.output/'native-build.json').write_text(build)
    entries=[str(a.fonts),str(len(cases))]
    for i,c in enumerate(cases):
        source=a.output/f'input-{i}.tex';source.write_text(c['source'])
        entries.extend([str(source),str(a.output/f'native-{i}.json'),'inline' if c['inline'] else 'display','display' if c['display'] else 'ordinary'])
    run([native],input='\n'.join(entries)+'\n')
    for i,e in enumerate(expected):
        actual=projection(json.loads((a.output/f'native-{i}.json').read_text()))
        assert e==actual,(i,cases[i],e,actual)
    report.update(nativePassed=True,nativeCases=len(cases))
    (a.output/'native-verification.json').write_text(json.dumps(report,indent=2)+'\n')
    build=run([a.compiler,'-b',root/'math_qed_action_kernel.vkf','-o',a.output/'qed_action_kernel','--diagnostics'])
    (a.output/'kernel-build.json').write_text(build)
    wasm=a.output/'qed-actions.wasm';manifest=a.output/'manifest.json'
    run([a.wasm_compiler,'--typed-ir',json.loads(build)['typed_ir_path'],'--wasm',wasm,'--manifest',manifest,'--entry','qed_trace','--prune-to-entry'])
    driver=a.output/'run-wasm.mjs'
    driver.write_text('''import {readFile,writeFile,appendFile} from 'node:fs/promises';import {pathToFileURL} from 'node:url';const {createSymbolicKernel}=await import(pathToFileURL(process.argv[2]));const manifest=JSON.parse(await readFile(process.argv[3]));const {instance}=await WebAssembly.instantiate(await readFile(process.argv[4]));const kernel=createSymbolicKernel({instance,manifest}),fonts=await readFile(process.argv[5],'utf8'),cases=JSON.parse(await readFile(process.argv[6]));await writeFile(process.argv[7],'');for(let i=0;i<cases.length;i++){const c=cases[i],q=JSON.parse(kernel.invokeValue('qed_trace',[c.source,fonts,c.inline,c.display]));await appendFile(process.argv[7],JSON.stringify(q)+'\\n');await writeFile(process.argv[8],JSON.stringify({completed:i+1,total:cases.length}));}''')
    run(['node',driver,a.wasm_runtime,manifest,wasm,a.fonts,a.output/'cases.json',a.output/'wasm.jsonl',a.output/'progress.json'],timeout=900)
    actual=[json.loads(line) for line in (a.output/'wasm.jsonl').read_text().splitlines()]
    assert len(actual)==len(expected)
    for i,(e,v) in enumerate(zip(expected,actual)):assert e==projection(v),(i,cases[i],e,projection(v))
    report.update(passed=True,wasmCases=len(cases),actualJsTagDepthProbe=True)
finally:(a.output/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ['passed','nativeCases','wasmCases']}))
