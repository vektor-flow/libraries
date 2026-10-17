"""Sequential bounded read-only tests. Logs are written only in this output."""
from pathlib import Path
import json,os,resource,signal,subprocess,sys,time
H=Path(__file__).resolve().parent;R=H.parents[2];P=H.parent/'tex-streaming-lexer-28'
label=sys.argv[1]
def limits():
 resource.setrlimit(resource.RLIMIT_AS,(512*1024*1024,)*2)
 resource.setrlimit(resource.RLIMIT_CPU,(55,)*2)
 resource.setrlimit(resource.RLIMIT_CORE,(0,0))
steps=[('review',[sys.executable,'-B',str(H/'test_review.py')],R),
 ('transport',['node','--jitless','--max-old-space-size=160','--max-semi-space-size=4',str(H/'test_transport.mjs')],R),
 ('original-model',[sys.executable,'-B',str(P/'test_reference.py')],R),
 ('original-source',[sys.executable,'-B',str(P/'verify_source.py')],R),
 ('original-host',['node','--jitless','--max-old-space-size=160','--max-semi-space-size=4',str(P/'test_origin_bridge.mjs')],R),
 ('combined-patch',['git','apply','--check','--whitespace=error-all',str(H/'review30-combined-threefile.patch')],R),
 ('delta-patch',['git','apply','--check','--unsafe-paths','--whitespace=error-all','--directory='+str(P/'candidate'),str(H/'review30-after-tsl28.patch')],R)]
records=[]
for name,args,cwd in steps:
 start=time.monotonic();timeout=False
 with (H/f'{label}-{name}.stdout').open('xb') as out,(H/f'{label}-{name}.stderr').open('xb') as err:
  p=subprocess.Popen(args,cwd=cwd,stdout=out,stderr=err,start_new_session=True,preexec_fn=limits,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PATH':'/home/viktor/.local/bin:'+os.environ['PATH']})
  try:p.wait(timeout=60)
  except subprocess.TimeoutExpired:timeout=True;os.killpg(p.pid,signal.SIGKILL);p.wait()
 records.append(dict(name=name,argv=args,pid=p.pid,exit=p.returncode,seconds=time.monotonic()-start,joined=True,timeout=timeout,as_limit_bytes=536870912))
 if p.returncode:break
result=dict(passed=len(records)==len(steps) and all(x['exit']==0 for x in records),stages=records,child_maxrss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,all_children_joined=True,native_executed=False,tex_executed=False)
(H/f'{label}-results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));sys.exit(0 if result['passed'] else 1)
