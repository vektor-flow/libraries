"""Actual-JS hidden execution geometry/state oracle; assertions execute in VKF."""
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
 cases=[]
 sources=[
  r'\qed a',r'\pushQED{a}',r'\pushQED{a}\qedhere\qedhere\popQED',r'\pushQED{a}\popQED',
  r'\pushQED{a}\pushQED{\popQED}\popQED',r'\pushQED{\pushQED{b}}\qedhere\popQED\popQED',
  r'\pushQED{\popQED}\qedhere',r'\pushQED{\qed a}\qedhere',r'\qedhere\qedhere',
  r'\pushQED{a}x_{\qedhere}\popQED',r'\pushQED{a}x^{\qedhere}_{\qedhere}\popQED',
  r'\pushQED{a}_b^x\qedhere_b^x',r'\pushQED{a}\scriptstyle\qedhere\scriptscriptstyle\qedhere',
  r'\pushQED{a}\mathbf{\qedhere}\qedhere',r'\pushQED{\mathbf{a}}\qedhere\qedhere',
  r'\pushQED{\qed a}\mathbf{\qedhere}\qedhere',
  r'\pushQED{a}\widehat{\mathrm{A\popQED V}}',
  r'\pushQED{a}\xrightarrow[\popQED]{x\popQED b}',
  r'\pushQED{a}\left(\mathrm{A\popQED V}\middle|b\right)',
  r'\widehat{\begin{equation}x\label{eq:x}\end{equation}}+\begin{equation}y\end{equation}',
  r'\widehat{\widehat{\begin{equation}x\label{eq:x}\end{equation}}}+\begin{equation}y\end{equation}',
  r'\widehat{\begin{equation}x\end{equation}}^{\begin{equation}y\end{equation}}',
  r'\xrightarrow{\begin{equation}x\label{eq:x}\end{equation}}+\begin{equation}y\end{equation}',
  r'\left(\begin{equation}x\label{eq:x}\end{equation}\middle|b\right)+\begin{equation}y\end{equation}',
  r'\left(\frac ab\middle|\left[c\middle|d\right]\right)',
  r'\left({a\middle|b}\right)',r'\left(a\middle|b\right)^{\middle|}',
  r'\left(\frac ab\middle|\left[c\middle|\frac ab\right]\right)',
  r'\pushQED{\middle|}\left(a\middle|\qedhere\right)',
  r'\pushQED{\begin{equation}x\end{equation}}\widehat{a\qedhere}\popQED',
  r'\textcolor{red}{\pushQED{\qed a}\qedhere}',
  r'\left\alpha\frac ab\middle|x\right)^{\qedhere}',
 ]
 for source in sources:cases.append({'source':source,'packages':['amsthm','amsmath'],'displayEnvironment':True})
 cases +=[{'source':r'\qed a','packages':['amsthm'],'inline':True,'qedSymbol':r'\square'},
          {'source':r'\qed a','packages':['amsthm'],'displayEnvironment':True,'qedSymbol':r'\square'},
          {'source':r'\pushQED{\qed a}\qedhere','packages':['amsthm'],'displayEnvironment':True,'qedSymbol':r'\square'}]
 for index in [19,20,22,23,29]:cases[index]['equationStart']=9
 (a.output/'cases.json').write_text(json.dumps(cases,indent=2))
 oracle=a.output/'reference.mjs';oracle.write_text('''import fs from'node:fs';import{pathToFileURL}from'node:url';const{typeset}=await import(pathToFileURL(process.argv[2]));const amsthm=await import(pathToFileURL(process.argv[6]));const maps=JSON.parse(fs.readFileSync(process.argv[3])).maps,cases=JSON.parse(fs.readFileSync(process.argv[4]));const out=cases.map(c=>{const selected={...maps,text:{...maps.text,...(c.qedSymbol!==undefined?{qedSymbol:c.qedSymbol}:{})}};const q=typeset(c.source,selected,{...c,extensions:[amsthm],mode:c.inline?'inline':'display',nativeSemantics:true});return{width:q.width,height:q.height,depth:q.depth,items:q.items,diagnostics:q.diagnostics,nextEquationNumber:q.nextEquationNumber,equationReferences:q.equationReferences,...(q.lastRow?{lastRow:q.lastRow}:{}),...(q.paragraphNodes?{paragraphNodes:q.paragraphNodes.map(n=>n.type==='box'?{type:n.type,box:{items:n.box.items,width:n.box.width,height:n.box.height,depth:n.box.depth}}:n)}:{})};});fs.writeFileSync(process.argv[5],JSON.stringify(out));''')
 run(['node',oracle,root.parent/'typing-layout.mjs',a.metrics,a.output/'cases.json',a.output/'reference.json',root.parent/'latex-modules/packages/amsthm.mjs'])
 expected=json.loads((a.output/'reference.json').read_text())
 native_exe=a.output/'dump';nativebuild=run([a.compiler,'-b',root/'math_execution_dump.vkf','-o',native_exe,'--diagnostics']);(a.output/'native-build.json').write_text(nativebuild)
 input=[str(a.fonts),str(len(cases))]
 for i,(case,e)in enumerate(zip(cases,expected)):
  request=a.output/f'request-{i}.json';reference=a.output/f'expected-{i}.json';output=a.output/f'actual-{i}.json';request.write_text(json.dumps(case));reference.write_text(json.dumps(e));input +=[str(request),str(reference),str(output)]
 run([native_exe],'\n'.join(input)+'\n');report['native']=True
 build=run([a.compiler,'-b',root/'math_execution_kernel.vkf','-o',a.output/'kernel','--diagnostics']);(a.output/'kernel-build.json').write_text(build)
 wasm=a.output/'kernel.wasm';manifest=a.output/'kernel-wasm.json';run([a.wasm_compiler,'--typed-ir',json.loads(build)['typed_ir_path'],'--wasm',wasm,'--manifest',manifest,'--entry','execution_check','--prune-to-entry'])
 driver=a.output/'wasm.mjs';driver.write_text('''import fs from'node:fs';import{pathToFileURL}from'node:url';const[runtime,mf,wf,ff,cf,ef,out,selected]=process.argv.slice(2);const{createSymbolicKernel}=await import(pathToFileURL(runtime));const manifest=JSON.parse(fs.readFileSync(mf)),{instance}=await WebAssembly.instantiate(fs.readFileSync(wf)),kernel=createSymbolicKernel({instance,manifest}),fonts=fs.readFileSync(ff,'utf8'),cases=JSON.parse(fs.readFileSync(cf)),expected=JSON.parse(fs.readFileSync(ef));for(const[i,c]of cases.entries()){if(i!==Number(selected))continue;const actual=kernel.invokeValue('execution_json',[fonts,JSON.stringify(c)]);fs.appendFileSync(out,actual+'\\n');if(!kernel.invokeValue('__vkf_module_math_display_metrics_kernel__assert_projection',[JSON.stringify(expected[i]),actual]))throw Error('VKF reference assertion failed');}''')
 for index in range(len(cases)):
  run(['node',driver,a.wasm_runtime,manifest,wasm,a.fonts,a.output/'cases.json',a.output/'reference.json',a.output/'wasm.jsonl',index])
  (a.output/'progress.json').write_text(json.dumps({'nativeCases':len(cases),'wasmCases':index+1,'wasmFreshInstancePerCase':True}))
 report.update(wasm=True,passed=True,cases=len(cases),wasmFreshInstancePerCase=True)
finally:(a.output/'verification.json').write_text(json.dumps(report,indent=2))
print(json.dumps({k:report.get(k) for k in ['passed','cases','native','wasm']}))
