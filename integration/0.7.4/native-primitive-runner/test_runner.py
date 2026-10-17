#!/usr/bin/env python3
"""Bounded fixtures plus unchanged real source hashes. No compiler/controller execution."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch
import runner as r

ARGS = None
RESULTS = []


class Tests(unittest.TestCase):
    def setUp(self):
        self.root = ARGS.artifacts/self._testMethodName
        self.root.mkdir()
        self.plan = ARGS.repo/'integration/0.7.4/native-gate-plan-05/plan.json'

    def fixture(self, entry='int64', normalize='success', compile='success', timeout=None, suffix='attempt'):
        attempt = self.root/suffix
        for name in ('cwd','tmpdir','cache','ccache','receipts'):
            (attempt/name).mkdir(parents=True)
        spec = r.spec_for(self.plan,entry,attempt)
        fake = Path(__file__).with_name('fake_tool.py').resolve()
        for stage,mode in [('normalize',normalize),('compile',compile)]:
            spec['argv'][stage] = ['/usr/bin/python3','-B',str(fake),stage,mode,spec['raw'],spec['normalized'],spec['binary']]
        spec['inputs'].append(r.pin(fake))
        if timeout:
            name,seconds = timeout; spec['entry']['deadlines_seconds'][name] = seconds
        return spec

    def run_fixture(self, **kw):
        spec = self.fixture(**kw); result = r.execute(spec)
        RESULTS.append(result)
        for row in result['stages']:
            self.assertTrue(row['children_joined']); self.assertEqual(row['remaining_identities'],[])
            self.assertTrue(all(r.matches(x) is None for x in row['tracked']))
        return result,spec

    def failure(self, stages, **kw):
        result,spec = self.run_fixture(**kw)
        self.assertFalse(result['passed']); self.assertTrue(result['error'])
        self.assertEqual([x['name'] for x in result['stages']],stages)
        return result,spec

    def test_all_four_exact_sources_and_success(self):
        for name in r.ORDER:
            result,spec = self.run_fixture(entry=name,suffix=name)
            self.assertTrue(result['passed'],result['error'])
            self.assertEqual(sum(spec['artifact_components_bytes'].values()),r.GIB)
            self.assertEqual(len(spec['entry']['assertions']),dict(int64=9,extraction=11,unicode=16,native_named_syntax_dependency=2)[name])
            for row in spec['materialize']:
                self.assertEqual(Path(row['destination']).read_bytes(),Path(row['source']['path']).read_bytes())
            for row in spec['stdlib_copies']:
                self.assertFalse(Path(row['destination']).is_symlink())
                self.assertEqual(r.pin(row['destination'])['sha256'],row['source']['sha256'])
            self.assertFalse(set(spec['unset']) & set(spec['environment']))
            self.assertEqual(spec,r.spec_for(self.plan,name,Path(spec['attempt_root'])) | {'argv':spec['argv'],'inputs':spec['inputs']})

    def test_materializer_determinism_and_exclusive(self):
        spec = self.fixture(); r.materialize(spec)
        first = (Path(spec['work'])/'materialization.json').read_bytes()
        with self.assertRaises(FileExistsError): r.materialize(spec)
        self.assertEqual(first,(Path(spec['work'])/'materialization.json').read_bytes())

    def test_missing_executable(self): self.failure(['normalize','compile'],compile='missing')
    def test_not_executable(self): self.failure(['normalize','compile'],compile='not_executable')
    def test_stale_executable(self): self.failure(['normalize'],normalize='stale_binary')
    def test_nonzero_normalize(self): self.failure(['normalize'],normalize='nonzero')
    def test_nonzero_compile(self): self.failure(['normalize','compile'],compile='nonzero')
    def test_nonzero_run(self): self.failure(['normalize','compile','run'],compile='run_nonzero')
    def test_unexpected_normalize_output(self): self.failure(['normalize'],normalize='unexpected')
    def test_unexpected_stdout(self): self.failure(['normalize','compile','run'],compile='run_stdout')
    def test_unexpected_stderr(self): self.failure(['normalize','compile','run'],compile='run_stderr')
    def test_raw_posthash_failure(self): self.failure(['normalize','compile','run'],compile='tamper_raw')

    def test_normalize_deadline(self):
        result,_ = self.failure(['normalize'],normalize='deadline',timeout=('normalize',.12))
        self.assertTrue(result['stages'][-1]['timed_out'])
    def test_compile_deadline(self):
        result,_ = self.failure(['normalize','compile'],compile='deadline',timeout=('compile',.12))
        self.assertTrue(result['stages'][-1]['timed_out'])
    def test_run_deadline(self):
        result,_ = self.failure(['normalize','compile','run'],compile='run_deadline',timeout=('run',.12))
        self.assertTrue(result['stages'][-1]['timed_out'])
    def test_detached_orphan_joined(self):
        result,_ = self.failure(['normalize'],normalize='orphan')
        self.assertGreaterEqual(len(result['stages'][0]['tracked']),2)
        self.assertTrue(result['stages'][0]['reaped'])
    def test_run_detached_orphan_joined(self):
        result,_ = self.failure(['normalize','compile','run'],compile='run_orphan')
        self.assertGreaterEqual(len(result['stages'][-1]['tracked']),2)

    def test_changed_real_pin_fails_before_spawn(self):
        spec = self.fixture(); spec['inputs'][0]['sha256']='0'*64
        with patch.object(r,'stage',side_effect=AssertionError('must not spawn')):
            result = r.execute(spec)
        self.assertFalse(result['passed']); self.assertEqual(result['stages'],[])

    def test_direct_payload_without_sandbox_rejected(self):
        spec = r.spec_for(self.plan,'int64',self.root/'new-attempt')
        req = dict(plan=str(self.plan),entry='int64',attempt_root=spec['attempt_root'],
                   host_namespaces={k:os.readlink('/proc/self/ns/'+k) for k in ('pid','net')})
        r.write(self.root/'spec.json',spec); r.write(self.root/'request.json',req)
        with self.assertRaisesRegex(RuntimeError,'sandbox namespace'):
            r.payload(self.root/'spec.json',r.pin(self.root/'spec.json')['sha256'],
                      self.root/'request.json',r.pin(self.root/'request.json')['sha256'])
        self.assertFalse(Path(spec['attempt_root']).exists())

    def request(self):
        f=self.root/'inert-authority.txt';f.write_text('INERT TEST FIXTURE ONLY\n'); pin=r.pin(f)
        review=self.root/'root-review-fixture.json'
        r.write(review,dict(coordinator=r.COORDINATOR,storage_v4_qualified=True,native_primitives_authorized=True))
        req=dict(coordinator=r.COORDINATOR,owner='test-owner',worker='F',iteration=1,entry='int64',
            attempt='new-attempt',attempt_root=str(self.root/'new-attempt'),phase_bytes=r.GIB,
            ram_peak_bytes=3*r.GIB,timeout_seconds=120,source_commit='fixture-only',plan=str(self.plan),
            live_qualification_review=r.pin(review),controller=pin,helpers=[pin],owned_processes=pin,
            resource_ledger=pin,predecessor_controller=pin,storage_policy=pin,runtime_config=pin,
            owner_transition=pin,extra_inputs=[],previous=[],
            host_namespaces={k:os.readlink('/proc/self/ns/'+k) for k in ('pid','net')})
        return req

    def test_prepare_exact_v4_interface_no_attempt_created(self):
        req=self.request();r.write(self.root/'request.json',req)
        bundle=r.prepare(self.root/'request.json',self.root/'review-only')
        g=r.read(bundle['grant']);m=r.read(bundle['manifest']);s=r.read(bundle['spec'])
        self.assertFalse(Path(req['attempt_root']).exists())
        for k in ('owner','worker','iteration','attempt','phase_scope','phase_bytes','ram_peak_bytes',
                  'timeout_seconds','source_commit','inputs','argv'):
            self.assertEqual(g[k],m[k])
        self.assertEqual(m['grant'],bundle['grant']);self.assertEqual(g['phase_bytes'],r.GIB)
        self.assertIn(bundle['spec'],g['inputs']);self.assertIn(r.pin(r.HERE),g['inputs'])
        self.assertEqual(s['environment']['HOME'],str(Path(s['work'])/'home'))
        with self.assertRaises(FileExistsError):r.prepare(self.root/'request.json',self.root/'review-only')

    def test_v4_regular_pin_and_accounting_compatibility(self):
        import importlib.util
        path=ARGS.repo/'integration/0.7.4/storage-terminal-recovery-06/candidate/storage-direct-v4/storage_paths.py'
        sp=importlib.util.spec_from_file_location('v4_paths_fixture',path)
        v4=importlib.util.module_from_spec(sp);sp.loader.exec_module(v4)
        spec=self.fixture();r.materialize(spec)
        for pin in spec['inputs']:v4.pinned(pin)
        self.assertGreater(v4.allocated(spec['attempt_root']),0)
        self.assertLess(v4.allocated(spec['attempt_root']),r.GIB)
        for key in ('cwd','tmpdir','cache','ccache','receipts'):
            v4.contained(spec['attempt_root'],str(Path(spec['attempt_root'])/key))

    def test_completed_result_requires_v4_join_and_exact_output(self):
        result,spec=self.run_fixture()
        self.assertTrue(result['passed'])
        bundle=dict(entry='int64',grant={'path':'fixture-grant'},manifest={'path':'fixture-manifest'},spec=None)
        spec_path=self.root/'spec.json';r.write(spec_path,spec);bundle['spec']=r.pin(spec_path)
        join=self.root/'join.json';r.write(join,dict(inert_fixture=True))
        row=dict(stage='joined',grant=bundle['grant'],manifest=bundle['manifest'],join=r.pin(join),inner_result=dict(exit=0))
        class Ledger:
            def snapshot(inner):return {'phases':{'F:test':row}}
        class FakeController:
            ledger=Ledger()
            def verify_join(inner,record,receipt):
                self.assertEqual(record,row);self.assertEqual(receipt,{'inert_fixture':True})
        grant=dict(worker='F',attempt='test');controller=FakeController()
        with patch.object(r,'validate_bundle',return_value=({},spec,grant,{})):
            with patch.object(r,'controller_for',return_value=(controller,grant,{})):
                self.assertIn('service_join',r.authenticate_completed(bundle))
                row['stage']='inner_finished'
                with self.assertRaisesRegex(RuntimeError,'not joined'):r.authenticate_completed(bundle)
                row['stage']='joined';row['inner_result']['exit']=1
                with self.assertRaisesRegex(RuntimeError,'payload failed'):r.authenticate_completed(bundle)
                row['inner_result']['exit']=0
                Path(result['stages'][-1]['stdout']['path']).write_text('changed')
                with self.assertRaisesRegex(RuntimeError,'changed input'):r.authenticate_completed(bundle)

    def test_bundle_binding_and_rejection(self):
        req=self.request();r.write(self.root/'request.json',req)
        b=r.prepare(self.root/'request.json',self.root/'bundle-output')
        r.validate_bundle(b)
        bad=copy.deepcopy(b);bad['previous']=[r.pin(self.root/'request.json')]
        with self.assertRaisesRegex(RuntimeError,'drift'):r.validate_bundle(bad)

    def test_driver_one_step_creates_empty_root_before_v4(self):
        req=self.request()
        # Fixture policy only; no operational config/state or native launch.
        policy=self.root/'policy.json';r.write(policy,dict(root=dict(path=str(self.root))))
        req['storage_policy']=r.pin(policy);r.write(self.root/'request.json',req)
        b=r.prepare(self.root/'request.json',self.root/'prepared')
        g=r.read(b['grant']);m=r.read(b['manifest']);events=[]
        class FakeController:
            def current(inner):
                self.assertTrue(Path(req['attempt_root']).is_dir())
                self.assertEqual(list(Path(req['attempt_root']).iterdir()),[])
                events.append('current')
            def outer(inner):events.append('outer');return 0
        with patch.object(r,'controller_for',return_value=(FakeController(),g,m)):
            with patch.object(r,'authenticate_completed',return_value={'joined':True}) as done:
                self.assertEqual(r.drive(self.root/'prepared/bundle.json',r.pin(self.root/'prepared/bundle.json')['sha256']),{'joined':True})
                self.assertEqual(done.call_count,1)
                with self.assertRaisesRegex(RuntimeError,'existing attempt'):
                    r.drive(self.root/'prepared/bundle.json',r.pin(self.root/'prepared/bundle.json')['sha256'])
        self.assertEqual(events,['current','outer'])

    def test_driver_stops_on_controller_failure(self):
        req=self.request();policy=self.root/'policy.json';r.write(policy,dict(root=dict(path=str(self.root))))
        req['storage_policy']=r.pin(policy);r.write(self.root/'request.json',req)
        b=r.prepare(self.root/'request.json',self.root/'prepared');g=r.read(b['grant']);m=r.read(b['manifest'])
        class FakeController:
            def current(inner):pass
            def outer(inner):return 1
        with patch.object(r,'controller_for',return_value=(FakeController(),g,m)):
            with patch.object(r,'authenticate_completed',side_effect=AssertionError('must stop')):
                with self.assertRaisesRegex(RuntimeError,'payload failed'):
                    r.drive(self.root/'prepared/bundle.json',r.pin(self.root/'prepared/bundle.json')['sha256'])

    def test_unqualified_and_underestimated_preparation_refused(self):
        req=self.request();req['phase_bytes']=r.GIB-1;r.write(self.root/'under.json',req)
        with self.assertRaisesRegex(RuntimeError,'estimate'):r.prepare(self.root/'under.json',self.root/'under-out')
        false=self.root/'false.json';r.write(false,dict(coordinator=r.COORDINATOR,storage_v4_qualified=False,native_primitives_authorized=False))
        req['phase_bytes']=r.GIB;req['live_qualification_review']=r.pin(false);r.write(self.root/'false-request.json',req)
        with self.assertRaisesRegex(RuntimeError,'qualification'):r.prepare(self.root/'false-request.json',self.root/'false-out')
        self.assertFalse((self.root/'false-out').exists())

    def test_sequential_missing_prior_blocks_before_controller(self):
        b=dict(entry='extraction',previous=[]);r.write(self.root/'bundle.json',b)
        with patch.object(r,'controller_for',side_effect=AssertionError('must not touch controller')):
            with self.assertRaisesRegex(RuntimeError,'predecessor'):
                r.drive(self.root/'bundle.json',r.pin(self.root/'bundle.json')['sha256'])

    def test_sequential_failure_never_advances(self):
        b=dict(entry='int64');r.write(self.root/'prior.json',b)
        b=dict(entry='extraction',previous=[r.pin(self.root/'prior.json')]);r.write(self.root/'bundle.json',b)
        with patch.object(r,'authenticate_completed',side_effect=RuntimeError('prior failed')) as auth:
            with patch.object(r,'controller_for',side_effect=AssertionError('must not launch')):
                with self.assertRaisesRegex(RuntimeError,'prior failed'):
                    r.drive(self.root/'bundle.json',r.pin(self.root/'bundle.json')['sha256'])
        self.assertEqual(auth.call_count,1)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--repo',type=Path,required=True)
    parser.add_argument('--artifacts',type=Path,required=True);ARGS=parser.parse_args()
    ARGS.repo=ARGS.repo.resolve();ARGS.artifacts=ARGS.artifacts.resolve();ARGS.artifacts.mkdir()
    start=time.monotonic();suite=unittest.defaultTestLoader.loadTestsFromTestCase(Tests)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    evidence=dict(tests=result.testsRun,errors=len(result.errors),failures=len(result.failures),
        seconds=time.monotonic()-start,native_compiler_executed=False,operational_mutations=False,
        fixture_results=RESULTS,all_recorded_children_absent=all(r.matches(s) is None for x in RESULTS for row in x['stages'] for s in row['tracked']))
    r.write(ARGS.artifacts/'verification.json',evidence)
    sys.exit(0 if result.wasSuccessful() and evidence['all_recorded_children_absent'] else 1)
