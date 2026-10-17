"""Python3.14 independent note-provider comparison with production JS text layout.

Both backends shape original source. This is component correctness evidence,
not an article geometry or complete-renderer timing benchmark.
"""
import argparse, hashlib, json, math, subprocess, sys
from pathlib import Path
if sys.version_info[:2] != (3,14): raise SystemExit('Python3.14 required')
p=argparse.ArgumentParser(description=__doc__)
for key in ['compiler','fonts','metrics','language','output']:
 p.add_argument('--'+key,type=Path,required=True)
for key in ['wasm-compiler','wasm-runtime']:
 p.add_argument('--'+key,type=Path)
p.add_argument('--source-root',type=Path)
a=p.parse_args()
if bool(a.wasm_compiler)!=bool(a.wasm_runtime):p.error('--wasm-compiler and --wasm-runtime must be supplied together')
a.output.mkdir(parents=True,exist_ok=False)
root=Path(__file__).resolve().parent;sources=a.source_root or root
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
report=dict(passed=False,completeRendererPort=False,performanceValidated=False,driverSha256=sha(Path(__file__)),sourceHashes={p.name:sha(p) for p in sources.glob('*.vkf')},compilerSha256=sha(a.compiler),wasmValidated=False,catalogSha256=sha(a.fonts),languageSha256=sha(a.language),referenceSha256=sha(root.parent/'document-text.mjs'))
if a.wasm_compiler:report.update(wasmCompilerSha256=sha(a.wasm_compiler),wasmRuntimeSha256=sha(a.wasm_runtime))
def run(command,input=None,timeout=300):
 q=subprocess.run(list(map(str,command)),input=input,text=True,capture_output=True,timeout=timeout)
 if q.returncode:
  report['failure']=dict(command=list(map(str,command)),stdout=q.stdout,stderr=q.stderr,exitCode=q.returncode)
  raise RuntimeError(q.stderr or q.stdout)
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
 elif isinstance(e,(str,bool)) or e is None:assert type(e) is type(v) and e==v,(path,e,v)
 else:
  assert isinstance(v,(int,float)) and math.isfinite(v),(path,e,v)
  error=abs(e-v);maximum=max(maximum,error);assert error<=1e-9,(path,e,v,error)
def normalize(v):
 for scene in v['scenes']:
  for k in list(scene):
   if k not in ['width','height','depth','items','lines']:del scene[k]
 return v
