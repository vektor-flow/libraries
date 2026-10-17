"""Python 3.14 development driver for native/WASM math-box geometry.

The reference executes the existing typing-layout atom function with probe boxes.
Instrumentation only exposes that private function and suppresses outer fraction
delimiters to inspect the fraction body; it does not replace its arithmetic.
Requests are written after compilation and include same-process edits/reverts.
"""
import argparse
import hashlib
import json
import math
import random
import subprocess
import sys
import time
from pathlib import Path

if sys.version_info[:2] != (3,14):
    raise SystemExit('Reference driver requires Python 3.14')
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--compiler',type=Path,required=True)
p.add_argument('--wasm-compiler',type=Path,required=True)
p.add_argument('--wasm-runtime',type=Path,required=True)
p.add_argument('--fonts',type=Path,required=True)
p.add_argument('--metrics',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
root=Path(__file__).resolve().parent
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
report={'componentOnly':True,'completeRendererPort':False,'passed':False,
        'sourceHashes':{f.name:sha(f)for f in root.glob('*.vkf')},
        'catalogSha256':sha(a.fonts/'catalog.vkfont'),'metricsSha256':sha(a.metrics),
        'compilerSha256':sha(a.compiler),'wasmCompilerSha256':sha(a.wasm_compiler),
        'runtimeSha256':sha(a.wasm_runtime),'referenceSha256':sha(root.parent/'typing-layout.mjs')}

def run(command,input=None,timeout=240):
    result=subprocess.run(list(map(str,command)),input=input,text=True,capture_output=True,timeout=timeout)
    if result.returncode:
        report['failure']={'command':list(map(str,command)),'stdout':result.stdout,'stderr':result.stderr}
        raise RuntimeError(result.stderr or result.stdout)
    return result.stdout

try:
    native=a.output/'geometry_dump'
    diagnostics=run([a.compiler,'-b',root/'math_geometry_dump.vkf','-o',native,'--diagnostics'])
    (a.output/'native-build.json').write_text(diagnostics)
    diagnostics=run([a.compiler,'-b',root/'math_geometry_kernel.vkf','-o',a.output/'geometry_kernel','--diagnostics'])
    (a.output/'kernel-build.json').write_text(diagnostics)
    wasm=a.output/'geometry.wasm';manifest=a.output/'geometry-wasm.json'
    run([a.wasm_compiler,'--typed-ir',json.loads(diagnostics)['typed_ir_path'],'--wasm',wasm,
         '--manifest',manifest,'--entry','geometry','--prune-to-entry'])
    report['nativeSha256']=sha(native);report['wasmSha256']=sha(wasm)
    # Compile before constructing unknown requests. No generated-result tables.
    rng=random.Random(826403)
    size=lambda:{'width':rng.uniform(0,100),'height':rng.uniform(0,45),'depth':rng.uniform(0,20)}
    cases=[]
    for style in range(4):
        for bold in [False,True]:
            for rule in [0,None,0.01,0.4,20]:
                for delimited in [False,True]:
                    q={'kind':'fraction','style':style,'bold':bold,'delimited':delimited,'n':size(),'d':size()}
                    if rule is not None:q['rule']=rule
                    cases.append(q)
            for cramped in [False,True]:
                for character in [False,True]:
                    for limits in [False,True]:
                        for has_sup,has_sub in [(True,False),(False,True),(True,True)]:
                            for arrow in [False,True]:
                                cases.append({'kind':'scripts','style':style,'bold':bold,'cramped':cramped,
                                    'body':{**size(),'italic':rng.uniform(-3,5),'character':character},
                                    'sup':size(),'sub':size(),'hasSup':has_sup,'hasSub':has_sub,
                                    'limits':limits,'arrow':arrow,'leftArrow':rng.choice([False,True])})
    delimiters=['(',')','[',']',r'\lfloor',r'\rfloor',r'\lceil',r'\rceil',r'\lbrace',r'\rbrace',
                r'\langle',r'\rangle','|',r'\Vert','/',r'\backslash',r'\uparrow',r'\downarrow',
                r'\updownarrow',r'\Uparrow',r'\Downarrow',r'\Updownarrow','.',r'\{',r'\}',r'\vert',r'\lvert',r'\rvert',r'\|']
    for style in range(4):
        for bold in [False,True]:
            for required in [0,8,17,40,81,200]:
                for token in delimiters:
                    cases.append({'kind':'delimiter','style':style,'bold':bold,'token':token,'required':required})
                for token in ['@ext:0','@ext:8','@ext:12','@ext:13','@ext:112']:
                    cases.append({'kind':'assemble','style':style,'bold':bold,'token':token,'required':required})
    for style in range(4):
        for font in ['', 'mathrm','mathbf','mathit','mathsf','mathtt','mathfrak','mathcal','mathscr','mathbb','mathnormal','boldsymbol']:
            for token in ['a','A','z','0','9','+',r'\sum',r'\alpha','@latexsym:'+r'\Box','@missing-glyph','漢']:
                cases.append({'kind':'glyph','style':style,'font':font,'token':token})
    cases.extend([cases[0],{**cases[0],'n':{'width':123,'height':0,'depth':0}},cases[0]])
    (a.output/'cases.json').write_text(json.dumps(cases))
    reference=(root.parent/'typing-layout.mjs').read_text()
    for relative in ['./qed-box.mjs','./document-links.mjs','./draft-parser.mjs']:
        reference=reference.replace(repr(relative),repr((root.parent/relative).resolve().as_uri()))
    old='mathMetrics=null}={})'
    assert reference.count(old)==1
    reference=reference.replace(old,'mathMetrics=null,_geometry=null}={})')
    old='if(node.left||node.right){const required='
    assert reference.count(old)==1
    reference=reference.replace(old,'if(!_geometry?.rawFraction&&(node.left||node.right)){const required=')
    hook=r'''
 if(_geometry){
  const r=_geometry,probe=(size,id)=>({type:'nativebox',box:{...size,items:[{kind:'probe',id,x:0,y:0}],class:r.limits?'op':'ord',arrowLabel:r.arrow}});
  if(r.bold)activeFont='boldsymbol';
  if(r.kind==='glyph'){
   activeFont=r.font;const b=glyph(r.token,r.style);
   return{width:b.width,height:b.height,depth:b.depth,classId:['ord','op','bin','rel','open','close','punct','inner'].indexOf(b.class),italic:b.italic??0,character:!!b.character,key:b.items[0]?.key??'',token:b.token??'',diagnostic:draft.diagnostics[0]??''};
  }
  if(r.kind==='assemble'||r.kind==='delimiter'){
   const b=r.kind==='assemble'?assemble(r.token,r.style,r.required):delimiter(r.token,r.style,r.required);
   return{width:b.width,height:b.height,depth:b.depth,items:b.items.map(i=>({key:i.key??'',x:i.x,y:i.y}))};
  }
  let node;
  if(r.kind==='fraction')node={type:'frac',num:[probe(r.n,'n')],den:[probe(r.d,'d')],style:r.style,...(r.rule===undefined?{}:{thickness:r.rule+'bp'}),...(r.delimited?{left:'.',right:'.'}:{})};
  else node={...probe(r.body,'body'),...(r.hasSup?{sup:[probe(r.sup,'sup')]}:{}),...(r.hasSub?{sub:[probe(r.sub,'sub')]}:{}),limits:r.limits,name:r.leftArrow?'xleftarrow':'xrightarrow'};
  const b=atom(node,r.style,r.cramped??false),positions={};
  for(const i of b.items)if(i.kind==='probe')positions[i.id]=[i.x,i.y];
  const rule=b.items.find(i=>i.kind==='rule');
  return{width:b.width,height:b.height,depth:b.depth,positions,...(rule?{rule:[rule.x,rule.y,rule.width,rule.height]}:{})};
 }
'''
    marker=' if(displayWidth!==null&&(!Number.isFinite(displayWidth)'
    assert reference.count(marker)==1
    reference=reference.replace(marker,hook+marker)
    (a.output/'instrumented-reference.mjs').write_text(reference)
    driver=a.output/'reference.mjs'
    driver.write_text('''import {readFile,writeFile} from 'node:fs/promises';
import {typeset} from './instrumented-reference.mjs';
const [metrics,cases,output]=process.argv.slice(2),maps=JSON.parse(await readFile(metrics)).maps;
const results=JSON.parse(await readFile(cases)).map(r=>typeset('x',maps,{_geometry:{...r,rawFraction:true},nativeSemantics:true}));
await writeFile(output,JSON.stringify(results));
''')
    run(['node',driver,a.metrics,a.output/'cases.json',a.output/'reference-results.json'])
    expected=json.loads((a.output/'reference-results.json').read_text())
    # Reuse one source path through every request to exercise actual changed input.
    source=a.output/'changed-after-compilation.json';actual=[]
    # One executable, fonts read once; overwrite the same input path only after
    # the preceding response is complete. This is verification, not a timing run.
    process=subprocess.Popen([str(native)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    try:
        process.stdin.write(str(a.fonts/'catalog.vkfont')+'\n'+str(len(cases))+'\n');process.stdin.flush()
        for index,case in enumerate(cases):
            source.write_text(json.dumps(case));output=a.output/f'native-{index}.json'
            process.stdin.write(str(source)+'\n'+str(output)+'\n');process.stdin.flush()
            deadline=time.monotonic()+30
            while True:
                try:
                    value=json.loads(output.read_text());break
                except (FileNotFoundError,json.JSONDecodeError):
                    if process.poll() is not None:
                        raise RuntimeError(process.stderr.read()or'Native geometry process ended without a response')
                    if time.monotonic()>deadline:raise TimeoutError('Native geometry request did not complete')
                    time.sleep(0.005)
            actual.append(value)
        process.stdin.close()
        assert process.wait(timeout=30)==0,process.stderr.read()
    finally:
        if process.poll() is None:process.terminate();process.wait(timeout=10)
    wasm_driver=a.output/'verify-wasm.mjs'
    wasm_driver.write_text('''import {readFile,writeFile} from 'node:fs/promises';
import {pathToFileURL} from 'node:url';
const [runtime,manifestPath,wasmPath,fontPath,casesPath,output]=process.argv.slice(2);
const {createSymbolicKernel}=await import(pathToFileURL(runtime));
const manifest=JSON.parse(await readFile(manifestPath)),{instance}=await WebAssembly.instantiate(await readFile(wasmPath));
const kernel=createSymbolicKernel({instance,manifest}),fonts=await readFile(fontPath,'utf8'),cases=JSON.parse(await readFile(casesPath));
const results=cases.map(r=>JSON.parse(kernel.invokeValue('geometry',[JSON.stringify(r),fonts])));
await writeFile(output,JSON.stringify(results));
''')
    run(['node',wasm_driver,a.wasm_runtime,manifest,wasm,a.fonts/'catalog.vkfont',a.output/'cases.json',a.output/'wasm-results.json'])
    wasm_actual=json.loads((a.output/'wasm-results.json').read_text())
    maximum=0.0;checks=[]
    def compare(expected,actual,path=''):
        global maximum
        if isinstance(expected,dict):
            assert expected.keys()==actual.keys(),(path,expected,actual)
            for key in expected:compare(expected[key],actual[key],path+'/'+key)
        elif isinstance(expected,list):
            assert len(expected)==len(actual),(path,expected,actual)
            for index,(e,v)in enumerate(zip(expected,actual)):compare(e,v,path+'/'+str(index))
        elif isinstance(expected,(bool,str)):
            assert expected==actual,(path,expected,actual)
        else:
            assert math.isfinite(actual),(path,actual)
            error=abs(expected-actual);maximum=max(maximum,error)
            assert error<=0.000000001,(path,expected,actual,error)
    for backend,values in [('native',actual),('wasm',wasm_actual)]:
        for index,(case,e,v)in enumerate(zip(cases,expected,values)):
            if case['kind']=='scripts':
                v['positions']={k:p for k,p in v['positions'].items() if k=='body' or case['hasSup' if k=='sup' else 'hasSub']}
            elif case.get('rule')==0:v.pop('rule')
            compare(e,v)
        checks.append({'backend':backend,'cases':len(cases),'passed':True})
    assert actual[-1]==actual[-3] and actual[-2]!=actual[-1]
    assert wasm_actual[-1]==wasm_actual[-3] and wasm_actual[-2]!=wasm_actual[-1]
    report.update(passed=True,casesPerBackend=len(cases),checks=checks,maxAbsoluteErrorBp=maximum,
                  toleranceBp=0.000000001,fullMathLayout=False,samePathEditsAndReverts=True,
                  referenceInstrumentation='Existing atom function with native probe boxes; raw fraction before outer delimiters')
finally:
    (a.output/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'passed':True,'casesPerBackend':len(cases),'maxAbsoluteErrorBp':maximum}))
