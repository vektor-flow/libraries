"""Python 3.14 preparation/reference driver for connected VKF package layout.

Cases are supplied only after compilation. Native and WASM execute production
parsing, box geometry, retained drawing and metadata; JavaScript is the oracle.
This qualifies expressions, never document geometry or renderer performance.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

if sys.version_info[:2] != (3, 14):
    raise SystemExit("Reference checks require Python 3.14")
p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--compiler", type=Path, required=True)
p.add_argument("--fonts", type=Path, required=True)
p.add_argument("--metrics", type=Path, required=True)
p.add_argument("--output", type=Path, required=True)
p.add_argument("--wasm-compiler", type=Path)
p.add_argument("--wasm-runtime", type=Path)
p.add_argument("--paragraph-mode", action="store_true", help="Native inline noad/glue/kern/penalty provider path")
a = p.parse_args()
a.output.mkdir(parents=True, exist_ok=False)
root = Path(__file__).resolve().parent
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
report = dict(passed=False, completeRendererPort=False, performanceValidated=False,
              paragraphMode=a.paragraph_mode, compilerSha256=sha(a.compiler), driverSha256=sha(Path(__file__)),
              sourceHashes={s.name: sha(s) for s in root.glob("*.vkf")},
              referenceHashes={str(s.relative_to(root.parent)): sha(s)
                  for s in [root.parent/"typing-layout.mjs", root.parent/"draft-parser.mjs",
                            *(root.parent/"latex-modules").rglob("*.mjs")]},
              catalogSha256=sha(a.fonts/"catalog.vkfont"), metricsSha256=sha(a.metrics))

def run(command, input=None, timeout=240):
    try:
        result = subprocess.run(list(map(str, command)), input=input, text=True,
                                capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        report["failure"] = dict(command=list(map(str, command)), timeoutSeconds=timeout)
        raise
    if result.returncode:
        report["failure"] = dict(command=list(map(str, command)), exitCode=result.returncode,
                                 stdout=result.stdout, stderr=result.stderr)
        raise RuntimeError(result.stderr or result.stdout)
    return result.stdout

maximum = 0.0
def compare(expected, value, path=""):
    global maximum
    if isinstance(expected, dict):
        assert expected.keys() == value.keys(), (path, list(expected), list(value))
        for key in expected:
            compare(expected[key], value[key], path+"/"+key)
    elif isinstance(expected, list):
        assert len(expected) == len(value), (path, len(expected), len(value))
        for index, (e, v) in enumerate(zip(expected, value)):
            compare(e, v, path+"/"+str(index))
    elif expected is None or isinstance(expected, (bool, str)):
        assert type(expected) is type(value) and expected == value, (path, expected, value)
    else:
        assert isinstance(value, (float, int)) and math.isfinite(value), (path, expected, value)
        error = abs(expected-value)
        maximum = max(maximum, error)
        assert error < 0.000000001, (path, expected, value, error)

try:
    native = a.output/"package_layout_dump"
    dump_source = "math_paragraph_layout_dump.vkf" if a.paragraph_mode else "math_package_layout_dump.vkf"
    kernel_source = "math_paragraph_kernel.vkf" if a.paragraph_mode else "math_layout_kernel.vkf"
    entry = "math_paragraph_packet" if a.paragraph_mode else "math_packet_with_context"
    build = run([a.compiler, "-b", root/dump_source, "-o", native, "--diagnostics"])
    (a.output/"native-build.json").write_text(build)
    if a.wasm_compiler:
        assert a.wasm_runtime
        build = run([a.compiler, "-b", root/kernel_source,
                     "-o", a.output/"kernel", "--diagnostics"])
        (a.output/"kernel-build.json").write_text(build)
        wasm, manifest = a.output/"layout.wasm", a.output/"layout-wasm.json"
        run([a.wasm_compiler, "--typed-ir", json.loads(build)["typed_ir_path"],
             "--wasm", wasm, "--manifest", manifest, "--entry", entry,
             "--prune-to-entry"])
        report.update(wasmCompilerSha256=sha(a.wasm_compiler),
                      wasmRuntimeSha256=sha(a.wasm_runtime), wasmSha256=sha(wasm))
    # No prepared decision/position or source result participates in compilation.
    cases = []
    sources = [
        "a+b", r"\faktor ab", r"\faktor{a_b}{x^2}", r"\faktor[]{a}{b}",
        r"\faktor[\scriptstyle]{a+b}{x}", r"\faktor[\color{red}]{x}{y}",
        r"\frac{\faktor ab}{\sqrt{\faktor xy}}",
        r"\faktor{\frac ab}{\sqrt{x}}", r"\faktor{\faktor ab}{\faktor xy}",
        r"\widehat{\faktor ab}", r"\faktor ab_x^y",
        r"\mathbf{\faktor ab}", r"\textcolor{blue}{\faktor ab}",
        r"\faktor{\kern-2pt a}{b}", r"\faktor{}{}", r"\faktor{a}",
        r"\faktor{\begin{equation}x\label{num}\end{equation}}{\begin{equation}y\label{den}\end{equation}}",
        r"\widehat{\faktor{\begin{equation}x\label{num}\end{equation}}{y}}+\begin{equation}x\end{equation}",
        r"\binom ab", r"\mathbbm{1}+\mathbbmss{A}+\mathbbmtt{x}",
        r"\Box+\Join+\mho", r"\mathbf{\Box}", r"\unknown"]
    if a.paragraph_mode:
        sources = ["", " ", "a+b=c", "x(y+z)=2", "a+-b", "a+b+", "a=b=c",
            r"\mathrel{x}y", r"a\quad b~c\ x", r"a\,b\:x\;y\!z",
            r"\mathbin{x}a", r"\scriptstyle a+b=c", r"\sum_a^b+x",
            r"\frac ab+\sqrt{x}", r"\left(a+b\right)=x",
            r"\mathbf{ab}+\text{ffi}", r"\color{red}a+b", r"a{\color{blue}b}+x",
            r"\widehat{a+b}=x", r"\faktor ab+x", r"\begin{matrix}a&b\\x&y\end{matrix}=x",
            r"\tag{A}a+b", r"\kern-1pt a+b", r"\unknown+x"]
    contexts = [("article", []), ("article", ["faktor", "amsmath", "bbm", "latexsym"]),
                ("amsart", ["faktor", "bbm", "latexsym"])]
    for class_name, names in contexts:
        for index, source in enumerate(sources):
            for inline in ((True,) if a.paragraph_mode else (False, True)):
                cases.append(dict(source=source, className=class_name, names=names,
                                  inline=inline, native=index % 2 == 0,
                                  display=index % 3 == 0, equationStart=9))
    # Explicit style coverage and request edit/revert controls.
    for style in [r"\displaystyle ", r"\textstyle ", r"\scriptstyle ", r"\scriptscriptstyle "]:
        cases.append(dict(source=style+r"\faktor{a_b}{x^2}", className="article",
                          names=["faktor"], inline=False, native=True, display=False, equationStart=99))
    control = dict(className="article", names=["faktor"], inline=False,
                   native=True, display=False, equationStart=1)
    cases += [dict(control, source=s) for s in [r"\faktor ab", r"\faktor ax", r"\faktor ab"]]
    if a.paragraph_mode:
        fonts_data = json.loads(a.metrics.read_text())["documentFonts"]
        roles = list(fonts_data)
        for i, case in enumerate(cases):
            case.update(inline=True, native=True, textSpacing=fonts_data[roles[i % len(roles)]]["spaces"])
    (a.output/"cases.json").write_text(json.dumps(cases))
    reference = a.output/"reference.mjs"
    reference.write_text("""import{readFile,writeFile}from'node:fs/promises';
