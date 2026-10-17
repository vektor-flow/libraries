import json,os,resource,subprocess,time,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
name=sys.argv[1] if len(sys.argv)>1 else 'tests01'
def limit():
 resource.setrlimit(resource.RLIMIT_AS,(512*1024*1024,512*1024*1024))
 resource.setrlimit(resource.RLIMIT_CPU,(20,20))
 resource.setrlimit(resource.RLIMIT_CORE,(0,0))
def identity(pid):
 try:
  fields=Path('/proc',str(pid),'stat').read_text().rsplit(')',1)[1].split()
  return dict(pid=pid,starttime=int(fields[19]))
 except FileNotFoundError:return None
start=time.monotonic();command=['/usr/bin/python3','-B',str(HERE/'test_trust.py')]
child=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,preexec_fn=limit,text=True)
saved=identity(child.pid)
try:stdout,stderr=child.communicate(timeout=35)
except subprocess.TimeoutExpired:
 child.kill();stdout,stderr=child.communicate();stderr+='\nTEST WALL TIMEOUT\n'
after=identity(child.pid)
assert after is None or after!=saved
(HERE/(name+'.stdout')).write_text(stdout);(HERE/(name+'.stderr')).write_text(stderr)
result=dict(command=command,pid=saved,exit=child.returncode,elapsed=time.monotonic()-start,joined=True,after=after,
 peak_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,limits=dict(AS=512*1024*1024,CPU=20,wall=35),
 runtime_namespace_operations=0,operational_mutations=0)
(HERE/(name+'.json')).write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result));print(stderr[-7000:]);sys.exit(child.returncode)
