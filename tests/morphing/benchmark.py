"""Native CPU workload benchmark; process wall time, not render/GPU timing."""
from pathlib import Path
import argparse, hashlib, json, platform, shutil, statistics, subprocess, time
p=argparse.ArgumentParser();p.add_argument('--compiler',type=Path,required=True);p.add_argument('--library',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--runs',type=int,default=7);a=p.parse_args()
out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
shutil.copy2(a.library/'Morphing.vkf',out/'Morphing.vkf');shutil.copytree(a.library/'morphing',out/'morphing')
cases=[('prepare',32,256,100),('sample',32,256,2000),('lookup',1024,1,10000),('channel',32,1024,8)]
report={'scope':'Warm native CPU process wall time including launch and fixture setup; compilation excluded; no renderer or GPU. One untimed warmup, seven timed runs by default.','platform':platform.platform(),'cpu':next((line.split(':',1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines() if line.startswith('model name')),platform.processor()),'compiler_sha256':hashlib.sha256(a.compiler.read_bytes()).hexdigest(),'sources':{f:hashlib.sha256((out/f).read_bytes()).hexdigest() for f in ['Morphing.vkf','morphing/state.vkf']},'cases':[]}
for kind,count,width,repeats in cases:
 for mode in [0,1]:
  name=f'{kind}-{mode}'
  text=f'''m:.Morphing
run()->num:
    [num] knots:[0:{count}]
    [num] values:[0:{count*width}]
    i:0
    i<{count}?>
        knots.(i):i*1.0
        .i:i+1
    .i:0
    i<{count*width}?>
        values.(i):(i%31)*0.125
        .i:i+1
    plan:m.prepare(knots,values,{width},{mode},true,true)
    [num] coordinates:[0:256]
    .i:0
    i<256?>
        coordinates.(i):i*({count}-1)/255.0
        .i:i+1
    checksum:0.0
    .i:0
    i<{repeats}?>
'''
  if kind=='prepare':text+=f'        next:m.prepare(knots,values,{width},{mode},true,true)\n        .checksum:checksum+next.curve.second.((i%{count})*{width})\n'
  elif kind=='channel':text+=f'        next:m.channel(plan,coordinates,i%{width})\n        .checksum:checksum+next.(i%256)\n'
  else:text+=f'        next:m.sample(plan,(i%997)*({count}-1)/996.0)\n        .checksum:checksum+next.value.(i%{width})+next.first.(i%{width})+next.second.(i%{width})\n'
  text+='        .i:i+1\n    @:checksum\n::run()\n'
  src=out/(name+'.vkf');src.write_text(text);binary=out/name
  build=subprocess.run([str(a.compiler),'-b',str(src),'-o',str(binary)],capture_output=True,text=True,timeout=180)
  (out/(name+'-build.log')).write_text(build.stdout+build.stderr);assert build.returncode==0,build.stderr
  times=[];checks=[]
  for run in range(a.runs+1):
   start=time.perf_counter_ns();r=subprocess.run([str(binary)],capture_output=True,text=True,timeout=120);elapsed=(time.perf_counter_ns()-start)/1e6
   assert r.returncode==0,r.stderr
   checks.append(r.stdout.strip())
   if run:times.append(elapsed)
  assert len(set(checks))==1
  row={'case':name,'states':count,'channels':width,'iterations':repeats,'coordinates_per_iteration':256 if kind=='channel' else 1,'milliseconds':times,'median_ms':statistics.median(times),'checksum':checks[0]}
  report['cases'].append(row);print(name,round(row['median_ms'],3),'ms',flush=True)
  (out/'benchmark.json').write_text(json.dumps(report,indent=2)+'\n')
