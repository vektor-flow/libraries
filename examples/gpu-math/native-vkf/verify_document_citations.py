"""Python3.14 independent actual-JS bibliography reference, native + WASM."""
import argparse,json,subprocess,hashlib,sys
from pathlib import Path
assert sys.version_info[:2]==(3,14)
p=argparse.ArgumentParser()
for n in ['compiler','output']:p.add_argument('--'+n,type=Path,required=True)
for n in ['wasm-compiler','wasm-runtime']:p.add_argument('--'+n,type=Path)
a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
root=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
report=dict(compilerSha256=sha(a.compiler),passed=False,completeRendererPort=False,performanceValidated=False,sourceHashes={p.name:sha(p) for p in root.glob("document_citations*.vkf")},referenceHash=sha(root.parent/'document-layout.mjs'))
def run(args,input=None,timeout=240):
 r=subprocess.run(list(map(str,args)),input=input,text=True,capture_output=True,timeout=timeout)
 if r.returncode:raise RuntimeError(r.stdout+'\n'+r.stderr)
 return r.stdout
try:
 native=a.output/'dump'
 build=run([a.compiler,'-b',root/'document_citations_dump.vkf','-o',native,'--diagnostics']);(a.output/'native-build.json').write_text(build)
 cases=[]
 for source in [r'word \cite{a,b} tail',r'\cite[see][p.~2]{b,a}',r'\parencite[p.~4]{a}',r'\autocite*{unknown}',r'\textcite{a}',r'\cite{}',r'\cite',r'\cite[x',r'\cite[a][b][c]{a}',r'\cite*word \cite{a}',r'\citecommand{a} \cite@{b}',r'\cite{a,a, b , unknown}',r'\verb|\cite{a}| \url{https://x/\cite{b}} \href{\cite{a}}{\cite{b}} \cite{a}',r'\\cite{a} \cite{a}',r'\begin{verbatim}\cite{a}\end{verbatim} \cite{b}',r'\cite{é中}',r'\cite[]{a}',r'\cite[][]{a}',r'\cite[before][]{a}',r'\cite[before][after]{a}']:
  for opts in [{},{'biblatex':True,'separator':'; '},{'links':True},{'legacy':True,'links':True}]:
   cases.append(dict(source=source,labels={'a':'Abl20','b':'B22','é中':'Ü9'},**opts))
 for source in [r'\bibitem{a}A \bibitem[x]{b}B \bibitem{c}C',r'\bibitem[]{a} \bibitem{a} \bibitem{b}',r'\bibitem[x]{a} \bibitem{new}',r'\bibitem {a} \bibitem [x] {b}',r'\bibitem{a{b}} \bibitem[x[y]{b}',r'\bibitem[open{b} \bibitem{c}']:
  cases.append(dict(operation='collect',source=source,labels={'initial':'I0'}))
 (a.output/'cases.json').write_text(json.dumps(cases))
 oracle=a.output/'reference.mjs'
 oracle.write_text("""import{readFile,writeFile}from'node:fs/promises';
import{maskTexLiterals}from"""+repr((root.parent/'latex-modules/core/literals.mjs').as_uri())+""";
import{encodeDestination}from"""+repr((root.parent/'document-links.mjs').as_uri())+r""";
const[c,o,layout]=process.argv.slice(2),code=await readFile(layout,'utf8');
const groupCode=code.slice(code.indexOf('function group('),code.indexOf('function length('));
const resolverCode=code.slice(code.indexOf('function resolveCitations('),code.indexOf(' const resolveRefs='));
const call=new Function('text','maskTexLiterals','bibliography','diagnostics','modules','config','documentLinks','encodeDestination',groupCode+resolverCode+';return resolveCitations(text);');
const results=JSON.parse(await readFile(c)).map(x=>{const bibliography=new Map(Object.entries(x.labels??{}));
if(x.operation==='collect'){const body=x.source;for(const m of body.matchAll(/\\bibitem\s*(?:\[([^\]]*)\])?\s*\{([^}]+)\}/g))bibliography.set(m[2],m[1]??String(bibliography.size+1));return Object.fromEntries(bibliography);}
const diagnostics=[],source=call(x.source,maskTexLiterals,bibliography,diagnostics,{packages:new Map(x.biblatex?[['biblatex',{}]]:[])},{legacyEquationAnchor:!!x.legacy,citationSeparator:x.separator},{enabled:!!x.links},encodeDestination);return{source,diagnostics};});await writeFile(o,JSON.stringify(results));""")
 run(['node',oracle,a.output/'cases.json',a.output/'reference.json',root.parent/'document-layout.mjs'])
 expected=json.loads((a.output/'reference.json').read_text())
 lines=[str(len(cases))]
 for i,c in enumerate(cases):lines += [json.dumps(c),str(a.output/f'native-{i}.json')]
 run([native],input='\n'.join(lines)+'\n')
 def compare(e,v,path):
  if e.get('error'):
   assert v.get('error')==e['error'] or (e['error'] in v.get('diagnostics',[])),(path,e,v)
  else:
   if 'plain' in v:v.pop('plain')
   assert e==v,(path,e,v)
 for i,e in enumerate(expected):compare(e,json.loads((a.output/f'native-{i}.json').read_text()),f'native/{i}')
 report['nativeCasesPassed']=len(cases)
 if a.wasm_compiler:
  if not a.wasm_runtime:raise ValueError('--wasm-runtime is required with --wasm-compiler')
  build=run([a.compiler,'-b',root/'document_citations_kernel.vkf','-o',a.output/'kernel','--diagnostics']);(a.output/'kernel-build.json').write_text(build)
  wasm,manifest=a.output/'bibliography.wasm',a.output/'manifest.json'
  run([a.wasm_compiler,'--typed-ir',json.loads(build)['typed_ir_path'],'--wasm',wasm,'--manifest',manifest,'--entry','packet','--prune-to-entry'])
  driver=a.output/'wasm.mjs'
  driver.write_text("""import{readFile,writeFile}from'node:fs/promises';import{pathToFileURL}from'node:url';
 const[r,m,w,c,o]=process.argv.slice(2),{createSymbolicKernel}=await import(pathToFileURL(r)),manifest=JSON.parse(await readFile(m)),{instance}=await WebAssembly.instantiate(await readFile(w)),k=createSymbolicKernel({instance,manifest});
 await writeFile(o,JSON.stringify(JSON.parse(await readFile(c)).map(x=>JSON.parse(k.invokeValue('packet',[JSON.stringify(x)])))));""")
  run(['node',driver,a.wasm_runtime,manifest,wasm,a.output/'cases.json',a.output/'wasm-results.json'])
  actual=json.loads((a.output/'wasm-results.json').read_text());assert len(actual)==len(expected)
  for i,(e,v) in enumerate(zip(expected,actual)):compare(e,v,f'wasm/{i}')
 report['backends']=['native']+(['wasm'] if a.wasm_compiler else [])
 report.update(passed=True,casesPerBackend=len(cases))
finally:(a.output/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
