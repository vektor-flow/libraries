"""Real immutable pins, isolated writable ledger, synthetic root authority/custody.
No test authority is operational. Target mapping is mocked only in this harness.
"""
from pathlib import Path
import copy,hashlib,json,os,sys,tempfile,unittest
from unittest.mock import patch
O=Path(__file__).resolve().parent
I=Path(json.loads((O/'input-pins.json').read_text())[0]['path']).parent
sys.path[:0]=[str(O/'candidate'),str(I)]
import terminal_recovery as tr
import storage_admission as sa
from storage_paths import Rejected,pinned_json
BASE,R,_,OWNERS=tr.live14_sources()
PROOF=json.loads((O/'readonly-observation.json').read_text())['proof']
REAL_STATE,REAL_LOCK=tr.LIVE14_STATE,tr.LIVE14_LOCK
LEGACY=tr.LIVE14_ANCHORS['legacy_authority']
REAL_AUTH=tr.authority
REAL_OBSERVE=tr.observe_live14

class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(prefix='isolated-',dir=O);self.addCleanup(self.tmp.cleanup)
  self.root=Path(self.tmp.name);self.state=self.root/'state.json';self.lock=self.root/'capacity.lock';self.lock.touch()
  self.state.write_text(json.dumps(BASE,sort_keys=True));self.count=0
  self.ownerfile=self.root/'owners.json';self.ownerfile.write_bytes(Path(OWNERS['pin']['path']).read_bytes());self.ownerfile.chmod(0o600)
  self.ownerpin=self.pin_path(self.ownerfile)
  def legacy_auth(pin,state,lock):
   if pin==LEGACY:
    return REAL_AUTH(pin,REAL_STATE,REAL_LOCK)
   return REAL_AUTH(pin,state,lock)
  self.startpatch(patch.object(tr,'authority',side_effect=legacy_auth))
  self.startpatch(patch.object(tr,'LIVE14_STATE',str(self.state)))
  self.startpatch(patch.object(tr,'LIVE14_LOCK',str(self.lock)))
  self.startpatch(patch.object(tr,'live14_current_owner',side_effect=lambda:tr.protected_pin(self.ownerpin)))
  self.observer=self.startpatch(patch.object(tr,'observe_live14',return_value=copy.deepcopy(PROOF)))
  auth=dict(schema=tr.LIVE14_AUTH_SCHEMA,coordinator=tr.ANCHORS['coordinator'],anchors=tr.LIVE14_ANCHORS,
   successor_state=str(self.state),capacity_lock=str(self.lock),predecessor_writers_held=True,external_unit_mutations_excluded=True)
  self.auth=self.pin(auth)
  self.l=sa.Ledger(self.state,self.lock,recovery_pin=self.auth)
  self.check=self.startpatch(patch.object(self.l,'check')) # Physical capacity is not under test here.
 def startpatch(self,p):
  r=p.start();self.addCleanup(p.stop);return r
 def pin_path(self,p):return dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
 def pin(self,data):
  self.count+=1;p=self.root/f'pin{self.count}.json';p.write_text(json.dumps(data,sort_keys=True));p.chmod(0o600);return self.pin_path(p)
 def recover(self):return tr.recover_live14(self.l)
 def reject_unchanged(self,fn):
  before=self.state.read_bytes()
  with self.assertRaises((Rejected,KeyError,ValueError,OSError)):fn()
  self.assertEqual(before,self.state.read_bytes())
 def transition(self,**kw):
  d=self.l.snapshot();rec=d['lanes']['F']
  t=dict(version=sa.VERSION,worker='F',coordinator=tr.ANCHORS['coordinator'],policy=rec['pin'],previous=rec['transitions'][-1],
   from_owner=R['owner'],to_owner='isolated-successor',kind='live14-recovered-terminal-failure',
   prior_phase=tr.LIVE14_KEY,recovery_event=d['recovery_events'][-1]['sha256'],phase_sequence=4)
  t.update(kw);return self.pin(t)
 def rotate(self,t=None):self.l.rotate_owner(t or self.transition(),verify_join=lambda *_:self.fail('no fabricated join callback'))
 def test_append_only_precise_charge_and_failed_phase(self):
  event=self.recover();d=self.l.snapshot()
  self.assertEqual(d['phases'],BASE['phases']);self.assertEqual(d['lanes'],BASE['lanes'])
  self.assertEqual(d['recovery_events'][:-1],BASE['recovery_events']);self.assertEqual(len(d['recovery_events']),2)
  self.assertEqual(tr.canonical(d['recovery_events'][0]),tr.canonical(BASE['recovery_events'][0]))
  self.assertEqual(self.l.active_rows(d),[]);self.assertEqual(event['ram_released'],3*2**30)
  self.assertEqual(d['phases'][tr.LIVE14_KEY]['stage'],'running');self.assertNotIn('join',d['phases'][tr.LIVE14_KEY])
  self.assertEqual(sum(r['phase_bytes'] for r in d['phases'].values()),16*2**20)
  self.assertEqual(d['lanes']['F']['policy']['historical_charge']+sum(r['phase_bytes'] for r in d['phases'].values()),19800301568)
  self.assertFalse(event['passed']);self.assertIsNone(event['workload_result'])
 def test_old_authority_and_old_event_compatibility(self):
  self.assertEqual(tr.validate_state(BASE,LEGACY,self.state,self.lock),{tr.KEY})
  self.assertEqual(self.l.owner(BASE,'A'),R['owner']);self.assertEqual(self.l.owner(BASE,'F'),R['owner'])
  self.recover()
  with self.assertRaises(Rejected):tr.validate_state(self.l.snapshot(),LEGACY,self.state,self.lock)
 def test_exact_full_snapshot_mismatches(self):
  for kind in ('admission','service','phase_charge','prior_charge','owner_chain','policy','join','extra_phase'):
   with self.subTest(kind=kind):
    d=copy.deepcopy(BASE)
    if kind=='admission':d['phases'][tr.LIVE14_KEY]['admission']['available']+=1
    elif kind=='service':d['phases'][tr.LIVE14_KEY]['service']['invocation']='different'
    elif kind=='phase_charge':d['phases'][tr.LIVE14_KEY]['phase_bytes']+=1
    elif kind=='prior_charge':d['phases']['F:live09-f-success-01']['phase_bytes']+=1
    elif kind=='owner_chain':d['lanes']['F']['transitions'].pop()
    elif kind=='policy':d['lanes']['F']['policy']['historical_charge']-=1
    elif kind=='join':d['phases'][tr.LIVE14_KEY]['join']={}
    else:d['phases']['F:extra']=dict(R,sequence=4)
    self.state.write_text(json.dumps(d));self.reject_unchanged(self.recover)
 def test_replay_rejected(self):
  self.recover();self.reject_unchanged(self.recover)
 def test_precise_proof_mismatches(self):
  for field,value in [('boot','other'),('outer_identity',dict(PROOF['outer_identity'],starttime=1)),
   ('inner_identity',dict(PROOF['inner_identity'],pid=1)),('inner_identity',dict(PROOF['inner_identity'],starttime=1)),
   ('cgroup','/wrong'),('lane_cgroups',{'F':'/wrong'}),('outer_absent_before',False),('outer_absent_after',False),
   ('inner_absent_before',False),('inner_absent_after',False),('empty_before',False),('empty_after',False),
   ('lanes_empty_before',False),('lanes_empty_after',False),('payload_files_absent_after',False),('empty_before',1)]:
   with self.subTest(field=field,value=value):
    p=copy.deepcopy(PROOF);p[field]=value;self.observer.return_value=p;self.reject_unchanged(self.recover)
 def test_invocation_exit_and_argv_mismatches(self):
  for key,value in [('InvocationID','new'),('MainPID','123'),('ExecMainPID','123'),('ExecMainStatus','199'),('MemoryMax','1'),('ControlGroup','/other')]:
   with self.subTest(key=key):
    p=copy.deepcopy(PROOF);p['properties_before'][key]=value;self.observer.return_value=p;self.reject_unchanged(self.recover)
  for idx,value in [(1,['/different']), (4,746716256178),(7,4130901),(8,True),(9,199)]:
   with self.subTest(index=idx):
    p=copy.deepcopy(PROOF);raw=json.loads(p['execstart_after']);raw['data'][0][idx]=value;p['execstart_after']=json.dumps(raw)
    self.observer.return_value=p;self.reject_unchanged(self.recover)
 def test_final_descendant_appears(self):
  p=copy.deepcopy(PROOF);p['lanes_empty_after']=False
  self.observer.side_effect=[PROOF,p];self.reject_unchanged(self.recover)
 def test_final_owner_change(self):
  def observation(r):self.ownerfile.write_text('{}');return copy.deepcopy(PROOF)
  self.observer.side_effect=observation;self.reject_unchanged(self.recover)
 def test_owner_already_changed(self):
  self.ownerfile.write_text('{}');self.reject_unchanged(self.recover)
 def test_five_second_deadline(self):
  with patch.object(tr.time,'monotonic',side_effect=[0,6]):self.reject_unchanged(self.recover)
 def test_final_deadline(self):
  with patch.object(tr.time,'monotonic',side_effect=[0,1,6]):self.reject_unchanged(self.recover)
 def test_authority_requires_explicit_exclusion(self):
  d=pinned_json(self.auth);d['external_unit_mutations_excluded']=False;self.l.recovery_pin=self.pin(d)
  self.reject_unchanged(self.recover)
 def test_authority_protection(self):
  Path(self.auth['path']).chmod(0o666);self.reject_unchanged(self.recover)
 def test_wrong_lock_target(self):
  with patch.object(tr,'LIVE14_LOCK',str(self.root/'different')):self.reject_unchanged(self.recover)
 def test_event_tamper_charge_history_and_duplicates(self):
  self.recover();good=self.l.snapshot()
  for kind in ('event','phase','old_event','duplicate','reorder','lane','prior_phase','proof'):
   with self.subTest(kind=kind):
    d=copy.deepcopy(good)
    if kind=='event':d['recovery_events'][1]['ram_released']+=1
    elif kind=='phase':d['phases'][tr.LIVE14_KEY]['phase_bytes']-=1
    elif kind=='old_event':d['recovery_events'][0]['passed']=True
    elif kind=='duplicate':d['recovery_events'].append(d['recovery_events'][1])
    elif kind=='reorder':d['recovery_events'].reverse()
    elif kind=='lane':d['lanes']['F']['transitions'].pop()
    elif kind=='prior_phase':d['phases']['F:live09-f-success-01']['stage']='running'
    else:
     d['recovery_events'][1]['observation']['inner_absent_after']=False
     body={k:v for k,v in d['recovery_events'][1].items() if k!='sha256'};d['recovery_events'][1]['sha256']=tr.digest(body)
    with self.assertRaises((Rejected,KeyError)):self.l.released(d)
 def test_recovered_lifecycle_blocked(self):
  self.recover()
  for method,args,kw in [('claim_launch',[],dict(authenticate=None,host=None)),('attach_service',[],dict(authenticate=None)),
    ('guard_service',[],dict(authenticate=None,host=None)),('finish_service',[{}],dict(authenticate=None)),
    ('preexec',[],dict(authenticate=None,host=None)),('monitor',[],dict(current=None,host_available=None)),
    ('join',[{}],dict(verify_join=None))]:
   with self.subTest(method=method):self.reject_unchanged(lambda:getattr(self.l,method)(tr.LIVE14_KEY,*args,**kw))
 def test_recovered_owner_cannot_reserve_until_succession(self):
  self.recover()
  gp=self.pin(dict(storage_admission_version=sa.VERSION,worker='F'))
  self.reject_unchanged(lambda:self.l.reserve(gp,self.pin({}),current=None,host=None,custody=None))
 def test_exact_succession_preserves_A_and_phases(self):
  self.recover();self.rotate();d=self.l.snapshot()
  self.assertEqual(self.l.owner(d,'F'),'isolated-successor');self.assertEqual(self.l.owner(d,'A'),R['owner'])
  self.assertEqual(d['phases'],BASE['phases']);self.assertEqual(len(d['lanes']['F']['transitions']),4)
  self.assertEqual(d['lanes']['A'],BASE['lanes']['A']);self.assertEqual(d['recovery_events'][0],BASE['recovery_events'][0])
  self.reject_unchanged(lambda:self.rotate())
 def test_successor_fields_mismatch(self):
  self.recover()
  for kw in [dict(prior_phase=tr.KEY),dict(recovery_event='fake'),dict(phase_sequence=3),dict(phase_sequence=True),
    dict(from_owner='fake'),dict(previous=None),dict(prior_join={}),dict(to_owner=R['owner'])]:
   with self.subTest(kw=kw):self.reject_unchanged(lambda:self.rotate(self.transition(**kw)))
 def test_succession_requires_fresh_absence(self):
  self.recover();p=copy.deepcopy(PROOF);p['inner_absent_after']=False;self.observer.return_value=p
  self.reject_unchanged(lambda:self.rotate())
 def test_succession_final_owner_changed(self):
  self.recover();n=[0]
  def observed(r):
   n[0]+=1
   if n[0]==1:self.ownerfile.write_text('{}')
   return copy.deepcopy(PROOF)
  self.observer.side_effect=observed;self.reject_unchanged(lambda:self.rotate())
 def test_old_A_unused_snapshot_prefix_and_new_A_rotation(self):
  self.recover();self.rotate();d=self.l.snapshot();rec=d['lanes']['A'];before=copy.deepcopy(d)
  t=dict(version=sa.VERSION,worker='A',coordinator=tr.ANCHORS['coordinator'],policy=rec['pin'],previous=rec['transitions'][-1],
   from_owner=R['owner'],to_owner='isolated-A-successor',kind='unused-owner-revocation',phase_sequence=4,unused_state=self.pin(before))
  self.l.rotate_owner(self.pin(t),verify_join=lambda *_:False)
  after=self.l.snapshot();self.assertEqual(self.l.owner(after,'A'),'isolated-A-successor');self.assertEqual(after['phases'],BASE['phases'])
 def test_save_failure_leaves_original(self):
  with patch.object(sa.os,'replace',side_effect=OSError('fixture precommit failure')):self.reject_unchanged(self.recover)
 def test_postrename_uncertainty_authenticates_on_reread(self):
  real=sa.os.fsync;renamed=[False];replace=sa.os.replace
  def rep(*a,**k):replace(*a,**k);renamed[0]=True
  def sync(fd):
   if renamed[0]:raise OSError('fixture directory fsync failure')
   return real(fd)
  with patch.object(sa.os,'replace',side_effect=rep),patch.object(sa.os,'fsync',side_effect=sync):
   with self.assertRaises(OSError):self.recover()
  self.assertIn(tr.LIVE14_KEY,self.l.released(self.l.snapshot()));self.reject_unchanged(self.recover)
 def test_sources_tamper_rejected(self):
  anchors=copy.deepcopy(tr.LIVE14_ANCHORS);anchors['stderr']=dict(anchors['stderr'],sha256='0'*64)
  with patch.object(tr,'LIVE14_ANCHORS',anchors):
   with self.assertRaises(Rejected):tr.live14_sources()


 def test_historical_recover_API_still_initializes_exact_old_event(self):
  state=self.root/'old-protocol-state.json'
  ap=self.pin(dict(schema=tr.EVENT_SCHEMA,coordinator=tr.ANCHORS['coordinator'],anchors=tr.ANCHORS,
   successor_state=str(state),capacity_lock=str(self.lock),predecessor_writers_held=True,external_unit_mutations_excluded=True))
  ledger=sa.Ledger(state,self.lock,recovery_pin=ap)
  proof=BASE['recovery_events'][0]['observation']
  with patch.object(tr,'observe',return_value=proof):event=tr.recover(ledger)
  old=ledger.snapshot();self.assertEqual(old['phases'],tr.historical()[0]['phases'])
  self.assertEqual(ledger.released(old),{tr.KEY});self.assertFalse(event['passed'])
  self.assertEqual(event['original_stage'],'launch_claimed');self.assertNotIn('service',old['phases'][tr.KEY])
 def test_real_observer_carries_nonempty_descendant_and_pid_absence_checks(self):
  import storage_controller as sc
  commands=[]
  def output(argv):
   commands.append(argv)
   if argv[0]=='systemctl':return chr(10).join(k+'='+v for k,v in PROOF['properties_before'].items())
   if 'get-property' in argv:return PROOF['execstart_before']
   return '{"type":"o","data":["/org/freedesktop/systemd1/unit/exact"]}'
  # Actual wrapper, mocked OS outputs. Recursive cgroup emptiness is a trusted OS seam.
  with patch.object(sc.Linux,'output',side_effect=output),patch.object(tr,'empty_cgroup',return_value=False):
   proof=REAL_OBSERVE(R)
  self.assertFalse(proof['empty_before']);self.assertFalse(proof['lanes_empty_after'])
  with self.assertRaises(Rejected):tr.validate_live14_proof(R,proof)
  self.assertEqual(len(commands),6)
 def test_next_owner_admission_and_replay_remain_charged(self):
  from contextlib import contextmanager
  self.recover();self.rotate();d=self.l.snapshot();rec=d['lanes']['F'];g=pinned_json(R['grant']);m=pinned_json(R['manifest'])
  attempt='isolated-next';path=rec['policy']['root']['path']+'/'+attempt
  g.update(owner='isolated-successor',iteration=16,attempt=attempt,owner_transition=rec['transitions'][-1])
  gp=self.pin(g)
  for k in ('owner','iteration','attempt'):m[k]=g[k]
  m.update(grant=gp,attempt_root=path,cwd=path+'/work',tmpdir=path+'/tmp',cache=path+'/cache',ccache=path+'/ccache',receipts=path+'/receipts',output_paths=[path+'/out'])
  mp=self.pin(m);entry=dict(grant=gp,thread=g['owner'],iteration=g['iteration'])
  own=self.root/'empty-attempt';own.mkdir();real_directory=sa.directory
  @contextmanager
  def mapped(p):
   with real_directory(own if str(p)==path else p) as fd:yield fd
  custody=copy.deepcopy(R['custody']);custody.update(unit='vkfworkers-f-isolated-next.service',cgroup='/isolated/cgroup')
  self.l.observe=lambda p:dict(rec['policy']['root'],path=str(p));self.l.usage=lambda p:0
  with patch.object(sa,'directory',mapped),patch.object(sa,'contained'):
   key=self.l.reserve(gp,mp,current=lambda:entry,host=lambda data:(5*2**30,0),custody=lambda *_:custody)
   self.reject_unchanged(lambda:self.l.reserve(gp,mp,current=lambda:entry,host=lambda data:(100*2**30,0),custody=lambda *_:custody))
  now=self.l.snapshot();self.assertEqual(key,'F:isolated-next');self.assertEqual(len(self.l.active_rows(now)),1)
  self.assertEqual(now['phases'][key]['ram_required_at_admission'],5*2**30)
  self.assertEqual(now['phases'][key]['sequence'],4)
  self.assertEqual(sum(x['phase_bytes'] for x in now['phases'].values()),20*2**20)
  for k,v in BASE['phases'].items():self.assertEqual(now['phases'][k],v)

if __name__=='__main__':unittest.main(verbosity=2)

