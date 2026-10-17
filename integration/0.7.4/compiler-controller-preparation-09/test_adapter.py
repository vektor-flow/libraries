"""Bounded host tests. Runtime rows exist ONLY in memory and are marked TEST_ONLY.
No successful-looking receipt is written; run()/payload/native/controller are never invoked.
"""
import copy
import resource
import time
import unittest
from pathlib import Path
import adapter as a

resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2))
resource.setrlimit(resource.RLIMIT_CPU,(30,30))
resource.setrlimit(resource.RLIMIT_CORE,(0,0))

class PlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = a.read(a.HERE.parent/'compiler-native-binding-08/root-check01/compiler-preview/plan.json')
        cls.review = a.read(a.HERE.parent/'compiler-native-binding-08/corrected-review.json')
        cls.head = 'b1aaaecb3702d86341c4366c91e09de2d8dd8e19'
    def test_real_eight_stage_plan(self): a.check_plan(self.p,self.head,self.review)
    def test_stale_head(self):
        with self.assertRaisesRegex(ValueError,'stale'): a.check_plan(self.p,'stale',self.review)
    def test_phase(self):
        p=copy.deepcopy(self.p);p['kind']='vkf'
        with self.assertRaisesRegex(ValueError,'compiler phase'): a.check_plan(p,self.head,self.review)
    def test_dropped_stage(self):
        p=copy.deepcopy(self.p);p['stages'].pop(5)
        with self.assertRaisesRegex(ValueError,'eight'): a.check_plan(p,self.head,self.review)
    def test_old_baseline_marker(self):
        p=copy.deepcopy(self.p);p['stages'][5]['stderr_contains']='old marker'
        with self.assertRaisesRegex(ValueError,'baseline'): a.check_plan(p,self.head,self.review)
    def test_dropped_review_field(self):
        p=copy.deepcopy(self.p);p['candidate_review'].pop('regression')
        with self.assertRaisesRegex(ValueError,'complete'): a.check_plan(p,self.head,self.review)
    def test_stage_timeout(self):
        p=copy.deepcopy(self.p);p['stages'][0]['timeout']=179
        with self.assertRaisesRegex(ValueError,'budgets'): a.check_plan(p,self.head,self.review)
    def test_relocation_keeps_complete_plan_and_cpp(self):
        target=str(a.HERE/'NEVER-MATERIALIZED/compiler')
        original=a.encoded(self.p)
        p,assets=a.relocate(self.p,target)
        self.assertEqual(a.encoded(self.p),original)
        a.check_plan(p,self.head,self.review)
        self.assertFalse(Path(target).exists())
        self.assertEqual(len(assets),len(self.p['generated']))
        for dest,b in assets:
            new=next(x for x in p['generated'] if x['path']==dest)
            self.assertEqual(a.digest(b),new['sha256'])
            rel=Path(dest).relative_to(target)
            old=Path(self.p['out'])/rel
            if old.suffix!='.json': self.assertEqual(b,a.raw(old))
        # Reversal of permitted root/digest changes recovers the whole original plan,
        # including every argv/provider/assertion reference/timeout/review field.
        reverse=a.encoded(p).decode().replace(target,self.p['out'])
        for old,new in zip(self.p['generated'],p['generated']):
            reverse=reverse.replace(new['sha256'],old['sha256'])
        self.assertEqual(a.decode(reverse),self.p)
    def test_required_template_fails_before_write(self):
        dest=a.HERE/'NEVER-CREATED'
        with self.assertRaisesRegex(ValueError,'actual root execution'):
            a.assemble(a.HERE.parent/'compiler-native-binding-08/root-check01/compiler-preview/plan.json',
                       a.HERE/'root-inputs.REQUIRED.json',str(dest))
        self.assertFalse(dest.exists())
    def test_writable_authority_and_alias(self):
        with self.assertRaisesRegex(ValueError,'writable root'):
            a.protected(['/tmp/attempt/grant.json'],['/tmp/attempt'])
    def test_ambiguous_json(self):
        with self.assertRaisesRegex(ValueError,'duplicate'):a.decode('{"x":1,"x":2}')
    def test_conflicting_pins(self):
        with self.assertRaisesRegex(ValueError,'conflicting'):
            a.unique([dict(path='/test',sha256='a'),dict(path='/test',sha256='b')])
    def test_complete_static_bundle(self):
        s=a.static_contract()
        self.assertEqual(len(s['v6_bundle']['helpers']),5)
        pins={p['path'] for p in s['pins']}
        for p in a.read(a.HERE.parent/'storage-policy-setup-11/binary-contract.json')+a.read(a.HERE.parent/'storage-policy-setup-11/policy-inputs.json'):
            self.assertIn(p['path'],pins)
        for name in ('authenticate.py','prepare.py','payload.py'):
            self.assertIn(str(a.PACKAGE/name),pins)

