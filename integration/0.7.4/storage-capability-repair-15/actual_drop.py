"""Only capability drops in this ordinary, bounded, single-threaded child."""
import json, os, resource, sys
from pathlib import Path
resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2))
resource.setrlimit(resource.RLIMIT_CPU,(10,10))
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
H=Path(__file__).resolve().parent
V=Path('/home/viktor/Projects/Vektor Flow/.coordination/s0-plan-20261012/synchronized-contexts/independent-workers/storage20gb/storage-direct-v6')
sys.path[:0]=[str(H/'proposed'),str(V)]
import private_workload as pw
from storage_paths import Rejected
assert Path(pw.__file__).resolve()==H/'proposed/private_workload.py'
origin=pw.context()
before=pw._security_snapshot()
assert not before['errors']
assert os.getuid()==os.geteuid()!=0 and os.getgid()==os.getegid()!=0
assert all(before['status'][k]==['0000000000000000'] for k in ('CapPrm','CapEff','CapAmb'))
assert before['status']['NoNewPrivs']==['0']
assert before['status']['CapInh']==['0000000800000000'], 'expected observed parent inheritable bit not present; do not synthesize it'
try:pw.policy_gate('origin',origin)
except Rejected as e:assert str(e)=='nonzero CapInh'
else:raise AssertionError('strict origin gate accepted nonzero inheritable set')
pw.initialize_origin_capabilities(origin)
passed=pw.policy_gate('origin',origin)
after=pw._security_snapshot()
assert all(after['status'][k]==['0000000000000000'] for k in ('CapInh','CapPrm','CapEff','CapAmb'))
for k in ('Uid','Gid','Groups','Threads','CapBnd','NoNewPrivs'):assert after['status'][k]==before['status'][k],k
assert pw.context()==origin
pw.initialize_origin_capabilities(origin)
again=pw._security_snapshot()
assert not again['errors'] and again['label']==after['label']
for k in ('Uid','Gid','Groups','Threads','CapInh','CapPrm','CapEff','CapAmb','CapBnd','NoNewPrivs'):
 assert again['status'][k]==after['status'][k], k
assert pw.context()==origin
pw.policy_gate('origin',origin)
print(json.dumps(dict(actual_drop_test='passed',pid=os.getpid(),origin=origin,before=before,after=after,origin_gate=passed,idempotent=True,namespace_or_service_created=False)))
