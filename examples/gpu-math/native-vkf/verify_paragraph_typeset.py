"""Python3.14 independent production-JS paragraph geometry oracle.

Scope: decoded literal words and whitespace; no TeX grammar. JS atoms is omitted
explicitly because it measures lazily visited shaping work, not rendered glyphs.
Glyphs, every line field, overall geometry and source diagnostics remain strict.
"""
import argparse, hashlib, json, math, re, subprocess, sys
from pathlib import Path
if sys.version_info[:2] != (3,14): raise SystemExit('Python3.14 required')
p=argparse.ArgumentParser(description=__doc__)
for key in ['compiler','wasm-compiler','wasm-runtime','fonts','metrics','language','output']:
 p.add_argument('--'+key,type=Path,required=True)
p.add_argument("--case-filter", help="Optional source regex for a focused gate")
a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
root=Path(__file__).resolve().parent
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
report={'driverSha256':sha(Path(__file__)),'caseFilter':a.case_filter,'passed':False,'completeRendererPort':False,'performanceValidated':False,'excludedInternalTelemetry':['JS atoms; VKF measurement_work differs for eager partial-range measurements'],'sourceHashes':{s.name:sha(s) for s in root.glob('paragraph*.vkf')},'compilerSha256':sha(a.compiler),'wasmCompilerSha256':sha(a.wasm_compiler),'wasmRuntimeSha256':sha(a.wasm_runtime),'catalogSha256':sha(a.fonts),'languageSha256':sha(a.language),'referenceSha256':sha(root.parent/'document-text.mjs')}
def run(command,input=None,timeout=300):
 q=subprocess.run(list(map(str,command)),input=input,text=True,capture_output=True,timeout=timeout)
 if q.returncode:
  report['failure']={'command':list(map(str,command)),'stdout':q.stdout,'stderr':q.stderr,'exitCode':q.returncode}
  raise RuntimeError(q.stderr or q.stdout)
 return q.stdout
maximum=0
def compare(e,v,path=''):
 global maximum
 if isinstance(e,dict):
  assert e.keys()==v.keys(),(path,list(e),list(v))
  for k in e:compare(e[k],v[k],path+'/'+k)
 elif isinstance(e,list):
  assert len(e)==len(v),(path,len(e),len(v))
  for i,(x,y) in enumerate(zip(e,v)):compare(x,y,path+'/'+str(i))
 elif isinstance(e,(str,bool)) or e is None:assert type(e) is type(v) and e==v,(path,e,v)
 else:
  assert isinstance(v,(int,float)) and math.isfinite(v),(path,e,v)
  error=abs(e-v);maximum=max(maximum,error)
  assert error<=1e-9,(path,e,v,error)
