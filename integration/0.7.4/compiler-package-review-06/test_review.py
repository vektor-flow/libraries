#!/usr/bin/env python3
"""Bounded host tests: fake compiler outputs only; all writes inside review output.

--original reproduces the gaps on the untouched package. No package test is
allowed to refresh the peer's previews or create peer temporary directories.
"""
import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.dont_write_bytecode = True
OUT = Path(__file__).resolve().parent
PEER = OUT.parent / 'compiler-build-preparation-03'
ORIGINAL = '--original' in sys.argv
if ORIGINAL:
    sys.argv.remove('--original')

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

auth = load('authenticate', PEER / 'authenticate.py')
SOURCE = PEER if ORIGINAL else OUT / 'candidate'
prep = load('prepare', SOURCE / 'prepare.py')
payload = load('payload', SOURCE / 'payload.py')
legacy = load('inherited_tests', SOURCE / 'test_preparation.py')

@classmethod
def setup_legacy(cls):
    cls.auth = auth.read(PEER / 'authentication.json')
    cls.r = prep.review(PEER / 'candidate-held.json')
    cls.base = OUT / 'test-tmp'
    cls.base.mkdir(exist_ok=True)

legacy.Preparation.setUpClass = setup_legacy
def save_local(path, obj):
    path = Path(path)
    if path.parent == PEER:
        path = OUT / ('test-' + ('original-' if ORIGINAL else 'patched-') + path.name)
    if not path.resolve().is_relative_to(OUT):
        raise AssertionError('test write outside output')
    auth.save(path, obj)
legacy.save = save_local

