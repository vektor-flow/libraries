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
report=dict(compilerSha256=sha(a.compiler),passed=False,completeRendererPort=False,performanceValidated=False,sourceHashes={p.name:sha(p) for g in ['bibtex*.vkf','bibliography*.vkf'] for p in root.glob(g)},referenceHash=sha(root.parent/'bibtex.mjs'))
def run(args,input=None,timeout=240):
 r=subprocess.run(list(map(str,args)),input=input,text=True,capture_output=True,timeout=timeout)
 if r.returncode:raise RuntimeError(r.stdout+'\n'+r.stderr)
 return r.stdout
try:
 native=a.output/'dump'
 build=run([a.compiler,'-b',root/'bibliography_dump.vkf','-o',native,'--diagnostics']);(a.output/'native-build.json').write_text(build)
 cases=[]
 def case(**v):cases.append(v)
 for source in [r'@string{venue="Journal " # {of Tests}} @book{parent, publisher={Press},year=2024} @article(child, AUTHOR="Smith, Jo and {A and B Foundation}",title={A {Nested} Title},journal=VENUE,crossref={parent})',
 '@article{x,title=undefined,month=JAN,year=2020}', '@comment{a {b} c} @preamble{"a"} @misc{k, title={x}}',
 '@book{x,title={x}', '@book{x,title="x}', '@book{x,title={a}}@book{x,title={b}}','@book{x,crossref={y}}@book{y,crossref={x}}','@book{x,crossref={missing}}',
 '@string{A={abc}} @string{b=A # {d}} @misc{t,title=b,year=2025}', '@book{a,title={one},title={two}}',
 '@book{x,invalid}', '@book{x,title=?}', '@string{x ? "oops"}', '@preamble{{x}} @online{ok,title={hello}}']:
  case(operation='parse',source=source)
 for source in ['Smith, Jo and {A and B Foundation}','John von Neumann','Charles Louis Xavier Joseph de la Vallée Poussin','von Last, Jr, First','Ada Able and Bob Zed and Cee Last','{Corporate and Sons}',r'Jo {de la} Last',"Garc\\'{i}a, Jo", 'One, Two, Three, Four']:
  case(operation='names',source=source)
 fields=dict(author='Smith, Jo and Able, Ada',title='A {Nested} Title',year='2020',journal='Journal',volume='4',number='2',pages='12 - 14',publisher='Press',location='Town',edition='2nd',series='Series',note='Note',doi='10.123/test',url='https://example.org')
 for kind in ['article','incollection','inproceedings','book','misc','unpublished','online','phdthesis']:
  for f in [fields,{},dict(title='Bare',date='2023-01',pages='S1-S4',url='https://test'),dict(title='Empty year',year='',date='2023-01')]:case(operation='format',type=kind,fields=f)
 db='@book{a,author={Zed, Ada},title={First},year={2020}}@book{z,author={Able, Bea},title={Last},year={2021}}'
 for style in ['numeric','alphabetic','unsupported']:
  for sorting in ['none','nty','nyt','anyt','unsupported']:
   case(source=r'\addbibresource{db}\cite[see][p.~2]{z,a}\printbibliography',entry='papers/main.tex',files={'papers/db.bib':db},options=['style='+style,'sorting='+sorting])
 literal='é😀 '+r'\verb|\bibliography{missing}\cite{missing}\printbibliography| \begin{verbatim}\bibliography{missing}\nocite{*}\end{verbatim}'+'\n% '+r'\bibliography{missing}'+'\n'+r'\\bibliography{missing} \url{https://example.org/\cite{missing}}'
 case(source=literal+r'\bibliography{ok}\cite{x}\printbibliography',files={'ok.bib':'@book{x,author={Smith, Jo},title={A},year={2020}}'})
 case(source=r'\bibliography{missing}\cite{unknown}\printbibliography[heading=none]',options=['style=unsupported'])
 collision=''.join('@book{'+k+',author={Able, Ada},title={'+k+'},year={2020}}' for k in ['b','a','c'])
 case(source=r'\bibliography{r}\nocite{*}\printbibliography',files={'r.bib':collision},options=['style=alphabetic','sorting=nyt'])
 case(source=r'\bibliography{r}\nocite{*}\printbibliography',files={'r.bib':collision},options=['style=alphabetic','sorting=none'],labelWidths={'Abl20a':1,'Abl20b':3,'Abl20c':2})
 case(source=r'\bibliography{r}\cite{a}\printbibliography',files={'r.bib':{'text':collision}},options=[])
 for names in [['Abel, Ada','de la Cruz, Bea','Dole, Cee'],['Éclair, Zoë','Eclair, Zoe','Æble, Œdi','Aeble, Oedi','ßmith, Jo'],['Able, Jo','A-ble, Jo','A ble, Jo'],['A$ble, Jo','A+ble, Jo','Able, Jo']]:
  values=''.join('@book{'+str(i)+',author={'+name+'},title={A title},year={2024}}' for i,name in enumerate(names))
  case(source=r'\bibliography{r}\nocite{*}\printbibliography',files={'r.bib':values},options=['style=alphabetic','sorting=nyt'])
 case(source=r'\bibliography{r}\nocite{*}\printbibliography',files={'r.bib':'@book{a,author={Abel, Ada},year={2024}}@book{b,author={Éclair, Bea},year={2024}}'},options=['style=alphabetic','sorting=none'])
 manual=r'\begin{thebibliography}{MANUAL}\bibitem[M]{m}Manual.\end{thebibliography}'
 generated=r'\printbibliography'
 masked=r'\verb|\printbibliography \begin{thebibliography}{LITERAL}| \url{https://x/\printbibliography} \begin{verbatim}\printbibliography\end{verbatim}'+'\n% '+r'\printbibliography'+'\n'+r'\\printbibliography'
 for fragment in [manual+generated,generated+manual,generated+manual+generated,manual,masked+generated,generated+masked+manual+generated,manual+generated+manual]:
  case(operation='measured',source=r'\bibliography{r}\nocite{*}'+fragment,files={'r.bib':db},options=['sorting=none'],labelWidths={'1':1,'2':3},widest='2')
 nested_database=r'@book{a,title={\begin{thebibliography}{INNER}Nested\end{thebibliography}},year={2020}}@book{b,title={Ordinary},year={2021}}'
 case(operation='measured',source=r'\bibliography{r}\nocite{*}'+generated+manual+generated,files={'r.bib':nested_database},options=['sorting=none'],labelWidths={'1':1,'2':3},widest='2')
 native_fixture=json.loads((root.parent/'tests/biblatex-native.json').read_text())
 case(source=r'\bibliography{refs}\cite{'+','.join(native_fixture['labels'])+r'}\printbibliography',files={'refs.bib':native_fixture['database']},options=['style=alphabetic','sorting=nyt'])
 original=Path('/home/viktor/Projects/Cuvami/staging/artifacts/gpu-math/20261016/vkf-port/parallel-document-blocks-40-01/files.json')
 if original.exists():
  fs=json.loads(original.read_text())
  case(source=r'\bibliography{references}\nocite{*}\printbibliography',files=fs,options=['style=alphabetic','sorting=nyt'])
  case(source=(original.parent/'source.tex').read_text(),files=fs,options=['style=alphabetic','sorting=nyt'])
 (a.output/'cases.json').write_text(json.dumps(cases))
 oracle=a.output/'reference.mjs'
 oracle.write_text("""import{readFile,writeFile}from'node:fs/promises';
import{parseBibtex,bibtexNames,formatBiblatexEntry,prepareBiblatex}from"""+repr((root.parent/'bibtex.mjs').as_uri())+""";
const[c,o]=process.argv.slice(2);const results=JSON.parse(await readFile(c)).map(x=>{try{
 if(x.operation==='parse'){const p=parseBibtex(x.source);return{entries:[...p.entries.values()],strings:Object.fromEntries(p.strings),diagnostics:p.diagnostics,error:'',valid:true};}
 if(x.operation==='names')return{names:bibtexNames(x.source),error:''};
 if(x.operation==='format')return{text:formatBiblatexEntry({type:x.type,fields:x.fields}),error:''};
 const p=prepareBiblatex(x.source,{files:x.files,entry:x.entry,options:x.options,measureLabel:x.labelWidths?(s=>x.labelWidths[s]??s.length):null});return{...p,labels:Object.fromEntries(p.labels),complete:!p.diagnostics.length};
 }catch(e){return{error:e.message};}});await writeFile(o,JSON.stringify(results));""")
 run(['node',oracle,a.output/'cases.json',a.output/'reference.json'])
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
  build=run([a.compiler,'-b',root/'bibliography_kernel.vkf','-o',a.output/'kernel','--diagnostics']);(a.output/'kernel-build.json').write_text(build)
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
