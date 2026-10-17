"""Owned tiny state fixtures only. No controller/service or native launch."""
import ast
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
CODE=HERE/'candidate/storage-direct-v5'
PROJECT=HERE.parents[4]
V4=PROJECT/'.coordination/s0-plan-20261012/synchronized-contexts/independent-workers/storage20gb/storage-direct-v4'
sys.path.insert(0,str(CODE))
import storage_admission as sa
import storage_controller as sc
import storage_paths as sp
import terminal_recovery as tr
spec=importlib.util.spec_from_file_location('recovery_fixture',HERE.parent/'storage-terminal-recovery-06/test_recovery.py')
prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
# Only reuse its mock-capacity fixture; never run its admin/live command tests.
prior.HERE=HERE;prior.CODE=CODE
LIVE=json.loads((V4/'direct-state-v4.json').read_text())

class Revocation(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory(dir=HERE,prefix='owner-test-');self.addCleanup(tmp.cleanup)
        self.f=prior.Fixture(tmp.name);self.f.recover()
        for r in LIVE['phases'].values():self.f.paths[r['attempt_identity']['path']]=r['attempt_identity']
        data=copy.deepcopy(LIVE)
        # The test's recovery event is authenticated to its OWN output state
        # and lock. Keep real phase rows, rebind only that fixture authority.
        data['recovery_events']=self.f.l.snapshot()['recovery_events']
        ft=sp.pinned_json(data['lanes']['F']['transitions'][0])
        ft['recovery_event']=data['recovery_events'][0]['sha256']
        data['lanes']['F']['transitions']=[self.f.pin(ft)]
        with self.f.l.transaction():self.f.l.save(data)
        self.before=self.f.l.snapshot()
    def transition(self):
        data=self.f.l.snapshot();rec=data['lanes']['A']
        return dict(version=sa.VERSION,worker='A',coordinator=rec['policy']['coordinator'],policy=rec['pin'],
            previous=rec['transitions'][-1],from_owner=self.f.l.owner(data,'A'),to_owner='fresh-A-mock-owner',
            kind='unused-owner-revocation',unused_state=self.f.pin(data),phase_sequence=len(data['phases']))
    def rotate(self,t):
        p=self.f.pin(t);self.f.l.rotate_owner(p,verify_join=lambda *a: (_ for _ in ()).throw(AssertionError('no fabricated join')));return p
    def test_actual_live_A_is_unused_and_old_rotation_cannot_proceed(self):
        self.assertFalse(any(r['worker']=='A' for r in self.before['phases'].values()))
        self.assertEqual(len(self.before['lanes']['A']['transitions']),1)
        t=self.transition();t['kind']='enrolled-unused'
        with self.assertRaises(sp.Rejected):self.rotate(t)
        t['kind']='joined'
        with self.assertRaises(sp.Rejected):self.rotate(t)
        self.assertEqual(self.before,self.f.l.snapshot())
    def test_exact_revocation_changes_only_append_only_A_owner_chain(self):
        p=self.rotate(self.transition());after=self.f.l.snapshot()
        expected=copy.deepcopy(self.before);expected['lanes']['A']['transitions'].append(p)
        self.assertEqual(after,expected);self.assertEqual(self.f.l.owner(after,'A'),'fresh-A-mock-owner')
        self.assertEqual(self.f.l.active_rows(after),[])
        self.assertEqual(len(after['phases']),2);self.assertEqual(sum(r['phase_bytes'] for r in after['phases'].values()),8*2**20)
        self.assertEqual(after['phases']['F:live07-f-success-01']['stage'],'joined')
        self.assertEqual(after['phases'][tr.KEY]['stage'],'launch_claimed')
    def test_stale_revocation_and_reuse_rejected(self):
        t=self.transition();self.rotate(t)
        with self.assertRaises(sp.Rejected):self.rotate(t)
        t['from_owner']='fresh-A-mock-owner';t['to_owner']='third-owner'
        with self.assertRaises(sp.Rejected):self.rotate(t)
    def test_wrong_authority_history_join_and_barrier_rejected(self):
        for key,value in (('coordinator','wrong'),('worker','F'),('from_owner','wrong'),('to_owner',''),
                          ('previous',None),('policy',self.before['lanes']['F']['pin']),
                          ('phase_sequence',0),('phase_sequence',True),('prior_join',{}),('prior_phase','invented'),('recovery_event','invented')):
            with self.subTest(key=key,value=value):
                t=self.transition();t[key]=value
                with self.assertRaises((sp.Rejected,KeyError)):self.rotate(t)
                self.assertEqual(self.before,self.f.l.snapshot())
    def test_F_normal_rotation_requires_authenticated_latest_join(self):
        data=self.f.l.snapshot();rec=data['lanes']['F'];row=data['phases']['F:live07-f-success-01']
        t=dict(version=sa.VERSION,worker='F',coordinator=rec['policy']['coordinator'],policy=rec['pin'],
            previous=rec['transitions'][-1],from_owner=self.f.l.owner(data,'F'),to_owner='fresh-F-mock-owner',
            kind='joined',prior_phase='F:live07-f-success-01',prior_join=row['join'])
        pin=self.f.pin(t)
        with self.assertRaises(sp.Rejected):self.f.l.rotate_owner(pin,verify_join=lambda *a:False)
        self.assertEqual(data,self.f.l.snapshot())
        calls=[]
        def verified(prior,receipt):
            self.assertEqual(prior,row);self.assertEqual(receipt,sp.pinned_json(row['join']));calls.append(prior)
            return True  # Mocked independent OS authentication, not a new live join.
        self.f.l.rotate_owner(pin,verify_join=verified)
        self.assertEqual(len(calls),1);self.assertEqual(self.f.l.owner(self.f.l.snapshot(),'F'),'fresh-F-mock-owner')
        self.assertEqual(self.f.l.snapshot()['phases'],data['phases'])
    def test_reuse_any_historical_owner_rejected(self):
        for owner in (self.before['lanes']['A']['policy']['owner'],self.f.l.owner(self.before,'A')):
            t=self.transition();t['to_owner']=owner
            with self.assertRaises(sp.Rejected):self.rotate(t)
    def test_snapshot_tampering_and_wrong_pin_fail(self):
        t=self.transition();Path(t['unused_state']['path']).write_text('{}')
        with self.assertRaises(sp.Rejected):self.rotate(t)
        self.assertEqual(self.before,self.f.l.snapshot())
    def test_reserved_A_phase_blocks_revocation_no_refund(self):
        t=self.transition();self.f.reserve(self.f.request('A','active-mock-01'))
        reserved=self.f.l.snapshot()
        with self.assertRaises(sp.Rejected):self.rotate(t)
        self.assertEqual(reserved,self.f.l.snapshot());self.assertEqual(len(reserved['phases']),3)
    def test_changed_state_snapshot_blocks_even_without_A_phase(self):
        t=self.transition();bad=copy.deepcopy(self.before);bad['lanes']['F']['transitions']=[]
        t['unused_state']=self.f.pin(bad)
        with self.assertRaises(sp.Rejected):self.rotate(t)
        self.assertEqual(self.before,self.f.l.snapshot())
    def test_future_A_admission_with_exact_new_owner_and_pin(self):
        self.rotate(self.transition());req=self.f.request('A','future-A')
        self.f.reserve(req);data=self.f.l.snapshot()
        self.assertEqual(data['phases']['A:future-A']['owner'],'fresh-A-mock-owner')
        self.assertEqual(self.f.l.owner(data,'A'),'fresh-A-mock-owner')
    def test_retired_owner_cannot_admit_after_revocation(self):
        retired=self.f.l.owner(self.before,'A');self.rotate(self.transition())
        req=self.f.request('A','retired-attempt',owner=retired)
        with self.assertRaises(sp.Rejected):self.f.reserve(req)
        self.assertEqual(len(self.f.l.snapshot()['phases']),2)
    def test_reader_rejects_fabricated_retired_owner_phase(self):
        self.rotate(self.transition());req=self.f.request('A','future-A');self.f.reserve(req)
        data=self.f.l.snapshot();data['phases']['A:future-A']['owner']=self.f.l.owner(self.before,'A')
        with self.assertRaises(sp.Rejected):self.f.l.owner(data,'A')
    def test_reader_rejects_deleted_historical_F_charge(self):
        self.rotate(self.transition());data=self.f.l.snapshot();del data['phases']['F:live07-f-success-01']
        with self.assertRaises(sp.Rejected):self.f.l.owner(data,'A')

class SourceAndAuthentication(unittest.TestCase):
    def test_sandbox_only_adds_three_nonrecursive_ro_remounts(self):
        src=ast.parse((V4/'storage_controller.py').read_text());fun=next(n for n in src.body if isinstance(n,ast.FunctionDef) and n.name=='sandbox')
        env={};exec(compile(ast.Module(body=[fun],type_ignores=[]),'old_sandbox','exec'),env)
        m=dict(attempt_root='/charged/a',cwd='/charged/a/cwd',argv=['/python','-B','/fixture'])
        old=env['sandbox'](m);new=sc.sandbox(m);i=old.index('--bind')
        self.assertEqual(new,old[:i]+['--remount-ro','/dev/pts','--remount-ro','/dev','--remount-ro','/proc']+old[i:])
        self.assertEqual(sc.STATE_HOME,sc.HERE.parent/'storage-direct-v4')
    def test_controller_all_guards_and_authentication_byte_equivalent_AST(self):
        before=ast.parse((V4/'storage_controller.py').read_text());after=ast.parse((CODE/'storage_controller.py').read_text())
        def nodes(tree):return {n.name:ast.dump(n,include_attributes=False) for n in tree.body if isinstance(n,(ast.ClassDef,ast.FunctionDef))}
        a,b=nodes(before),nodes(after);a.pop('sandbox');b.pop('sandbox');self.assertEqual(a,b)
        self.assertEqual((CODE/'storage_paths.py').read_bytes(),(V4/'storage_paths.py').read_bytes())
        self.assertEqual((CODE/'terminal_recovery.py').read_bytes(),(V4/'terminal_recovery.py').read_bytes())
    def test_old_and_current_exact_bundle_authentication_still_required(self):
        c=sc.Controller.__new__(sc.Controller);c.config_pin={'path':'mock-config','sha256':'x'}
        r=LIVE['phases']['F:live07-f-success-01'];g=sp.pinned_json(r['grant'])
        bundle=dict(controller=g['controller'],helpers=g['helpers'],config=r['custody']['config'])
        c.config={'preserved_record_authorities':[bundle]};c.authenticate_record_sources(r)
        c.config={'preserved_record_authorities':[]}
        with self.assertRaises(sp.Rejected):c.authenticate_record_sources(r)
        c.config={'preserved_record_authorities':[dict(bundle,helpers=bundle['helpers'][:-1])]}
        with self.assertRaises(sp.Rejected):c.authenticate_record_sources(r)
    def test_F_normal_join_anchor_available_A_no_phase(self):
        r=LIVE['phases']['F:live07-f-success-01'];receipt=sp.pinned_json(r['join'])
        self.assertEqual(r['stage'],'joined');self.assertEqual(r['inner_result']['exit'],1)
        self.assertTrue(receipt['actual_service_joined']);self.assertFalse(any(r['worker']=='A' for r in LIVE['phases'].values()))

if __name__=='__main__':unittest.main(verbosity=2)
