"""Python3.14 actual-JS inline-parser action trace oracle; no glyph lowering claim."""
import argparse, hashlib, json, subprocess, sys
from pathlib import Path
if sys.version_info[:2]!=(3,14):raise SystemExit('Python3.14 required')
p=argparse.ArgumentParser(description=__doc__)
for key in ['compiler','wasm-compiler','wasm-runtime','fonts','metrics','output']:p.add_argument('--'+key,type=Path,required=True)
a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
root=Path(__file__).resolve().parent;sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
report={'passed':False,'completeRendererPort':False,'glyphOrParagraphLoweringQualified':False,'driverSha256':sha(Path(__file__)),'sources':{s.name:sha(s) for s in root.glob('text_parser*.vkf')},'referenceSha256':sha(root.parent/'document-text.mjs'),'catalogSha256':sha(a.fonts),'compilerSha256':sha(a.compiler),'wasmCompilerSha256':sha(a.wasm_compiler),'wasmRuntimeSha256':sha(a.wasm_runtime),'explicitBoundary':['Native glyph/box/dimension/availability/linkappearance semantics remain lowering actions','Unicode lowercase transformation remains an explicit action','UTF16-splitting command/accent/delimiter edges remain unqualified']}
def run(command,input=None,timeout=300):
 q=subprocess.run(list(map(str,command)),input=input,text=True,capture_output=True,timeout=timeout)
 if q.returncode:
  report['failure']={'command':list(map(str,command)),'stdout':q.stdout,'stderr':q.stderr,'exitCode':q.returncode};raise RuntimeError(q.stderr or q.stdout)
 return q.stdout
