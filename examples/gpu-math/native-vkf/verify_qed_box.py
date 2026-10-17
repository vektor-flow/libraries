"""Python 3.14 reference driver; production QED geometry is shared VKF."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
if sys.version_info[:2] != (3,14):raise SystemExit('Reference checks require Python 3.14')
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--compiler',type=Path,required=True)
p.add_argument('--wasm-compiler',type=Path,required=True)
p.add_argument('--wasm-runtime',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
root=Path(__file__).resolve().parent
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
report=dict(passed=False,completeRendererPort=False,performanceValidated=False,
            compilerSha256=sha(a.compiler),wasmCompilerSha256=sha(a.wasm_compiler),
            wasmRuntimeSha256=sha(a.wasm_runtime),referenceSha256=sha(root.parent/'qed-box.mjs'),
            sourceHashes={s.name:sha(s) for s in root.glob('math_qed*.vkf')})
def run(command,input=None):
    result=subprocess.run(list(map(str,command)),input=input,text=True,capture_output=True,timeout=120)
    if result.returncode:
        report['failure']=dict(command=list(map(str,command)),stdout=result.stdout,stderr=result.stderr,exitCode=result.returncode)
        raise RuntimeError(result.stderr or result.stdout)
    return result.stdout
maximum=0.0
def compare(expected,actual,path=''):
    global maximum
    if isinstance(expected,dict):
        assert expected.keys()==actual.keys(),(path,list(expected),list(actual))
        for k in expected:compare(expected[k],actual[k],path+'/'+k)
    elif isinstance(expected,list):
        assert len(expected)==len(actual)
        for i,(x,y) in enumerate(zip(expected,actual)):compare(x,y,path+'/'+str(i))
    elif isinstance(expected,str):assert expected==actual,(path,expected,actual)
    else:
        assert isinstance(actual,(float,int)) and math.isfinite(actual)
        error=abs(expected-actual);maximum=max(maximum,error)
        assert error<=0.000000001,(path,expected,actual,error)
try:
    # Include actual font quads, small side glue, optical sizes and a generic
    # deterministic sequence. These are correctness cases, never timings.
    quads=[0,0.1,0.4,1,7,9.962640099626402,11.955168119551681,12,100]+[i/17 for i in range(1,129)]
    (a.output/'cases.json').write_text(json.dumps(quads)+'\n')
    reference=a.output/'reference.mjs'
    reference.write_text('''import {readFile,writeFile} from 'node:fs/promises';import {pathToFileURL} from 'node:url';
const {qedBox}=await import(pathToFileURL(process.argv[2]));const values=JSON.parse(await readFile(process.argv[3]));await writeFile(process.argv[4],JSON.stringify(values.map(qedBox)));''')
    run(['node',reference,root.parent/'qed-box.mjs',a.output/'cases.json',a.output/'reference.json'])
    expected=json.loads((a.output/'reference.json').read_text())
    native=a.output/'qed_dump'
    build=run([a.compiler,'-b',root/'math_qed_dump.vkf','-o',native,'--diagnostics'])
    (a.output/'native-build.json').write_text(build)
    entries=[str(len(quads))]
    for i,quad in enumerate(quads):entries.extend([str(quad),str(a.output/f'native-{i}.json')])
    run([native],input='\n'.join(entries)+'\n')
    for i,e in enumerate(expected):compare(e,json.loads((a.output/f'native-{i}.json').read_text()),f'native/{i}')
    report.update(nativePassed=True,nativeCases=len(quads))
    build=run([a.compiler,'-b',root/'math_qed_kernel.vkf','-o',a.output/'qed_kernel','--diagnostics'])
    (a.output/'kernel-build.json').write_text(build)
    wasm=a.output/'qed.wasm';manifest=a.output/'manifest.json'
    run([a.wasm_compiler,'--typed-ir',json.loads(build)['typed_ir_path'],'--wasm',wasm,'--manifest',manifest,'--entry','qed_box','--prune-to-entry'])
    driver=a.output/'run-wasm.mjs'
    driver.write_text('''import {readFile,writeFile} from 'node:fs/promises';import {pathToFileURL} from 'node:url';
const {createSymbolicKernel}=await import(pathToFileURL(process.argv[2]));const manifest=JSON.parse(await readFile(process.argv[3]));const {instance}=await WebAssembly.instantiate(await readFile(process.argv[4]));const kernel=createSymbolicKernel({instance,manifest}),quads=JSON.parse(await readFile(process.argv[5]));await writeFile(process.argv[6],JSON.stringify(quads.map(quad=>JSON.parse(kernel.invokeValue('qed_box',[quad])))));''')
    run(['node',driver,a.wasm_runtime,manifest,wasm,a.output/'cases.json',a.output/'wasm.json'])
    actual=json.loads((a.output/'wasm.json').read_text())
    for i,(e,v) in enumerate(zip(expected,actual)):compare(e,v,f'wasm/{i}')
    assert len(actual)==len(expected)
    report.update(passed=True,wasmCases=len(quads),maximumAbsoluteError=maximum)
finally:(a.output/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ['passed','nativeCases','wasmCases','maximumAbsoluteError']}))
