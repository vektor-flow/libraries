#!/usr/bin/env python3
"""Unchanged Python token assertions around an externally admitted native binary.

This adapter never compiles, creates temporary directories, or grants admission.
Run only inside the coordinator's bounded driver/cgroup after guarded compilation.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import unittest

sys.dont_write_bytecode = True
TESTS = (
    'test_literal_link_targets_preserve_percent_and_hash',
    'test_math_commands_comments_and_utf8_byte_spans',
    'test_one_executable_reads_fresh_unknown_sources',
    'test_verbatim_and_escaped_control_symbols',
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def pin(path):
    path = Path(path).resolve()
    return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def verify(value):
    require(pin(value['path']) == value, 'Changed pinned input: ' + value['path'])


def load_module(name, value):
    verify(value)
    spec = importlib.util.spec_from_file_location(name, value['path'])
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def input_pins(preparation):
    return [preparation[key] for key in ('test_source', 'owned_processes', 'compiler', 'normalizer')] + preparation['runtime'] + preparation['stdlib'] + [
        {'path': value['path'], 'sha256': value['sha256']} for value in preparation['modules'].values()]


def read_preparation(path, expected_hash):
    verify({'path': str(Path(path).resolve()), 'sha256': expected_hash})
    value = json.loads(Path(path).read_text())
    require(value['schema'] == 1 and value['preparation_only'] is True and value['executed'] is False, 'Invalid preparation')
    require(value['limits']['native_run_seconds'] == 10, 'Changed native deadline')
    for item in input_pins(value):
        verify(item)
    require(set(value['modules']) == {'token_dump', 'tex_tokens', 'tex_text'}, 'Unexpected local token closure')
    return value


def check_child(code, receipt):
    require(code == 0, 'Native token child failed: ' + str(code))
    require(receipt.get('timed_out') is False and receipt.get('guard_error') is None,
            'Native token child timed out or guard failed')
    require(receipt.get('orphaned_descendant_on_exit') is False and
            receipt.get('no_live_descendants') is True and receipt.get('remaining_identities') == [],
            'Native token descendants not proved joined')


def make_suite(original, runner):
    class GuardedTokens(original.NativeVkfTokens):
        __unittest_skip__ = False
        __unittest_skip_why__ = ''

        @classmethod
        def setUpClass(cls):
            # No original compiler/tempdir setup is invoked.
            pass

        @classmethod
        def tearDownClass(cls):
            # All execution evidence remains owned by the external driver.
            pass

        def tokens(self, source):
            stdout = runner(source, self._testMethodName)
            fields = list(map(int, stdout.split()))
            self.assertTrue(fields, 'Missing token count')
            self.assertGreaterEqual(fields[0], 0)
            # Original tokens() parsing and all original byte-span checks retained.
            self.assertEqual(len(fields), 1+3*fields[0])
            raw = source.encode()
            return [(fields[i], fields[i+1], fields[i+2],
                     raw[fields[i+1]:fields[i+2]].decode())
                    for i in range(1, len(fields), 3)]

    names = tuple(unittest.defaultTestLoader.getTestCaseNames(GuardedTokens))
    require(names == TESTS, 'Original four-test collection changed')
    for name in (*TESTS, 'check_tokens'):
        require(getattr(GuardedTokens, name) is getattr(original.NativeVkfTokens, name), 'Original assertion method replaced: ' + name)
    return unittest.TestSuite(GuardedTokens(name) for name in TESTS)


class OwnedTokens:
    def __init__(self, preparation, binary, directory, owned):
        self.preparation, self.binary, self.directory, self.owned = preparation, binary, directory, owned
        self.calls = 0
        owned.enable_subreaper()

    def __call__(self, source, test_name):
        self.calls += 1
        require(self.calls <= 9, 'Unexpected additional native invocation')
        attempt = self.directory / ('call-%02d' % self.calls)
        attempt.mkdir()
        fixture = self.directory / 'changed-after-compilation.tex'
        # Reuse the same file path, as in the original fresh/changed/restored test.
        fixture.write_bytes(source.encode('utf8'))
        (attempt / 'source.tex').write_bytes(fixture.read_bytes())
        (attempt / 'stdin').write_bytes((str(fixture)+'\n').encode('utf8'))
        expected_fixture = pin(fixture)

        def guard():
            verify(self.binary)
            verify(expected_fixture)

        guard()
        started = time.monotonic()
        record = {'test': test_name, 'argv': [self.binary['path']], 'cwd': str(self.directory.parent),
                  'deadline_seconds': 10, 'binary': self.binary, 'fixture': expected_fixture,
                  'stdin': pin(attempt/'stdin')}
        try:
            with (attempt/'stdin').open('rb') as stdin, (attempt/'stdout').open('wb') as stdout, (attempt/'stderr').open('wb') as stderr:
                child = subprocess.Popen(record['argv'], cwd=record['cwd'], stdin=stdin,
                                         stdout=stdout, stderr=stderr, start_new_session=True)
                # Every native launch goes directly to the pinned owned waiter.
                # The outer admitted cgroup is mandatory secondary containment.
                code, receipt = self.owned.wait_owned(child, 10, guard=guard)
            record.update(exit=code, ownership=receipt)
            guard()
            check_child(code, receipt)
            record['posthash_match'] = True
        except Exception as error:
            record['error'] = str(error)
            raise
        finally:
            record['elapsed_seconds'] = time.monotonic()-started
            for name in ('stdout', 'stderr'):
                if (attempt/name).exists():
                    record[name] = pin(attempt/name)
            (attempt/'receipt.json').write_text(json.dumps(record, indent=2)+'\n')
        return (attempt/'stdout').read_text(encoding='utf8')


def self_check(preparation):
    original = load_module('original_native_token_checks', preparation['test_source'])
    calls = []
    suite = make_suite(original, lambda source, name: calls.append((source, name)))
    require(suite.countTestCases() == 4 and calls == [], 'Static collection launched work')
    clean = {'timed_out': False, 'guard_error': None, 'orphaned_descendant_on_exit': False,
             'no_live_descendants': True, 'remaining_identities': []}
    check_child(0, clean)
    negatives = [(1, clean), (0, {**clean, 'timed_out': True}),
                 (0, {**clean, 'guard_error': 'changed input'}),
                 (0, {**clean, 'orphaned_descendant_on_exit': True}),
                 (0, {**clean, 'no_live_descendants': False}),
                 (0, {**clean, 'remaining_identities': [{'pid': 123}]}), (0, {})]
    for code, receipt in negatives:
        try:
            check_child(code, receipt)
        except ValueError:
            continue
        raise AssertionError('Guarded negative control accepted')
    print(json.dumps({'collected_unchanged_tests': list(TESTS), 'negative_receipt_controls': len(negatives),
                      'native_processes_started': 0, 'native_tests_passed': None}))


def run(preparation, binary, output):
    output = Path(output).resolve()
    require(output.is_dir() and Path.cwd().resolve() == output, 'Run from the admitted existing OUTPUT directory')
    require(Path(binary['path']).is_relative_to(output), 'Binary must belong to admitted OUTPUT')
    verify(binary)
    for key, expected in preparation['environment'].items():
        require(os.environ.get(key) == expected, 'Wrong admitted environment: ' + key)
    for key in preparation['unset']:
        require(key not in os.environ, 'Forbidden inherited environment: ' + key)
    require(os.environ.get('VKF_COMPILER') == preparation['compiler']['path'], 'Wrong compiler identity environment')
    directory = output/'python-native-evidence'
    directory.mkdir()  # Refuse reuse; never delete previous evidence.
    original = load_module('original_native_token_checks', preparation['test_source'])
    owned = load_module('pinned_owned_processes', preparation['owned_processes'])
    runner = OwnedTokens(preparation, binary, directory, owned)
    (directory/'inputs.json').write_text(json.dumps({'binary': binary, 'pins': input_pins(preparation)}, indent=2)+'\n')
    with (directory/'unittest.log').open('w') as log:
        result = unittest.TextTestRunner(stream=log, verbosity=2, failfast=True).run(make_suite(original, runner))
    posthash = True
    try:
        for value in [binary, *input_pins(preparation)]:
            verify(value)
    except (ValueError, OSError) as error:
        posthash = False
        posthash_error = str(error)
    complete = result.wasSuccessful() and result.testsRun == 4 and not result.skipped and runner.calls == 9 and posthash
    summary = {'complete': complete, 'tests_run': result.testsRun, 'skips': result.skipped,
               'errors': len(result.errors), 'failures': len(result.failures), 'native_calls': runner.calls,
               'posthash_match': posthash, 'original419_credit': 0,
               'limitation': 'Application token tests only; external launch admission and compile evidence require coordinator review.'}
    if not posthash:
        summary['posthash_error'] = posthash_error
    (directory/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(json.dumps(summary))
    return 0 if complete else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['self-check', 'run'])
    parser.add_argument('--preparation', required=True)
    parser.add_argument('--preparation-sha256', required=True)
    parser.add_argument('--binary')
    parser.add_argument('--binary-sha256')
    parser.add_argument('--output-dir')
    args = parser.parse_args()
    preparation = read_preparation(args.preparation, args.preparation_sha256)
    if args.action == 'self-check':
        self_check(preparation)
        return 0
    if not all((args.binary, args.binary_sha256, args.output_dir)):
        parser.error('run requires admitted --binary, --binary-sha256 and --output-dir')
    return run(preparation, {'path': str(Path(args.binary).resolve()), 'sha256': args.binary_sha256}, args.output_dir)


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, OSError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