class RuntimeContractTests(unittest.TestCase):
    def setUp(self):
        # NOT a controller receipt: deliberately non-file in-memory model values.
        P=lambda name:dict(path='/TEST_ONLY/'+name,sha256='TEST_ONLY')
        self.gp,self.mp=P('grant'),P('manifest')
        self.s=dict(pins=[P('helper'),P('binary'),P('policy'),P('payload')],
                    v6_bundle=dict(controller=P('controller'),config=P('config'),helpers=[P('helper')]))
        self.r=dict(owner='TEST_ONLY_owner',iteration=7,owner_transition=P('transition'),boot='TEST_ONLY_boot',source_commit='TEST_ONLY_head')
        self.c=dict(request=self.r,attempt_root='/TEST_ONLY/attempt')
        self.g=dict(storage_admission_version='direct-directory-v2',coordinator=a.COORDINATOR,
                    worker='A',owner=self.r['owner'],iteration=7,attempt='TEST_ONLY_attempt',phase_scope='compiler',
                    phase_bytes=a.GIB,ram_peak_bytes=8*a.GIB,timeout_seconds=1200,source_commit='TEST_ONLY_head',
                    owner_transition=P('transition'),storage_policy=P('A_policy'),controller=P('controller'),
                    runtime_config=P('config'),helpers=[P('helper')],inputs=self.s['pins'].copy(),argv=['TEST_ONLY'])
        self.m={k:copy.deepcopy(self.g[k]) for k in a.MATCH}
        self.m.update(grant=self.gp,controller=P('controller'),attempt_root=self.c['attempt_root'])
        owner=dict(grant=self.gp,thread=self.r['owner'],iteration=7)
        self.owners=dict(workers=dict(A=owner))
        self.pub=dict(coordinator=a.COORDINATOR,published=True,under_capacity_lock=True,grant=self.gp,
                      manifest=self.mp,owner_transition=P('transition'),owner_entry=owner)
        self.row=dict(stage='running',grant=self.gp,manifest=self.mp,owner=self.r['owner'],worker='A',
                      ram_bytes=8*a.GIB,phase_bytes=a.GIB,custody=dict(controller=P('controller'),config=P('config'),cgroup='/TEST_ONLY/cgroup'),
                      service=dict(identity=dict(cgroup='/TEST_ONLY/cgroup'),invocation='TEST_ONLY_invocation'))
        self.state=dict(lanes=dict(A=dict(transitions=[P('transition')],pin=P('A_policy'))),
                        phases={'A:TEST_ONLY_attempt':self.row})
    def check(self):
        return a.validate_runtime(self.c,self.s,self.g,self.m,self.gp,self.mp,self.state,self.owners,self.pub,'/TEST_ONLY/cgroup','TEST_ONLY_boot')
    def test_in_memory_model_only(self): self.assertIs(self.check(),self.row)
    def test_stale_owner(self):
        self.g['owner']='stale'
        with self.assertRaisesRegex(ValueError,'stale owner'):self.check()
    def test_owner_ledger_only_rotation(self):
        self.owners['workers']['A']['thread']='old unpublished owner'
        with self.assertRaisesRegex(ValueError,'publication'):self.check()
    def test_unpublished_receipt(self):
        self.pub['published']=False
        with self.assertRaisesRegex(ValueError,'publication receipt'):self.check()
    def test_publication_without_lock(self):
        self.pub['under_capacity_lock']=False
        with self.assertRaisesRegex(ValueError,'publication receipt'):self.check()
    def test_stale_transition(self):
        self.state['lanes']['A']['transitions'][-1]['sha256']='old'
        with self.assertRaisesRegex(ValueError,'stale ledger'):self.check()
    def test_f_lane_rejected(self):
        self.g['worker']='F';self.g['ram_peak_bytes']=3*a.GIB
        with self.assertRaises(ValueError):self.check()
    def test_forecast_not_admission_profile(self):
        self.g['ram_peak_bytes']=4*a.GIB
        with self.assertRaisesRegex(ValueError,'budget'):self.check()
    def test_omitted_helper_set(self):
        self.g['helpers']=[]
        with self.assertRaisesRegex(ValueError,'bundle'):self.check()
    def test_each_omitted_input(self):
        for i in range(len(self.s['pins'])):
            self.g['inputs']=self.s['pins'][:i]+self.s['pins'][i+1:]
            self.m['inputs']=self.g['inputs']
            with self.assertRaisesRegex(ValueError,'omission'):self.check()
    def test_manifest_mismatch(self):
        self.m['argv']=['altered']
        with self.assertRaisesRegex(ValueError,'manifest'):self.check()
    def test_prelaunch_or_joined_not_running(self):
        for stage in ('reserved','launch_claimed','inner_finished','joined'):
            self.row['stage']=stage
            with self.assertRaisesRegex(ValueError,'running'):self.check()
    def test_wrong_namespace_custody(self):
        self.row['custody']['cgroup']='/other'
        with self.assertRaisesRegex(ValueError,'custody'):self.check()
    def test_stale_boot(self):
        self.r['boot']='old boot'
        with self.assertRaisesRegex(ValueError,'boot'):self.check()
    def test_wrong_manifest_receipt(self):
        self.row['manifest']=dict(path='/different',sha256='different')
        with self.assertRaisesRegex(ValueError,'running'):self.check()

if __name__=='__main__':
    start=time.monotonic()
    suite=unittest.defaultTestLoader.loadTestsFromModule(__import__(__name__))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    print('HOST ONLY seconds=%.6f maxrss_kib=%d native_children=0 test_children=0' %
          (time.monotonic()-start,resource.getrusage(resource.RUSAGE_SELF).ru_maxrss))
    raise SystemExit(not result.wasSuccessful())