import{typeset}from"""+repr((root.parent/"typing-layout.mjs").as_uri())+""";
import{resolveModules}from"""+repr((root.parent/"latex-modules/registry.mjs").as_uri())+""";
const[m,c,o]=process.argv.slice(2),maps=JSON.parse(await readFile(m)).maps,result=[];
for(const x of JSON.parse(await readFile(c))){
 const modules=await resolveModules('\\\\documentclass{'+x.className+'}'+x.names.map(n=>'\\\\usepackage{'+n+'}').join(''));
 const r=typeset(x.source,maps,{mode:x.inline?'inline':'display',nativeSemantics:x.native,
 displayEnvironment:x.display,equationStart:x.equationStart,paragraphMode:"""+str(a.paragraph_mode).lower()+""",textSpacing:x.textSpacing??null,packages:[...modules.packages.keys()],
 extensions:[...modules.packages.values()].filter(p=>p.parseMathCommand)});
 result.push(Object.fromEntries(['width','height','depth','items','diagnostics','atoms','complete','nextEquationNumber','equationReferences','lastRow','paragraphNodes'].filter(k=>r[k]!==undefined).map(k=>[k,r[k]])));
}await writeFile(o,JSON.stringify(result));""")
    run(["node", reference, a.metrics, a.output/"cases.json", a.output/"reference-results.json"])
    expected = json.loads((a.output/"reference-results.json").read_text())
    lines = [str(a.fonts/"catalog.vkfont"), str(len(cases))]
    for index, case in enumerate(cases):
        source, output = a.output/f"input-{index}.tex", a.output/f"native-{index}.json"
        source.write_text(case["source"])
        lines += [case["className"], str(len(case["names"])), *case["names"],
                  "inline" if case["inline"] else "display",
                  "native" if case["native"] else "preview",
                  "display-environment" if case["display"] else "ordinary",
                  str(case["equationStart"]), *([json.dumps(case["textSpacing"])] if a.paragraph_mode else []), str(source), str(output)]
    run([native], input="\n".join(lines)+"\n")
    native_values = [json.loads((a.output/f"native-{i}.json").read_text()) for i in range(len(cases))]
    for i, (e, v) in enumerate(zip(expected, native_values)):
        compare(e, v, f"native/{i}")
    assert native_values[-1] == native_values[-3] != native_values[-2]
    report["nativePassed"] = True
    if a.wasm_compiler:
        driver = a.output/"wasm.mjs"
        driver.write_text("""import{readFile,writeFile,appendFile}from'node:fs/promises';
