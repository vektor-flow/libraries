"""Python3.14 independent class-module reference; no document input/layout."""
import argparse, hashlib, json, math, subprocess, sys
from pathlib import Path
if sys.version_info[:2] != (3,14):
    raise SystemExit("Python3.14 required")
p=argparse.ArgumentParser(description=__doc__)
for name in ["compiler","wasm-compiler","wasm-runtime","output"]:
    p.add_argument("--"+name,type=Path,required=True)
a=p.parse_args()
a.output.mkdir(parents=True,exist_ok=False)
root=Path(__file__).resolve().parent
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
report=dict(passed=False,completeRendererPort=False,performanceValidated=False,
    compilerSha256=sha(a.compiler),wasmCompilerSha256=sha(a.wasm_compiler),
    wasmRuntimeSha256=sha(a.wasm_runtime),driverSha256=sha(Path(__file__)),
    sourceHashes={s.name:sha(s) for s in root.glob("document_class*.vkf")},
    referenceHashes={name:sha(root.parent/"latex-modules/classes"/(name+".mjs")) for name in ["article","amsart"]})
def run(command,input=None):
    result=subprocess.run(list(map(str,command)),input=input,text=True,capture_output=True,timeout=120)
    if result.returncode:
        report["failure"]=dict(command=list(map(str,command)),stdout=result.stdout,stderr=result.stderr)
        raise RuntimeError(result.stderr or result.stdout)
    return result.stdout
maximum=0.0
def compare(e,v,path=""):
    global maximum
    if isinstance(e,dict):
        assert e.keys()==v.keys(),(path,list(e),list(v))
        for key in e:compare(e[key],v[key],path+"/"+key)
    elif isinstance(e,list):
        assert len(e)==len(v),(path,len(e),len(v))
        for i,(x,y) in enumerate(zip(e,v)):compare(x,y,path+"/"+str(i))
    elif isinstance(e,(str,bool)) or e is None:
        assert type(e) is type(v) and e==v,(path,e,v)
    else:
        assert isinstance(v,(int,float)) and math.isfinite(v),(path,e,v)
        error=abs(e-v);maximum=max(maximum,error)
        assert error<1e-9,(path,e,v,error)
try:
    native=a.output/"dump"
    build=run([a.compiler,"-b",root/"document_class_dump.vkf","-o",native,"--diagnostics"])
    (a.output/"native-build.json").write_text(build)
    build=run([a.compiler,"-b",root/"document_class_kernel.vkf","-o",a.output/"kernel","--diagnostics"])
    (a.output/"kernel-build.json").write_text(build)
    wasm,manifest=a.output/"class.wasm",a.output/"manifest.json"
    run([a.wasm_compiler,"--typed-ir",json.loads(build)["typed_ir_path"],"--wasm",wasm,"--manifest",manifest,"--entry","class_packet","--prune-to-entry"])
    cases=[dict(name=n,options=o) for n,options in [
        ("article",[[],["10pt"],["11pt"],["12pt","a4paper"],["letterpaper"],["a4paper","letterpaper"],["11pt","12pt"],["bad","bad"]]),
        ("amsart",[[],["8pt"],["9pt","a4paper"],["10pt","letterpaper"],["11pt"],["12pt"],["11pt","12pt"],["12pt","11pt"],["15pt"],["draft","twoside"]]),
        ("unknown",[[]])] for o in options]
    (a.output/"cases.json").write_text(json.dumps(cases))
    oracle=a.output/"reference.mjs"
    oracle.write_text("""import{readFile,writeFile}from'node:fs/promises';
import article from"""+repr((root.parent/"latex-modules/classes/article.mjs").as_uri())+""";
import amsart from"""+repr((root.parent/"latex-modules/classes/amsart.mjs").as_uri())+""";
const[c,o]=process.argv.slice(2),classes={article,amsart};
await writeFile(o,JSON.stringify(JSON.parse(await readFile(c)).map(x=>{
 const m=classes[x.name];if(!m)return{config:{},diagnostics:['Unsupported document class: '+x.name],complete:false};
 const diagnostics=x.options.filter(v=>!m.options.includes(v)).map(v=>'Unsupported '+x.name+' option: '+v);
 return{config:m.configure(x.options),diagnostics,complete:!diagnostics.length};
})));""")
    run(["node",oracle,a.output/"cases.json",a.output/"reference.json"])
    expected=json.loads((a.output/"reference.json").read_text())
    lines=[str(len(cases))]
    for i,c in enumerate(cases):lines += [c["name"],str(len(c["options"])),*c["options"],str(a.output/f"native-{i}.json")]
    run([native],input="\n".join(lines)+"\n")
    for i,e in enumerate(expected):compare(e,json.loads((a.output/f"native-{i}.json").read_text()),f"native/{i}")
    driver=a.output/"wasm.mjs"
    driver.write_text("""import{readFile,writeFile}from'node:fs/promises';import{pathToFileURL}from'node:url';
const[r,m,w,c,o]=process.argv.slice(2),{createSymbolicKernel}=await import(pathToFileURL(r)),manifest=JSON.parse(await readFile(m)),
{instance}=await WebAssembly.instantiate(await readFile(w)),k=createSymbolicKernel({instance,manifest});
await writeFile(o,JSON.stringify(JSON.parse(await readFile(c)).map(x=>JSON.parse(k.invokeValue('class_packet',[x.name,x.options])))));""")
    run(["node",driver,a.wasm_runtime,manifest,wasm,a.output/"cases.json",a.output/"wasm-results.json"])
    actual=json.loads((a.output/"wasm-results.json").read_text())
    for i,(e,v) in enumerate(zip(expected,actual)):compare(e,v,f"wasm/{i}")
    assert len(actual)==len(expected)
    report.update(passed=True,casesPerBackend=len(cases),maxAbsoluteErrorBp=maximum)
finally:
    (a.output/"verification.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps({k:report[k] for k in ["passed","casesPerBackend","maxAbsoluteErrorBp"]}))