try:
 sources_text=['A short footnote.',r'Longer \textit{internationalization} paragraph with $x^2+y_1$ and an ordinary conclusion. '*5,r'\textit{Date}: October 16, 2026.',r'\textit{Key words and phrases.}\hspace{0.5em}Algebra.',r' Leading source space with \mbox{boxed $x+y$} words.','',r'First \\ second line with $\frac ab$ final.',r'Unknown \unknown{recovery} remains diagnosed.']
 cases=[]
 for name,opts in [('article','10pt'),('amsart','12pt')]:
  for source in sources_text:
   cases.append(dict(name=name,options=opts,hyperref=False,notes=[dict(number=1,admin=True,source=source),dict(number=2,marker=1,source=source),dict(number=3,symbol=2,source=source)]))
  for source in [r'Linked \href{https://example.test/a_b}{office} text.',r'\hyperlink{target}{Several words in a destination link.} '*5,'',r'\hypersetup{colorlinks,linkcolor=blue}\hyperlink{k}{colored link} tail.']:
   style=dict(enabled=True,borderWidth=0,colorlinks=True,ref=[0,0,1,1],cite=[0,1,0,1],url=[1,0,0,1])
   cases.append(dict(name=name,options=opts,hyperref=True,notes=[dict(number=1,admin=True,source=source),dict(number=2,marker=1,source=source,linkAppearance=style),dict(number=3,symbol=2,source=source)]))
 (a.output/'cases.json').write_text(json.dumps(cases,indent=2))
 oracle=a.output/'reference.mjs'
 oracle.write_text('''import{readFile,writeFile}from'node:fs/promises';import{pathToFileURL}from'node:url';
const[root,metrics,casefile,out]=process.argv.slice(2),{typesetDocumentText}=await import(pathToFileURL(root+'/document-text.mjs')),data=JSON.parse(await readFile(metrics)),cases=JSON.parse(await readFile(casefile)),classes={};for(const n of ['article','amsart'])classes[n]=(await import(pathToFileURL(root+'/latex-modules/classes/'+n+'.mjs'))).default;
const pt=72/72.27,results=cases.map(c=>{const config=classes[c.name].configure(c.options.split(',')),ams=c.name==='amsart',scenes=[],firstHeights=[],depths=[],reserves=[],indents=[],firsts=[],counts=[],diagnostics=[],style={enabled:c.hyperref,borderWidth:1,colorlinks:false,ref:[1,0,0,1],cite:[0,1,0,1],url:[0,1,1,1]};let first=0;
for(const note of c.notes){const indent=note.admin?config.paragraphIndent:1.8*data.documentFonts.footnote.spaces.quad,source=config.legacyEquationAnchor&&/^\\s/.test(note.source)?'\\\\mbox{}\\\\hspace{'+data.documentFonts.footnote.spaces.space+'bp}'+note.source.trimStart():note.source,
box=typesetDocumentText(source,{...data,documentLinks:note.linkAppearance??style},{legacyTextSymbols:config.legacyTextSymbols,font:'footnote',width:config.textWidth,firstIndent:indent,tolerance:9999,emergencyStretch:3*data.documentFonts.footnote.spaces.quad}),font=data.documentFonts[note.symbol?'notemark':'footnotemark'],code=note.symbol?[3,121,122,120,123,107][note.symbol-1]:String(note.marker??note.number).charCodeAt(0),height=Math.max(ams?data.documentFonts.footnote.nativeFootnoteSep:6.65*pt,(font.symbols[code]?.height??0)+data.documentFonts.footnote.markRaise),depth=Math.max(ams?.3*config.footnoteLeading:2.85*pt,box.lines.at(-1)?.depth??0),items=box.items.map(x=>({...x}));if(c.hyperref){const item=items.find(x=>x.kind!=='link');if(item)item.destinationIds=[...new Set([...(item.destinationIds??[]), 'footnote:'+note.number])];}
if(!note.admin){const marker=typesetDocumentText(note.symbol?'\\\\char'+[3,121,122,120,123,107][note.symbol-1]+' ':String(note.marker??note.number),data,{legacyTextSymbols:config.legacyTextSymbols,font:note.symbol?'notemark':'footnotemark',width:100,justify:false}),raise=ams?.9*data.documentFonts.footnote.spaces.xheight:data.documentFonts.footnote.markRaise;for(const item of marker.items)items.push({...item,x:item.x-marker.width-.5*pt,y:item.y-raise,flowLine:0});diagnostics.push(...marker.diagnostics);}
scenes.push({width:box.width,height:box.height,depth:box.depth,items,lines:box.lines});firstHeights.push(height);depths.push(depth);reserves.push(height+(config.footnoteLeading??9.5*pt)*(box.lines.length-1)+depth);indents.push(indent);firsts.push(first);counts.push(box.lines.length);first+=box.lines.length;diagnostics.push(...box.diagnostics);}
return{scenes,firstHeights,depths,reserves,indents,firsts,counts,diagnostics:[...new Set(diagnostics)],unresolved:[]};});await writeFile(out,JSON.stringify(results));''')
 run(['node',oracle,root.parent,a.metrics,a.output/'cases.json',a.output/'reference.json'])
 expected=json.loads((a.output/'reference.json').read_text())
 build=run([a.compiler,'-b',sources/'document_notes_dump.vkf','-o',a.output/'dump','--diagnostics'],timeout=600)
 (a.output/'native-build.json').write_text(build)
 metrics=json.loads(a.metrics.read_text());roles=json.dumps(list(metrics['documentFonts']))
 lines=[str(a.fonts),str(a.language),roles,str(len(cases))]
 for i,c in enumerate(cases):
  definitions=a.output/f'notes-{i}.json';definitions.write_text(json.dumps(c['notes']))
  lines += [c['name'],c['options'],str(c['hyperref']).lower(),str(definitions),str(a.output/f'native-{i}.json')]
 run([a.output/'dump'],input='\n'.join(lines)+'\n',timeout=900)
 for i,e in enumerate(expected):compare(e,normalize(json.loads((a.output/f'native-{i}.json').read_text())),f'native/{i}')
 report['nativeCasesPassed']=len(cases)
 (a.output/'verification.json').write_text(json.dumps(report,indent=2))
 if a.wasm_compiler:
  build=run([a.compiler,'-b',sources/'document_notes_kernel.vkf','-o',a.output/'kernel','--diagnostics'])
  (a.output/'kernel-build.json').write_text(build)
  wasm=a.output/'notes.wasm';manifest=a.output/'manifest.json'
  run([a.wasm_compiler,'--typed-ir',json.loads(build)['typed_ir_path'],'--wasm',wasm,'--manifest',manifest,'--entry','note_packet','--prune-to-entry'])
  driver=a.output/'wasm.mjs';driver.write_text('''import{readFile,writeFile}from'node:fs/promises';import{pathToFileURL}from'node:url';const[r,m,w,f,l,roles,c,o]=process.argv.slice(2),{createSymbolicKernel}=await import(pathToFileURL(r)),manifest=JSON.parse(await readFile(m)),{instance}=await WebAssembly.instantiate(await readFile(w)),kernel=createSymbolicKernel({instance,manifest}),fonts=await readFile(f,'utf8'),language=await readFile(l,'utf8'),cases=JSON.parse(await readFile(c)),results=[];for(const v of cases)results.push(JSON.parse(kernel.invokeValue('note_packet',[fonts,language,roles,v.name,v.options,JSON.stringify(v.notes),v.hyperref])));await writeFile(o,JSON.stringify(results));''')
  run(['node',driver,a.wasm_runtime,manifest,wasm,a.fonts,a.language,roles,a.output/'cases.json',a.output/'wasm.json'],timeout=900)
  for i,(e,v) in enumerate(zip(expected,json.loads((a.output/'wasm.json').read_text()),strict=True)):compare(e,normalize(v),f'wasm/{i}')
  report.update(wasmValidated=True,wasmCasesPassed=len(cases))
 report.update(passed=True,maxNumericErrorBp=maximum)
finally:(a.output/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='sourceHashes'}))
