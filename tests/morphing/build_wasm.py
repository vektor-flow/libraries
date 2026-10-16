"""Build a canonical VKF biological demo WASM; host code only transports values."""
import argparse,functools,hashlib,http.server,json,shutil,subprocess,threading
from pathlib import Path

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for name in ['library','source','compiler','wasm-compiler','runtime-root','output']:p.add_argument('--'+name,type=Path,required=True)
 p.add_argument('--playwright',type=Path);p.add_argument('--chromium',type=Path)
 a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
 project=out/'source';project.mkdir();shutil.copy2(a.source,project/'biological_callable.vkf');shutil.copy2(a.library/'Morphing.vkf',project/'Morphing.vkf');shutil.copytree(a.library/'morphing',project/'morphing')
 for name,digest in {'playground/vkf-concurrent-values.mjs': '40159185c5ad84750cfbb34c3a272b174c7954671c9e7da90d5c58b6ca2b8679', 'vf-ui/vf-symbolic-kernel-runtime.mjs': '69e80bffc12d7c020fc94c0af480ccf05912cf534f1aa6e9aaf80c68e7971fae'}.items():
  if hashlib.sha256((a.runtime_root/name).read_bytes()).hexdigest()!=digest:raise RuntimeError('Runtime does not match the qualified canonical ABI: '+name)
 report={'completeNativeViewIntegration':False,'hostInterpolation':False,'canonicalWASM':True,'passed':False}
 def run(cmd,name):
  r=subprocess.run([str(x) for x in cmd],capture_output=True,text=True,timeout=180)
  (out/(name+'.log')).write_text(r.stdout+r.stderr)
  if r.returncode:raise RuntimeError(name+': '+r.stderr)
  return r
 sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
 try:
  result=run([a.compiler,'-b',project/'biological_callable.vkf','-o',out/'native-producer','--diagnostics'],'native-build');diagnostics=json.loads(result.stdout)
  package=out/'package';package.mkdir();(package/'vf-ui').mkdir();(package/'playground').mkdir()
  command=[a.wasm_compiler,'--typed-ir',diagnostics['typed_ir_path'],'--wasm',package/'biological.wasm','--manifest',package/'biological-wasm.json','--entry','demo_entry','--prune-to-entry'];run(command,'wasm-build')
  for name in ['vf-ui/vf-symbolic-kernel-runtime.mjs','playground/vkf-concurrent-values.mjs']:shutil.copy2(a.runtime_root/name,package/name)
  (package/'morphing-demo.mjs').write_text(LOADER)
  (package/'index.html').write_text('<!doctype html><meta charset="utf-8"><script type="module">import {loadMorphingDemo} from "./morphing-demo.mjs";window.loadMorphingDemo=loadMorphingDemo;</script>')
  (out/'verify-node.mjs').write_text(NODE)
  report['node']=json.loads(run(['node',out/'verify-node.mjs',package],'node-check').stdout)
  if a.playwright and a.chromium:
   handler=functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(package));server=http.server.ThreadingHTTPServer(('127.0.0.1',0),handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
   try:
    (out/'verify-browser.cjs').write_text(BROWSER)
    report['browser']=json.loads(run(['node',out/'verify-browser.cjs',a.playwright,a.chromium,'http://127.0.0.1:'+str(server.server_port)],'browser-check').stdout)
   finally:server.shutdown();server.server_close();thread.join()
  report.update(passed=True,wasmCommand=[str(x) for x in command],compilerSha256=sha(a.compiler),wasmCompilerSha256=sha(a.wasm_compiler),sources={str(f.relative_to(project)):sha(f) for f in project.rglob('*.vkf')},artifacts={str(f.relative_to(package)):sha(f) for f in package.rglob('*') if f.is_file()})
 finally:(out/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({'passed':True,'package':str(package),'browser':bool(a.playwright and a.chromium)}))

LOADER='''import {createSymbolicKernel} from './vf-ui/vf-symbolic-kernel-runtime.mjs';
// No host interpolation. Coordinate is forwarded unchanged to compiled VKF.
export async function loadMorphingDemo(resolution=24,mode=1,smoothStart=true,smoothEnd=true){
 const [m,w]=await Promise.all([fetch(new URL('./biological-wasm.json',import.meta.url)),fetch(new URL('./biological.wasm',import.meta.url))]);
 if(!m.ok||!w.ok)throw Error('Morphing artifact unavailable');
 const manifest=await m.json();let result=await WebAssembly.instantiate(await w.arrayBuffer());
 let kernel=createSymbolicKernel({instance:result.instance,manifest});let instance=result.instance;result=null;
 let scene=kernel.invokeValue('demo_prepare',[resolution,mode,smoothStart,smoothEnd]);
 return Object.freeze({resolution,mode,smoothStart,smoothEnd,
 sample(coordinate){
  if(!kernel)throw Error('Morphing scene disposed');
  const frame=kernel.invokeValue('demo_sample',[scene,coordinate]);
  const surface=kernel.invokeValue('demo_surface',[scene,coordinate,frame.scale]);
  const rows=[];for(let row=0;row<128;row++)rows.push(kernel.invokeValue('demo_row',[surface,row]));
  return {...frame,vertices:rows.flat()};
 },
 dispose(){scene=null;kernel=null;instance=null;}});
}
'''
NODE='''import {readFile} from 'node:fs/promises';import {pathToFileURL} from 'node:url';import assert from 'node:assert/strict';
const base=process.argv[2];globalThis.fetch=async url=>new Response(await readFile(url));const {loadMorphingDemo}=await import(pathToFileURL(base+'/morphing-demo.mjs'));
const modes=[];for(const mode of [0,1])for(const start of [false,true])for(const end of [false,true]){
 const scene=await loadMorphingDemo(16,mode,start,end);const frame=scene.sample(.5);assert.equal(frame.coverage.length,256);assert(frame.vertices.length>0&&frame.vertices.length%18===0&&frame.vertices.every(Number.isFinite));assert(frame.coverage.every(x=>Number.isFinite(x)&&x>=0&&x<=1));assert.throws(()=>scene.sample(-1));assert.equal(scene.sample(0).coverage.length,256);scene.dispose();modes.push({mode,start,end});}
console.log(JSON.stringify({passed:true,options:modes,invalidCoordinateRejected:true,recovery:true}));
'''
BROWSER='''const {chromium}=require(process.argv[2]);(async()=>{const browser=await chromium.launch({executablePath:process.argv[3],headless:true,args:['--no-sandbox','--disable-gpu']});try{const page=await browser.newPage();await page.goto(process.argv[4]);await page.waitForFunction(()=>window.loadMorphingDemo);const report=await page.evaluate(async()=>{const scene=await window.loadMorphingDemo(24,1,true,true);const frames=[];for(const q of [0,.5,1,1.5,2]){const start=performance.now();const f=scene.sample(q);if(f.coverage.length!==576||f.coverage.some(x=>!Number.isFinite(x)||x<0||x>1))throw Error('invalid frame');frames.push({q,measure:f.measure,milliseconds:performance.now()-start});}let rejected=false;try{scene.sample(-1)}catch{rejected=true}if(!rejected||scene.sample(0).coverage.length!==576)throw Error('recovery failed');scene.dispose();let disposed=false;try{scene.sample(0)}catch{disposed=true}if(!disposed)throw Error('disposed scene remains callable');return{passed:true,frames,recovery:true,disposed:true};});console.log(JSON.stringify(report));}finally{await browser.close()}})().catch(e=>{console.error(e);process.exit(1)});
'''
if __name__=='__main__':main()
