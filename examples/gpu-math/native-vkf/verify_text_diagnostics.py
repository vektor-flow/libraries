"""Python3.14 focused actual-JS source-order diagnostics and geometry reference."""
import argparse,hashlib,json,math,subprocess,sys
from pathlib import Path
assert sys.version_info[:2]==(3,14)
p=argparse.ArgumentParser(description=__doc__)
for name in ['compiler','wasm-compiler','wasm-runtime','fonts','metrics','language','output']:p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);root=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
report={'passed':False,'completeRendererPort':False,'sourceHashes':{p.name:sha(p) for pattern in ['text_parser*.vkf','text_paragraph*.vkf','text_inline*.vkf','paragraph_inline*.vkf'] for p in root.glob(pattern)}}
def run(command,input=None,timeout=300):
 q=subprocess.run(list(map(str,command)),text=True,input=input,capture_output=True,timeout=timeout)
 assert q.returncode==0,(command,q.stdout,q.stderr)
 return q.stdout
maximum=0
def compare(e,v,path=''):
 global maximum
 if isinstance(e,dict):
  assert e.keys()==v.keys(),(path,e.keys(),v.keys())
  for k in e:compare(e[k],v[k],path+'/'+k)
 elif isinstance(e,list):
  assert len(e)==len(v),(path,len(e),len(v))
  for i,(x,y) in enumerate(zip(e,v)):compare(x,y,path+'/'+str(i))
 elif isinstance(e,(str,bool)) or e is None:assert type(e)is type(v) and e==v,(path,e,v)
 else:
  d=abs(e-v);assert math.isfinite(v) and d<1e-9,(path,e,v);maximum=max(maximum,d)
def geometry(q):
 assert q.pop('loweringComplete') and q.pop('pending')==[] and q.pop('sceneCount')==0,q
 assert q.pop('complete')==(not q['diagnostics']),q
 return q
try:
 metrics=json.loads(a.metrics.read_text());roles=json.dumps(list(metrics['documentFonts']));optical=bool(metrics.get('fontProfile'))
 cases=[dict(source=source,role=role) for role in ['roman','footnote'] for source in ['☃ \\unknown tail', '\\unknown ☃ tail','☃ \\textit{\\unknown tail} ☃','\\unknown ☃ \\unknown']]
 (a.output/'cases.json').write_text(json.dumps(cases)+'\n')
 oracle=a.output/'reference.mjs';oracle.write_text("import{readFile,writeFile}from'node:fs/promises';import{pathToFileURL}from'node:url';const{typesetDocumentText}=await import(pathToFileURL(process.argv[2]));const data=JSON.parse(await readFile(process.argv[3])),cases=JSON.parse(await readFile(process.argv[4]));await writeFile(process.argv[5],JSON.stringify(cases.map(c=>{const q=typesetDocumentText(c.source,data,{font:c.role,width:100,justify:false,hyphens:false});return{width:q.width,height:q.height,depth:q.depth,diagnostics:q.diagnostics,items:q.items.map(({key,x,y,flowLine})=>({key,x,y,flowLine})),lines:q.lines};})));" )
 run(['node',oracle,root.parent/'document-text.mjs',a.metrics,a.output/'cases.json',a.output/'reference.json'])
 expected=json.loads((a.output/'reference.json').read_text());native=a.output/'dump'
 build=run([a.compiler,'-b',root/'text_paragraph_dump.vkf','-o',native,'--diagnostics']);(a.output/'native-build.json').write_text(build)
 entries=[str(a.fonts),str(a.language),roles,str(optical).lower(),str(len(cases))]
 for i,c in enumerate(cases):
  source=a.output/f'input-{i}.tex';source.write_text(c['source']);entries.extend([str(source),c['role'],'100','0','false','false','200','0','false','true','false','1',str(a.output/f'native-{i}.json')])
 run([native],input='\n'.join(entries)+'\n')
 for i,e in enumerate(expected):compare(e,geometry(json.loads((a.output/f'native-{i}.json').read_text())),f'native/{i}')
 report.update(nativePassed=True,nativeCases=len(cases));(a.output/'native-verification.json').write_text(json.dumps(report,indent=2)+'\n')
 build=run([a.compiler,'-b',root/'text_paragraph_kernel.vkf','-o',a.output/'kernel','--diagnostics']);(a.output/'kernel-build.json').write_text(build)
 manifest=a.output/'manifest.json';wasm=a.output/'kernel.wasm';run([a.wasm_compiler,'--typed-ir',json.loads(build)['typed_ir_path'],'--wasm',wasm,'--manifest',manifest,'--entry','paragraph_packet','--prune-to-entry'])
 driver=a.output/'run-wasm.mjs';driver.write_text("import{readFile,writeFile,appendFile}from'node:fs/promises';import{pathToFileURL}from'node:url';const{createSymbolicKernel}=await import(pathToFileURL(process.argv[2]));const manifest=JSON.parse(await readFile(process.argv[3])),{instance}=await WebAssembly.instantiate(await readFile(process.argv[4])),kernel=createSymbolicKernel({instance,manifest}),fonts=await readFile(process.argv[5],'utf8'),language=await readFile(process.argv[6],'utf8'),metrics=JSON.parse(await readFile(process.argv[7])),roles=JSON.stringify(Object.keys(metrics.documentFonts)),cases=JSON.parse(await readFile(process.argv[8]));await writeFile(process.argv[9],'');for(let i=0;i<cases.length;i++){const c=cases[i];const q=kernel.invokeValue('paragraph_packet',[fonts,language,c.source,c.role,roles,!!metrics.fontProfile,100,0,false,false,200,0,false,true,false,1]);await appendFile(process.argv[9],q+'\\n');await writeFile(process.argv[10],JSON.stringify({completed:i+1,total:cases.length}));}")
 run(['node',driver,a.wasm_runtime,manifest,wasm,a.fonts,a.language,a.metrics,a.output/'cases.json',a.output/'wasm-results.jsonl',a.output/'progress.json'],timeout=300)
 actual=[json.loads(line) for line in (a.output/'wasm-results.jsonl').read_text().splitlines()];assert len(actual)==len(expected)
 for i,(e,v) in enumerate(zip(expected,actual)):compare(e,geometry(v),f'wasm/{i}')
 report.update(passed=True,wasmPassed=True,wasmCases=len(cases),maximumAbsoluteError=maximum)
finally:(a.output/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ['passed','nativeCases','wasmCases','maximumAbsoluteError']}))
