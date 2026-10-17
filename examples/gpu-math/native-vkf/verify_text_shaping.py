"""Python 3.14 preparation/reference driver for shared VKF literal shaping.

The independent oracle calls the actual document-text.mjs literal-input path.
It does not replace production shaping or use document-specific resources.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

if sys.version_info[:2] != (3, 14):
    raise SystemExit('Reference checks require Python 3.14')
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--compiler', type=Path, required=True)
p.add_argument('--wasm-compiler', type=Path)
p.add_argument('--browser-package', type=Path)
p.add_argument('--source-root', type=Path)
p.add_argument('--wasm-runtime', type=Path)
p.add_argument('--fonts', type=Path, required=True)
p.add_argument('--metrics', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
a.output.mkdir(parents=True, exist_ok=False)
root = Path(__file__).resolve().parent
source_root = a.source_root or root
if a.browser_package:
    a.wasm_runtime = a.browser_package/'vf-ui/vf-symbolic-kernel-runtime.mjs'
else:
    assert a.wasm_compiler and a.wasm_runtime, 'Provide --browser-package or legacy compiler/runtime'
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
report = dict(passed=False, completeRendererPort=False, performanceValidated=False,
              compilerSha256=sha(a.compiler), wasmCompilerSha256=sha(a.wasm_compiler) if a.wasm_compiler else None,
              wasmRuntimeSha256=sha(a.wasm_runtime), catalogSha256=sha(a.fonts),
              metricsSha256=sha(a.metrics), referenceSha256=sha(root.parent/'document-text.mjs'),
              sourceHashes={s.name:sha(s) for pattern in ['text_shaping*.vkf','text_font_metrics*.vkf','math_glyphs.vkf'] for s in source_root.glob(pattern)})

def run(command, input=None, timeout=240):
    result = subprocess.run(list(map(str, command)), input=input, text=True,
                            capture_output=True, timeout=timeout)
    if result.returncode:
        report['failure'] = dict(command=list(map(str,command)), stdout=result.stdout,
                                 stderr=result.stderr, exitCode=result.returncode)
        raise RuntimeError(result.stderr or result.stdout)
    return result.stdout

maximum = 0.0
def compare(expected, actual, path=''):
    global maximum
    if isinstance(expected, dict):
        assert expected.keys()==actual.keys(), (path,list(expected),list(actual))
        for key in expected: compare(expected[key],actual[key],path+'/'+key)
    elif isinstance(expected, list):
        assert len(expected)==len(actual),(path,len(expected),len(actual))
        for i,(left,right) in enumerate(zip(expected,actual)):compare(left,right,path+'/'+str(i))
    elif isinstance(expected,(str,bool)) or expected is None:
        assert type(expected) is type(actual) and expected==actual,(path,expected,actual)
    else:
        assert isinstance(actual,(int,float)) and math.isfinite(actual),(path,actual)
        error=abs(expected-actual);maximum=max(maximum,error)
        assert error<=0.000000001,(path,expected,actual,error)

def projection(value):
    return {**{k:value[k] for k in ['width','height','depth','atoms','diagnostics']},
            'items':[{k:item[k] for k in ['key','x','y']} for item in value['items']]}

try:
    metrics=json.loads(a.metrics.read_text())
    roles=list(metrics['documentFonts'])+['missing-role']
    words=['','AVATAR','Toffee','office','affinity','ffi','ffl','A V ',
           "``Quoted''---text--end",'‘word’ “text” – —','ıȷ',
           'Ångström naïve façade','A☃V☃','A😀V','!`?`','ffiffiffi']
    cases=[]
    for role in roles:
        for source in words:
            length=len(source.encode('utf-16-le'))//2
            cases.append(dict(role=role,source=source,start=0,stop=length))
        for source,start,stop in [('office',2,6),('affinity',2,7),('AVATAR',1,5),('åffi',1,4)]:
            cases.append(dict(role=role,source=source,start=start,stop=stop))
    (a.output/'cases.json').write_text(json.dumps(cases,ensure_ascii=True,indent=2)+'\n')
    oracle=a.output/'reference.mjs'
    oracle.write_text('''import {readFile,writeFile} from 'node:fs/promises';
import {pathToFileURL} from 'node:url';
const {typesetDocumentText}=await import(pathToFileURL(process.argv[2]));
const data=JSON.parse(await readFile(process.argv[3]));
const cases=JSON.parse(await readFile(process.argv[4]));
const result=cases.map(c=>{const source=c.source.slice(c.start,c.stop), q=typesetDocumentText(source,data,{font:c.role,width:1000000,justify:false,hyphens:false,literal:true,literalInput:true});
return {width:q.width,height:q.height,depth:q.depth,atoms:q.atoms,diagnostics:q.diagnostics,items:q.items.map(({key,x,y})=>({key,x,y}))};});
await writeFile(process.argv[5],JSON.stringify(result));
''')
    run(['node',oracle,root.parent/'document-text.mjs',a.metrics,a.output/'cases.json',a.output/'reference.json'])
    expected=json.loads((a.output/'reference.json').read_text())
    native=a.output/'text_dump'
    build=run([a.compiler,'-b',source_root/'text_shaping_dump.vkf','-o',native,'--diagnostics'])
    (a.output/'native-build.json').write_text(build)
    entries=[str(a.fonts),str(len(cases))]
    for i,case in enumerate(cases):
        source=a.output/f'input-{i}.txt';source.write_text(case['source'])
        entries.extend([case['role'],str(case['start']),str(case['stop']),str(source),str(a.output/f'native-{i}.json')])
    run([native],input='\n'.join(entries)+'\n',timeout=300)
    for i,e in enumerate(expected):compare(e,projection(json.loads((a.output/f'native-{i}.json').read_text())),f'native/{i}')
    report.update(nativePassed=True,nativeCases=len(cases),nativeMaximumError=maximum)
    (a.output/'native-verification.json').write_text(json.dumps(report,indent=2)+'\n')
    if a.browser_package:
        browser=a.output/'browser'
        run(['node',root/'compile_browser_kernel.mjs','--package',a.browser_package,
             '--source',source_root/'text_shaping_kernel.vkf','--entry','text_packet',
             '--entry-call','::text_packet("","","",0,0)','--output',browser])
        wasm=browser/'kernel.wasm';manifest=browser/'manifest.json'
    else:
        kernel=a.output/'text_kernel'
        build=run([a.compiler,'-b',source_root/'text_shaping_kernel.vkf','-o',kernel,'--diagnostics'])
        (a.output/'kernel-build.json').write_text(build)
        wasm=a.output/'text.wasm';manifest=a.output/'manifest.json'
        run([a.wasm_compiler,'--typed-ir',json.loads(build)['typed_ir_path'],'--wasm',wasm,'--manifest',manifest,'--entry','text_packet','--prune-to-entry'])
    driver=a.output/'run-wasm.mjs'
    driver.write_text('''import {readFile,writeFile,appendFile} from 'node:fs/promises';
import {pathToFileURL} from 'node:url';
const {createSymbolicKernel}=await import(pathToFileURL(process.argv[2]));
const manifest=JSON.parse(await readFile(process.argv[3]));
const {instance}=await WebAssembly.instantiate(await readFile(process.argv[4]));
const kernel=createSymbolicKernel({instance,manifest}),fonts=await readFile(process.argv[5],'utf8'),cases=JSON.parse(await readFile(process.argv[6]));
await writeFile(process.argv[7],'');
for(let i=0;i<cases.length;i++){const c=cases[i];const q=JSON.parse(kernel.invokeValue('text_packet',[fonts,c.source,c.role,c.start,c.stop]));await appendFile(process.argv[7],JSON.stringify(q)+'\\n');await writeFile(process.argv[8],JSON.stringify({completed:i+1,total:cases.length}));}
''')
    run(['node',driver,a.wasm_runtime,manifest,wasm,a.fonts,a.output/'cases.json',a.output/'wasm-results.jsonl',a.output/'progress.json'],timeout=900)
    actual=[json.loads(line) for line in (a.output/'wasm-results.jsonl').read_text().splitlines()]
    assert len(actual)==len(expected)
    for i,(e,v) in enumerate(zip(expected,actual)):compare(e,projection(v),f'wasm/{i}')
    report.update(passed=True,wasmPassed=True,wasmCases=len(cases),maximumAbsoluteError=maximum)
finally:
    (a.output/'verification.json').write_text(json.dumps(report,ensure_ascii=True,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ['passed','nativeCases','wasmCases','maximumAbsoluteError']}))
