"""Bounded tests: real pinned historical files; mocked live observations and capacity.
All actual writes, including flock/state/crash/race fixtures, are beneath HERE.
No service, payload, compiler, mount or operational mutation.
"""
import copy
import hashlib
import json
import multiprocessing as mp
import os
from pathlib import Path
import stat
import sys
import tempfile
import time
import unittest
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import patch, Mock

HERE=Path(__file__).resolve().parent
CODE=HERE/'candidate/storage-direct-v4'
sys.path.insert(0,str(CODE))
import storage_admission as sa
import storage_controller as sc
import storage_paths as sp
import terminal_recovery as tr
GIB=sa.GIB
BASELINE, ORIGINAL=tr.historical()
PROOF=json.loads((HERE.parent/'storage-execstart-repair-05/recovery-read-only-result.json').read_text())['observation']
JOINS=[]

class Fixture:
    def __init__(self, root):
        self.root=Path(root); self.state=self.root/'state.json'; self.lock=self.root/'capacity.lock'
        self.lock.touch(); self.count=0
        a=dict(schema=tr.EVENT_SCHEMA,coordinator=tr.ANCHORS['coordinator'],anchors=tr.ANCHORS,
            successor_state=str(self.state),capacity_lock=str(self.lock),
            predecessor_writers_held=True,external_unit_mutations_excluded=True)
        self.ap=self.pin(a); self.l=self.open(); self.paths={}; self.maps={}
        for lane,rec in BASELINE['lanes'].items():
            for k in ('root','old_volume','old_workspace','old_workspace_alias'):
                self.paths[rec['policy'][k]['path']]=rec['policy'][k]
            self.maps[rec['policy']['root']['path']]=self.root/lane
            (self.root/lane).mkdir()
        self.paths[ORIGINAL['attempt_identity']['path']]=ORIGINAL['attempt_identity']
    def pin(self,obj):
        self.count+=1; p=self.root/f'pin-{self.count}.json';p.write_text(json.dumps(obj,sort_keys=True))
        return sc.pin(p)
    def open(self):
        return sa.Ledger(self.state,self.lock,recovery_pin=self.ap,
            observe=lambda p:self.paths[str(p)],usage=lambda p:0,space=self.space)
    def space(self,p):
        for rec in BASELINE['lanes'].values():
            if str(p)==rec['policy']['old_volume']['path']:
                return dict(free=10*GIB,used=rec['policy']['historical_charge'])
        return dict(free=10**15,used=0)
    def recover(self):
        with patch.object(tr,'observe',return_value=copy.deepcopy(PROOF)):
            return tr.recover(self.l)
    def transition(self,lane,to=None):
        data=self.l.snapshot(); rec=data['lanes'][lane]
        t=dict(version=sa.VERSION,worker=lane,coordinator=rec['policy']['coordinator'],policy=rec['pin'],
            previous=None,from_owner=rec['policy']['owner'],to_owner=to or 'new-'+lane,
            phase_sequence=len(data['phases']))
        if lane=='F':t.update(kind='recovered-terminal-failure',prior_phase=tr.KEY,recovery_event=data['recovery_events'][0]['sha256'])
        else:t.update(kind='enrolled-unused',enrollment=tr.ANCHORS['state'])
        return self.pin(t)
    def rotate(self,lane):
        p=self.transition(lane);self.l.rotate_owner(p,verify_join=lambda *a:False);return p
    @contextmanager
    def mapped(self):
        original=sp.directory
        def remap(path):
            path=Path(path)
            for root,dest in self.maps.items():
                if path.is_relative_to(root):path=dest/path.relative_to(root);break
            return original(path)
        with patch.object(sa,'directory',side_effect=remap),patch.object(sp,'directory',side_effect=remap):
            yield
    def request(self,lane,attempt='fresh-01',owner=None,ram=3*GIB):
        data=self.l.snapshot();rec=data['lanes'][lane]
        g=sp.pinned_json(ORIGINAL['grant'])
        root=rec['policy']['root']; path=str(Path(root['path'])/attempt)
        (self.maps[root['path']]/attempt).mkdir(exist_ok=True)
        self.paths.setdefault(path,dict(root,path=path,ino=8000+self.count))
        g.update(ram_peak_bytes=ram,worker=lane,owner=owner or self.l.owner(data,lane),attempt=attempt,iteration=100,
            storage_policy=rec['pin'],owner_transition=rec['transitions'][-1] if rec['transitions'] else None,
            predecessor_controller=rec['policy']['predecessor_controller'],resource_ledger=rec['policy']['predecessor_ledger'],
            controller=sc.pin(CODE/'storage_controller.py'),helpers=[sc.pin(CODE/n) for n in sc.HELPERS])
        gp=self.pin(g)
        m={k:g[k] for k in ('owner','worker','iteration','attempt','phase_scope','phase_bytes','ram_peak_bytes',
                'timeout_seconds','source_commit','inputs','argv','controller')}
        m.update(grant=gp,attempt_root=path,cwd=path+'/work',tmpdir=path+'/tmp',cache=path+'/cache',
            ccache=path+'/ccache',receipts=path+'/receipts',output_paths=[path+'/out'])
        mpin=self.pin(m); e=dict(grant=gp,thread=g['owner'],iteration=100)
        def custody(g,m):
            return dict(controller=g['controller'],config=g['runtime_config'],identity=ORIGINAL['custody']['identity'],
                service_argv=['/fake/never-executed'],unit='vkfworkers-'+lane.lower()+'-'+attempt+'.service',
                cgroup='/mock/'+lane+'/'+attempt)
        return gp,mpin,e,custody
    def reserve(self,req,available=5*GIB):
        gp,mpin,e,custody=req
        with self.mapped():
            return self.l.reserve(gp,mpin,current=lambda:e,host=lambda data:(available,0),custody=custody)