import{pathToFileURL}from'node:url';
const[r,m,w,f,c,o]=process.argv.slice(2),{createSymbolicKernel}=await import(pathToFileURL(r)),
 manifest=JSON.parse(await readFile(m)),{instance}=await WebAssembly.instantiate(await readFile(w)),
 kernel=createSymbolicKernel({instance,manifest}),fonts=await readFile(f,'utf8'),results=[];
for(const x of JSON.parse(await readFile(c))){
 const p=kernel.invokeValue('"""+entry+"""',[x.source,fonts,x.names,x.className,x.inline,x.native,x.display,x.equationStart,...(x.textSpacing?[JSON.stringify(x.textSpacing)]:[])]),q=p.items,items=[];
 for(let i=0;i<q.count;i++)items.push({...JSON.parse('{'+q.payload[q.ids[i]]+'}'),x:q.xs[i],y:q.ys[i],...(q.flow[i]?{flowX:q.flow_x[i],flowWidth:q.flow_width[i]}:{})});
 const value={width:p.width,height:p.height,depth:p.depth,items,diagnostics:JSON.parse('['+p.diagnostics+']'),atoms:p.atoms,complete:p.complete,nextEquationNumber:p.nextEquationNumber,equationReferences:JSON.parse(p.equationReferences),...(p.hasLastRow?{lastRow:p.lastRow}:{}),...(p.paragraphNodes?{paragraphNodes:JSON.parse(p.paragraphNodes)}:{})};
 results.push(value);await appendFile(o+'.jsonl',JSON.stringify(value)+'\\n');
}await writeFile(o,JSON.stringify(results));""")
        run(["node", driver, a.wasm_runtime, manifest, wasm, a.fonts/"catalog.vkfont",
             a.output/"cases.json", a.output/"wasm-results.json"])
        values = json.loads((a.output/"wasm-results.json").read_text())
        assert len(values) == len(expected)
        for i, (e, v) in enumerate(zip(expected, values)):
            compare(e, v, f"wasm/{i}")
        assert values[-1] == values[-3] != values[-2]
        report["wasmPassed"] = True
    report.update(passed=True, casesPerBackend=len(cases), maxAbsoluteErrorBp=maximum)
finally:
    (a.output/"verification.json").write_text(json.dumps(report, indent=2)+"\n")
print(json.dumps({k: report[k] for k in ["passed", "casesPerBackend", "maxAbsoluteErrorBp"]}))
