"""Independent actual JS package-registry/parser reference; VKF owns parsing."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
if sys.version_info[:2] != (3,14):raise SystemExit('Reference checks require Python 3.14')
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--compiler',type=Path,required=True)
p.add_argument('--wasm-compiler',type=Path,required=True)
p.add_argument('--wasm-runtime',type=Path,required=True)
p.add_argument('--fonts',type=Path,required=True)
p.add_argument('--metrics',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
root=Path(__file__).resolve().parent
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
report=dict(passed=False,completeRendererPort=False,performanceValidated=False,compilerSha256=sha(a.compiler),
            wasmCompilerSha256=sha(a.wasm_compiler),wasmRuntimeSha256=sha(a.wasm_runtime),
            catalogSha256=sha(a.fonts),metricsSha256=sha(a.metrics),
            sourceHashes={s.name:sha(s) for s in root.glob('*.vkf')},
            referenceHashes={str(s.relative_to(root.parent)):sha(s) for s in [root.parent/'draft-parser.mjs',root.parent/'latex-modules/registry.mjs',*[root.parent/f'latex-modules/packages/{name}.mjs' for name in ['amsthm','bbm','latexsym','faktor','amsmath']]]})
def run(command,input=None,timeout=240):
    result=subprocess.run(list(map(str,command)),input=input,text=True,capture_output=True,timeout=timeout)
    if result.returncode:
        report['failure']=dict(command=list(map(str,command)),stdout=result.stdout,stderr=result.stderr,exitCode=result.returncode)
        raise RuntimeError(result.stderr or result.stdout)
    return result.stdout
try:
    contexts=[([],"article"),(["amsmath"],"article"),(["amsthm"],"article"),(["bbm"],"article"),(["latexsym"],"article"),(["faktor"],"article"),([],"amsart"),(["amsmath","amsthm","bbm","latexsym","faktor"],"article")]
    sources=[r'\qed',r'a\qedhere',r'\popQED',r'\pushQED{\qed}a\qedhere\popQED',
             r'\pushQED\mathbf x\popQED',r'\pushQED',r'\pushQED{}',r'\pushQED{a_b}',
             r'\pushQED{\unknown}',r'\pushQED{\frac{a}',r'\pushQED{\pushQED{b}\qedhere}\popQED',
             r'\mathbbm{1}+\mathbbmss{A}+\mathbbmtt{x}',r'\mathbbm1',r'\mathbbm',
             r'\Box+\Diamond+\Join+\mho',r'\leadsto+\sqsubset+\sqsupset+\lhd+\unlhd+\rhd+\unrhd',
             r'\bm{\Box}',r'\faktor{a}{b}',r'\faktor[\scriptstyle]{a_b}{x}',
             r'\faktor{\unknown}{\unknown}',r'\faktor ab',r'\faktor',r'\faktor{a',
             r'\faktor[\color{red}]{a}{b}',r'\faktor{\frac ab}{\sqrt{x}}',
             r'\faktor{\begin{matrix}a&b\\x&y\end{matrix}}{x}',
             r'\faktor{\pushQED{b}\qedhere}{\mathbbm1}',
             r'\binom ab+\pmod{x}+\pod{a}+\mod b+\bmod',r'\genfrac{}{}{0pt}{}{a}{b}',
             r'\tag{A}x\notag\nonumber+\operatorname*{foo}_a',r'\cdots,\cdots a',
             r'\frac ab+\dfrac ab',r'\qed_a^b',r'\pushQED{a}_b^x\popQED',r'\faktor{a}{b}_x^y']
    cases=[dict(source=source,names=names,className=class_name,native=native) for names,class_name in contexts for native in [True,False] for source in sources]
    (a.output/'cases.json').write_text(json.dumps(cases,indent=2)+'\n')
    oracle=a.output/'reference.mjs'
    oracle.write_text('''import {readFile,writeFile} from 'node:fs/promises';import {pathToFileURL} from 'node:url';
const {parseDraft}=await import(pathToFileURL(process.argv[2]));const {resolveModules}=await import(pathToFileURL(process.argv[3]));const data=JSON.parse(await readFile(process.argv[4])),cases=JSON.parse(await readFile(process.argv[5]));const result=[];
for(const c of cases){const modules=await resolveModules('\\\\documentclass{'+c.className+'}'+c.names.map(n=>'\\\\usepackage{'+n+'}').join(''));result.push(parseDraft(c.source,data.maps.display,{packages:[...modules.packages.keys()],extensions:[...modules.packages.values()].filter(p=>p.parseMathCommand),nativeSemantics:c.native}));}await writeFile(process.argv[6],JSON.stringify(result));''')
    run(['node',oracle,root.parent/'draft-parser.mjs',root.parent/'latex-modules/registry.mjs',a.metrics,a.output/'cases.json',a.output/'reference.json'])
    expected=json.loads((a.output/'reference.json').read_text())
    native=a.output/'package_dump'
    build=run([a.compiler,'-b',root/'math_package_dump.vkf','-o',native,'--diagnostics'])
    (a.output/'native-build.json').write_text(build)
    entries=[str(a.fonts),str(len(cases))]
    for i,c in enumerate(cases):
        source=a.output/f'input-{i}.tex';source.write_text(c['source'])
        entries.extend([str(source),str(a.output/f'native-{i}.json'),json.dumps(c['names']),c['className'],'native' if c['native'] else 'preview','ast'])
    run([native],input='\n'.join(entries)+'\n',timeout=300)
    for i,e in enumerate(expected):
        actual=json.loads((a.output/f'native-{i}.json').read_text())
        assert e==actual,(i,cases[i],e,actual)
    report.update(nativePassed=True,nativeCases=len(cases))
    (a.output/'native-verification.json').write_text(json.dumps(report,indent=2)+'\n')
    build=run([a.compiler,'-b',root/'math_package_kernel.vkf','-o',a.output/'package_kernel','--diagnostics'])
    (a.output/'kernel-build.json').write_text(build)
    wasm=a.output/'packages.wasm';manifest=a.output/'manifest.json'
    run([a.wasm_compiler,'--typed-ir',json.loads(build)['typed_ir_path'],'--wasm',wasm,'--manifest',manifest,'--entry','package_packet','--prune-to-entry'])
    driver=a.output/'run-wasm.mjs'
    driver.write_text('''import {readFile,writeFile,appendFile} from 'node:fs/promises';import {pathToFileURL} from 'node:url';
const {createSymbolicKernel}=await import(pathToFileURL(process.argv[2]));const manifest=JSON.parse(await readFile(process.argv[3]));const {instance}=await WebAssembly.instantiate(await readFile(process.argv[4]));const kernel=createSymbolicKernel({instance,manifest}),fonts=await readFile(process.argv[5],'utf8'),cases=JSON.parse(await readFile(process.argv[6]));await writeFile(process.argv[7],'');for(let i=0;i<cases.length;i++){const c=cases[i],value=JSON.parse(kernel.invokeValue('package_packet',[c.source,fonts,c.names,c.className,c.native,false]));await appendFile(process.argv[7],JSON.stringify(value)+'\\n');await writeFile(process.argv[8],JSON.stringify({completed:i+1,total:cases.length}));}''')
    run(['node',driver,a.wasm_runtime,manifest,wasm,a.fonts,a.output/'cases.json',a.output/'wasm-results.jsonl',a.output/'progress.json'],timeout=900)
    actual=[json.loads(line) for line in (a.output/'wasm-results.jsonl').read_text().splitlines()]
    assert len(actual)==len(expected)
    for i,(e,v) in enumerate(zip(expected,actual)):assert e==v,(i,cases[i],e,v)
    report.update(passed=True,wasmPassed=True,wasmCases=len(cases))
finally:(a.output/'verification.json').write_text(json.dumps(report,ensure_ascii=True,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ['passed','nativeCases','wasmCases']}))
