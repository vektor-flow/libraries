"""Read-only controls using captured already-joined F cases; no launch or replay."""
import copy,json,resource
from preflight import OUT,save,pinned_json
from validate_fixture import validate_fixture
resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2));resource.setrlimit(resource.RLIMIT_CPU,(20,20))
fixtures={}
for mode in ['success','nonzero','timeout']:
 r=json.loads((OUT/('live24-f-'+mode+'-01-observation.json')).read_text());m=pinned_json(r['phase']['manifest']);records=[json.loads(x) for x in r['payload_stdout'].splitlines() if x.strip()]
 from pathlib import Path
 payload=Path(m['output_paths'][0]).read_bytes();assert validate_fixture(records,mode,m,payload)
 fixtures[mode]=(records,m,payload)
neg=[]
def bad(name,mode,mutate):
 records,m,payload=copy.deepcopy(fixtures[mode]);mutate(records)
 try:validate_fixture(records,mode,m,payload)
 except (AssertionError,KeyError,ValueError,TypeError):neg.append(name)
 else:raise AssertionError('invalid fixture accepted '+name)
for mode in fixtures:
 bad(mode+' missing output',mode,lambda r:r.pop())
 bad(mode+' duplicate report',mode,lambda r:r.append(copy.deepcopy(r[9])))
 bad(mode+' wrong mode',mode,lambda r:r[9].update(mode='bogus'))
 bad(mode+' readonly false',mode,lambda r:r[9].update(outside_readonly=False))
 bad(mode+' missing pre',mode,lambda r:r.__setitem__(0,{}))
 bad(mode+' missing post',mode,lambda r:r.__setitem__(4,{}))
 bad(mode+' wrong mount hash',mode,lambda r:r[9]['effective_storage'].update(mountinfo_sha256='0'*64))
 records,m,payload=fixtures[mode]
 try:validate_fixture(records,mode,m,b'')
 except AssertionError:neg.append(mode+' missing payload')
 else:raise AssertionError('missing payload accepted')
bad('missing fork child','timeout',lambda r:r.pop())
bad('wrong child PID','timeout',lambda r:r[11].update(namespace_pid=999))
bad('both fork returns nonzero','timeout',lambda r:r[11].update(namespace_child=999))
bad('parent self-child','timeout',lambda r:r[10].update(namespace_child=r[10]['namespace_pid']))
bad('extra fork field','timeout',lambda r:r[10].update(extra=True))
# Both parent/child scheduling orders are valid.
r,m,p=copy.deepcopy(fixtures['timeout']);r[10:]=r[10:][::-1];assert validate_fixture(r,'timeout',m,p)
save('fixture-parser-tests.json',dict(passed=True,positive=4,negative=len(neg),cases=neg,already_captured_only=True,new_attempts=0))
print('PASS: 4 captured-record positives and',len(neg),'negatives; no new attempt')
