"""Independent binary64 bit checks for VKF decimal decoding (Python3.14/Node).

This qualifies numeric conversion only, not full rendering or performance.
Native returns exact integer significand/exponent components; WASM transports
binary64 directly. Native zero sign is normalized by the component adapter.
"""
import argparse
import decimal
import hashlib
import json
import math
import random
import struct
import subprocess
import sys
from pathlib import Path

if sys.version_info[:2]!=(3,14):raise SystemExit('Python3.14 required')
p=argparse.ArgumentParser(description=__doc__)
for name in ['compiler','wasm-compiler','wasm-runtime','output']:p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
root=Path(__file__).resolve().parent
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
report={'passed':False,'componentOnly':True,'completeRendererPort':False,'performanceValidated':False,
        'nativeZeroSignNormalized':True,'sourceHashes':{s.name:sha(s)for s in root.glob('*.vkf')},
        'compilerSha256':sha(a.compiler),'wasmCompilerSha256':sha(a.wasm_compiler),'runtimeSha256':sha(a.wasm_runtime)}
def run(command,input=None,timeout=900):
    r=subprocess.run(list(map(str,command)),input=input,text=True,capture_output=True,timeout=timeout)
    if r.returncode:
        report['failure']={'command':list(map(str,command)),'exitCode':r.returncode,'stdout':r.stdout,'stderr':r.stderr}
        raise RuntimeError(r.stderr or r.stdout)
    return r.stdout
bits=lambda value:struct.pack('<d',value).hex()
try:
    native=a.output/'decimal_dump'
    (a.output/'native-build.json').write_text(run([a.compiler,'-b',root/'binary_decimal_dump.vkf','-o',native,'--diagnostics']))
    built=run([a.compiler,'-b',root/'binary_decimal_kernel.vkf','-o',a.output/'kernel','--diagnostics'])
    (a.output/'kernel-build.json').write_text(built)
    wasm=a.output/'kernel.wasm';manifest=a.output/'manifest.json'
    run([a.wasm_compiler,'--typed-ir',json.loads(built)['typed_ir_path'],'--wasm',wasm,'--manifest',manifest,'--entry','decimal','--prune-to-entry'])
    report['wasmSha256']=sha(wasm)
    # Inputs are selected only after both application artifacts compile.
    cases=['0','-0','0.1','-2.5','9.962660024906601','6.643837516661154',
           '9007199254740991','9007199254740992','9007199254740993','9007199254740995',
           '1e22','1e23','1e-22','1e-23','1e300','-1e300','1e-300',
           '2.4703282292062327e-324','2.4703282292062328e-324',
           '4.9406564584124654e-324','-4.9406564584124654e-324',
           '2.225073858507201e-308','2.2250738585072014e-308',
           '1.7976931348623157e308','1.7976931348623159e308','1e309','-1e9999','-1e-9999']
    rng=random.Random(831)
    for _ in range(96):
        value=math.ldexp(rng.uniform(1,2),rng.randint(-1000,996))
        if rng.randrange(2):value=-value
        cases.extend([repr(value),format(value,'.17g')])
    decimal.getcontext().prec=2000
    for value in [0.1,0.3,1.0,2.0,9.962660024906601,1e-20,1e20,-0.1]:
        other=math.nextafter(value,math.inf)
        middle=(decimal.Decimal.from_float(value)+decimal.Decimal.from_float(other))/2
        cases.append(str(middle))
    for _ in range(40):
        digits=str(rng.randrange(1,10))+''.join(str(rng.randrange(10))for _ in range(rng.randint(20,80)))
        place=rng.randrange(1,len(digits))
        cases.append(('-'if rng.randrange(2)else'')+digits[:place]+'.'+digits[place:]+'e'+str(rng.randint(-200,200)))
    cases=list(dict.fromkeys(cases))
    (a.output/'cases.json').write_text(json.dumps(cases))
    expected=[float(value)for value in cases]
    native_lines=run([native],input=str(len(cases))+'\n'+'\n'.join(cases)+'\n').splitlines()
    (a.output/'native-results.json').write_text(json.dumps(native_lines))
    assert len(native_lines)==len(cases)
    for i,(value,line)in enumerate(zip(expected,native_lines)):
        if not math.isfinite(value):assert line=='invalid',(i,line)
        else:
            sig,exp=map(int,line.split(','));actual=math.ldexp(sig,exp)
            assert bits(actual)==bits(0.0 if value==0 else value),(i,cases[i],actual,value)
    driver=a.output/'check.mjs'
    driver.write_text('''import {readFile,writeFile} from 'node:fs/promises';
import {pathToFileURL} from 'node:url';
const [runtime,manifestFile,wasmFile,casesFile,output]=process.argv.slice(2);
const {createSymbolicKernel}=await import(pathToFileURL(runtime));
const {instance}=await WebAssembly.instantiate(await readFile(wasmFile));
const kernel=createSymbolicKernel({instance,manifest:JSON.parse(await readFile(manifestFile))});
const bits=value=>{const bytes=new ArrayBuffer(8);new DataView(bytes).setFloat64(0,value,true);return Buffer.from(bytes).toString('hex');};
const results=[];
for(const source of JSON.parse(await readFile(casesFile))){
 const expected=JSON.parse(source),actual=kernel.invokeValue('decimal',[source]);
 const passed=actual.valid===Number.isFinite(expected)&&(!actual.valid||bits(actual.value)===bits(expected));
 results.push({source,passed,valid:actual.valid,bits:bits(actual.value),expectedBits:bits(expected)});
 if(!passed)throw Error(JSON.stringify(results.at(-1)));
}
await writeFile(output,JSON.stringify(results));
''')
    run(['node',driver,a.wasm_runtime,manifest,wasm,a.output/'cases.json',a.output/'wasm-results.json'])
    report.update(passed=True,casesPerBackend=len(cases),native=True,wasm=True)
finally:
    (a.output/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report.get(k)for k in ['passed','casesPerBackend','native','wasm']}))
