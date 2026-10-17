"""Native source presentation versus actual JS document-layout trace.

Checks title thanks ordering, native-width author separation, AMS end matter
and scoped source link policy. Source-less control blocks normalize to "".
Scene/page geometry and performance are outside this source-presentation gate.
"""
import argparse,hashlib,json,math,re,subprocess,sys
from pathlib import Path
if sys.version_info[:2]!=(3,14):raise SystemExit('Python3.14 required')
p=argparse.ArgumentParser(description=__doc__)
for k in ['compiler','fonts','metrics','language','source-root','output']:p.add_argument('--'+k,type=Path,required=True)
a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);root=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
report=dict(passed=False,completeRendererPort=False,performanceValidated=False,wasmValidated=False,compilerSha256=sha(a.compiler),driverSha256=sha(Path(__file__)),sourceHashes={f.name:sha(f) for f in a.source_root.glob('*.vkf')},referenceSha256=sha(root.parent/'document-layout.mjs'),catalogSha256=sha(a.fonts),metricsSha256=sha(a.metrics),languageSha256=sha(a.language))
def run(cmd,input=None,timeout=300):
 q=subprocess.run(list(map(str,cmd)),input=input,capture_output=True,text=True,timeout=timeout)
 if q.returncode:
  report['failure']=dict(command=list(map(str,cmd)),stdout=q.stdout,stderr=q.stderr,exitCode=q.returncode);raise RuntimeError(q.stderr or q.stdout)
 return q.stdout
maximum=0
metrics=json.loads(a.metrics.read_text());footquad=metrics['documentFonts']['footnote']['spaces']['quad']
def text(s):
 # Source representation can use equivalent bp/em glue; compare values in bp
 # independently, keeping all surrounding text and command order strict.
 return re.split(r'\\hspace\{([+-]?[0-9.]+)(bp|em)\}',s)
def compare(x,y,path=''):
 global maximum
 if isinstance(x,dict):
  assert x.keys()==y.keys(),(path,x.keys(),y.keys())
  for k in x:compare(x[k],y[k],path+'/'+k)
 elif isinstance(x,list):
  assert len(x)==len(y),(path,len(x),len(y))
  for i,(e,v) in enumerate(zip(x,y)):compare(e,v,path+'/'+str(i))
 elif isinstance(x,str):
  ex=text(x);vy=text(y);assert len(ex)==len(vy),(path,x,y)
  for i in range(0,len(ex),3):
   assert ex[i]==vy[i],(path,x,y)
   if i+2<len(ex):
    en=float(ex[i+1])*(footquad if ex[i+2]=='em' else 1);vn=float(vy[i+1])*(footquad if vy[i+2]=='em' else 1);delta=abs(en-vn);maximum=max(maximum,delta);assert delta<1e-9,(path,en,vn)
 else:assert x==y,(path,x,y)
try:
 authors=[' Alice ','Alice \\and Bob',r'\textit{Alice}\and Bob',r'Alice\thanks{First grant.}\and Bob\thanks{Second grant.}',r'{A\and B}\and Carol',r'Alice\and Bob\and Carol',r'$x+y$\and\textit{Bob}',r'Alice\thanks{Grant {nested} source.}\and\mbox{Bob}']
 cases=[r'\documentclass{article}\title{A title}\author{'+author+r'}\begin{document}\maketitle Text\footnote{Body note.} end.\end{document}' for author in authors]
 cases += [r'\documentclass[12pt]{amsart}\title{A title}\author{Alice}\address{Institute, Main Street}\email{a@example.test}\subjclass{Primary 20J06}\keywords{Algebra, homology}\begin{document}\maketitle Text.\end{document}',r'\documentclass[12pt]{amsart}\title{Title}\author{Alice}\begin{document}\date{Today}\subjclass[2010]{Primary 16E40}\keywords{Algebra}\address{Street 2}\email{b@example.test}\maketitle Text\footnote{First body note.}\end{document}']
 for body in [r'\hypersetup{colorlinks,linkcolor=blue}First\footnote{Blue}.\par Second.',r'First \hypersetup{colorlinks,linkcolor=blue}\footnote{Blue} rest.\par Second.',r'\hypersetup{linkcolor=blue}\begin{quote}\hypersetup{linkcolor=green}Inside\footnote{Green}.\end{quote}After\footnote{Blue}.',r'\begin{quote}One \hypersetup{colorlinks,linkcolor=green}\footnote{Green}.\par Two.\end{quote}After\footnote{Red}.',r'\begin{proof}\hypersetup{colorlinks,linkcolor=green}Proof text\footnote{Green}.\end{proof}After.',r'\hypersetup{linkcolor=blue}\maketitle Text\footnote{Blue}.']:
  cases.append(r'\documentclass{article}\usepackage{hyperref,amsthm}\hypersetup{urlcolor=magenta}\author{Alice\thanks{A grant.}\and Bob}\begin{document}'+body+r'\end{document}')
 (a.output/'cases.json').write_text(json.dumps(cases,indent=2))
 oracle=a.output/'reference.mjs';oracle.write_text('''import{readFile,writeFile}from'node:fs/promises';import{pathToFileURL}from'node:url';const[module,metrics,cases,out]=process.argv.slice(2),{typesetDocument}=await import(pathToFileURL(module)),data=JSON.parse(await readFile(metrics)),sources=JSON.parse(await readFile(cases)),results=[];for(const source of sources){const q=await typesetDocument(source,data,{buildContext:{trace:true}});results.push({blocks:q.trace.blocks.map(({kind,source,context})=>({kind,source:source??'',linkAppearance:context.linkAppearance,...(context.nextLinkAppearance?{nextLinkAppearance:context.nextLinkAppearance}:{})})),footnotes:q.footnotes,unresolved:[]});}await writeFile(out,JSON.stringify(results));''')
 run(['node',oracle,root.parent/'document-layout.mjs',a.metrics,a.output/'cases.json',a.output/'reference.json'])
 expected=json.loads((a.output/'reference.json').read_text())
 build=run([a.compiler,'-b',a.source_root/'document_notes_present_dump.vkf','-o',a.output/'dump','--diagnostics'],timeout=600)
 (a.output/'native-build.json').write_text(build)
 lines=[str(a.fonts),str(a.language),json.dumps(list(metrics['documentFonts'])),str(len(cases))]
 for i,source in enumerate(cases):
  file=a.output/f'case-{i}.tex';file.write_text(source);lines += [str(file),str(a.output/f'native-{i}.json')]
 run([a.output/'dump'],input='\n'.join(lines)+'\n',timeout=900)
 for i,e in enumerate(expected):compare(e,json.loads((a.output/f'native-{i}.json').read_text()),f'native/{i}')
 report.update(passed=True,nativeCasesPassed=len(cases),maxSourceGlueDifferenceBp=maximum)
finally:(a.output/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='sourceHashes'}))