class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=HERE,prefix='test-');self.addCleanup(self.tmp.cleanup)
        self.f=Fixture(self.tmp.name)
    def assert_old(self):
        self.assertEqual(sp.pinned_json(tr.ANCHORS['state']),BASELINE)
    def test_exact_atomic_release_preserves_original_phase_and_failure(self):
        f=self.f; event=f.recover();data=f.l.snapshot()
        self.assertEqual(data['phases'],BASELINE['phases']);self.assertEqual(data['lanes'],BASELINE['lanes'])
        self.assertEqual(f.l.active_rows(data),[])
        self.assertEqual(data['lanes']['F']['policy']['historical_charge']+sum(r['phase_bytes'] for r in data['phases'].values()),19787718656)
        self.assertFalse(event['passed']);self.assertIsNone(event['workload_result']);self.assert_old()
        with self.assertRaises(sp.Rejected):f.recover()
    def test_no_initialize_no_missing_state_fallback(self):
        with self.assertRaises(RuntimeError):self.f.l.initialize()
        with self.assertRaises(FileNotFoundError):self.f.l.snapshot()
        self.f.lock.unlink()
        with self.assertRaises(FileNotFoundError):self.f.recover()
    def test_malformed_and_changed_proof(self):
        variants=[]
        for k,v in [('boot','other'),('outer_pid',True),('outer_starttime',1),('outer_absent_after',False),
                    ('inner_absent_before',False),('empty_after',False),('cgroup','/wrong')]:
            o=copy.deepcopy(PROOF);o[k]=v;variants.append(o)
        for k,v in [('InvocationID','other'),('LoadState','not-found'),('MainPID','1'),('ExecMainStatus','0')]:
            o=copy.deepcopy(PROOF)
            for s in ('before','after'):o['properties_'+s][k]=v
            variants.append(o)
        o=copy.deepcopy(PROOF); raw=json.loads(o['execstart_before']);raw['data'][0][1][-1]='wrong';o['execstart_before']=json.dumps(raw);variants.append(o)
        o=copy.deepcopy(PROOF);o['extra']='unknown';variants.append(o)
        for o in variants:
            with self.subTest(proof=o),patch.object(tr,'observe',return_value=o),self.assertRaises((sp.Rejected,RuntimeError)):
                tr.recover(self.f.l)
            self.assertFalse(self.f.state.exists())
    def test_changed_final_sample_and_stale_proof(self):
        o=copy.deepcopy(PROOF);o['properties_after']['InvocationID']='changed'
        with patch.object(tr,'observe',side_effect=[PROOF,o]),self.assertRaises(sp.Rejected):tr.recover(self.f.l)
        with patch.object(tr,'observe',return_value=PROOF),patch.object(tr.time,'monotonic',side_effect=[0,6]),self.assertRaises(sp.Rejected):tr.recover(self.f.l)
        self.assertFalse(self.f.state.exists())
    def test_changed_source_before_publication(self):
        real=tr.historical;count=[0]
        def changed():
            count[0]+=1
            if count[0]>=4:raise sp.Rejected('source pin mismatch')
            return real()
        with patch.object(tr,'historical',side_effect=changed),self.assertRaises(sp.Rejected):self.f.recover()
        self.assertFalse(self.f.state.exists())
    def test_crash_before_replace(self):
        with patch.object(sa.os,'replace',side_effect=OSError('crash-before')),self.assertRaises(OSError):self.f.recover()
        self.assertFalse(self.f.state.exists());self.assert_old();self.f.recover()
    def test_temp_file_fsync_failure(self):
        with patch.object(sa.os,'fsync',side_effect=OSError('fsync')),self.assertRaises(OSError):self.f.recover()
        self.assertFalse(self.f.state.exists())
    def test_post_replace_directory_fsync_uncertain_requires_durable_reread(self):
        real=os.fsync
        def fail_dir(fd):
            if stat.S_ISDIR(os.fstat(fd).st_mode):raise OSError('uncertain directory fsync')
            return real(fd)
        with patch.object(sa.os,'fsync',side_effect=fail_dir):
            with self.assertRaises(OSError):self.f.recover()
            self.assertTrue(self.f.state.exists())
            with self.assertRaises(OSError):self.f.l.snapshot()
        data=self.f.l.snapshot();self.assertEqual(self.f.l.active_rows(data),[])
        with self.assertRaises(sp.Rejected):self.f.recover()
    def test_missing_corrupt_duplicate_event_and_changed_original_fail_all_readers(self):
        f=self.f;f.recover();good=f.state.read_text()
        def no_event(d):d.pop('recovery_events')
        def empty(d):d['recovery_events']=[]
        def duplicate(d):d['recovery_events']*=2
        def phase(d):d['phases'][tr.KEY]['phase_bytes']=0
        def join(d):d['phases'][tr.KEY]['join']={}
        def disk(d):d['lanes']['F']['policy']['historical_charge']=0
        def proof(d):d['recovery_events'][0]['observation']['empty_after']=False
        def hash_changed(d):d['recovery_events'][0]['sha256']='0'*64
        for mutate in (no_event,empty,duplicate,phase,join,disk,proof,hash_changed):
            data=json.loads(good);mutate(data);f.state.write_text(json.dumps(data))
            for reader in (f.l.snapshot,lambda:f.l.active_rows(data),lambda:f.l.check(data)):
                with self.subTest(mutation=mutate.__name__),self.assertRaises((sp.Rejected,KeyError)):reader()
        f.state.write_text(good.rstrip()[:-1]+',"version":"direct-directory-v4"}')
        with self.assertRaises(sp.Rejected):f.l.snapshot()
    def test_owner_transitions_explicit_distinct_and_replay_rejected(self):
        f=self.f;f.recover()
        with self.assertRaisesRegex(sp.Rejected,'explicit successor'):f.reserve(f.request('F'))
        for lane in ('A','F'):
            stale=f.request(lane,'stale-owner')
            pin=f.rotate(lane);
            with self.assertRaisesRegex(sp.Rejected,'owner/state mismatch'):f.reserve(stale)
            d=f.l.snapshot();self.assertEqual(f.l.owner(d,lane),'new-'+lane)
            with self.assertRaises(sp.Rejected):f.l.rotate_owner(pin,verify_join=lambda *a:True)
        self.assertEqual(f.l.snapshot()['phases'],BASELINE['phases']);self.assert_old()
    def test_invalid_owner_anchors_and_fabricated_join(self):
        f=self.f;f.recover()
        for lane in ('A','F'):
            base=sp.pinned_json(f.transition(lane))
            mutations=[dict(base,prior_join={}),dict(base,from_owner='wrong'),dict(base,phase_sequence=99),dict(base,phase_sequence=True),
                dict(base,kind='joined',prior_phase=tr.KEY,prior_join={})]
            if lane=='F':mutations.append(dict(base,recovery_event='wrong'))
            for t in mutations:
                with self.assertRaises((sp.Rejected,KeyError)):f.l.rotate_owner(f.pin(t),verify_join=lambda *a:True)
        self.assertTrue(all(not r['transitions'] for r in f.l.snapshot()['lanes'].values()))
    def test_recovered_phase_never_replays_any_lifecycle_path(self):
        f=self.f;f.recover()
        calls=[lambda:f.l.claim_launch(tr.KEY,authenticate=Mock(),host=Mock()),
            lambda:f.l.preexec(tr.KEY,authenticate=Mock(),host=Mock()),
            lambda:f.l.attach_service(tr.KEY,authenticate=Mock()),
            lambda:f.l.monitor(tr.KEY,current=Mock(),host_available=Mock()),
            lambda:f.l.guard_service(tr.KEY,authenticate=Mock(),host=Mock()),
            lambda:f.l.finish_service(tr.KEY,{},authenticate=Mock()),
            lambda:f.l.join(tr.KEY,{},verify_join=Mock())]
        for call in calls:
            with self.assertRaisesRegex(sp.Rejected,'permanently consumed'):call()
        self.assertEqual(f.l.snapshot()['phases'],BASELINE['phases'])
    def test_admission_claim_preexec_runtime_and_disk_readers(self):
        f=self.f;f.recover();f.rotate('A');f.rotate('F')
        ra=f.request('A');a=f.reserve(ra)
        rf=f.request('F')
        with self.assertRaisesRegex(sp.Rejected,'RAM admission'):f.reserve(rf) # A's full 3GiB is retained
        f.l.claim_launch(a,authenticate=lambda *a:None,host=lambda d:(5*GIB,0))
        with self.assertRaisesRegex(sp.Rejected,'preexec RAM'):f.l.preexec(a,authenticate=lambda *a:None,host=lambda d:(5*GIB-1,0))
        f.l.preexec(a,authenticate=lambda *a:None,host=lambda d:(5*GIB,0))
        f.l.attach_service(a,authenticate=lambda *a:dict(invocation='mock',identity={'pid':1}))
        f.l.guard_service(a,authenticate=lambda *a:None,host=lambda d:(GIB,0))
        with self.assertRaisesRegex(sp.Rejected,'emergency'):f.l.guard_service(a,authenticate=lambda *a:None,host=lambda d:(GIB-1,0))
        f.l.monitor(a,current=lambda:ra[2],host_available=lambda:GIB)
        f.l.check(f.l.snapshot())
        self.assertEqual(sum(r['ram_bytes'] for r in f.l.active_rows(f.l.snapshot())),3*GIB)
        self.assertEqual(f.l.snapshot()['phases'][tr.KEY],ORIGINAL)
    def test_new_f_admission_and_old_attempt_consumed(self):
        f=self.f;f.recover();f.rotate('F')
        bad=f.request('F',attempt='live04-f-success-01')
        with self.assertRaisesRegex(sp.Rejected,'permanently charged'):f.reserve(bad)
        key=f.reserve(f.request('F'));self.assertEqual(key,'F:fresh-01')
        with self.assertRaises(sp.Rejected):f.reserve(f.request('F','fresh-02'))
        self.assertEqual(f.l.snapshot()['phases'][tr.KEY],ORIGINAL)
    def test_owner_race_and_admission_race(self):
        f=self.f;f.recover()
        pins=[f.transition('F',to='race-one'),f.transition('F',to='race-two')]
        self.race(lambda i:f.l.rotate_owner(pins[i],verify_join=lambda *a:False))
        f.rotate('A');ra=f.request('A');rf=f.request('F')
        self.race(lambda i:f.reserve([ra,rf][i]))
        d=f.l.snapshot();self.assertEqual(len(d['phases']),2);self.assertEqual(sum(r['ram_bytes'] for r in f.l.active_rows(d)),3*GIB)
    def race(self,call):
        ctx=mp.get_context('fork');ready=ctx.Event();q=ctx.Queue()
        def run(i):
            ready.wait(5)
            try:call(i);q.put('ok')
            except sp.Rejected:q.put('rejected')
        children=[ctx.Process(target=run,args=(i,)) for i in range(2)]
        for c in children:c.start()
        ready.set()
        for c in children:
            c.join(10)
            if c.is_alive():c.terminate();c.join(5)
            JOINS.append(dict(pid=c.pid,exitcode=c.exitcode,joined=not c.is_alive(),proc_absent=not Path(f'/proc/{c.pid}').exists()))
            self.assertEqual(c.exitcode,0)
        self.assertEqual(sorted([q.get(timeout=1),q.get(timeout=1)]),['ok','rejected']);q.close();q.join_thread()
    def test_recovery_concurrent_publication(self):
        self.race(lambda i:self.f.recover());self.assertEqual(self.f.l.snapshot()['phases'],BASELINE['phases'])
    def test_recovery_and_admission_share_one_lock(self):
        f=self.f;ctx=mp.get_context('fork');observing=ctx.Event();release=ctx.Event();waiting=ctx.Event();q=ctx.Queue()
        def recover_child():
            def observe(r):
                observing.set()
                if not release.wait(3):raise RuntimeError('test synchronization timeout')
                return copy.deepcopy(PROOF)
            with patch.object(tr,'observe',side_effect=observe):tr.recover(f.l)
            q.put('recovered')
        def admit_child():
            waiting.set()
            try:
                f.l.reserve(ORIGINAL['grant'],ORIGINAL['manifest'],current=lambda:None,host=lambda d:(20*GIB,0),custody=Mock())
                q.put('unexpected admission')
            except sp.Rejected as error:q.put(str(error))
        children=[ctx.Process(target=recover_child),ctx.Process(target=admit_child)]
        try:
            children[0].start();self.assertTrue(observing.wait(3))
            children[1].start();self.assertTrue(waiting.wait(3));time.sleep(.03)
            self.assertTrue(q.empty());self.assertFalse(f.state.exists())
        finally:
            release.set()
            for c in children:
                if c.pid is None:continue
                c.join(8)
                if c.is_alive():c.terminate();c.join(5)
                JOINS.append(dict(pid=c.pid,exitcode=c.exitcode,joined=not c.is_alive(),proc_absent=not Path(f'/proc/{c.pid}').exists()))
        self.assertTrue(all(c.exitcode==0 for c in children))
        self.assertEqual(sorted([q.get(timeout=1),q.get(timeout=1)]),['explicit successor owner transition required','recovered'])
        q.close();q.join_thread();self.assertEqual(f.l.snapshot()['phases'],BASELINE['phases'])

    def test_host_reader_skips_only_authenticated_recovery_and_rejects_resurrection(self):
        f=self.f;f.recover();data=f.l.snapshot()
        c=sc.Controller.__new__(sc.Controller);c.ledger=f.l
        c.config=json.loads((HERE/'runtime-config.template.json').read_text())
        c.os=Mock()
        c.os.show.return_value=dict(MainPID='0',ActiveState='failed')
        c.os.empty.return_value=True;c.os.units.return_value=set()
        c.authenticate_record=Mock(side_effect=AssertionError('recovered record must use historical authority'))
        with patch.object(sc,'mem',return_value=5*GIB):self.assertEqual(c.host(data),(5*GIB,0))
        c.authenticate_record.assert_not_called()
        c.os.units.side_effect=lambda pattern:{ORIGINAL['custody']['unit']} if pattern=='vkfworkers-*.service' else set()
        with self.assertRaisesRegex(sp.Rejected,'unreserved worker'):c.host(data)
        c.os.units.side_effect=None;c.os.units.return_value=set()
        data['recovery_events']=[]
        with self.assertRaises(sp.Rejected):c.host(data)
    def test_host_authenticates_new_live_intents_and_exact_old_authority(self):
        f=self.f;f.recover();f.rotate('F');key=f.reserve(f.request('F'));data=f.l.snapshot()
        c=sc.Controller.__new__(sc.Controller);c.ledger=f.l;c.config=json.loads((HERE/'runtime-config.template.json').read_text())
        c.config_pin=sc.pin(HERE/'runtime-config.template.json');c.os=Mock()
        c.os.show.return_value=dict(MainPID='0',ActiveState='failed');c.os.empty.return_value=True;c.os.units.return_value=set()
        c.authenticate_record=Mock()
        with patch.object(sc,'mem',return_value=8*GIB):self.assertEqual(c.host(data),(8*GIB,0))
        c.authenticate_record.assert_called_once_with(data['phases'][key])
        c.authenticate_record_sources(ORIGINAL)
        bad=copy.deepcopy(ORIGINAL);bad['custody']['config']=f.ap
        with self.assertRaises(sp.Rejected):c.authenticate_record_sources(bad)
    def test_authority_pin_corruption_unknown_schema_and_no_historical_overwrite(self):
        f=self.f;f.recover()
        Path(f.ap['path']).write_text('{}')
        for call in (f.l.snapshot,lambda:f.l.active_rows(json.loads(f.state.read_text())),lambda:f.l.owner(json.loads(f.state.read_text()),'F')):
            with self.assertRaises(sp.Rejected):call()
    def test_absence_denies_permission_and_missing_hierarchy(self):
        p=Mock();p.lstat.side_effect=PermissionError('denied')
        with self.assertRaises(PermissionError):tr.absent(p)
        p.lstat.side_effect=FileNotFoundError();self.assertTrue(tr.absent(p))
        with patch.object(Path,'is_file',return_value=False),self.assertRaises(sp.Rejected):tr.empty_cgroup(ORIGINAL['custody']['cgroup'])
    def test_hard_crash_publication_boundaries(self):
        ctx=mp.get_context('fork')
        for boundary in ('before-file-fsync','before-replace','after-replace'):
            with tempfile.TemporaryDirectory(dir=HERE,prefix='crash-') as temp:
                f=Fixture(temp)
                def run():
                    real_replace=os.replace
                    def crash_replace(*a,**k):
                        if boundary=='before-replace':os._exit(71)
                        real_replace(*a,**k);os._exit(72)
                    if boundary=='before-file-fsync':
                        with patch.object(sa.os,'fsync',side_effect=lambda fd:os._exit(70)):f.recover()
                    else:
                        with patch.object(sa.os,'replace',side_effect=crash_replace):f.recover()
                child=ctx.Process(target=run);child.start();child.join(5)
                if child.is_alive():child.terminate();child.join(5)
                JOINS.append(dict(pid=child.pid,exitcode=child.exitcode,joined=not child.is_alive(),proc_absent=not Path(f'/proc/{child.pid}').exists(),boundary=boundary))
                self.assertIn(child.exitcode,(70,71,72))
                if boundary=='after-replace':
                    self.assertEqual(f.l.snapshot()['phases'],BASELINE['phases'])
                    with self.assertRaises(sp.Rejected):f.recover()
                else:
                    self.assertFalse(f.state.exists());f.recover()
                self.assert_old()
    def test_same_lane_concurrent_admission_and_owner_change(self):
        f=self.f;f.recover();f.rotate('F')
        reqs=[f.request('F','same-race-1'),f.request('F','same-race-2')]
        self.race(lambda i:f.reserve(reqs[i],available=20*GIB))
        d=f.l.snapshot();self.assertEqual(len(f.l.active_rows(d)),1)
        t=sp.pinned_json(f.transition('F',to='wrong-again'))
        t.update(from_owner='new-F',previous=d['lanes']['F']['transitions'][-1])
        with self.assertRaisesRegex(sp.Rejected,'outstanding'):f.l.rotate_owner(f.pin(t),verify_join=lambda *a:True)
    def test_normal_successor_join_and_next_owner_transition_keep_recovery(self):
        f=self.f;f.recover();f.rotate('F');key=f.reserve(f.request('F'))
        f.l.claim_launch(key,authenticate=lambda *a:None,host=lambda d:(5*GIB,0))
        f.l.attach_service(key,authenticate=lambda *a:dict(identity={'pid':1},invocation='new'))
        f.l.finish_service(key,dict(remaining_identities=[],tracked=[],inputs_reverified=True),authenticate=lambda *a:None)
        d=f.l.snapshot();r=d['phases'][key]
        receipt=f.pin(dict(grant=r['grant'],manifest=r['manifest'],main_pid=0,cgroup_empty=True,remaining_identities=[],actual_service_joined=True))
        f.l.join(key,receipt,verify_join=lambda *a:True)
        rec=f.l.snapshot()['lanes']['F']
        t=f.pin(dict(version=sa.VERSION,worker='F',coordinator=rec['policy']['coordinator'],policy=rec['pin'],
            previous=rec['transitions'][-1],from_owner='new-F',to_owner='next-F',prior_phase=key,prior_join=receipt))
        f.l.rotate_owner(t,verify_join=lambda *a:True)
        self.assertEqual(f.l.owner(f.l.snapshot(),'F'),'next-F')
        self.assertEqual(f.l.snapshot()['phases'][tr.KEY],ORIGINAL)

    def test_a8_and_f3_full_ram_profiles(self):
        f=self.f;f.recover();f.rotate('A');f.rotate('F')
        req=f.request('A',ram=8*GIB)
        with self.assertRaisesRegex(sp.Rejected,'RAM admission'):f.reserve(req,available=10*GIB-1)
        key=f.reserve(req,available=10*GIB)
        f.l.claim_launch(key,authenticate=lambda *a:None,host=lambda d:(10*GIB,0))
        f.l.preexec(key,authenticate=lambda *a:None,host=lambda d:(10*GIB,0))
        reqf=f.request('F')
        with self.assertRaisesRegex(sp.Rejected,'RAM admission'):f.reserve(reqf,available=13*GIB-1)
        f.reserve(reqf,available=13*GIB)
        self.assertEqual(sum(r['ram_bytes'] for r in f.l.active_rows(f.l.snapshot())),11*GIB)
    def test_admin_owner_plan_and_rotate_commands(self):
        import recovery_admin as admin
        import io
        f=self.f;f.recover()
        installed=Path(tr.ANCHORS['state']['path']).parent.parent/'storage-direct-v4/recovery_admin.py'
        def command(args):
            with patch.object(admin,'__file__',str(installed)),patch.object(admin,'Ledger',return_value=f.l), \
                 patch.object(sys,'argv',['recovery_admin.py',*args,'--authority-sha256',f.ap['sha256']]), \
                 patch('sys.stdout',new=io.StringIO()) as stream:
                admin.main();return json.loads(stream.getvalue())
        for lane in ('F','A'):
            plan=command(['transition-plan','--worker',lane,'--to-owner','cli-'+lane])
            pin=f.pin(plan)
            receipt=command(['rotate','--transition',pin['path'],'--transition-sha256',pin['sha256']])
            self.assertEqual(receipt['owner'],'cli-'+lane)
        result=command(['inspect']);self.assertEqual(result['active_ram'],0);self.assertEqual(result['charged']['F'],19787718656)

if __name__=='__main__':
    try:unittest.main(verbosity=2)
    finally:(HERE/'owned-test-joins.json').write_text(json.dumps(JOINS,indent=2)+'\n')
