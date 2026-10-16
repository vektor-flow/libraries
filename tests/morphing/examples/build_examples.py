"""Build and verify native surface examples, then emit canonical WGSL (no GPU execution)."""
import argparse,hashlib,json,shutil,subprocess
from pathlib import Path

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ['library','compiler','gpu-compiler','output']:p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    src=out/'source';src.mkdir();shutil.copytree(a.library/'morphing',src/'morphing')
    pkg=out/'package';pkg.mkdir()
    sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
    report={'emitted':False,'nativeVerified':False,'browserVerified':False,'hardwareExecuted':False,'compilerSha256':sha(a.compiler),'gpuCompilerSha256':sha(a.gpu_compiler)}
    try:
        for name,expected in [('verify','55296'),('kernel','-1')]:
            source=src/(name+'.vkf');shutil.copy2(a.library/'tests/morphing/examples'/(name+'.vkf'),source)
            r=subprocess.run([str(a.compiler),'-b',str(source),'-o',str(out/name),'--diagnostics'],capture_output=True,text=True,timeout=180)
            (out/(name+'-compile.log')).write_text(r.stdout+r.stderr)
            if r.returncode:raise RuntimeError(r.stderr)
            result=subprocess.run([str(out/name)],capture_output=True,text=True,timeout=180)
            (out/(name+'-native.log')).write_text(result.stdout+result.stderr)
            if result.returncode or result.stdout.strip()!=expected:raise RuntimeError(name+' native failure '+result.stdout+result.stderr)
            if name=='kernel':ir=json.loads(r.stdout)['typed_ir_path']
        report['nativeVerified']=True
        command=[str(a.gpu_compiler),'--source',str(src/'kernel.vkf'),'--typed-ir',ir,'--emit-wgsl-real-f32-field',str(pkg/'surfaces.wgsl'),'--wgsl-field-entry','kernel','--wgsl-field-count','0','--wgsl-field-output-width','21']
        r=subprocess.run(command,capture_output=True,text=True,timeout=180);(out/'gpu.log').write_text(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError(r.stderr)
        report.update(emitted=True,sources={str(f.relative_to(src)):sha(f) for f in src.rglob('*.vkf')},artifacts={f.name:sha(f) for f in pkg.iterdir()})
    finally:(out/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'emitted':True,'package':str(pkg)}))
if __name__=='__main__':main()