try:
 metrics=json.loads(a.metrics.read_text());roles=list(metrics['documentFonts']);optical=bool(metrics.get('fontProfile'))
 texts=['','words and punctuation.','{a {b} c} tail',r'\textbf{bold \emph{italic}} roman',r'\emph{emph \emph{upright}}',r'\textrm{a}\textnormal{b}\textit{c}\texttt{d}\textsf{e}\textsc{f}\textsl{g}\textup{h}',r'{\rmfamily a \bfseries b \itshape c \ttfamily d \sffamily e \slshape f \scshape g} h',r'\rm a\bf b\it c\tt d\sf e\sl f\sc g\em h',r'\protect\relax\ignorespaces a',r'\Huge x \unknown{y}',r'\textbf missing',r'\textbf{$a}b$ c} tail',r'$a+b$ and \(x^2\)',r'$unfinished',r'\(unfinished',r'a~b\ c\  d',r'\@a\,b\quad c\qquad d\newblock e\italiccorrection f\/g',r'\char65 \char 00066 end',r'\char nope',r"\'a \v{c} \u{\i} \`{\j}",r'\^o\~n\"a\=a\r{a}\c{c}\.a',"\\'",r'\i\j\lq\lq word\rq\rq end\lq x\rq',r'\hspace*{1em plus2pt minus .5pt} x',r'\hspace{bad}x',r'\vkftikzbox{absent}',r'\documentanchor{label%3Aalpha}',r'\href{https://a.test/\%20\#x}{link \textbf{bold}}',r'\href{unfinished',r'\url{https://a.test/a%20#b}',r'\nolinkurl|literal%#_\x|',r'\url|unfinished',r'\url {non ascii å}',r'\hyperlink{name}{linked \emph{text}}',r'\hypertarget{name}{target}',r'\hyperref[label]{reference}',r'\hyperref missing',r'\hyperref[unfinished',r'\documentlinkspan{cite}{label%3Ax}{citation}',r'\documentlink{cite}{citation}{label%3Ax}',r'\mbox{unbreakable \textit{italic}} end',r'\mbox{\unknown{x}}',r'\lowercase{UPPER Ελληνικά}',r'\{\}\_\%\#\$\&\textbackslash',r'\textbullet\dots\ldots\TeX\LaTeX',r'\footnotemark{1:2}',r'\symbolfootnotemark{1}',r'\hypersetup{colorlinks,urlcolor=red}\href{x}{y}',r'\hyperlink{x}{\href{y}{nested}}','raw%percent\nline']
 cases=[]
 for font in ['roman','footnote']:
  for source in texts:cases.append(dict(source=source,font=font,hyperref=True,literal=False,literal_input=False,legacy=False,bib_url=False))
 for source in [r'\href{x}{y}',r'\hyperlink{x}{y}',r'\hypertarget{x}{y}',r'\hyperref[x]{y}',r'\url{x}']:
  cases.append(dict(source=source,font='roman',hyperref=False,literal=False,literal_input=False,legacy=False,bib_url=False))
 for source in ['','\nA  B\nC\n','A\r','\n\nA\n\n','A\n \t','A\r\nB\r\n']:
  for literal_input in [False,True]:cases.append(dict(source=source,font='mono',hyperref=False,literal=True,literal_input=literal_input,legacy=False,bib_url=False))
 (a.output/'cases.json').write_text(json.dumps(cases,ensure_ascii=True,indent=2)+'\n')
 oracle=a.output/'reference.mjs';oracle.write_text('''import{readFile,writeFile}from'node:fs/promises';import{pathToFileURL}from'node:url';import{dirname,resolve}from'node:path';
const original=await readFile(process.argv[2],'utf8');let source=original;const replace=(from,to)=>{if(!source.includes(from))throw Error('Reference hook missing: '+from);source=source.replace(from,to);};
source=source.replace(/from '([^']+)'/g,(_,p)=>'from '+JSON.stringify(pathToFileURL(resolve(dirname(process.argv[2]),p)).href));
replace('const fonts=data.documentFonts;','const trace=[];let traceSuppress=false,traceSuppressGlue=false;const fonts=data.documentFonts;');
replace('function appendText(text,role){','function appendText(text,role){if(text&&!traceSuppress)trace.push({event:"word",role,value:text});');
replace('function glue(role,{nonbreak=false,explicit=false}={}){','function glue(role,{nonbreak=false,explicit=false}={}){if(!traceSuppressGlue)trace.push({event:"glue",role,nonbreak,explicit});');
replace('function group(){','function group_native(){');replace(' function parse(role,stop=false){',' function group(){const value=group_native();trace.push({event:"argument",value});return value;} function parse(role,stop=false){');
replace('const name=match[1];','const name=match[1];trace.push({event:"command",name,role});');
replace('if(href){at=href.end;','if(href){trace.push({event:"command",name:"href",role},{event:"target",value:href.value});at=href.end;');
replace('if(url){if(/','if(url){trace.push({event:"command",name:source.charCodeAt(at+1)===110?"nolinkurl":"url",role},{event:"target",value:url.value});if(/');
replace("if(/\\\\s/.test(c)){", "if(/\\\\s/.test(c)){trace.push({event:'space',role});");
replace("if(!nodes.at(-1)?.explicit)glue(role);", "if(!nodes.at(-1)?.explicit){traceSuppressGlue=true;glue(role);traceSuppressGlue=false;}");
replace('const box=typeset(source.slice(begin,end),','trace.push({event:"math",role,value:source.slice(begin,end)});const box=typeset(source.slice(begin,end),');
replace('if(code){at+=code[0].length;','if(code){trace.push({event:"char",code:code[1]});at+=code[0].length;');
replace('const base=shape(letter,role),','trace.push({event:"accent_base",role,value:letter});const base=shape(letter,role),');
replace('appendText(text.toLowerCase(),role);','{traceSuppress=true;appendText(text.toLowerCase(),role);traceSuppress=false;}');
replace('else appendText(name,role);','else {traceSuppress=true;appendText(name,role);traceSuppress=false;}');
replace("if(i)nodes.push({type:'forced'});nodes.push({type:'box',box:shape(line.replaceAll(' ','\\\\u0020'),font)});", "if(i){trace.push({event:'forced'});nodes.push({type:'forced'});}trace.push({event:'literal',role:font,value:line});nodes.push({type:'box',box:shape(line.replaceAll(' ','\\\\u0020'),font)});");
replace('return out;\\n}', 'out.parserTrace=trace;return out;\\n}');
const instrumented=process.argv[5];await writeFile(instrumented,source);const{typesetDocumentText}=await import(pathToFileURL(instrumented));const data=JSON.parse(await readFile(process.argv[3])),cases=JSON.parse(await readFile(process.argv[4]));const syntax=/^(Unsupported document text command:|Inferred inline math close|Missing text accent base|Command requires hyperref:|Unfinished href|Unfinished URL|Only hyperref\\[|URL whitespace and non-ASCII|Missing optical text font:)/;
const out=cases.map(c=>{const q=typesetDocumentText(c.source,{...data,documentLinks:{enabled:c.hyperref}},{font:c.font,width:1000000,justify:false,hyphens:false,literal:c.literal,literalInput:c.literal_input,legacyTextSymbols:c.legacy,bibUrl:c.bib_url});return{trace:q.parserTrace,diagnostics:q.diagnostics.filter(d=>syntax.test(d))};});await writeFile(process.argv[6],JSON.stringify(out));''')
 run(['node',oracle,root.parent/'document-text.mjs',a.metrics,a.output/'cases.json',a.output/'instrumented-reference.mjs',a.output/'reference.json'])
 expected=json.loads((a.output/'reference.json').read_text())
 native=a.output/'dump';build=run([a.compiler,'-b',root/'text_parser_dump.vkf','-o',native,'--diagnostics']);(a.output/'native-build.json').write_text(build)
 entries=[str(a.fonts),json.dumps(roles),str(optical).lower(),str(len(cases))]
 for i,c in enumerate(cases):
  path=a.output/f'input-{i}.tex';path.write_text(c['source']);entries.extend([str(path),c['font'],*[str(c[k]).lower() for k in ['hyperref','literal','literal_input','legacy','bib_url']],str(a.output/f'native-{i}.json')])
 run([native],input='\n'.join(entries)+'\n',timeout=600)
 for i,e in enumerate(expected):
  actual=json.loads((a.output/f'native-{i}.json').read_text());value={k:actual[k] for k in ['trace','diagnostics']};assert e==value,('native',i,cases[i],e,value)
 report.update(nativePassed=True,nativeCases=len(cases));(a.output/'native-verification.json').write_text(json.dumps(report,indent=2)+'\n')
 build=run([a.compiler,'-b',root/'text_parser_kernel.vkf','-o',a.output/'kernel','--diagnostics']);(a.output/'kernel-build.json').write_text(build)
 wasm=a.output/'kernel.wasm';manifest=a.output/'manifest.json';run([a.wasm_compiler,'--typed-ir',json.loads(build)['typed_ir_path'],'--wasm',wasm,'--manifest',manifest,'--entry','text_parse','--prune-to-entry'])
 driver=a.output/'run-wasm.mjs';driver.write_text('''import{readFile,writeFile,appendFile}from'node:fs/promises';import{pathToFileURL}from'node:url';const{createSymbolicKernel}=await import(pathToFileURL(process.argv[2]));const manifest=JSON.parse(await readFile(process.argv[3]));const{instance}=await WebAssembly.instantiate(await readFile(process.argv[4]));const kernel=createSymbolicKernel({instance,manifest}),fonts=await readFile(process.argv[5],'utf8'),metrics=JSON.parse(await readFile(process.argv[6])),roles=JSON.stringify(Object.keys(metrics.documentFonts)),cases=JSON.parse(await readFile(process.argv[7]));await writeFile(process.argv[8],'');for(let i=0;i<cases.length;i++){const c=cases[i],q=JSON.parse(kernel.invokeValue('text_parse',[fonts,c.source,c.font,roles,!!metrics.fontProfile,c.hyperref,c.literal,c.literal_input,c.legacy,c.bib_url]));await appendFile(process.argv[8],JSON.stringify(q)+'\\n');await writeFile(process.argv[9],JSON.stringify({completed:i+1,total:cases.length}));}''')
 run(['node',driver,a.wasm_runtime,manifest,wasm,a.fonts,a.metrics,a.output/'cases.json',a.output/'wasm-results.jsonl',a.output/'progress.json'],timeout=900)
 actual=[json.loads(s) for s in (a.output/'wasm-results.jsonl').read_text().splitlines()];assert len(actual)==len(expected)
 for i,(e,q) in enumerate(zip(expected,actual)):
  value={k:q[k] for k in ['trace','diagnostics']};assert e==value,('wasm',i,cases[i],e,value)
 report.update(passed=True,wasmPassed=True,wasmCases=len(cases))
finally:(a.output/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ['passed','nativeCases','wasmCases']}))
