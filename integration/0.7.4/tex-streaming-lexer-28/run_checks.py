"""Sequential ordinary checks: <=512 MiB address space, <=60s wall, joined."""
from pathlib import Path
import json,os,resource,signal,subprocess,sys,time
H=Path(__file__).resolve().parent;R=H.parents[2]
label=sys.argv[1]
def limits():
 resource.setrlimit(resource.RLIMIT_AS,(512*1024*1024,)*2)
 resource.setrlimit(resource.RLIMIT_CPU,(55,)*2)
 resource.setrlimit(resource.RLIMIT_CORE,(0,0))
steps=[('model',[sys.executable,'-B',str(H/'test_reference.py')])]
if label.startswith('final'):
 steps += [('source',[sys.executable,'-B',str(H/'verify_source.py')]),('origin-bridge',['node','--jitless','--max-old-space-size=160','--max-semi-space-size=4',str(H/'test_origin_bridge.mjs')]),('patch',['git','apply','--check','--whitespace=error-all',str(H/'streaming-mouth.patch')])]
records=[]
for name,args in steps:
 before=time.monotonic();timedout=False
 with (H/f'{label}-{name}.stdout').open('xb') as out,(H/f'{label}-{name}.stderr').open('xb') as err:
  p=subprocess.Popen(args,cwd=R,stdout=out,stderr=err,start_new_session=True,preexec_fn=limits,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PATH':'/home/viktor/.local/bin:'+os.environ['PATH']})
  try:p.wait(timeout=60)
  except subprocess.TimeoutExpired:
   timedout=True;os.killpg(p.pid,signal.SIGKILL);p.wait()
 records.append(dict(name=name,argv=args,pid=p.pid,exit=p.returncode,seconds=time.monotonic()-before,joined=True,timeout=timedout,as_limit_bytes=512*1024*1024))
 if p.returncode!=0:break
result=dict(stages=records,passed=len(records)==len(steps) and all(x['exit']==0 for x in records),all_children_joined=True,native_executed=False,child_maxrss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)
(H/f'{label}-results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));sys.exit(0 if result['passed'] else 1)
