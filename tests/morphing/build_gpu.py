"""Emit compiler-owned real-f32 field kernels. Browser execution is a separate gate."""
import argparse, hashlib, json, shutil, subprocess
from pathlib import Path

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['library','compiler','gpu-compiler','output']:
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    project=out/'source';project.mkdir();shutil.copytree(a.library/'morphing',project/'morphing')
    package=out/'package';package.mkdir()
    sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
    report={'emitted':False,'browserVerified':False,'hardwareExecuted':False,'compilerSha256':sha(a.compiler),'gpuCompilerSha256':sha(a.gpu_compiler),'kernels':{}}
    try:
        for name,expected in [('state','2'),('field','1'),('measure-chunk','1'),('reduce','6'),('measure','6'),('calibrate','1'),('check-controls','2'),('render-controls','1'),('triangles','64'),('triangle-packet','64')]:
            source=project/(name+'.vkf');shutil.copy2(a.library/'tests/morphing'/('gpu-'+name+'.vkf'),source)
            command=[str(a.compiler),'-b',str(source),'-o',str(out/name),'--diagnostics']
            r=subprocess.run(command,capture_output=True,text=True,timeout=180)
            (out/(name+'-compile.log')).write_text(r.stdout+r.stderr)
            if r.returncode:raise RuntimeError(name+': '+r.stderr)
            native=subprocess.run([str(out/name)],capture_output=True,text=True,timeout=30)
            if native.returncode or native.stdout.strip()!=expected:raise RuntimeError(name+': native fixture '+native.stdout+native.stderr)
            ir=json.loads(r.stdout)['typed_ir_path']
            command=[str(a.gpu_compiler),'--source',str(source),'--typed-ir',ir,'--emit-wgsl-real-f32-field',str(package/(name+'.wgsl')),'--wgsl-field-entry','kernel','--wgsl-field-count','0','--wgsl-field-output-width','72' if name=='triangle-packet' else '1']
            r=subprocess.run(command,capture_output=True,text=True,timeout=180)
            (out/(name+'-gpu.log')).write_text(r.stdout+r.stderr)
            report['kernels'][name]={'command':command,'exit':r.returncode}
            if r.returncode:raise RuntimeError(name+': '+r.stderr)
        report.update(emitted=True,sources={str(f.relative_to(project)):sha(f) for f in project.rglob('*.vkf')},artifacts={f.name:sha(f) for f in package.iterdir()})
    finally:(out/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'emitted':True,'package':str(package)}))
if __name__=='__main__':main()
