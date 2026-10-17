"""Compare connected VKF expression layout with the existing renderer.

Python 3.14 only builds/drives independent references. Production parsing,
geometry, retained draw commands and JSON output execute in shared VKF code.
This progressively qualifies math layout, not complete document rendering.
"""
import argparse
import hashlib
import json
import math
import re
import subprocess
import sys
from pathlib import Path

if sys.version_info[:2]!=(3,14):raise SystemExit('Reference checks require Python 3.14')
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--compiler',type=Path,required=True)
p.add_argument('--fonts',type=Path,required=True)
p.add_argument('--metrics',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
p.add_argument('--wasm-compiler',type=Path)
p.add_argument('--wasm-runtime',type=Path)
p.add_argument('--wasm-fresh-instance-per-case',action='store_true',help='Correctness-only isolation of allocator state; never a timing run')
p.add_argument('--inline',action='store_true')
p.add_argument('--preview',action='store_true')
p.add_argument('--display-environment',action='store_true')
p.add_argument('--equation-start',type=int,default=1)
p.add_argument('--case-filter',help='Focused reference subset (regex), with all three edit/revert controls retained; never qualifies the full corpus')
p.add_argument('--wasm-timeout',type=int,default=240,help='Correctness runner budget in seconds; never a renderer performance acceptance gate')
a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
root=Path(__file__).resolve().parent
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
report={'passed':False,'completeRendererPort':False,'fullMathLayout':False,
        'sourceHashes':{s.name:sha(s)for s in root.glob('*.vkf')},
        'driverSha256':sha(Path(__file__)),'catalogSha256':sha(a.fonts/'catalog.vkfont'),'metricsSha256':sha(a.metrics),
        'referenceSha256':sha(root.parent/'typing-layout.mjs'),
        'compilerSha256':sha(a.compiler),'inline':a.inline,'nativeSemantics':not a.preview,'displayEnvironment':a.display_environment,'equationStart':a.equation_start,
        'wasmCorrectnessBudgetSeconds':a.wasm_timeout,'performanceValidated':False}
def run(command,input=None,timeout=240):
    try:r=subprocess.run(list(map(str,command)),input=input,text=True,capture_output=True,timeout=timeout)
    except subprocess.TimeoutExpired:
        report['failure']={'command':list(map(str,command)),'timeoutSeconds':timeout}
        raise
    if r.returncode:
        report['failure']={'command':list(map(str,command)),'stderr':r.stderr,'stdout':r.stdout}
        raise RuntimeError(r.stderr or r.stdout)
    return r.stdout
maximum=0.0
def compare(e,v,path=''):
    global maximum
    if isinstance(e,dict):
        assert e.keys()==v.keys(),(path,list(e),list(v))
        for k in e:compare(e[k],v[k],path+'/'+k)
    elif isinstance(e,list):
        assert len(e)==len(v),(path,len(e),len(v))
        for i,(x,y)in enumerate(zip(e,v)):compare(x,y,path+'/'+str(i))
    elif isinstance(e,(bool,str))or e is None:
        assert type(e)is type(v)and e==v,(path,e,v)
    else:
        assert isinstance(v,(int,float))and math.isfinite(v),(path,e,v)
        error=abs(e-v);maximum=max(maximum,error)
        assert error<=0.000000001,(path,e,v,error)

try:
    native=a.output/'layout_dump'
    diagnostics=run([a.compiler,'-b',root/'math_layout_dump.vkf','-o',native,'--diagnostics'])
    (a.output/'native-build.json').write_text(diagnostics)
    if a.wasm_compiler:
        assert a.wasm_runtime is not None
        diagnostics=run([a.compiler,'-b',root/'math_layout_kernel.vkf','-o',a.output/'layout_kernel','--diagnostics'])
        (a.output/'kernel-build.json').write_text(diagnostics)
        wasm=a.output/'layout.wasm';manifest=a.output/'layout-wasm.json'
        run([a.wasm_compiler,'--typed-ir',json.loads(diagnostics)['typed_ir_path'],'--wasm',wasm,
             '--manifest',manifest,'--entry','math_packet','--prune-to-entry'])
        report.update(wasmSha256=sha(wasm),wasmCompilerSha256=sha(a.wasm_compiler),wasmRuntimeSha256=sha(a.wasm_runtime))
    # Unknown source requests are materialized only after native/WASM compilation.
    cases=['','x','x+y=2','-x+y','x+-y','x=+y','x+','(x+y)z','x(y)z','[x+y]',
           r'a\,b\:c\;x\!y\quad a\qquad b~c\ x',
           r'\displaystyle a+\textstyle b+\scriptstyle c+\scriptscriptstyle x',
           r'\mathbf{x}+\mathit{a}+\mathsf{b}+\mathtt{c}',
           r'\mathcal{A}+\mathbb{R}+\bm{x}',r'\mathop{x}\limits_a^b',
           r'\mathrel{x}+\mathord{y}',r'\mathbin{x}\mathrel{y}',
           r'\frac{a}{b}',r'\frac{x^2}{y_1}',r'\dfrac{a+\frac bc}{x}',
           r'\tfrac{a}{\frac{b}{c}}',r'\binom{x}{2}',r'\dbinom ab',r'\tbinom{x}{2}',
           r'\genfrac{[}{]}{0pt}{2}{a}{b}',
           r'x^a',r'x_a',r'x_a^b',r'{x}^2',r'\mathbf{x}_a^b',r"x''^2",
           r'\sum_a^b',r'\sum\nolimits_a^b',r'\int_a^b',r'\lim_{a}^b',
           r'\sqrt{x}',r'\sqrt[2]{x+1}',r'\sqrt[\frac12]{\frac{a}{b_2}}',
           r'\left(\frac ab\right)^2',r'\left. a\right|_1',
           r'\left(a+\left[b\right]\right)',
           r'\color{red}a+b',r'a+{\color{blue}b+c}+x',
           r'\textcolor[HTML]{12abef}{\frac ab}+x',r'\color[rgb]{.5,.1,1}x_a^b',
           r'\frac{a}',r'\sqrt',r'{a',r'^2+_a',r'\unknown+x',r'\label{eq:x}x']
    for base in ['x',r'\frac ab',r'\sqrt{x}']:
        for depth in [1,3,8]:cases.append('a_{'*depth+base+'}'*depth)
    for style in [r'\displaystyle ',r'\textstyle ',r'\scriptstyle ',r'\scriptscriptstyle ']:
        for body in [r'x_a^b+\frac ab',r'\sqrt[2]{\frac ab}',r'\left[\frac ab\right]',r'\sum_a^b',r'\bm{x_a^b}']:
            cases.append(style+body)
    cases.extend(['x'*200,'{'*32+'a'+'}'*32,'a+b','a+c','a+b'])
    cases[-3:-3]=[r'a\kern-1.5pt b',r'a\hspace{2em}b',r'a\mkern+.5mu b',r'\genfrac{}{}{.5pt}{}{a}{b}',
                    r'\genfrac{}{}{-2bp}{}{a}{b}',r'\genfrac{}{}{bad}{}{a}{b}',r'\hspace',r'\kern{']
    for unit in ['pt','bp','em','ex','mu','mm','cm','in','pc']:
        for value in ['.5','-1.25','2.','99999']:
            cases.insert(-3,r'a\hspace{'+value+unit+'}b')
    cases[-3:-3]=[r'\text{abc def}',r'\text{office afflict ffi ffl ff fi fl}',
        r'\textbf{abc \textit{xy} z}',r'\text{a\emph{b\emph{x}}c}',
        r'\text{a{b}c}',r'\text{\%\$\#\&\_\{\}\textbackslash\textasciicircum\textasciitilde\ }',
        r'\text{a\unsupported b}',r'\text{a\textbf b}',r'\text{a\textbf{b}',r'\text',
        r'\operatorname{lim}_x',r'\operatorname*{sup}_{a}^b',r'\operatorname{sin}x',
        r'\text{α β}',r'\textrm{a~b}',r'\text{\emph{a\textnormal{b}}}',r'\texttt{a b}',
        r'\text{a\textit{b}c}',r'\text{\textit{ab} c}',r'\textcolor{blue}{\text{ffi a}}',
        r'a\dots b',r'a\dots+b',r'a\ldots b',r'\dotsc x',r'\dotsi\int x',
        r'\qty{12345.6789}{\kilo\metre\per\second\squared}',r'\unit{\micro\metre}',
        r'\num{1.23e-4}',r'\ang{10;20;30}',r'\unit[per-mode=symbol]{\metre\per\second}',
        r'\text{'+'x'*200+'}']
    for name in ['hat','tilde','bar','vec','dot','ddot','dddot','ddddot','acute','grave','breve','check','mathring','overline','underline']:
        cases.insert(-3,chr(92)+name+'{x_a}+'+chr(92)+name+'{ab}')
        cases.insert(-3,'\\'+name+r'{x}_a^b')
    cases[-3:-3]=[r'\boxed{x+\frac ab}',r'\fbox{a b}',r'\phantom{x_a^b}+y',
        r'\hphantom{\frac ab}x',r'\vphantom{\sum_a^b}x',r'\mathstrut+x',
        r'\smash{\frac ab}+x',r'\smash[t]{x_a}+\smash[b]{y^b}',
        r'\scriptstyle\boxed{x_a^b}',r'\color{red}\boxed{\hat{x}}',
        r'\boxed{\fbox{a}}',r'\overline{\underline{\frac ab}}']
    for base in ['x','+','=',r'\sum',r'\frac ab','a+b']:
        for name in ['overset','underset','stackrel']:
            cases.insert(-3,'\\'+name+'{a_b}{'+base+'}')
    cases[-3:-3]=[r'\scriptstyle\overset ab',r'\color{red}\underset{\frac ab}{x}',r'\overset{a}{x}^b',r'\underset{a}{x}_b']
    for style in [r'\displaystyle ',r'\textstyle ',r'\scriptstyle ',r'\scriptscriptstyle ']:
        for name in ['xrightarrow','xleftarrow']:
            for labels in ['{a}','[b]{a}',r'[x_2]{\frac ab}','{}']:
                cases.insert(-3,style+'\\'+name+labels)
    cases[-3:-3]=[r'a\xrightarrow[b]{a}x',r'\color{red}\xleftarrow{x}',r'\bm{\xrightarrow[b]{a}}',r'\mathsf{\xleftarrow{\text{ab}}}',r'\xrightarrow{\xleftarrow[b]{a}}',r'\frac{\xrightarrow[b]{a}}{x}',r'\xleftarrow',r'\xrightarrow[']
    for style in ['',r'\textstyle ',r'\scriptstyle ',r'\scriptscriptstyle ']:
        for name in ['pmod','pod','mod','bmod']:
            argument=' ' if name=='bmod' else r'{a+\frac{x}{b}}'
            cases.insert(-3,style+'x\\'+name+argument+'y')
    cases[-3:-3]=[r'\pmod{}',r'\pod{\pmod{x}}',r'\mod{x}_a^b',
        r'\color{red}x\bmod y',r'\mathsf{x\pmod{a}}',r'\bm{x\bmod y}',
        r'\pmod',r'\mod{',r'\bmod+x',r'x+\bmod']
    for name in ['overrightarrow','overleftarrow','overleftrightarrow','underrightarrow','underleftarrow','underleftrightarrow','overbrace','underbrace']:
        for style in ['',r'\scriptstyle ']:
            for body in ['x',r'a+\frac{x}{b}']:
                cases.insert(-3,style+chr(92)+name+'{'+body+'}_a^b')
    for name in ['matrix','pmatrix','bmatrix','Bmatrix','vmatrix','Vmatrix','cases','smallmatrix','aligned','split','gathered','align*','gather*','multline*','eqnarray*']:
        cases.insert(-3,r'\begin{'+name+r'}a&=b\\x+1&y\end{'+name+'}')
    cases[-3:-3]=[r'\begin{array}{|r||lc|}a&b&x\\[2pt]x+y&\frac ab&a\hline\end{array}',
        r'\begin{array}{cc}\hline a&b\\\cline{1-1}x&y\end{array}',
        r'\begin{pmatrix}a&\begin{bmatrix}x\\y\end{bmatrix}\\b&x\end{pmatrix}',
        r'\begin{matrix}a&',r'\begin{aligned}x&+y\\a&=b\end{aligned}',
        r'\begin{equation*}a+\frac xb\end{equation*}']
    for name in ['widehat','widetilde']:
        for style in ['',r'\scriptstyle ',r'\scriptscriptstyle ']:
            for body in ['x','xy',r'\frac{a}{x}',r'abcdefghij',r'\widehat{x}+y']:
                cases.insert(-3,style+chr(92)+name+'{'+body+'}_a^b')
    cases[-3:-3]=[r'\color{red}\widehat{a+\frac xb}',r'\mathbf{\widetilde{abcdef}}',
        r'\bm{\overleftrightarrow{x_a}}',r'\textcolor{blue}{\underbrace{a+b}}',
        r'\widehat{\scriptstyle a+b}',r'\widetilde{\widehat{\frac ab}}',
        r'\begin{array}{cc}a&b\\[bad]x&y\end{array}',
        r'\begin{array}{cc}\cline{0-1}a&b\\\cline{2-3}x&y\end{array}',
        r'\begin{array}{cc}\cline{bad}a&b\end{array}',
        r'\scriptstyle\begin{pmatrix}a&x\\b&y\end{pmatrix}',
        r'\textcolor{red}{\begin{cases}a&b\\x&y\end{cases}}']
    cases[-3:-3]=[r'a+\tag{X}b',r'\tag*{abc}',r'\scriptstyle x\tag{ab}',
        r'\begin{equation}x+1\end{equation}',r'\begin{equation}x\tag{A}\end{equation}',
        r'\begin{align}x&=a\\y&=b\end{align}',r'\begin{align}x&=a\notag\\y&=b\end{align}',
        r'\begin{align*}x&=a\tag{X}\\y&=b\tag*{Y}\end{align*}',
        r'\begin{gather}a\\x+1\end{gather}',r'\begin{multline}a+b\\x+y\end{multline}',
        r'\begin{eqnarray}a&=&b\\x&=&y\end{eqnarray}']
    cases[-3:-3]=[r'\begin{equation}x+1\label{eq:x}\end{equation}',
        r'\begin{equation*}x\label{eq:star}\end{equation*}',
        r'\begin{equation}x\tag{A}\label{eq:custom}\end{equation}',
        r'\begin{align}x&=a\label{eq:x}\\y&=b\label{eq:y}\end{align}',
        r'\begin{align}x&=a\notag\label{eq:x}\\y&=b\tag{Y}\label{eq:y}\end{align}',
        r'\begin{align*}x&=a\tag*{X}\label{eq:x}\label{eq:alias}\\y&=b\label{eq:y}\end{align*}',
        r'\begin{array}{cc}\hline a\label{array:x}&b\\x&y\label{array:y}\end{array}',
        r'\begin{equation}\begin{align}x&=a\label{same}\end{align}\label{same}\end{equation}',
        r'\begin{gather}\label{empty}\\x\label{next}\end{gather}',
        r'\begin{multline}a+b\label{first}\\x+y\label{last}\end{multline}']
    cases[-3:-3]=[r'\begin{equation}\end{equation}',r'\begin{equation*}\end{equation*}',
        r'\begin{equation*}a&+b\\=x\end{equation*}',
        r'\begin{equation}a&+b\\=x\label{eq:all}\end{equation}',
        r'\begin{equation*}a&\color{red}+b\\\scriptstyle x\end{equation*}',
        r'\begin{equation*}a\\[bad]+b\end{equation*}',
        r'\begin{equation*}\hline a&b\end{equation*}',
        r'\widehat{\begin{equation*}a&+b\end{equation*}}',
        r'\begin{equation}a&{\begin{equation*}x&y\end{equation*}}^b\\+x\end{equation}']
    cases[-3:-3]=[r'\widehat{\begin{equation}x\label{eq:x}\end{equation}}+\begin{equation}y\end{equation}',
        r'\widetilde{\begin{equation}x\label{eq:x}\end{equation}}+\begin{equation}y\end{equation}',
        r'\widehat{\widetilde{\begin{equation}x\label{eq:x}\end{equation}}}+\begin{equation}y\end{equation}',
        r'\widehat{\begin{align}x&=a\label{eq:a}\\y&=b\label{eq:b}\end{align}}+\begin{equation}y\end{equation}',
        r'\widehat{\begin{equation}x\tag{A}\label{eq:x}\end{equation}}+\begin{equation}y\end{equation}',
        r'\widehat{\begin{equation*}x\label{eq:x}\end{equation*}}+\begin{equation}y\end{equation}',
        r'\widehat{\begin{equation}x\notag\label{eq:x}\end{equation}}+\begin{equation}y\end{equation}',
        r'\widehat{\begin{equation}x\end{equation}}^{\begin{equation}y\label{eq:sup}\end{equation}}',
        r'\widehat{\begin{equation}x\end{equation}}_{\begin{equation}y\label{eq:sub}\end{equation}}',
        r'\frac{\widehat{\begin{equation}x\end{equation}}}{\begin{equation}y\label{eq:den}\end{equation}}',
        r'\sqrt[\begin{equation}y\label{eq:index}\end{equation}]{\widehat{\begin{equation}x\end{equation}}}']
    cases[-3:-3]=[r'\xrightarrow{\begin{equation}x\label{eq:up}\end{equation}}+\begin{equation}y\end{equation}',
        r'\xleftarrow[\begin{equation}x\label{eq:down}\end{equation}]{\begin{equation}y\label{eq:up}\end{equation}}+\begin{equation}x\end{equation}',
        r'\xrightarrow{\widehat{\begin{equation}x\label{eq:up}\end{equation}}}+\begin{equation}y\end{equation}',
        r'\xrightarrow{\begin{equation}x\tag{A}\label{eq:up}\end{equation}}+\begin{equation}y\end{equation}']
    row_source=r'\begin{eqnarray*}a&=&b\\x&=&y\end{eqnarray*}'
    for before,after in [('{','}'),(r'\overline{','}'),(r'\boxed{','}'),(r'\overbrace{','}'),
                         (r'\left(','\\right)'),('x+',''),(r'\tag{A}',''),
                         (r'\begin{equation*}',r'\end{equation*}')]:
        cases.insert(-3,before+row_source+after)
    cases.insert(-3,'x'*3000)
    cases[-3:-3]=[r'\mathcal{a}+\mathbb{b}+\mathscr{c}',
        r'\frac{\mathcal{a}}{\mathscr{b}}',r'x^{\mathcal{a}}_{\mathscr{b}}']
    report.update(originalCorpusCases=len(cases),caseFilter=a.case_filter,fullCorpus=a.case_filter is None)
    if a.case_filter is not None:
        selected=[source for source in cases[:-3]if re.search(a.case_filter,source)]
        assert selected,'Reference case filter selected no feature cases'
        cases=selected+cases[-3:]
        report['scope']='Focused feature cases plus three edit/revert controls; not full-corpus qualification'
    (a.output/'cases.json').write_text(json.dumps(cases))
    driver=a.output/'reference.mjs'
    driver.write_text('''import {readFile,writeFile} from 'node:fs/promises';
import {typeset} from '''+repr((root.parent/'typing-layout.mjs').as_uri())+''';
const [metrics,cases,output,mode,native,display,equation,selected]=process.argv.slice(2),maps=JSON.parse(await readFile(metrics)).maps;
const result=JSON.parse(await readFile(cases)).map(source=>{const r=typeset(source,maps,{mode,nativeSemantics:native==='native',displayEnvironment:display==='true',equationStart:Number(equation)});return Object.fromEntries(['width','height','depth','items','diagnostics','atoms','complete','nextEquationNumber','equationReferences','lastRow'].map(k=>[k,r[k]]));});
await writeFile(output,JSON.stringify(result));
''')
    run(['node',driver,a.metrics,a.output/'cases.json',a.output/'reference-results.json','inline'if a.inline else'display','preview'if a.preview else'native',str(a.display_environment).lower(),str(a.equation_start)])
    expected=json.loads((a.output/'reference-results.json').read_text())
    lines=[str(a.fonts/'catalog.vkfont'),'inline'if a.inline else'display','preview'if a.preview else'native','display-environment'if a.display_environment else'ordinary',str(a.equation_start),str(len(cases))]
    for i,source in enumerate(cases):
        path=a.output/f'input-{i}.tex';path.write_text(source)
        lines.extend([str(path),str(a.output/f'native-{i}.json')])
    run([native],input='\n'.join(lines)+'\n')
    outputs={'native':[json.loads((a.output/f'native-{i}.json').read_text())for i in range(len(cases))]}
    for i,(e,v)in enumerate(zip(expected,outputs['native'])):compare(e,v,'native/'+str(i))
    assert outputs['native'][-1]==outputs['native'][-3]and outputs['native'][-2]!=outputs['native'][-1]
    native_gate={'passed':True,'backend':'native','cases':len(cases),'maxAbsoluteErrorBp':maximum,'fullRenderer':False}
    report['nativeReferenceCompleted']=native_gate
    (a.output/'native-verification.json').write_text(json.dumps(native_gate,indent=2)+'\n')
    if a.wasm_compiler:
        driver=a.output/'verify-wasm.mjs'
        driver.write_text('''import {readFile,writeFile,appendFile} from 'node:fs/promises';
import {pathToFileURL} from 'node:url';
const [runtime,manifestFile,wasmFile,fontsFile,casesFile,output,inline,native,display,equation,selected]=process.argv.slice(2);
const {createSymbolicKernel}=await import(pathToFileURL(runtime));
const manifest=JSON.parse(await readFile(manifestFile)),{instance}=await WebAssembly.instantiate(await readFile(wasmFile)),kernel=createSymbolicKernel({instance,manifest});
const fonts=await readFile(fontsFile,'utf8'),cases=JSON.parse(await readFile(casesFile));
const results=[];
for(const [index,source]of cases.entries()){
 if(selected!==undefined&&index!==Number(selected))continue;
 const start=performance.now(),p=kernel.invokeValue('math_packet',[source,fonts,inline==='true',native==='true',display==='true',Number(equation)]),q=p.items,items=[];
 for(let i=0;i<q.count;i++)items.push({...JSON.parse('{'+q.payload[q.ids[i]]+'}'),x:q.xs[i],y:q.ys[i],...(q.flow[i]?{flowX:q.flow_x[i],flowWidth:q.flow_width[i]}:{})});
 results.push({width:p.width,height:p.height,depth:p.depth,items,diagnostics:JSON.parse('['+p.diagnostics+']'),atoms:p.atoms,complete:p.complete,nextEquationNumber:p.nextEquationNumber,equationReferences:JSON.parse(p.equationReferences),...(p.hasLastRow?{lastRow:p.lastRow}:{})});
 await appendFile(output+'.jsonl',JSON.stringify(results.at(-1))+'\\n');
 await writeFile(output+'.progress.json',JSON.stringify({completed:index+1,total:cases.length,lastMilliseconds:performance.now()-start}));
}
await writeFile(output,JSON.stringify(results));
''')
        command=['node',driver,a.wasm_runtime,manifest,wasm,a.fonts/'catalog.vkfont',a.output/'cases.json',a.output/'wasm-results.json',str(a.inline).lower(),str(not a.preview).lower(),str(a.display_environment).lower(),str(a.equation_start)]
        if a.wasm_fresh_instance_per_case:
            for index in range(len(cases)):
                run(command+[str(index)],timeout=a.wasm_timeout)
            combined=[json.loads(line)for line in (a.output/'wasm-results.json.jsonl').read_text().splitlines()]
            (a.output/'wasm-results.json').write_text(json.dumps(combined))
            report['wasmFreshInstancePerCase']=True
        else:run(command,timeout=a.wasm_timeout)
        outputs['wasm']=json.loads((a.output/'wasm-results.json').read_text())
    differences=[]
    for backend,values in outputs.items():
        if backend=='native':continue
        assert len(values)==len(expected)
        for i,(e,v)in enumerate(zip(expected,values)):
            try:compare(e,v)
            except AssertionError as error:differences.append({'backend':backend,'index':i,'source':cases[i],'error':str(error)})
        assert values[-1]==values[-3]and values[-2]!=values[-1]
    report.update(passed=not differences,casesPerBackend=len(cases),backends=list(outputs),differences=differences,maxAbsoluteErrorBp=maximum,toleranceBp=0.000000001)
finally:
    partial=a.output/'wasm-results.json.jsonl'
    if not report['passed']and partial.exists()and 'expected'in globals():
        saved=[json.loads(line)for line in partial.read_text().splitlines()]
        partial_gate={'passed':True,'cases':len(saved),'totalCases':len(expected),'fullCorpusCompleted':len(saved)==len(expected)}
        try:
            for i,(e,v)in enumerate(zip(expected,saved)):compare(e,v,'wasm/'+str(i))
        except AssertionError as error:partial_gate.update(passed=False,error=str(error))
        report['wasmPartialReference']=partial_gate
    (a.output/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'passed':report['passed'],'casesPerBackend':len(cases),'different':differences[:8]}))
if not report['passed']:raise SystemExit(1)
