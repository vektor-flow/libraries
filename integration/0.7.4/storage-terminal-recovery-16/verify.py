"""Bounded foreground runner; all artifacts and children owned by recovery16."""
from pathlib import Path
import datetime,hashlib,json,os,resource,subprocess,time
O=Path(__file__).resolve().parent
log=[]
for name in ('test_recovery16.py','read_only.py'):
 start=time.monotonic()
 with (O/(name+'.stdout')).open('w') as out,(O/(name+'.stderr')).open('w') as err:
  p=subprocess.Popen(['/usr/bin/python3','-B',str(O/name)],stdout=out,stderr=err,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
  try:
   stat=Path(f'/proc/{p.pid}/stat').read_text();ident=dict(pid=p.pid,starttime=int(stat[stat.rindex(')')+2:].split()[19]))
  except FileNotFoundError:ident=dict(pid=p.pid,starttime=None)
  try:code=p.wait(timeout=90)
  except subprocess.TimeoutExpired:p.kill();code=p.wait();raise
 log.append(dict(command=name,identity=ident,exit=code,seconds=time.monotonic()-start,joined=True,proc_absent=not Path(f'/proc/{p.pid}').exists()))
 (O/'verification.json').write_text(json.dumps(dict(children=log,max_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,utc=datetime.datetime.now(datetime.timezone.utc).isoformat()),indent=2)+'\n')
 if code:raise SystemExit(code)
print('bounded tests and readonly check passed; children joined')