try:
 cases=[]
 texts=['','   \t\n','A','  A V  ','office affinity difficult efficient','The quick brown fox jumps over the lazy dog.','Representation internationalization implementation configuration.','The mathematical rendering algorithm determines paragraph geometry.','AVATAR Toffee office! Next? End.','ABC. Next word. A. Next.','``Quoted words\'\' --- and -- more text.','hyphenation-related non-isomorphic mathematics','word- another word','A☃V☃ unsupported 😀 characters','line\nbreak\t collapsed\r\nwhitespace','before\u00a0after\u2009thin\u3000space']
 for role in ['roman','italic','mono']:
  for text in texts:
   for width in [45,120]:
    cases.append(dict(source=text,role=role,width=width,indent=0,justify=True,hyphens=True,tolerance=200,emergency=0,preserve=False,sentence=True,french=False,scale=1))
 for opts in [dict(indent=8),dict(justify=False),dict(hyphens=False),dict(emergency=10),dict(preserve=True),dict(sentence=False),dict(french=True),dict(scale=2)]:
  for text in ['  Word. Next? Text.  ','affinity implementation representation internationalization']:
   c=dict(source=text,role='roman',width=55,indent=0,justify=True,hyphens=True,tolerance=200,emergency=0,preserve=False,sentence=True,french=False,scale=1);c.update(opts);cases.append(c)
 cases.append(dict(source='A A WWWWWWWWWWWWWWWWWWWWWWWW',role='roman',width=18,indent=0,justify=True,hyphens=False,tolerance=200,emergency=0,preserve=False,sentence=True,french=False,scale=1))
 for width,indent,scale in [(55.25,2.5,0.75),(60.5,1.25,1.5)]:
  cases.append(dict(source='Fractional paragraph controls. Next sentence with affinity.',role='roman',width=width,indent=indent,justify=True,hyphens=True,tolerance=200,emergency=3.25,preserve=False,sentence=True,french=False,scale=scale))
 if a.case_filter:cases=[c for c in cases if re.search(a.case_filter,c['source'])]
 assert cases, 'No matching cases'
 (a.output/'cases.json').write_text(json.dumps(cases,ensure_ascii=True,indent=2)+'\n')
 oracle=a.output/'reference.mjs';oracle.write_text('''import{readFile,writeFile}from'node:fs/promises';import{pathToFileURL}from'node:url';const{typesetDocumentText}=await import(pathToFileURL(process.argv[2]));const data=JSON.parse(await readFile(process.argv[3])),cases=JSON.parse(await readFile(process.argv[4]));const out=cases.map(c=>{const q=typesetDocumentText(c.source,data,{font:c.role,width:c.width,firstIndent:c.indent,justify:c.justify,hyphens:c.hyphens,tolerance:c.tolerance,emergencyStretch:c.emergency,preserveTrailingSpace:c.preserve,sentenceSpacing:c.sentence,frenchSpacing:c.french,spaceScale:c.scale});return{width:q.width,height:q.height,depth:q.depth,diagnostics:q.diagnostics,items:q.items.map(({key,x,y,flowLine})=>({key,x,y,flowLine})),lines:q.lines};});await writeFile(process.argv[5],JSON.stringify(out));''')
 run(['node',oracle,root.parent/'document-text.mjs',a.metrics,a.output/'cases.json',a.output/'reference.json'])
 expected=json.loads((a.output/'reference.json').read_text())
 native=a.output/'dump';build=run([a.compiler,'-b',root/'paragraph_typeset_dump.vkf','-o',native,'--diagnostics']);(a.output/'native-build.json').write_text(build)
 entries=[str(a.fonts),str(a.language),str(len(cases))]
 for i,c in enumerate(cases):
  src=a.output/f'input-{i}.txt';src.write_text(c['source'])
  entries.extend([str(src),c['role'],str(c['width']),str(c['indent']),str(c['justify']).lower(),str(c['hyphens']).lower(),str(c['tolerance']),str(c['emergency']),str(c['preserve']).lower(),str(c['sentence']).lower(),str(c['french']).lower(),str(c['scale']),str(a.output/f'native-{i}.json')])
 run([native],input='\n'.join(entries)+'\n',timeout=600)
 for i,e in enumerate(expected):compare(e,json.loads((a.output/f'native-{i}.json').read_text()),f'native/{i}')
 report.update(nativePassed=True,nativeCases=len(cases),nativeMaximumError=maximum)
 (a.output/'native-verification.json').write_text(json.dumps(report,indent=2)+'\n')
 build=run([a.compiler,'-b',root/'paragraph_typeset_kernel.vkf','-o',a.output/'kernel','--diagnostics']);(a.output/'kernel-build.json').write_text(build)
 wasm=a.output/'kernel.wasm';manifest=a.output/'manifest.json';run([a.wasm_compiler,'--typed-ir',json.loads(build)['typed_ir_path'],'--wasm',wasm,'--manifest',manifest,'--entry','paragraph_packet','--prune-to-entry'])
 driver=a.output/'run-wasm.mjs';driver.write_text('''import{readFile,writeFile,appendFile}from'node:fs/promises';import{pathToFileURL}from'node:url';const{createSymbolicKernel}=await import(pathToFileURL(process.argv[2]));const manifest=JSON.parse(await readFile(process.argv[3]));const{instance}=await WebAssembly.instantiate(await readFile(process.argv[4]));const kernel=createSymbolicKernel({instance,manifest}),fonts=await readFile(process.argv[5],'utf8'),language=await readFile(process.argv[6],'utf8'),cases=JSON.parse(await readFile(process.argv[7]));await writeFile(process.argv[8],'');for(let i=0;i<cases.length;i++){const c=cases[i],q=JSON.parse(kernel.invokeValue('paragraph_packet',[fonts,language,c.source,c.role,c.width,c.indent,c.justify,c.hyphens,c.tolerance,c.emergency,c.preserve,c.sentence,c.french,c.scale]));await appendFile(process.argv[8],JSON.stringify(q)+'\\n');await writeFile(process.argv[9],JSON.stringify({completed:i+1,total:cases.length}));}''')
 run(['node',driver,a.wasm_runtime,manifest,wasm,a.fonts,a.language,a.output/'cases.json',a.output/'wasm-results.jsonl',a.output/'progress.json'],timeout=900)
 actual=[json.loads(line) for line in (a.output/'wasm-results.jsonl').read_text().splitlines()]
 assert len(actual)==len(expected)
 for i,(e,v) in enumerate(zip(expected,actual)):compare(e,v,f'wasm/{i}')
 report.update(passed=True,wasmPassed=True,wasmCases=len(cases),maximumAbsoluteError=maximum)
finally:(a.output/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ['passed','nativeCases','wasmCases','maximumAbsoluteError']}))
