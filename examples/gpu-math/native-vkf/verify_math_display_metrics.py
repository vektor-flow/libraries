"""Focused actual-JS geometry oracle; all assertions execute in shared VKF."""
import argparse,json,subprocess,hashlib,sys
from pathlib import Path
if sys.version_info[:2]!=(3,14):raise SystemExit('Python3.14 required')
p=argparse.ArgumentParser(description=__doc__)
for k in ['compiler','wasm-compiler','wasm-runtime','fonts','metrics','output']:p.add_argument('--'+k,type=Path,required=True)
a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);root=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
report={'passed':False,'performanceValidated':False,'referenceSha256':sha(root.parent/'typing-layout.mjs'),'compilerSha256':sha(a.compiler),'wasmCompilerSha256':sha(a.wasm_compiler),'sourceHashes':{p.name:sha(p) for p in root.glob('*.vkf')}}
def run(cmd,input=None,timeout=240):
 r=subprocess.run(list(map(str,cmd)),input=input,text=True,capture_output=True,timeout=timeout)
 if r.returncode:
  report['failure']={'command':list(map(str,cmd)),'stdout':r.stdout,'stderr':r.stderr};raise RuntimeError(r.stderr or r.stdout)
 return r.stdout
try:
 metrics=json.loads(a.metrics.read_text());base=metrics['documentFonts']['roman']['size'];pt=72/72.27
 native={'baseline':14*pt,'jot':3.5*pt,'lineSkip':pt,'lineSkipLimit':pt}
 cases=[]
 for source in [r'\begin{aligned}a&=b\\c&=d\end{aligned}',r'\begin{align}a&=b\\c&=d\end{align}',r'\begin{align*}a&=b\\c&=d\end{align*}',r'\begin{alignat}{2}a&=b&c&=d\\a&=b\end{alignat}',r'\begin{gather}a=b\\c=d\end{gather}',r'\begin{multline}a+b\\c+d\end{multline}',r'\begin{eqnarray}a&=&b\\c&=&d\end{eqnarray}',r'\begin{matrix}a&b\\c&d\end{matrix}',r'\left(\begin{aligned}a&=\frac ab\\c&=d\end{aligned}\right)']:
  cases.append({'source':source,'mathMetrics':native,'displayEnvironment':True})
 for width in [0.001,25,1000]:cases.append({'source':'a+b+c+d','displayWidth':width})
 cases.append({'source':r'a+b\tag{A}','displayWidth':0.001})
 cases.append({'source':r'\begin{equation}+a=b\end{equation}','legacyEquationAnchor':True})
 cases.append({'source':r'\begin{equation*}+a=b\end{equation*}','legacyEquationAnchor':True})
 cases.append({'source':r'\begin{aligned}a&=b\\c&=d\end{aligned}','mathMetrics':{},'inline':True})
 (a.output/'cases.json').write_text(json.dumps(cases,indent=2))
 oracle=a.output/'reference.mjs';oracle.write_text('''import fs from'node:fs';import{pathToFileURL}from'node:url';const{typeset}=await import(pathToFileURL(process.argv[2]));const maps=JSON.parse(fs.readFileSync(process.argv[3])).maps,cases=JSON.parse(fs.readFileSync(process.argv[4]));const out=cases.map(c=>{const q=typeset(c.source,maps,{...c,mode:c.inline?'inline':'display',nativeSemantics:true});return{width:q.width,height:q.height,depth:q.depth,items:q.items,diagnostics:q.diagnostics,nextEquationNumber:q.nextEquationNumber,equationReferences:q.equationReferences,...(q.lastRow?{lastRow:q.lastRow}:{}),...(q.paragraphNodes?{paragraphNodes:q.paragraphNodes.map(n=>n.type==='box'?{type:n.type,box:{items:n.box.items,width:n.box.width,height:n.box.height,depth:n.box.depth}}:n)}:{})};});fs.writeFileSync(process.argv[5],JSON.stringify(out));''')
 run(['node',oracle,root.parent/'typing-layout.mjs',a.metrics,a.output/'cases.json',a.output/'reference.json'])
 expected=json.loads((a.output/'reference.json').read_text())
 native_exe=a.output/'dump';nativebuild=run([a.compiler,'-b',root/'math_display_metrics_dump.vkf','-o',native_exe,'--diagnostics']);(a.output/'native-build.json').write_text(nativebuild)
 input=[str(a.fonts),str(len(cases))]
 for i,(case,e)in enumerate(zip(cases,expected)):
  request=a.output/f'request-{i}.json';reference=a.output/f'expected-{i}.json';output=a.output/f'actual-{i}.json';request.write_text(json.dumps(case));reference.write_text(json.dumps(e));input +=[str(request),str(reference),str(output)]
 run([native_exe],'\n'.join(input)+'\n');report['native']=True
 build=run([a.compiler,'-b',root/'math_display_metrics_kernel.vkf','-o',a.output/'kernel','--diagnostics']);(a.output/'kernel-build.json').write_text(build)
 wasm=a.output/'kernel.wasm';manifest=a.output/'kernel-wasm.json';run([a.wasm_compiler,'--typed-ir',json.loads(build)['typed_ir_path'],'--wasm',wasm,'--manifest',manifest,'--entry','display_metrics_check','--prune-to-entry'])
 driver=a.output/'wasm.mjs';driver.write_text('''import fs from'node:fs';import{pathToFileURL}from'node:url';const[runtime,mf,wf,ff,cf,ef,out]=process.argv.slice(2);const{createSymbolicKernel}=await import(pathToFileURL(runtime));const manifest=JSON.parse(fs.readFileSync(mf)),{instance}=await WebAssembly.instantiate(fs.readFileSync(wf)),kernel=createSymbolicKernel({instance,manifest}),fonts=fs.readFileSync(ff,'utf8'),cases=JSON.parse(fs.readFileSync(cf)),expected=JSON.parse(fs.readFileSync(ef));for(const[i,c]of cases.entries()){const actual=kernel.invokeValue('display_metrics_json',[fonts,JSON.stringify(c)]);fs.appendFileSync(out,actual+'\\n');if(!kernel.invokeValue('assert_projection',[JSON.stringify(expected[i]),actual]))throw Error('VKF reference assertion failed');}''')
 run(['node',driver,a.wasm_runtime,manifest,wasm,a.fonts,a.output/'cases.json',a.output/'reference.json',a.output/'wasm.jsonl']);report.update(wasm=True,passed=True,cases=len(cases))
finally:(a.output/'verification.json').write_text(json.dumps(report,indent=2))
print(json.dumps({k:report.get(k) for k in ['passed','cases','native','wasm']}))
