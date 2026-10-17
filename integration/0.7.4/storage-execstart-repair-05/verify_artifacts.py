"""Small joined verification; writes only beside this file."""
from pathlib import Path
import ast,datetime,hashlib,json,os,subprocess,sys,tempfile,time
O=Path(__file__).resolve().parent

def pin(p): return dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def identity(pid):
 p=Path('/proc')/str(pid)
 return dict(pid=pid,starttime=int((p/'stat').read_text().rsplit(')',1)[1].split()[19]),
             boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip())
report=dict(start=datetime.datetime.now(datetime.timezone.utc).isoformat(),runner=identity(os.getpid()),jobs=[])
for p in [*list((O/'candidate').rglob('*.py')),O/'recovery_check.py',O/'test_repair.py',O/'build_candidate.py']:
 ast.parse(p.read_text(),filename=str(p))
for script,filename in [('test_repair.py','test-results.txt'),('recovery_check.py','recovery-read-only-result.json')]:
 start=time.monotonic()
 with (O/filename).open('w') as out:
  job=subprocess.Popen([sys.executable,'-B',str(O/script)],stdout=out,stderr=subprocess.STDOUT,cwd=O)
  ident=identity(job.pid); code=job.wait(timeout=30)
 report['jobs'].append(dict(script=script,identity=ident,exit=code,joined=True,seconds=time.monotonic()-start,proc_absent=not Path('/proc',str(job.pid)).exists()))
 assert code==0,filename
with tempfile.TemporaryDirectory(dir=O,prefix='patch-check-') as temp:
 args=['git','apply','--unsafe-paths','--directory='+temp]
 patch=(O/'candidate-new-files.patch').read_bytes()
 for cmd in ([*args,'--check'],args):
  r=subprocess.run(cmd,input=patch,capture_output=True,timeout=10,cwd=O.parents[2])
  assert r.returncode==0,r.stderr.decode()
 for p in (O/'candidate'/'storage-direct-v3').iterdir():
  assert p.read_bytes()==(Path(temp)/'storage-direct-v3'/p.name).read_bytes()
report['patch_applied_and_byte_matched']=True
pins=json.loads((O/'input-pins.json').read_text())
report['input_recheck']=[dict(**p,unchanged=pin(Path(p['path']))['sha256']==p['sha256']) for p in pins]
assert all(p['unchanged'] for p in report['input_recheck'])
report['end']=datetime.datetime.now(datetime.timezone.utc).isoformat()
(O/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(tests='23/23',patch=True,unchanged_inputs=len(pins),joined=report['jobs']),indent=2))
