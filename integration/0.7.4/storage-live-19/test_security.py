"""Synthetic parser controls only; no runtime qualification credit."""
import copy,json,os
from preflight import save
from validate_security import validate_security
status=dict(Uid=[str(os.getuid())]*4,Gid=[str(os.getgid())]*4,Groups=['1000'],Threads=['1'],NoNewPrivs=['0'],**{k:['0000000000000000'] for k in ['CapInh','CapPrm','CapEff','CapAmb','CapBnd']})
def diag(kind,stage,label):return dict(private_workload_security=kind,stage=stage,label=label,status=copy.deepcopy(status),observation_errors=[])
a=[diag('origin-capability-drop-before','origin','unconfined'),diag('origin-capability-drop-after','origin','unconfined'),diag('policy-gate','origin','unconfined'),diag('policy-gate','pre','vkf-storage-pre-v2 (enforce)'),diag('policy-gate','post','bwrap//&unpriv_bwrap (enforce)')]
a[1].update(passed=True,error=None);a[4]['status']['NoNewPrivs']=['1']
def check(d):return validate_security('\n'.join(json.dumps(x) for x in d[:3]),d[3:])
assert len(check(a))==5
negatives=[]
for label in ['vkf-storage-pre-v1 (enforce)','vkf-storage-pre-v2//&bwrap (enforce)','unconfined','vkf-storage-pre-v2 (complain)']:
 b=copy.deepcopy(a);b[3]['label']=label;negatives.append(b)
for i in range(5):
 b=copy.deepcopy(a);b[i]['observation_errors']=['missing'];negatives.append(b)
for i in [1,2,3,4]:
 b=copy.deepcopy(a);b[i]['status']['CapInh']=['0000000000000001'];negatives.append(b)
for i in range(5):
 b=copy.deepcopy(a);del b[i];negatives.append(b)
for b in negatives:
 try:check(b)
 except (AssertionError,KeyError):pass
 else:raise AssertionError('Invalid diagnostics accepted')
save('security-parser-tests.json',dict(positive=1,negative=len(negatives),passed=True,runtime_qualification=False))
print('PASS: strict v2-only labels, missing records/errors/capabilities rejected')
