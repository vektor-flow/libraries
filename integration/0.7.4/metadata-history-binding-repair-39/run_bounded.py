"""Sequential host runner. 512MiB AS, 50 CPU seconds, 55s wall alarm, all children joined."""
import json,os,resource,runpy,signal,subprocess,sys,time,traceback
from pathlib import Path
H=Path(__file__).resolve().parent
ALLOWED={'build_packet.py','seal_source.py','test_controls.py','verify_packet.py','describe_packet.py','final_verify.py','independent_verify.py','audit_history.py','test_relocation.py'}
def child(name):
 resource.setrlimit(resource.RLIMIT_AS,(512*2**20,)*2)
 resource.setrlimit(resource.RLIMIT_CPU,(50,50));resource.setrlimit(resource.RLIMIT_CORE,(0,0))
 sys.dont_write_bytecode=True
 os.environ['PYTHONDONTWRITEBYTECODE']='1';os.environ['TMPDIR']=str(H)
 started=time.monotonic();children=[];original=subprocess.Popen
 class JoinedPopen(original):
  def __init__(self,*args,**kwargs):
   super().__init__(*args,**kwargs);children.append(self)
 subprocess.Popen=JoinedPopen
 def alarm(*args):raise TimeoutError('bounded host wall time exceeded')
 signal.signal(signal.SIGALRM,alarm);signal.alarm(55)
 success=False;code=1
 try:
  runpy.run_path(str(H/name),run_name='__main__');success=True;code=0
 except SystemExit as e:
  code=e.code or 0;success=code==0
 except BaseException:traceback.print_exc()
 finally:
  signal.alarm(0);rows=[]
  for p in children:
   unexpected=p.poll() is None
   if unexpected:p.kill();success=False;code=1
   p.wait(timeout=2)
   rows.append(dict(pid=p.pid,argv=p.args,exit=p.returncode,joined=True,absent=not Path('/proc',str(p.pid)).exists(),unexpected_live_child=unexpected))
  report=dict(script=name,passed=success,exit=code,seconds=time.monotonic()-started,limit_address_space_bytes=512*2**20,wall_limit_seconds=55,children=rows,all_children_joined=all(r['joined'] and r['absent'] for r in rows),peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,peak_child_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,memory=[x for x in Path('/proc/self/status').read_text().splitlines() if x.startswith(('VmHWM:','VmPeak:'))],native_execution=False,task_overlap=0)
  (H/(name+'.bounded.json')).write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
 return code
if __name__=='__main__':
 name=sys.argv[1];assert name in ALLOWED
 if len(sys.argv)==3 and sys.argv[2]=='--child':sys.exit(child(name))
 started=time.monotonic()
 with (H/(name+'.stdout')).open('xb') as out,(H/(name+'.stderr')).open('xb') as err:
  p=subprocess.Popen(['/usr/bin/python3','-I','-B',str(Path(__file__).resolve()),name,'--child'],cwd=H,stdout=out,stderr=err,start_new_session=True)
  try:code=p.wait(timeout=59)
  except BaseException:
   os.killpg(p.pid,signal.SIGKILL);p.wait();raise
 report=dict(script=name,pid=p.pid,exit=code,joined=True,absent=not Path('/proc',str(p.pid)).exists(),seconds=time.monotonic()-started)
 (H/(name+'.runner.json')).write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(report));sys.exit(code)
