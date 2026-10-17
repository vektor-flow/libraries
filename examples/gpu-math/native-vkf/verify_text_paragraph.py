"""Python3.14 actual production JS mixed-role TeX paragraph geometry oracle.

Strict glyphs, geometry, line fields and source diagnostics. Public JS atoms is
excluded explicitly: VKF eagerly measures partial-word corrections. This gate
requires complete=true and no unresolved scenes for its ordinary inline scope.
"""
import argparse, hashlib, json, math, re, subprocess, sys
from pathlib import Path
if sys.version_info[:2] != (3,14): raise SystemExit('Python3.14 required')
p=argparse.ArgumentParser(description=__doc__)
for key in ['compiler','wasm-compiler','wasm-runtime','fonts','metrics','language','output']:
 p.add_argument('--'+key,type=Path,required=True)
p.add_argument("--resume-existing",action="store_true",help="Reference verification only: verify immutable input hashes and reuse existing native stage after an interrupted or corrected oracle")
p.add_argument("--source-root",type=Path,help="Frozen VKF module closure for concurrent development")
p.add_argument("--case-filter", help="Optional source regex for a focused gate")
p.add_argument("--math-source",action="store_true",help="Connected source paragraph with native math nodes and retained scenes")
p.add_argument("--link-source",action="store_true",help="Connected PDF link scopes, colors and source anchors")
p.add_argument("--hyperref-disabled",action="store_true")
p.add_argument("--bib-url",action="store_true")
a=p.parse_args();
if a.link_source:a.math_source=True
a.output.mkdir(parents=True,exist_ok=a.resume_existing)
root=Path(__file__).resolve().parent
source_root=a.source_root or root
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
link_style={'enabled':not a.hyperref_disabled,'borderWidth':1,'colorlinks':False,'ref':[1,0,0,1],'cite':[0,1,0,1],'url':[0,1,1,1]} if a.link_source else {}
report={'driverSha256':sha(Path(__file__)),'caseFilter':a.case_filter,'mathSource':a.math_source,'passed':False,'completeRendererPort':False,'performanceValidated':False,'excludedInternalTelemetry':['JS atoms; VKF measurement_work differs for eager partial-range measurements'],'sourceHashes':{s.name:sha(s) for pattern in (['*.vkf'] if a.math_source else ['paragraph_inline*.vkf','text_paragraph*.vkf','text_inline*.vkf','text_parser*.vkf']) for s in source_root.glob(pattern)},'compilerSha256':sha(a.compiler),'wasmCompilerSha256':sha(a.wasm_compiler),'wasmRuntimeSha256':sha(a.wasm_runtime),'catalogSha256':sha(a.fonts),'languageSha256':sha(a.language),'referenceSha256':sha(root.parent/'document-text.mjs')}
if a.resume_existing:
 previous=json.loads((a.output/'verification.json').read_text())
 for key in ['sourceHashes','compilerSha256','wasmCompilerSha256','wasmRuntimeSha256','catalogSha256','languageSha256','referenceSha256']:
  assert previous[key]==report[key],('Cannot resume changed reference inputs',key)
 assert (a.output/'native-build.json').is_file() and (a.output/'dump').is_file()
 backups=sorted(a.output.glob('verification-before-resume-*.json'))
 (a.output/f'verification-before-resume-{len(backups)}.json').write_text(json.dumps(previous,indent=2)+'\n')
 report['resumedVerificationOnly']=True
 report['resumedDriverSha256']=previous['driverSha256']
 report['nativeBinarySha256']=sha(a.output/'dump')
 old_cases=json.loads((a.output/'cases.json').read_text())
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
 texts=['','  A V  ','office affinity difficult efficient',r'{a {b} c} tail',r'\textbf{bold \emph{italic}} roman',r'\emph{emph \emph{upright}}',r'\textit{office} after. Next',r'\textit{office} after, more',r'\textit{office}. after',r'\textit{f }\textrm{after} next',r'\textrm{a}\textnormal{b}\textit{c}\texttt{d}\textsf{e}\textsc{f}\textsl{g}\textup{h}',r'{\rmfamily a \bfseries b \itshape c \ttfamily d \sffamily e \slshape f \scshape g} h',r'\rm a\bf b\it c\tt d\sc g\em h',r'\protect\relax\ignorespaces a',r'a~b\ c\  d',r'\@a\,b\quad c\qquad d\newblock e\italiccorrection f\/g',r'\i\j\lq\lq word\rq\rq end\lq x\rq',r'\textbackslash path',r'Representation \textit{internationalization implementation} configuration.',r'word- \textbf{hyphenation-related non-isomorphic} mathematics',r'first \\ forced \textit{next}',r'\unknown{recovery} end','raw%percent line','A☃V☃ unsupported 😀 characters',r'word\, following more text',r'\textit{word}\, following more text']
 if a.math_source:
  texts=[r'Word.\hspace{1pt} next sentence.',r'Word.\char65 next sentence.',r'Word.\footnotemark{2} next sentence.',r'Word.\symbolfootnotemark{9} next sentence.',r"Word.\'{e} next \TeX \LaTeX \ldots tail.",r'Word.\hspace{bad} next sentence.',r'Word.\textbullet next \% tail.',r'Word.\mbox{a\TeX b} next.',r'Before \mbox{a $x+y$ b} after.',r'Before \mbox{a \mbox{b $x^2$} c} tail.',r'\textit{A \mbox{office ffi} word}',r'A \mbox{} B',r'A \mbox{a \unknown b} B',r'Before $a+b=c$ after.',r'Before \(a+b=c\) after.',r'Words $x^2+y_1$ words.',
   r'Words $\frac ab+\sqrt{x}$ after.',r'\textit{Italic $x+y$ after} upright.',
   r'Before $a\quad b~c\ x$ after.',r'Before $a\kern-1pt b$ following more text.',
   r'First $a=b=c=d$ followed by representation implementation.',r'$x+y$ $a+b$ tail.',
   r'$\mathbf{ab}+\text{ffi}$ following words.',r'Words $\color{red}a+b$ after.',
   r'Words $\begin{matrix}a&b\\x&y\end{matrix}$ after.',r'Empty $$ next.',
   r'Words $\tag{A}a+b$ after.',r'Words $\unknown+x$ after.',r'$\displaystyle\sum_a^b+x$ after.',
   r'Before $a+b$\, following more text.',r'Words $\left(\frac ab\right)=x$ words.']
 if a.link_source:
  texts=[r'A \hyperlink{target}{office affinity implementation} tail.',
   r'A \href{https://example.test/a\%20b?q=x\&z=y}{office $x+y$ text} tail.',
   r'A \hyperref[eq:x]{long representation implementation} tail.',
   r'A \documentlinkspan{cite}{label%3Ax}{office affinity implementation} tail.',
   r'\documentanchor{label%3Ax}A V\documentanchor{trailing}',
   r'A \hypertarget{key}{office affinity} after.',
   r'A \mbox{\hyperlink{k}{word $x+y$}} after.',
   r'A \documentlink{ref}{office $x+y$}{label%3Ax} after.',
   r'A \documentlink{cite}{office}{} after.',
   r'\hypersetup{colorlinks,allcolors=blue}A \hyperlink{k}{office $x+y$ text} tail.',
   r'\hypersetup{hidelinks}A \hyperlink{k}{office affinity} tail.',
   r'A \hyperlink{outer}{one \hyperlink{inner}{two} three} tail.',
   r'A \hyperlink{outer}{\hyperlink{inner}{}} tail.',
   r'\hypersetup{colorlinks,linkcolor=red}A \hyperlink{outer}{one \hypersetup{linkcolor=blue}\hyperlink{inner}{two} three} tail.',
   r'\hypersetup{colorlinks}A \documentlink{ref}{\href{https://example.test}{office}}{label%3Ax} after.',
   r'A \hyperlink{k}{☃ \hyperlink{inner}{word} \unknown} tail.',
   r'\documentanchor{empty}',r'  \documentanchor{empty}  ',
   r'\lowercase{OFFICE AFFINITY} next.',r'\lowercase{ΟΣ İ ΣΑ ΑΣ} next.',
   r'Word.\hyperlink{k}{} next.',r'Word.\hypersetup{unknown,linkcolor=bad} next.',
   r'A \url{https://example.test/a_b?x=1&y=2} tail.',
   r'A \nolinkurl{https://example.test/a~b} tail.',
   r'A \hyperlink{outer}{one \url{https://example.test/a_b} more} tail.',
   r'Word.\url{} next.',r'A \url{longunbreakablecomponentunfinished',
   r'A \url{https://example.test/ø😀} tail.',r'A \url{.#_-+} tail.']
 for role in ['roman','footnote']:
  for text in texts:
   for width in [45,120]:
    cases.append(dict(source=text,role=role,width=width,indent=0,justify=True,hyphens=True,tolerance=200,emergency=0,preserve=False,sentence=True,french=False,scale=1))
 for opts in [dict(indent=8),dict(justify=False),dict(hyphens=False),dict(emergency=10),dict(preserve=True),dict(sentence=False),dict(french=True),dict(scale=0.75)]:
  c=dict(source=r'  Word. \textit{affinity implementation} representation. Next?  ',role='roman',width=55,indent=0,justify=True,hyphens=True,tolerance=200,emergency=0,preserve=False,sentence=True,french=False,scale=1);c.update(opts);cases.append(c)
 if a.case_filter:cases=[c for c in cases if re.search(a.case_filter,c['source'])]
 assert cases, 'No matching cases'
 if a.resume_existing:assert cases==old_cases,'Cannot resume changed source cases'
 (a.output/'cases.json').write_text(json.dumps(cases,ensure_ascii=True,indent=2)+'\n')
 oracle=a.output/'reference.mjs';oracle.write_text('''import{readFile,writeFile}from'node:fs/promises';import{pathToFileURL}from'node:url';const{typesetDocumentText}=await import(pathToFileURL(process.argv[2]));const data=JSON.parse(await readFile(process.argv[3])),cases=JSON.parse(await readFile(process.argv[4]));const linkStyle=JSON.parse(process.argv[6]);if(Object.keys(linkStyle).length)data.documentLinks=linkStyle;const out=cases.map(c=>{const q=typesetDocumentText(c.source,data,{font:c.role,width:c.width,firstIndent:c.indent,justify:c.justify,hyphens:c.hyphens,tolerance:c.tolerance,emergencyStretch:c.emergency,preserveTrailingSpace:c.preserve,sentenceSpacing:c.sentence,frenchSpacing:c.french,spaceScale:c.scale,bibUrl:process.argv[7]==='true'});return{width:q.width,height:q.height,depth:q.depth,diagnostics:q.diagnostics,items:'''+("q.items" if a.math_source else "q.items.map(({key,x,y,flowLine})=>({key,x,y,flowLine}))")+''',lines:q.lines,...(q.destinations?{destinations:q.destinations}:{})};});await writeFile(process.argv[5],JSON.stringify(out));''')
 run(['node',oracle,root.parent/'document-text.mjs',a.metrics,a.output/'cases.json',a.output/'reference.json',json.dumps(link_style),str(a.bib_url).lower()])
 expected=json.loads((a.output/'reference.json').read_text())
 metrics=json.loads(a.metrics.read_text());roles=json.dumps(list(metrics['documentFonts']));optical=bool(metrics.get('fontProfile'))
 def geometry(q):
  assert q.pop('loweringComplete') and q.pop('pending')==[],q
  scenes=q.pop('sceneCount')
  assert a.math_source or scenes==0,q
  assert q.pop('complete')==(not q['diagnostics']),q
  return q
 native=a.output/'dump'
 if not a.resume_existing:
  build=run([a.compiler,'-b',source_root/('text_source_paragraph_dump.vkf' if a.math_source else 'text_paragraph_dump.vkf'),'-o',native,'--diagnostics']);(a.output/'native-build.json').write_text(build)
  entries=[str(a.fonts),str(a.language),roles,str(optical).lower()]
  if a.math_source:entries.extend([json.dumps(link_style),str(a.link_source and not a.hyperref_disabled).lower(),str(a.bib_url).lower()])
  entries.append(str(len(cases)))
  for i,c in enumerate(cases):
   src=a.output/f'input-{i}.txt';src.write_text(c['source'])
   entries.extend([str(src),c['role'],str(c['width']),str(c['indent']),str(c['justify']).lower(),str(c['hyphens']).lower(),str(c['tolerance']),str(c['emergency']),str(c['preserve']).lower(),str(c['sentence']).lower(),str(c['french']).lower(),str(c['scale']),str(a.output/f'native-{i}.json')])
  run([native],input='\n'.join(entries)+'\n',timeout=600)
 for i,e in enumerate(expected):compare(e,geometry(json.loads((a.output/f'native-{i}.json').read_text())),f'native/{i}')
 report.update(nativePassed=True,nativeCases=len(cases),nativeMaximumError=maximum)
 (a.output/'native-verification.json').write_text(json.dumps(report,indent=2)+'\n')
 build=run([a.compiler,'-b',source_root/('text_source_paragraph_kernel.vkf' if a.math_source else 'text_paragraph_kernel.vkf'),'-o',a.output/'kernel','--diagnostics']);(a.output/'kernel-build.json').write_text(build)
 wasm=a.output/'kernel.wasm';manifest=a.output/'manifest.json';run([a.wasm_compiler,'--typed-ir',json.loads(build)['typed_ir_path'],'--wasm',wasm,'--manifest',manifest,'--entry','paragraph_packet','--prune-to-entry'])
 driver=a.output/'run-wasm.mjs';driver.write_text('''import{readFile,writeFile,appendFile}from'node:fs/promises';import{pathToFileURL}from'node:url';const{createSymbolicKernel}=await import(pathToFileURL(process.argv[2]));const manifest=JSON.parse(await readFile(process.argv[3]));const{instance}=await WebAssembly.instantiate(await readFile(process.argv[4]));const kernel=createSymbolicKernel({instance,manifest}),fonts=await readFile(process.argv[5],'utf8'),language=await readFile(process.argv[6],'utf8'),metrics=JSON.parse(await readFile(process.argv[10])),roles=JSON.stringify(process.argv[13]==='true'?{roles:Object.keys(metrics.documentFonts),documentLinks:JSON.parse(process.argv[11]),hyperref:process.argv[12]==='true',bibUrl:process.argv[14]==='true'}:Object.keys(metrics.documentFonts)),cases=JSON.parse(await readFile(process.argv[7]));await writeFile(process.argv[8],'');for(let i=0;i<cases.length;i++){const c=cases[i],q=JSON.parse(kernel.invokeValue('paragraph_packet',[fonts,language,c.source,c.role,roles,!!metrics.fontProfile,c.width,c.indent,c.justify,c.hyphens,c.tolerance,c.emergency,c.preserve,c.sentence,c.french,c.scale]));await appendFile(process.argv[8],JSON.stringify(q)+'\\n');await writeFile(process.argv[9],JSON.stringify({completed:i+1,total:cases.length}));}''')
 run(['node',driver,a.wasm_runtime,manifest,wasm,a.fonts,a.language,a.output/'cases.json',a.output/'wasm-results.jsonl',a.output/'progress.json',a.metrics,json.dumps(link_style),str(a.link_source and not a.hyperref_disabled).lower(),str(a.math_source).lower(),str(a.bib_url).lower()],timeout=900)
 actual=[json.loads(line) for line in (a.output/'wasm-results.jsonl').read_text().splitlines()]
 assert len(actual)==len(expected)
 for i,(e,v) in enumerate(zip(expected,actual)):compare(e,geometry(v),f'wasm/{i}')
 report.update(passed=True,wasmPassed=True,wasmCases=len(cases),maximumAbsoluteError=maximum)
finally:(a.output/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ['passed','nativeCases','wasmCases','maximumAbsoluteError']}))
