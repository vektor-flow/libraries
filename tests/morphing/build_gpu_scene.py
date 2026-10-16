"""Build canonical VKF preparation/clock module; GPU execution is packaged separately."""
import argparse, hashlib, json, shutil, subprocess
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
for n in ['library','compiler','wasm-compiler','runtime-root','output']:p.add_argument('--'+n,type=Path,required=True)
a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
source=out/'source';source.mkdir();shutil.copytree(a.library/'morphing',source/'morphing')
text=(a.library/'tests/morphing/wasm-demo.vkf').read_text().rsplit('::demo_entry(0).measure',1)[0]
text+=(a.library/'tests/morphing/gpu-controls.vkf').read_text()
path=source/'scene.vkf';path.write_text(text)
def run(cmd,name):
 r=subprocess.run([str(x) for x in cmd],capture_output=True,text=True,timeout=180)
 (out/(name+'.log')).write_text(r.stdout+r.stderr)
 if r.returncode:raise RuntimeError(r.stderr)
 return r
r=run([a.compiler,'-b',path,'-o',out/'scene','--diagnostics'],'native')
package=out/'package';package.mkdir();(package/'vf-ui').mkdir();(package/'playground').mkdir()
run([a.wasm_compiler,'--typed-ir',json.loads(r.stdout)['typed_ir_path'],'--wasm',package/'scene.wasm','--manifest',package/'scene.json','--entry','gpu_entry','--prune-to-entry'],'wasm')
for name,digest in {'playground/vkf-concurrent-values.mjs':'40159185c5ad84750cfbb34c3a272b174c7954671c9e7da90d5c58b6ca2b8679','vf-ui/vf-symbolic-kernel-runtime.mjs':'69e80bffc12d7c020fc94c0af480ccf05912cf534f1aa6e9aaf80c68e7971fae'}.items():
 f=a.runtime_root/name
 if hashlib.sha256(f.read_bytes()).hexdigest()!=digest:raise RuntimeError('Unqualified canonical runtime '+name)
 shutil.copy2(f,package/name)
sha=lambda x:hashlib.sha256(x.read_bytes()).hexdigest()
(out/'verification.json').write_text(json.dumps({'emitted':True,'executed':False,'sources':{str(f.relative_to(source)):sha(f) for f in source.rglob('*.vkf')},'artifacts':{str(f.relative_to(package)):sha(f) for f in package.rglob('*') if f.is_file()}},indent=2)+'\n')
print(package)
