"""Actual-JS graphic dimension/vector leaf qualification; VKF assertions own checks."""
import argparse,json,subprocess,sys,hashlib
from pathlib import Path
if sys.version_info[:2]!=(3,14):raise SystemExit('Python3.14 required')
p=argparse.ArgumentParser(description=__doc__)
for k in ['compiler','output']:p.add_argument('--'+k,type=Path,required=True)
for k in ['wasm-compiler','wasm-runtime']:p.add_argument('--'+k,type=Path)
a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);root=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
report={'passed':False,'performanceValidated':False,'sourceHashes':{p.name:sha(p)for p in root.glob('document_graphics*.vkf')},'referenceSha256':sha(root.parent/'document-floats.mjs')}
def run(command,input=None):
 r=subprocess.run(list(map(str,command)),input=input,text=True,capture_output=True,timeout=240)
 if r.returncode:report['failure']={'command':list(map(str,command)),'stdout':r.stdout,'stderr':r.stderr};raise RuntimeError(r.stderr or r.stdout)
 return r.stdout
try:
 options=[{}, {'width':'100bp'}, {'height':'2cm'}, {'width':'100bp','height':'20bp'}, {'width':'100bp','height':'20bp','keepaspectratio':True}, {'width':'.5\\textwidth'}, {'height':'.25\\textheight'}, {'width':'\\linewidth'}, {'scale':'0.7'}, {'width':'3em','scale':'2'}, {'width':'not-a-length'}, {'width':'nonsensept'}, {'width':'12.5pt'}, {'height':'5ex'}, {'width':' 1.2 in '}, {'scale':'0'}, {'scale':True}, {'width':True}, {'width':'0bp'}, {'height':'-5bp'}, {'scale':0}, {'scale':False}, {'scale':None}, {'scale':'true'}, {'scale':'1e-2'}, {'scale':'+2'}, {'scale':'0x2'}, {'width':'1e2bp'}, {'width':'2..2pt'}, {'width':'...\\textwidth'}]
 assets=[{'width':120,'height':80},{'widthBp':133.4,'heightBp':72.25,'items':[{'kind':'glyph','key':'text/a','x':2,'y':-3,'sx':2,'sy':0.5,'color':[1,0,0,1]},{'kind':'rule','x':3,'y':4,'width':5,'height':1,'custom':'retained'}]}]
 cases=[{'asset':asset,'options':option,'config':{'textWidth':345,'textHeight':550,'fontSize':10},'x':17,'y':23}for asset in assets for option in options]
 (a.output/'cases.json').write_text(json.dumps(cases))
 oracle=a.output/'reference.mjs';oracle.write_text("import fs from 'node:fs';import{pathToFileURL}from'node:url';const{graphicDimensions,graphicItems}=await import(pathToFileURL(process.argv[2]));const cases=JSON.parse(fs.readFileSync(process.argv[3]));const out=cases.map(c=>{try{const dimensions=graphicDimensions(c.asset,c.options,c.config);return{dimensions,items:graphicItems(c.asset,'asset',c.x,c.y,dimensions)}}catch(e){return{diagnostics:[e.message]}}});fs.writeFileSync(process.argv[4],JSON.stringify(out));")
 run(['node',oracle,root.parent/'document-floats.mjs',a.output/'cases.json',a.output/'reference.json'])
 expected=json.loads((a.output/'reference.json').read_text());lines=[str(len(cases))]
 for index,(case,reference)in enumerate(zip(cases,expected)):
  for key in ['asset','options','config']:(a.output/f'{key}-{index}.json').write_text(json.dumps(case[key]))
  (a.output/f'expected-{index}.json').write_text(json.dumps(reference))
  lines +=[str(a.output/f'{key}-{index}.json')for key in ['asset','options','config','expected','actual']]+['true',str(case['x']),str(case['y'])]
 native=a.output/'dump';build=run([a.compiler,'-b',root/'document_graphics_dump.vkf','-o',native,'--diagnostics']);(a.output/'native-build.json').write_text(build)
 run([native],'\n'.join(lines)+'\n');report['native']=True
 if a.wasm_compiler:
  build=run([a.compiler,'-b',root/'document_graphics_kernel.vkf','-o',a.output/'kernel','--diagnostics']);(a.output/'kernel-build.json').write_text(build)
  manifest=a.output/'kernel-wasm.json';wasm=a.output/'kernel.wasm';run([a.wasm_compiler,'--typed-ir',json.loads(build)['typed_ir_path'],'--wasm',wasm,'--manifest',manifest,'--entry','check','--prune-to-entry'])
  driver=a.output/'wasm.mjs';driver.write_text("import fs from'node:fs';import{pathToFileURL}from'node:url';const[r,m,w,c,e,out]=process.argv.slice(2);const{createSymbolicKernel}=await import(pathToFileURL(r));const manifest=JSON.parse(fs.readFileSync(m)),{instance}=await WebAssembly.instantiate(fs.readFileSync(w)),kernel=createSymbolicKernel({instance,manifest}),cases=JSON.parse(fs.readFileSync(c)),expected=JSON.parse(fs.readFileSync(e));for(const[i,q]of cases.entries()){const args=[JSON.stringify(q.asset),JSON.stringify(q.options),JSON.stringify(q.config),true,q.x,q.y];const actual=kernel.invokeValue('json',args);fs.appendFileSync(out,actual+'\\n');if(!kernel.invokeValue('check',[...args,JSON.stringify(expected[i])]))throw Error('VKF graphics reference');}")
  run(['node',driver,a.wasm_runtime,manifest,wasm,a.output/'cases.json',a.output/'reference.json',a.output/'wasm.jsonl']);report.update(passed=True,wasm=True,cases=len(cases))
 else:report.update(passed=True,wasm=False,cases=len(cases))
finally:(a.output/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report.get(k)for k in ['passed','native','wasm','cases']}))
