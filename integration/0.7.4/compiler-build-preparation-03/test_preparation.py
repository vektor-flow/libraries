#!/usr/bin/env python3
"""Host-only orchestration tests. All compiler/link outputs below are FAKE bytes."""
import copy, hashlib, json, os, shlex, sys, tempfile, unittest
from pathlib import Path
sys.dont_write_bytecode=True
from authenticate import HERE, D, CACHE, read, save, pin, sha, md
from prepare import build_plan, tests_plan, review, identity, link_command, require, HELD, current_head
from payload import execute, validate_md, validate_admission

class Preparation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.auth=read(HERE/'authentication.json');cls.r=review(HERE/'candidate-held.json')
        cls.base=HERE/'host-test-artifacts';cls.base.mkdir(exist_ok=True)
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix=self._testMethodName+'-',dir=self.base);self.addCleanup(self.temp.cleanup);self.basepath=Path(self.temp.name)
    def plan(self):return build_plan(self.basepath/'attempt',self.r,self.auth)
    def fake(self,plan,fail=None,drift=None):
        seen=[]
        def run(s):
            seen.append(s['name']);stdout='';stderr='';code=0
            if s['name']==fail:code=19
            else:
                for dest in s.get('outputs',[]):Path(dest).write_bytes(b'FAKE HOST TEST OUTPUT\n'+plan['identity'].encode())
                if 'md' in s:
                    deps=[x.get('effective',x.get('path')) for x in s['expected']]
                    if drift==s['name']:deps.append(str(self.basepath/'unexpected.hpp'))
                    Path(s['md']).write_text('fake: '+' '.join(shlex.quote(p) for p in deps)+'\n')
                if s.get('expected_exit')=='nonzero':code=1;stderr=s['stderr_contains']
                else:stdout=s.get('stdout') or ''
            return code,stdout,stderr,dict(no_live_descendants=True,timed_out=False,simulation=True)
        return run,seen
    def test_original_identity_algorithm_reproduces_d288(self):
        d285=read(CACHE/'Proof/tests/independent-worker-D/iteration285-lifetime02/delta-profile.json')
        result=identity(d285['identity'],[sha(D/'numeric_1.cpp'),sha(D/'lower_expression_stages_9.cpp')],'D288')
        self.assertEqual(result,read(D/'delta-profile.json')['identity'])
    def test_exact_order_only53_90_and_new_paths(self):
        p=self.plan();old=read(HERE.parent/'compiler-renderer-repair-02/build-prerequisites.json')['ordered_link_argv']
        new=p['stages'][2]['argv'];a=[x for x in old if x.endswith(('.o','.a'))];b=[x for x in new if x.endswith(('.o','.a'))]
        self.assertEqual(len(a),240);self.assertEqual([i for i,(x,y) in enumerate(zip(a,b)) if x!=y],[54,91])
        for s in p['stages']:
            for path in s.get('outputs',[]):self.assertTrue(Path(path).is_relative_to(Path(p['out'])))
        self.assertFalse(p['executable']);self.assertNotEqual(p['identity'],p['parent_identity'])
    def test_hold_is_unconditionally_rejected(self):
        p=self.plan()
        with self.assertRaisesRegex(ValueError,'held'):validate_admission(p,{},pin(Path(p['out'])/'plan.json'))
        p['executable']=True;p['candidate_review']['accepted']=True;p['candidate_review']['whole_record_projection_regression_reviewed']=True
        with self.assertRaisesRegex(ValueError,'unaccepted'):validate_admission(p,{},pin(Path(p['out'])/'plan.json'))
    def test_fake_complete_orchestration_no_native_credit(self):
        p=self.plan();run,seen=self.fake(p);execute(p,dict(timeout_seconds=30,disk_bytes=20_000_000),run)
        self.assertEqual(len(seen),8);receipt=read(Path(p['out'])/'compiler-receipt.json');self.assertFalse(receipt['native_build_passed']);self.assertFalse(receipt['core_regression_passed'])
        self.assertTrue(read(Path(p['out'])/'execution-summary.json')['all_recorded_children_joined'])
    def test_compiler_failure_stops_before_identity_or_link(self):
        p=self.plan();run,seen=self.fake(p,fail='compile-53')
        with self.assertRaisesRegex(ValueError,'unexpected exit'):execute(p,dict(timeout_seconds=30,disk_bytes=20_000_000),run)
        self.assertEqual(seen,['compile-53'])
    def test_dependency_drift_stops_before_link(self):
        p=self.plan();run,seen=self.fake(p,drift='compile-53')
        with self.assertRaisesRegex(ValueError,'dependency drift'):execute(p,dict(timeout_seconds=30,disk_bytes=20_000_000),run)
        self.assertEqual(seen,['compile-53'])
    def test_changed_and_missing_dependency_rejected(self):
        p=self.plan();s=copy.deepcopy(p['stages'][0]);dep=self.basepath/'local.hpp';dep.write_text('first');h=sha(dep)
        s['expected']=[dict(effective=str(dep),sha256=h)];s['mapping']={};Path(s['md']).write_text('fake: '+shlex.quote(str(dep))+'\n')
        dep.write_text('changed')
        with self.assertRaisesRegex(ValueError,'bytes changed'):validate_md(s,{})
        dep.unlink()
        with self.assertRaises(FileNotFoundError):validate_md(s,{})
    def test_missing_expected_md_and_phony_rules(self):
        p=self.plan();s=p['stages'][0];Path(s['md']).write_text('fake: '+shlex.quote(s['expected'][0]['effective'])+'\n\nphony:\n')
        self.assertEqual(len(md(s['md'])),1)
        with self.assertRaisesRegex(ValueError,'missing expected'):validate_md(s,{})
    def test_regression_md_requires_actual_source(self):
        p=self.plan();s=p['stages'][3]
        Path(s['md']).write_text('fake: '+shlex.quote(s['expected'][-1]['effective'])+'\n')
        with self.assertRaisesRegex(ValueError,'missing regression source'):validate_md(s,{})
    def test_failed_join_stops(self):
        p=self.plan();seen=[]
        def fake(s):seen.append(s['name']);return 0,'','',dict(no_live_descendants=False)
        with self.assertRaisesRegex(ValueError,'joined'):execute(p,dict(timeout_seconds=30,disk_bytes=20_000_000),fake)
        self.assertEqual(seen,['compile-53'])
    def test_stale_application_head_prevents_launch(self):
        p=self.plan();p['application_head_at_preparation']='stale';run,seen=self.fake(p)
        with self.assertRaisesRegex(ValueError,'stale application HEAD'):execute(p,dict(timeout_seconds=30,disk_bytes=20_000_000),run)
        self.assertEqual(seen,[])
    def test_current_closures_all_requested_controls_without_native(self):
        fake=self.basepath/'FAKE-NOT-A-COMPILER';fake.write_bytes(b'not executable')
        parent=read(D/'delta-profile.json')['identity']
        # Fixture metadata only, never native evidence; tests_plan does not execute it.
        receipt=dict(compiler=pin(fake),candidate_sha256=self.r['candidate']['sha256'],native_build_passed=True,identity=identity(parent,[self.r['candidate']['sha256']],'compiler-build-preparation-03'))
        counts={};application={}
        for selection in ['d288','metadata','a345','f364','a347','full-app']:
            p=tests_plan(self.basepath/selection,self.r,self.auth,receipt,selection);self.assertFalse(p['executable'])
            counts[selection]=dict(cases=len(p['cases']),runs=sum('-run-' in x['name'] for x in p['stages']),modules=len(p['application_inputs']),assertions=sum(sum(c['assertions'].values()) for c in p['cases']))
            self.assertEqual(p['application_head_at_preparation'],current_head())
            if selection=='d288':
                for stage in p['stages']:
                    if stage['name'].endswith('-compile'):self.assertNotIn('-b',stage['argv']);self.assertNotIn('--diagnostics',stage['argv'])
            application[selection]=dict(head=p['application_head_at_preparation'],inputs=p['application_inputs'],cases=p['cases'])
        self.assertEqual(counts['d288']['runs'],10);self.assertEqual(counts['f364']['runs'],11);self.assertEqual(counts['a347']['runs'],2)
        save(HERE/'current-application-inputs.json',dict(preview_only=True,regenerate_at_each_future_attempt=True,selections=application))
        save(HERE/'closure-preview-counts.json',dict(host_preparation_only=True,fake_compiler_never_executed=True,head=current_head(),counts=counts))
    def test_environment_and_disk_stop(self):
        p=self.plan();run,seen=self.fake(p)
        with self.assertRaisesRegex(ValueError,'disk'):execute(p,dict(timeout_seconds=30,disk_bytes=1),run)
        self.assertEqual(seen,[])

if __name__=='__main__':unittest.main(verbosity=2)
