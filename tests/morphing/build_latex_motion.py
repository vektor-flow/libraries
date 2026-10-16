"""Build VKF motion over the existing LaTeX engine's prepared instance packets."""
from pathlib import Path
import argparse, subprocess, json, shutil, hashlib
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--compiler',required=True);a=p.parse_args()
root=Path(__file__).resolve().parents[2];out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
if (out/'morphing').resolve()!=(root/'morphing').resolve():shutil.copytree(root/'morphing',out/'morphing',dirs_exist_ok=True)
shutil.copy2(root/'tests/morphing/gpu-latex-motion.vkf',out/'gpu-latex-motion.vkf');commands=[]
def run(cmd):
 r=subprocess.run([str(x) for x in cmd],capture_output=True,text=True);commands.append({'command':[str(x) for x in cmd],'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr});(out/'build.json').write_text(json.dumps(commands,indent=2));assert r.returncode==0,r.stderr;return r.stdout
info=json.loads(run(['/home/viktor/.local/bin/vkf-cuvami','-b',out/'gpu-latex-motion.vkf','-o',out/'native','--diagnostics']))
run([a.compiler,'--source',out/'gpu-latex-motion.vkf','--typed-ir',info['typed_ir_path'],'--emit-wgsl-real-f32-field',out/'gpu-latex-motion.wgsl','--wgsl-field-entry','kernel','--wgsl-field-count','0','--wgsl-field-output-width','16'])
(out/'contract.json').write_text(json.dumps({'header':['example','q','mode','smoothStart','smoothEnd','extent','instanceCount','groupCount'],'data':'16*N engine instance floats, N exact group IDs, 6*G group origins x0,y0,x1,y1,x2,y2','values':[0,1,2],'outputWidth':16,'layout':'rect4 uv4 rgba4 info4','rule':'Input unpadded normalized rect. Output padded1px; info.yz are unpadded pixel dimensions.','ownership':'Existing LaTeX engine parses/layouts/glyph atlas; compiled VKF animates group placement.','compilerSha256':hashlib.sha256(Path(a.compiler).read_bytes()).hexdigest(),'sourceSha256':hashlib.sha256((root/'morphing/latex_motion.vkf').read_bytes()).hexdigest()},indent=2))
print(out/'contract.json')
