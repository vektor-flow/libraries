"""Compare retained VKF quotient placement to actual typing-layout.mjs."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
if sys.version_info[:2]!=(3,14):raise SystemExit('Reference checks require Python 3.14')
p=argparse.ArgumentParser(description=__doc__)
for name in ['compiler','wasm-compiler','wasm-runtime','fonts','metrics','output']:p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
root=Path(__file__).resolve().parent
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
report=dict(passed=False,completeRendererPort=False,performanceValidated=False,compilerSha256=sha(a.compiler),wasmCompilerSha256=sha(a.wasm_compiler),wasmRuntimeSha256=sha(a.wasm_runtime),catalogSha256=sha(a.fonts),metricsSha256=sha(a.metrics),referenceSha256=sha(root.parent/'typing-layout.mjs'),sourceHashes={s.name:sha(s) for s in root.glob('math_quotient*.vkf')})
def run(command,input=None,timeout=240):
    result=subprocess.run(list(map(str,command)),input=input,text=True,capture_output=True,timeout=timeout)
    if result.returncode:
        report['failure']=dict(command=list(map(str,command)),stdout=result.stdout,stderr=result.stderr,exitCode=result.returncode)
        raise RuntimeError(result.stderr or result.stdout)
    return result.stdout
maximum=0.0
def compare(e,v,path=''):
    global maximum
    if isinstance(e,dict):
        assert e.keys()==v.keys(),(path,list(e),list(v))
        for k in e:compare(e[k],v[k],path+'/'+k)
    elif isinstance(e,list):
        assert len(e)==len(v)
        for i,(x,y) in enumerate(zip(e,v)):compare(x,y,path+'/'+str(i))
    elif isinstance(e,str) or e is None:assert e==v,(path,e,v)
    else:
        assert isinstance(v,(int,float)) and math.isfinite(v)
        delta=abs(e-v);maximum=max(maximum,delta)
        assert delta<=0.000000001,(path,e,v,delta)
try:
    sizes=[dict(numerator=dict(width=nw,height=nh,depth=nd),denominator=dict(width=dw,height=dh,depth=dd)) for nw,nh,nd,dw,dh,dd in [(0,0,0,0,0,0),(5,7,1,6,8,2),(1,2,20,3,1,40),(10,25,0,8,30,0),(0.1,0.2,0.3,0.4,0.5,0.6),(50,0,0,60,0,0),(7,1,2,8,0,0),(25,30,8,70,9,11),(40,8,2,30,60,9),(5,3,8,3,7,10),(10,10,10,10,10,10),(100,100,100,100,100,100)]]
    cases=[dict(sizes=s,style=style,font=font,color=color) for s in sizes for style in range(4) for font in ['', 'boldsymbol'] for color in ['null','[0.2,0.4,0.6,1]']]
    (a.output/'cases.json').write_text(json.dumps(cases,indent=2)+'\n')
    oracle=a.output/'reference.mjs'
    oracle.write_text('''import {readFile,writeFile} from 'node:fs/promises';import {pathToFileURL} from 'node:url';
const {typeset}=await import(pathToFileURL(process.argv[2]));const data=JSON.parse(await readFile(process.argv[3])),cases=JSON.parse(await readFile(process.argv[4]));const result=cases.map(c=>{const box=(which)=>({...c.sizes[which],items:[{kind:'glyph',key:which,x:0,y:0}]});const extension={mathCommands:['\\\\fixture'],parseMathCommand(raw,{take}){take();return{type:'quotient',num:[{type:'nativebox',box:box('numerator')}],den:[{type:'nativebox',box:box('denominator')}]};}};let source='\\\\fixture';if(c.font)source='\\\\bm{'+source+'}';if(c.color!=='null')source='\\\\color[rgb]{.2,.4,.6}'+source;if(c.style===2)source='\\\\scriptstyle '+source;if(c.style===3)source='\\\\scriptscriptstyle '+source;const q=typeset(source,data.maps,{mode:c.style===1?'inline':'display',nativeSemantics:true,extensions:[extension]});return{width:q.width,height:q.height,depth:q.depth,diagnostics:q.diagnostics,items:q.items.map(({flowX,flowWidth,...item})=>item)};});await writeFile(process.argv[5],JSON.stringify(result));''')
    run(['node',oracle,root.parent/'typing-layout.mjs',a.metrics,a.output/'cases.json',a.output/'reference.json'])
    expected=json.loads((a.output/'reference.json').read_text())
    native=a.output/'quotient_dump'
    build=run([a.compiler,'-b',root/'math_quotient_dump.vkf','-o',native,'--diagnostics'])
    (a.output/'native-build.json').write_text(build)
    entries=[str(a.fonts),str(len(cases))]
    for i,c in enumerate(cases):entries.extend([json.dumps(c['sizes']),str(c['style']),c['font'],c['color'],str(a.output/f'native-{i}.json')])
    run([native],input='\n'.join(entries)+'\n')
    for i,e in enumerate(expected):compare(e,json.loads((a.output/f'native-{i}.json').read_text()),f'native/{i}')
    report.update(nativePassed=True,nativeCases=len(cases),nativeMaximumError=maximum)
    (a.output/'native-verification.json').write_text(json.dumps(report,indent=2)+'\n')
    build=run([a.compiler,'-b',root/'math_quotient_kernel.vkf','-o',a.output/'quotient_kernel','--diagnostics'])
    (a.output/'kernel-build.json').write_text(build)
    wasm=a.output/'quotient.wasm';manifest=a.output/'manifest.json'
    run([a.wasm_compiler,'--typed-ir',json.loads(build)['typed_ir_path'],'--wasm',wasm,'--manifest',manifest,'--entry','quotient_packet','--prune-to-entry'])
    driver=a.output/'run-wasm.mjs'
    driver.write_text('''import {readFile,writeFile,appendFile} from 'node:fs/promises';import {pathToFileURL} from 'node:url';const {createSymbolicKernel}=await import(pathToFileURL(process.argv[2]));const manifest=JSON.parse(await readFile(process.argv[3]));const {instance}=await WebAssembly.instantiate(await readFile(process.argv[4]));const kernel=createSymbolicKernel({instance,manifest}),fonts=await readFile(process.argv[5],'utf8'),cases=JSON.parse(await readFile(process.argv[6]));await writeFile(process.argv[7],'');for(let i=0;i<cases.length;i++){const c=cases[i],value=JSON.parse(kernel.invokeValue('quotient_packet',[fonts,JSON.stringify(c.sizes),c.style,c.font,c.color]));await appendFile(process.argv[7],JSON.stringify(value)+'\\n');await writeFile(process.argv[8],JSON.stringify({completed:i+1,total:cases.length}));}''')
    run(['node',driver,a.wasm_runtime,manifest,wasm,a.fonts,a.output/'cases.json',a.output/'wasm.jsonl',a.output/'progress.json'],timeout=900)
    actual=[json.loads(line) for line in (a.output/'wasm.jsonl').read_text().splitlines()]
    assert len(actual)==len(expected)
    for i,(e,v) in enumerate(zip(expected,actual)):compare(e,v,f'wasm/{i}')
    report.update(passed=True,wasmCases=len(cases),maximumAbsoluteError=maximum)
finally:(a.output/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ['passed','nativeCases','wasmCases','maximumAbsoluteError']}))
