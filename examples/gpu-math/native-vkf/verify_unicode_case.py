"""Python3.14 actual ECMAScript casing reference, generic Unicode17 assets only."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
assert sys.version_info[:2]==(3,14)
p=argparse.ArgumentParser(description=__doc__)
for key in ['compiler','wasm-compiler','wasm-runtime','output']:p.add_argument('--'+key,type=Path,required=True)
a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);root=Path(__file__).resolve().parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
report={'passed':False,'completeRendererPort':False,'sourceHashes':{s.name:sha(s) for s in root.glob('unicode_case*.vkf')},'preparationSha256':sha(root/'prepare_unicode_case.py')}
def run(command,input=None,timeout=300):
 q=subprocess.run(list(map(str,command)),input=input,text=True,capture_output=True,timeout=timeout);assert q.returncode==0,(command,q.stdout,q.stderr);return q.stdout
try:
 oracle=a.output/'reference.mjs';oracle.write_text(r"""import{writeFile}from'node:fs/promises';const cases=[];for(let code=0;code<=0x10ffff;code++){if(code>=0xd800&&code<=0xdfff)continue;const c=String.fromCodePoint(code);if(c.toUpperCase()!==c||c.toLowerCase()!==c)cases.push(c);}const neighbors=['A','Σ','İ','ͅ','́','\u200d',"'",':','.', '-', ' ', 'א', 'a','1'];for(const a of neighbors)for(const b of neighbors)cases.push(a+'Σ'+b,a+'Σ'+b+'Σ',a+'́Σ́'+b);cases.push(String.raw`A \textit{mixed Straße} and $l_1+σ$ \@abc`,String.raw`ΟΣ \textbf{İ ﬃ} $ασ$`,String.raw`unclosed $greek σ`,String.raw`escaped \$ mixed`);const tex=s=>s.replace(/\$[^$]*\$|\\[A-Za-z]+|[^\\$]+|./g,p=>p.startsWith('\\')||p.startsWith('$')?p:p.toUpperCase());await writeFile(process.argv[2],JSON.stringify(cases));await writeFile(process.argv[3],JSON.stringify(cases.map(s=>[s.toUpperCase(),s.toLowerCase(),tex(s)])));await writeFile(process.argv[4],JSON.stringify({unicode:process.versions.unicode,cases:cases.length}));""")
 run(['node',oracle,a.output/'cases.json',a.output/'reference.json',a.output/'metadata.json']);expected=json.loads((a.output/'reference.json').read_text());report.update(json.loads((a.output/'metadata.json').read_text()))
 build=run([a.compiler,'-b',root/'unicode_case_dump.vkf','-o',a.output/'dump','--diagnostics']);(a.output/'native-build.json').write_text(build)
 run([a.output/'dump'],input=str(a.output/'cases.json')+'\n'+str(a.output/'native.json')+'\n');actual=json.loads((a.output/'native.json').read_text());assert actual==expected,next(((i,e,v) for i,(e,v) in enumerate(zip(expected,actual)) if e!=v),('count',len(expected),len(actual)))
 report.update(nativePassed=True)
 build=run([a.compiler,'-b',root/'unicode_case_kernel.vkf','-o',a.output/'kernel','--diagnostics']);(a.output/'kernel-build.json').write_text(build)
 manifest=a.output/'manifest.json';wasm=a.output/'kernel.wasm';run([a.wasm_compiler,'--typed-ir',json.loads(build)['typed_ir_path'],'--wasm',wasm,'--manifest',manifest,'--entry','unicode_batch','--prune-to-entry'])
 driver=a.output/'run-wasm.mjs';driver.write_text("import{readFile,writeFile}from'node:fs/promises';import{pathToFileURL}from'node:url';const{createSymbolicKernel}=await import(pathToFileURL(process.argv[2]));const manifest=JSON.parse(await readFile(process.argv[3])),{instance}=await WebAssembly.instantiate(await readFile(process.argv[4])),kernel=createSymbolicKernel({instance,manifest});await writeFile(process.argv[6],kernel.invokeValue('unicode_batch',[await readFile(process.argv[5],'utf8')]));")
 run(['node',driver,a.wasm_runtime,manifest,wasm,a.output/'cases.json',a.output/'wasm.json'])
 actual=json.loads((a.output/'wasm.json').read_text());assert actual==expected,next(((i,e,v) for i,(e,v) in enumerate(zip(expected,actual)) if e!=v),('count',len(expected),len(actual)))
 report.update(passed=True,wasmPassed=True)
finally:(a.output/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ['passed','cases','unicode']}))
