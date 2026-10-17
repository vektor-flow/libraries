"""Qualify actual float assembly with provider-owned, source-independent packets."""
import argparse,json,subprocess,sys,hashlib
from pathlib import Path
if sys.version_info[:2]!=(3,14):raise SystemExit('Python3.14 required')
p=argparse.ArgumentParser(description=__doc__)
for k in ['compiler','output']:p.add_argument('--'+k,type=Path,required=True)
for k in ['wasm-compiler','wasm-runtime']:p.add_argument('--'+k,type=Path)
a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);root=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
report={'passed':False,'performanceValidated':False,'sourceHashes':{p.name:sha(p)for p in root.glob('document_float_measure*.vkf')},'referenceSha256':sha(root.parent/'document-floats.mjs'),'scope':'Actual unchanged float assembly, with generic provider-owned line packets replacing only document-text import'}
def run(command,input=None):
 r=subprocess.run(list(map(str,command)),input=input,text=True,capture_output=True,timeout=240)
 if r.returncode:report['failure']={'command':list(map(str,command)),'stdout':r.stdout,'stderr':r.stderr};raise RuntimeError(r.stderr or r.stdout)
 return r.stdout
try:
 packets=[]
 for lines in [1,2,3]:
  packets.append({'width':40,'height':8,'depth':2,'diagnostics':[], 'items':[item for i in range(lines) for item in [{'kind':'link','flowLine':i,'x':0,'y':i*14,'width':30,'height':8,'target':'label:x'},{'kind':'glyph','flowLine':i,'key':'text/a','x':i*2,'y':i*14,'destinationIds':['existing'] if i==0 else []}]],'lines':[{'height':8+i,'depth':2+i,'baseline':i*14} for i in range(lines)]})
 cases=[]
 for style in ['', 'plain']:
  for packet in packets:
   for variant in range(4):
    children=[{'kind':'caption','source':'caption','destinationIds':['new','existing']},{'kind':'image','asset':'figure.png','options':{'width': '180bp' if variant==1 else '90bp'}},{'kind':'vspace','amount':-3,'trailingLine':True},{'kind':'verbatim' if variant==2 else 'paragraph','source':'body','context':{'lineHeight':11}}]
    if variant==3:children[1]['asset']='missing.png'
    cases.append({'block':{'style':style,'blocks':children,'center':True,'placement':'htbp'},'config':{'textWidth':100,'textHeight':400,'fontSize':10},'assets':{'figure':{'width':160,'height':80}},'packets':[packet,{}, {},packet]})
 (a.output/'cases.json').write_text(json.dumps(cases))
 actual=(root.parent/'document-floats.mjs').read_text().replace("import {markDestination} from './document-links.mjs';","import {markDestination} from "+json.dumps((root.parent/'document-links.mjs').as_uri())+";").replace("import {typesetDocumentText} from './document-text.mjs';","function typesetDocumentText(source){return structuredClone(globalThis.__floatPackets[source]);}")
 (a.output/'actual-reference.mjs').write_text(actual)
 oracle=a.output/'reference.mjs';oracle.write_text("import fs from 'node:fs';import{pathToFileURL}from'node:url';const{measureDocumentFloat}=await import(pathToFileURL(process.argv[2]));const cases=JSON.parse(fs.readFileSync(process.argv[3]));const out=cases.map(c=>{globalThis.__floatPackets={};c.block.blocks.forEach((b,i)=>{if(b.source)globalThis.__floatPackets[b.source]=c.packets[i]});return measureDocumentFloat(c.block,{config:c.config,data:{documentFonts:{roman:{spaces:{quad:10}},mono:{spaces:{quad:10}}}},assets:c.assets,resolveText:x=>x,packages:[],extensions:[]})});fs.writeFileSync(process.argv[4],JSON.stringify(out));")
 run(['node',oracle,a.output/'actual-reference.mjs',a.output/'cases.json',a.output/'reference.json']);expected=json.loads((a.output/'reference.json').read_text());lines=[str(len(cases))]
 for index,(case,e)in enumerate(zip(cases,expected)):
  (a.output/f'request-{index}.json').write_text(json.dumps(case));(a.output/f'expected-{index}.json').write_text(json.dumps(e));lines +=[str(a.output/f'{key}-{index}.json')for key in ['request','expected','actual']]
 native=a.output/'dump';build=run([a.compiler,'-b',root/'document_float_measure_dump.vkf','-o',native,'--diagnostics']);(a.output/'native-build.json').write_text(build);run([native],'\n'.join(lines)+'\n');report['native']=True
 if a.wasm_compiler:
  build=run([a.compiler,'-b',root/'document_float_measure_kernel.vkf','-o',a.output/'kernel','--diagnostics']);(a.output/'kernel-build.json').write_text(build);wasm=a.output/'kernel.wasm';manifest=a.output/'kernel-wasm.json';run([a.wasm_compiler,'--typed-ir',json.loads(build)['typed_ir_path'],'--wasm',wasm,'--manifest',manifest,'--entry','check','--prune-to-entry'])
  driver=a.output/'wasm.mjs';driver.write_text("import fs from'node:fs';import{pathToFileURL}from'node:url';const[r,m,w,c,e,out]=process.argv.slice(2);const{createSymbolicKernel}=await import(pathToFileURL(r));const manifest=JSON.parse(fs.readFileSync(m)),{instance}=await WebAssembly.instantiate(fs.readFileSync(w)),kernel=createSymbolicKernel({instance,manifest}),cases=JSON.parse(fs.readFileSync(c)),expected=JSON.parse(fs.readFileSync(e));for(const[i,q]of cases.entries()){const actual=kernel.invokeValue('json',[JSON.stringify(q)]);fs.appendFileSync(out,actual+'\\n');if(!kernel.invokeValue('check',[JSON.stringify(q),JSON.stringify(expected[i])]))throw Error('VKF float reference');}")
  run(['node',driver,a.wasm_runtime,manifest,wasm,a.output/'cases.json',a.output/'reference.json',a.output/'wasm.jsonl']);report.update(passed=True,wasm=True,cases=len(cases))
 else:report.update(passed=True,wasm=False,cases=len(cases))
finally:(a.output/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report.get(k)for k in ['passed','native','wasm','cases']}))
