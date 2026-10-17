"""Real VKF paragraphs inside generic floats, checked against actual JS."""
import argparse,json,subprocess,sys,hashlib
from pathlib import Path
if sys.version_info[:2]!=(3,14):raise SystemExit('Python3.14 required')
p=argparse.ArgumentParser(description=__doc__)
for k in ['compiler','fonts','metrics','language','output']:p.add_argument('--'+k,type=Path,required=True)
a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);root=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
report={'passed':False,'performanceValidated':False,'sourceHashes':{p.name:sha(p)for p in root.glob('*.vkf')},'referenceSha256':sha(root.parent/'document-floats.mjs'),'compilerSha256':sha(a.compiler),'fontsSha256':sha(a.fonts),'languageSha256':sha(a.language)}
def run(command,input=None,timeout=900):
 r=subprocess.run(list(map(str,command)),input=input,text=True,capture_output=True,timeout=timeout)
 if r.returncode:report['failure']={'command':list(map(str,command)),'stdout':r.stdout,'stderr':r.stderr};raise RuntimeError(r.stderr or r.stdout)
 return r.stdout
try:
 metrics=json.loads(a.metrics.read_text());ams=bool(metrics.get('fontProfile'));klass='amsart'if ams else'article';opts='12pt'if ams else'10pt'
 cases=[]
 sources=[('caption','Figure 1: A short caption.'),('caption','Figure 1: Mathematics $a+\\frac{b}{x}$ and styled \\textbf{words}.'),('caption','Caption words with mathematics $x+y$ that wrap onto several lines. '*8),('paragraph','A native paragraph with $a+b$ and \\emph{optical text}. '*4),('verbatim','literal $x$ \\alpha {x} line two'),('caption','Figure 1: A link \\href{https://example.com/a}{caption words}.'),('caption','A URL \\url{https://example.com/a-b?c=d}.'),('caption','An unknown \\unknowncommand and words.')]
 for style in ['', 'plain']:
  for kind,source in sources:
   cases.append({'class':klass,'classOptions':opts,'block':{'kind':'figure','style':style,'center':True,'placement':'tbp','blocks':[{'kind':'image','asset':'figure.png','options':{'width':'45bp'}},{'kind':kind,'source':source,'destinationIds':['label:caption']},{'kind':'vspace','amount':-2}]},'assets':{'figure':{'widthBp':90,'heightBp':60,'items':[{'kind':'rule','x':1,'y':2,'width':40,'height':20}]}}})
 (a.output/'cases-input.json').write_text(json.dumps(cases))
 oracle=a.output/'reference.mjs';oracle.write_text("import fs from'node:fs';import{pathToFileURL}from'node:url';const{measureDocumentFloat}=await import(pathToFileURL(process.argv[2]));const{typesetDocument}=await import(pathToFileURL(process.argv[3]));const data=JSON.parse(fs.readFileSync(process.argv[4])),cases=JSON.parse(fs.readFileSync(process.argv[5]));const results=[];for(const c of cases){const doc='\\\\documentclass['+c.classOptions+']{'+c.class+'}\\\\usepackage{graphicx,hyperref,amsmath}\\\\begin{document}\\\\end{document}';const config=(await typesetDocument(doc,data)).config;config.textWidth=130;c.config=config;results.push(measureDocumentFloat(c.block,{config,data,assets:c.assets,resolveText:x=>x,packages:['graphicx','hyperref','amsmath'],extensions:[]}))};fs.writeFileSync(process.argv[6],JSON.stringify(cases));fs.writeFileSync(process.argv[7],JSON.stringify(results));")
 run(['node',oracle,root.parent/'document-floats.mjs',root.parent/'document-layout.mjs',a.metrics,a.output/'cases-input.json',a.output/'cases.json',a.output/'reference.json'])
 cases=json.loads((a.output/'cases.json').read_text());expected=json.loads((a.output/'reference.json').read_text())
 entries=[str(a.fonts),str(a.language),json.dumps(list(metrics['documentFonts'])),str(len(cases))]
 for index,(case,e)in enumerate(zip(cases,expected)):
  (a.output/f'request-{index}.json').write_text(json.dumps(case));(a.output/f'expected-{index}.json').write_text(json.dumps(e));entries +=[str(a.output/f'{key}-{index}.json')for key in ['request','expected','actual']]
 native=a.output/'dump';build=run([a.compiler,'-b',root/'document_materialize_floats_dump.vkf','-o',native,'--diagnostics']);(a.output/'native-build.json').write_text(build);run([native],'\n'.join(entries)+'\n');report.update(native=True,passed=True,cases=len(cases))
finally:(a.output/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report.get(k)for k in ['passed','native','cases']}))
