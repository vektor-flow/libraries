"""No operational writes. Exact real proof plus in-memory v8 API/schema projection."""
import copy,hashlib,json,os,pathlib,resource,time
from unittest.mock import patch
from contextlib import contextmanager
import preflight as p
import rotate_owners as rot
import qualify as q
import publication as pub
import storage_admission as adm
import terminal_recovery as recovery
from storage_controller import HELPERS
resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2))
resource.setrlimit(resource.RLIMIT_CPU,(30,30))
start=time.monotonic()
assert json.loads((p.OUT/'initial-loaded-policy.json').read_text())['exact'] is True
assert json.loads((p.OUT/'security-parser-tests.json').read_text())['passed'] is True
assert json.loads((p.OUT/'publication-tests.json').read_text())['success'] is True
pre,auth,authority,cp,c,real,before,adapter,owner_bytes=rot.validate_before()
statepin=p.pin(real.state);ownerpin=p.pin(pathlib.Path(c['owner_state']))
assert before==json.loads((p.OUT.parent/'storage-live-17/final-state.json').read_text())
receipt=json.loads((p.OUT.parent/'storage-live-17/final-owner-state.json').read_text())
assert receipt['pin']==ownerpin and receipt['state']==json.loads(owner_bytes)
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
class Projection(adm.Ledger):
 def __init__(self):
  super().__init__(real.state,real.lock,recovery_pin=real.recovery_pin);self.memory=copy.deepcopy(before);self.precommit_checks=0
 @contextmanager
 def transaction(self,**kwargs):yield copy.deepcopy(self.memory)
 def save(self,data,**kwargs):
  if kwargs.get('before_publish'):
   kwargs['before_publish']();self.precommit_checks+=1
  self.memory=copy.deepcopy(data)
projection=Projection()
with patch.object(adm,'pinned_json',loader),patch.object(adm,'pinned',verify),patch.object(recovery,'pinned',verify):
 fp=writer(rot.SETUP/'F-owner-transition.json',rot.ftransition(before,c,auth))
 projection.rotate_owner(fp,verify_join=rot.verify_normal_join)
 afterf=copy.deepcopy(projection.memory)
 snap=writer(rot.SETUP/'unused-A-state-after-F.json',afterf)
 ap=writer(rot.SETUP/'A-owner-transition.json',rot.transition('A','unused-owner-revocation',afterf,c,auth,unused_state=snap,phase_sequence=5))
 projection.rotate_owner(ap,verify_join=rot.forbidden_join)
 data=projection.memory;projection.check(data)
 assert projection.precommit_checks==0 and all(projection.owner(data,w)==p.OWNER for w in 'FA')
 assert data['phases']==before['phases'] and data['recovery_events']==before['recovery_events']
 transitions=dict(F=fp,A=ap)
 records,desired=q.build_plan(data,transitions,owner_bytes,writer)
 pub.validate_selection(data,c,desired,'initial',records,owner_bytes,transitions,auth,loader,verify)
 expected=(json.dumps(desired,indent=2)+'\n').encode()
 for rec in records:
  g,m=loader(rec['grant']),loader(rec['manifest'])
  assert len(g['helpers'])==5 and g['phase_bytes']==4194304 and 0<g['timeout_seconds']<=10
  assert g['qualification_limits']==dict(max_attempts=16,consumed_before_live19=5,total_bytes=67108864,consumed_bytes_before_live19=20971520,max_phase_bytes=4194304)
  assert m['grant']==rec['grant'] and m['controller']==g['controller']
  for k in ('owner','worker','iteration','attempt','phase_scope','phase_bytes','ram_peak_bytes','timeout_seconds','source_commit','inputs','argv'):assert m[k]==g[k]
  assert g['storage_policy'] in c['approved_policies'] and g['owner_transition']==transitions[g['worker']]
  assert g['argv'][2]==str(p.REPAIR/'fixture.py') and g['argv'][3]==rec['mode']
  assert not pathlib.Path(m['attempt_root']).exists()
  paths=[pp['path'] for pp in g['inputs']]
  assert any('/ctypes/__init__.py' in path for path in paths) and any('/_ctypes.' in path for path in paths) and any('/libffi.so.' in path for path in paths)
  assert c['recovery_authority'] in g['inputs']
  for k in ('cwd','tmpdir','cache','ccache','receipts'):assert pathlib.Path(m[k]).is_relative_to(m['attempt_root'])
  nextowners=copy.deepcopy(desired);nextowners['workers'][rec['worker']]=dict(thread=p.OWNER,iteration=19,grant=rec['grant'])
  pub.validate_selection(data,c,nextowners,rec['attempt'],[rec],expected,transitions,auth,loader,verify)
  expected=(json.dumps(nextowners,indent=2)+'\n').encode();desired=nextowners
assert real.snapshot()==before and p.pin(real.state)==statepin and p.pin(pathlib.Path(c['owner_state']))==ownerpin
assert not rot.SETUP.exists()
for path in p.OUT.glob('*.py'):compile(path.read_text(),str(path),'exec')
p.save('dry-validation.json',dict(passed=True,operational_writes=0,operational_setup_absent=True,real_config=cp,real_state=statepin,real_owners=ownerpin,receipt_schema='pin,state',real_independent_join_calls=rot.join_calls,real_fresh_terminal_checks=True,in_memory_api_projection=True,real_precommit_check=False,normal_F_succession=True,projected_transitions=[fp,ap],projected_grants=records,publication_selections_validated=7,seconds=time.monotonic()-start))
p.save('dry-script-pins.json',[p.pin(path) for path in p.OUT.glob('*.py')])
print('PASS: exact real v8 state/owner/authority/normal join; joined-F API projection; unused-A projection; six fresh schemas; seven selections; operational bytes unchanged')
