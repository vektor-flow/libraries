"""Emit the native library's indexed text-unfold channels through VKF typed IR."""
from pathlib import Path
import argparse,subprocess,shutil,json,hashlib
p=argparse.ArgumentParser();p.add_argument('--compiler',type=Path,required=True);p.add_argument('--gpu-compiler',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();root=Path(__file__).resolve().parents[2];out=a.output.resolve();out.mkdir(parents=True,exist_ok=False);shutil.copytree(root/'morphing',out/'morphing');source=out/'gpu-unfold.vkf';shutil.copy2(root/'tests/morphing/gpu-unfold.vkf',source)
r=subprocess.run([str(a.compiler),'-b',str(source),'-o',str(out/'native'),'--diagnostics'],capture_output=True,text=True);assert r.returncode==0,r.stderr;info=json.loads(r.stdout)
subprocess.run([str(a.gpu_compiler),'--source',str(source),'--typed-ir',info['typed_ir_path'],'--emit-wgsl-real-f32-field',str(out/'unfold.wgsl'),'--wgsl-field-entry','kernel','--wgsl-field-count','0','--wgsl-field-output-width','1'],check=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
(out/'SOURCE.json').write_text(json.dumps({'sourceSha256':sha(root/'morphing/unfold.vkf'),'fixtureSha256':sha(source),'compilerSha256':sha(a.compiler),'gpuCompilerSha256':sha(a.gpu_compiler),'wgslSha256':sha(out/'unfold.wgsl'),'indexedChannels':['alpha','growth','red','green','blue'],'rendererOwns':'cached glyph and row indices, font coverage, playback'},indent=2)+'\n')
