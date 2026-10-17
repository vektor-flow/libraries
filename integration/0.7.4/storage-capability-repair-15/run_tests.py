"""Sequential bounded ordinary children. No operational or native execution."""
import datetime, hashlib, json, os, resource, signal, subprocess, sys, time
from pathlib import Path
H=Path(__file__).resolve().parent
V=Path('/home/viktor/Projects/Vektor Flow/.coordination/s0-plan-20261012/synchronized-contexts/independent-workers/storage20gb/storage-direct-v6')
def status():
 return {k:v.split() for line in Path('/proc/self/status').read_text().splitlines() for k,_,v in [line.partition(':')] if k in ('Uid','Gid','CapInh','CapPrm','CapEff','CapBnd','CapAmb','NoNewPrivs')}
def pin(p):return dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def ident(pid):
 try:return dict(pid=pid,starttime=int((Path('/proc')/str(pid)/'stat').read_text().rsplit(')',1)[1].split()[19]))
 except FileNotFoundError:return None
name=sys.argv[1] if len(sys.argv)>1 else 'tests02'
assert len(name)==7 and name.startswith('tests') and name[5:].isdigit()
run=H/name;run.mkdir(exist_ok=False)
parent_before=status();records=[]
for name in ('actual_drop.py','test_repair.py'):
 started=time.monotonic();timed_out=False
 with (run/(name+'.stdout')).open('x') as out,(run/(name+'.stderr')).open('x') as err:
  child=subprocess.Popen(['/usr/bin/python3.14','-I','-B',str(H/name)],cwd=H,stdout=out,stderr=err,start_new_session=True)
  identity=ident(child.pid)
  try:code=child.wait(timeout=25)
  except subprocess.TimeoutExpired:
   timed_out=True;os.killpg(child.pid,signal.SIGKILL);code=child.wait(timeout=5)
  finally:
   if child.poll() is None:os.killpg(child.pid,signal.SIGKILL);child.wait(timeout=5)
 record=dict(script=pin(H/name),argv=['/usr/bin/python3.14','-I','-B',str(H/name)],identity=identity,exit=code,timed_out=timed_out,seconds=time.monotonic()-started,waited=True,identity_after=ident(child.pid),peak_children_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)
 records.append(record)
 (run/'joins.json').write_text(json.dumps(records,indent=2)+'\n')
 print(json.dumps(record),flush=True)
 if code or timed_out:break
parent_after=status()
result=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),records=records,parent_before=parent_before,parent_after=parent_after,parent_unchanged=parent_before==parent_after,all_children_waited_and_absent=all(r['waited'] and r['identity_after'] is None for r in records),limits=dict(address_space_bytes=512*1024**2,cpu_seconds={'actual_drop.py':10,'test_repair.py':15},wall_seconds_per_child=25,timeout_cleanup_seconds=5),passed=len(records)==2 and all(r['exit']==0 for r in records) and parent_before==parent_after)
(run/'result.json').write_text(json.dumps(result,indent=2)+'\n')
assert result['passed'] and result['all_children_waited_and_absent'], result
