"""Read-only real-state validation and explicitly in-memory successor projection.
Real joins only; no operational state/authority/grant/setup writes, no launches.
"""
import argparse,copy,hashlib,json,os,pathlib,resource,time
from unittest.mock import patch
import preflight as p
import rotate_owners as rot
import qualify as q
import publication as pub
import storage_admission as adm
from storage_controller import Controller, HELPERS
resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2))
resource.setrlimit(resource.RLIMIT_CPU,(30,30))
start=time.monotonic()
pre,auth,authority,cp,c,real,before,adapter,owner_bytes=rot.validate_before()
statepin=p.pin(real.state);ownerpin=p.pin(pathlib.Path(c['owner_state']))
assert before==json.loads((p.OUT.parent/'storage-live-13/final-state.json').read_text())
receipt=json.loads((p.OUT.parent/'storage-live-13/final-owner-state.json').read_text())
assert receipt['pin']==ownerpin and receipt['state']==json.loads(owner_bytes)
# Authenticate reviewed schemas and context receipts, without copying old authority.
contexts=[]
for d,names in {
 'storage-live-12':['HANDOFF.txt','api-review.json','read-only-seal.json','final-owner-state.json'],
 'storage-live-13':['HANDOFF.txt','root-wrapper-review.json','root-corrected-rotate_owners.py'],
 'storage-policy-setup-11':['HANDOFF.txt','REVIEW.txt','SYSTEM-SETUP.txt','root-installed.json','root-loaded-new-policy-check.json','root-loaded-uncompressed-comparison.json'],
 'storage-propagation-repair-10':['SUCCESSOR.txt'],
 'storage-live-09':['HANDOFF.txt'],
 'storage-mount-repair-08':['fixture.py','effective_storage.py']}.items():
 for n in names:contexts.append(p.pin(p.OUT.parent/d/n))
review=json.loads((p.OUT.parent/'storage-live-13/root-wrapper-review.json').read_text())
assert p.pin(p.OUT.parent/'storage-live-13/root-corrected-rotate_owners.py')['sha256']==review['candidate_sha256']
objects={}
def writer(path,obj):
 assert path.is_relative_to(rot.SETUP) and not path.exists()
 raw=(json.dumps(obj,indent=2)+'\n').encode();pp=dict(path=str(path),sha256=hashlib.sha256(raw).hexdigest())
 assert str(path) not in objects;objects[str(path)]=(pp,raw)
 return pp
def verify(pp):
 if pp['path'] in objects:
  ref,raw=objects[pp['path']];assert pp==ref;return raw
 return p.pinned(pp)
def loader(pp):return json.loads(verify(pp))
# Projection invokes unchanged API validation on memory only. No join mocked.
from contextlib import contextmanager
class Projection(adm.Ledger):
 def __init__(self):
  super().__init__(real.state,real.lock,recovery_pin=real.recovery_pin)
  self.memory=copy.deepcopy(before)
 @contextmanager
 def transaction(self,**kwargs):yield copy.deepcopy(self.memory)
 def save(self,data,**kwargs):self.memory=copy.deepcopy(data)
projection=Projection();joins=[]
r=before['phases']['F:live09-f-success-01'];gp,mp=r['grant'],r['manifest']
ctrl=Controller(argparse.Namespace(config_sha256=cp['sha256'],grant=pathlib.Path(gp['path']),grant_sha256=gp['sha256'],manifest=pathlib.Path(mp['path']),manifest_sha256=mp['sha256']))
def real_join(row,receipt):
 t=time.monotonic();ok=ctrl.verify_join(row,receipt);assert ok and row['inner_result']['exit']==1
 joins.append(dict(verified=ok,seconds=time.monotonic()-t,join=row['join']))
 return ok
with patch.object(adm,'pinned_json',loader),patch.object(adm,'pinned',verify):
 fp=writer(rot.SETUP/'F-owner-transition.json',rot.transition('F','joined',before,c,auth,prior_phase='F:live09-f-success-01',prior_join=r['join']))
 projection.rotate_owner(fp,verify_join=real_join)
 afterf=copy.deepcopy(projection.memory)
 snap=writer(rot.SETUP/'unused-A-state-after-F.json',afterf)
 ap=writer(rot.SETUP/'A-owner-transition.json',rot.transition('A','unused-owner-revocation',afterf,c,auth,unused_state=snap,phase_sequence=len(afterf['phases'])))
 projection.rotate_owner(ap,verify_join=real_join)
 data=projection.memory;projection.check(data)
 assert len(joins)==1 and all(projection.owner(data,w)==p.OWNER for w in 'FA')
 assert data['phases']==before['phases'] and data['recovery_events']==before['recovery_events']
 transitions=dict(F=fp,A=ap)
 records,desired=q.build_plan(data,transitions,owner_bytes,writer)
 pub.validate_selection(data,c,desired,'initial',records,owner_bytes,transitions,auth,loader,verify)
 expected=(json.dumps(desired,indent=2)+'\n').encode()
 for rec in records:
  g,m=loader(rec['grant']),loader(rec['manifest'])
  assert len(g['helpers'])==5 and g['phase_bytes']==4194304 and 0<g['timeout_seconds']<=10
  assert g['qualification_limits']==dict(max_attempts=16,consumed_before_live14=3,total_bytes=67108864,consumed_bytes_before_live14=12582912,max_phase_bytes=4194304)
  assert m['grant']==rec['grant'] and m['controller']==g['controller']
  for k in ('owner','worker','iteration','attempt','phase_scope','phase_bytes','ram_peak_bytes','timeout_seconds','source_commit','inputs','argv'):assert m[k]==g[k]
  assert g['storage_policy'] in c['approved_policies'] and g['owner_transition']==transitions[g['worker']]
  assert g['argv'][2]==str(p.REPAIR/'fixture.py') and g['argv'][3]==rec['mode']
  assert not pathlib.Path(m['attempt_root']).exists()
  for k in ('cwd','tmpdir','cache','ccache','receipts'):
   assert pathlib.Path(m[k]).is_relative_to(m['attempt_root'])
  nextowners=copy.deepcopy(desired);nextowners['workers'][rec['worker']]=dict(thread=p.OWNER,iteration=14,grant=rec['grant'])
  pub.validate_selection(data,c,nextowners,rec['attempt'],[rec],expected,transitions,auth,loader,verify)
  expected=(json.dumps(nextowners,indent=2)+'\n').encode();desired=nextowners
assert real.snapshot()==before and p.pin(real.state)==statepin and p.pin(pathlib.Path(c['owner_state']))==ownerpin
assert not rot.SETUP.exists()
for path in p.OUT.glob('*.py'):compile(path.read_text(),str(path),'exec')
p.save('reviewed-context-pins.json',contexts)
p.save('dry-validation.json',dict(passed=True,operational_writes=0,operational_setup_absent=True,real_config=cp,real_state=statepin,real_owners=ownerpin,receipt_schema='pin,state',real_independent_joins=joins,in_memory_api_projection=True,projected_transitions=[fp,ap],projected_grants=records,publication_selections_validated=7,seconds=time.monotonic()-start))
print('PASS: real state/receipt/config; real join; in-memory API transitions; six grant schemas; seven publication selections; operational state bytes unchanged')