class Review(legacy.Preparation):
    # Inherit the 13 original orchestration checks as well as independent cases.
    def approval(self):
        candidate = self.basepath / 'candidate.cpp'
        regression = self.basepath / 'regression.cpp'
        candidate.write_text('FAKE SOURCE, NEVER COMPILED')
        regression.write_text('FAKE REGRESSION, NEVER COMPILED')
        r = copy.deepcopy(self.r)
        r.update(candidate=auth.pin(candidate), regression=auth.pin(regression),
                 accepted=True, whole_record_projection_regression_reviewed=True)
        path = self.basepath / 'review.json'
        auth.save(path, r)
        return path, prep.review(path)

    def binding(self, review_path, r):
        p = dict(executable=True, candidate_review=r, kind='compiler',
                 out=str(self.basepath / 'attempt'))
        pp = {'path': str(self.basepath / 'plan.json'), 'sha256': 'fixture'}
        admitted = dict(coordinator='01a14893-cb1e-7203-97dd-de3da44dcf31',
                        plan=pp, charged_attempt=p['out'], phase='compiler',
                        native_execution=True, environment_qualified=True,
                        ram_bytes=1, disk_bytes=1, timeout_seconds=1)
        for key in ['grant', 'controller_receipt', 'environment_qualification', 'candidate_review']:
            admitted[key] = auth.pin(review_path)
        return p, admitted, pp

    def test_full_review_binding(self):
        path, r = self.approval()
        p, admitted, pp = self.binding(path, r)
        payload.validate_admission(p, admitted, pp)
        for field, replacement in [('candidate_success_stdout', 'WEAKENED\n'),
                                    ('baseline_failure_marker', 'other failure'),
                                    ('regression', r['candidate'])]:
            with self.subTest(field=field):
                wrong = copy.deepcopy(p)
                wrong['candidate_review'][field] = replacement
                with self.assertRaisesRegex(ValueError, 'approval binding mismatch'):
                    payload.validate_admission(wrong, admitted, pp)

    def receipt(self):
        binary = self.basepath / 'FAKE-NOT-EXECUTABLE'
        binary.write_text('fake compiler bytes')
        parent = auth.read(auth.D / 'delta-profile.json')['identity']
        return dict(compiler=auth.pin(binary), candidate_sha256=self.r['candidate']['sha256'],
                    native_build_passed=True, core_regression_passed=True,
                    candidate_review=self.r,
                    identity=prep.identity(parent, [self.r['candidate']['sha256']], prep.TAG))

    def test_core_regression_required(self):
        r = self.receipt()
        r['core_regression_passed'] = False
        with self.assertRaisesRegex(ValueError, 'core regression not passed'):
            prep.tests_plan(self.basepath / 'attempt', self.r, self.auth, r, 'metadata')

    def test_receipt_regression_review_required(self):
        r = self.receipt()
        r['candidate_review'] = copy.deepcopy(self.r)
        r['candidate_review']['candidate_success_stdout'] = 'different regression\n'
        with self.assertRaisesRegex(ValueError, 'regression review mismatch'):
            prep.tests_plan(self.basepath / 'attempt', self.r, self.auth, r, 'metadata')

    def test_compiler_mutation_after_preparation_stops_before_child(self):
        receipt = self.receipt()
        p = prep.tests_plan(self.basepath / 'attempt', self.r, self.auth, receipt, 'metadata')
        Path(receipt['compiler']['path']).write_text('REPLACED COMPILER')
        seen = []
        def no_native(stage):
            seen.append(stage['name'])
            raise AssertionError('reached child with changed compiler')
        with self.assertRaisesRegex(ValueError, 'changed/missing input'):
            payload.execute(p, dict(timeout_seconds=30, disk_bytes=20_000_000), no_native)
        self.assertEqual(seen, [])

    def test_orphan_cleanup_is_not_baseline_failure_evidence(self):
        p = self.plan()
        run, seen = self.fake(p)
        def fake(stage):
            code, stdout, stderr, join = run(stage)
            if stage['name'] == 'run-regression-baseline':
                code = 125
                join['orphaned_descendant_on_exit'] = True
            return code, stdout, stderr, join
        with self.assertRaisesRegex(ValueError, 'not cleanly joined'):
            payload.execute(p, dict(timeout_seconds=30, disk_bytes=20_000_000), fake)
        self.assertEqual(seen[-1], 'run-regression-baseline')

    def test_preexisting_link_output_rejected_before_launch(self):
        p = self.plan()
        Path(p['stages'][2]['outputs'][0]).write_text('stale executable')
        run, seen = self.fake(p)
        with self.assertRaisesRegex(ValueError, 'preexisting stage output'):
            payload.execute(p, dict(timeout_seconds=30, disk_bytes=20_000_000), run)
        self.assertEqual(seen, [])

    def test_report_escape_rejected_before_launch(self):
        p = self.plan()
        # This path is never written, even on the original implementation.
        p['stages'][0]['report'] = str(self.basepath / 'outside-attempt.report')
        def no_native(stage):
            raise AssertionError('launched with report escape')
        with self.assertRaisesRegex(ValueError, 'output escapes'):
            payload.execute(p, dict(timeout_seconds=30, disk_bytes=20_000_000), no_native)

    def test_stage_output_hashes_and_receipt_joins(self):
        p = self.plan()
        run, seen = self.fake(p)
        payload.execute(p, dict(timeout_seconds=30, disk_bytes=20_000_000), run)
        rows = auth.read(Path(p['out']) / 'results.json')
        for stage, row in zip(p['stages'], rows):
            self.assertEqual(row.get('outputs'), [auth.pin(x) for x in stage['outputs']])
            self.assertEqual(len(row.get('logs', [])), 2)
            for log in row['logs']:
                prep.verify(log)
            if 'md' in stage:
                self.assertEqual(row.get('depfile'), auth.pin(stage['md']))
        receipt = auth.read(Path(p['out']) / 'compiler-receipt.json')
        self.assertEqual(receipt.get('candidate_review'), p['candidate_review'])
        self.assertEqual(receipt.get('plan'), auth.pin(Path(p['out']) / 'plan.json'))
        self.assertEqual(receipt.get('results'), auth.pin(Path(p['out']) / 'results.json'))
        self.assertFalse(receipt['native_build_passed'])

    def test_changed_linked_compiler_cannot_be_receipted(self):
        p = self.plan()
        run, seen = self.fake(p)
        real_check = payload.check_result
        def check(stage, *args):
            real_check(stage, *args)
            if stage['name'] == 'run-regression-baseline':
                (Path(p['out']) / 'vkf-strict').write_text('changed linked compiler '+p['identity'])
        with patch.object(payload, 'check_result', check):
            with self.assertRaisesRegex(ValueError, 'changed/missing input'):
                payload.execute(p, dict(timeout_seconds=30, disk_bytes=20_000_000), run)
        self.assertFalse((Path(p['out']) / 'compiler-receipt.json').exists())

    def test_actual_link_missing_provider_rejected(self):
        p = self.plan()
        run, seen = self.fake(p)
        def fake(stage):
            result = run(stage)
            if stage['name'] == 'link-compiler':
                text = Path(stage['md']).read_text()
                first = next(a for a in stage['argv'] if a.endswith('.o'))
                Path(stage['md']).write_text(text.replace(first, '', 1))
            return result
        with self.assertRaisesRegex(ValueError, 'missing expected MD dependencies'):
            payload.execute(p, dict(timeout_seconds=30, disk_bytes=20_000_000), fake)
        self.assertEqual(seen[-1], 'link-compiler')

    def test_link_consumes_exact_generated_object_bytes(self):
        p = self.plan()
        run, seen = self.fake(p)
        def fake(stage):
            result = run(stage)
            if stage['name'] == 'link-compiler':
                Path(p['stages'][0]['outputs'][0]).write_text('changed generated object')
            return result
        with self.assertRaisesRegex(ValueError, 'dependency bytes changed'):
            payload.execute(p, dict(timeout_seconds=30, disk_bytes=20_000_000), fake)
        self.assertEqual(seen[-1], 'link-compiler')

if __name__ == '__main__':
    unittest.main(verbosity=2)
