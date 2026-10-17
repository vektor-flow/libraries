#!/usr/bin/env python3
"""Bounded host-only validation. No source application or native execution."""
import datetime
import difflib
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
ALLOWED_HEADS = {
    '11c7b8ab0985575bda8e9554023c347e2430871e',
    'ca3015b4e65a0627c65e2cdc4048b93a0c8673ad',
}
EXPECTED_PATHS = {
    'examples/gpu-math/native-vkf/pdf_selection.vkf',
    'examples/gpu-math/native-vkf/pdf_selection_tests.vkf',
}


def main():
    result = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'runner_pid': os.getpid(), 'checks': [], 'native_tests': 'UNEXECUTED',
              'native_assertions': 41, 'pdf_generated': False,
              'source_patch_applied': False}

    def command(name, argv):
        start = time.monotonic()
        child = subprocess.Popen(argv, cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            stdout, stderr = child.communicate(timeout=30)
        except subprocess.TimeoutExpired:
            child.kill()
            stdout, stderr = child.communicate()
            raise
        finally:
            child.wait()
        (HERE / (name + '.stdout')).write_bytes(stdout)
        (HERE / (name + '.stderr')).write_bytes(stderr)
        result['checks'].append({'name': name, 'argv': argv, 'pid': child.pid,
                                 'returncode': child.returncode, 'joined': True,
                                 'seconds': time.monotonic() - start})
        if child.returncode:
            raise RuntimeError(name + ' failed; inspect its stdout/stderr')
        return stdout

    try:
        head = command('head', ['git', 'rev-parse', 'HEAD']).decode().strip()
        assert head in ALLOWED_HEADS, head
        result['head'] = head
        pins = json.loads((HERE / 'input-pins.json').read_text())
        changed = []
        for name, pin in pins['files'].items():
            if hashlib.sha256(Path(name).read_bytes()).hexdigest() != pin['sha256']:
                changed.append(name)
        # The coordinator explicitly authorized this evidence/status-only advance.
        assert all(name == str(REPO / 'integration/0.7.4/COORDINATOR-STATUS.txt')
                   for name in changed), changed
        result['changed_pinned_inputs'] = changed
        result['production_input_pins_unchanged'] = True

        paths = sorted(p for p in (HERE / 'candidate').rglob('*') if p.is_file())
        assert {p.relative_to(HERE / 'candidate').as_posix() for p in paths} == EXPECTED_PATHS
        patch = []
        for path in paths:
            relative = path.relative_to(HERE / 'candidate').as_posix()
            assert not (REPO / relative).exists(), 'New source path already exists: ' + relative
            patch.extend([f'diff --git a/{relative} b/{relative}\n', 'new file mode 100644\n'])
            patch.extend(difflib.unified_diff([], path.read_text().splitlines(keepends=True),
                                            fromfile='/dev/null', tofile='b/' + relative))
        # Check independently reconstructed patch, without applying it anywhere.
        assert (HERE / 'selection-encoding.patch').read_text() == ''.join(patch)
        result['patch_matches_candidate'] = True
        result['patch_sha256'] = hashlib.sha256((HERE / 'selection-encoding.patch').read_bytes()).hexdigest()
        command('host-oracles', [sys.executable, '-B', str(HERE / 'verify_oracles.py')])
        command('patch-check', ['git', 'apply', '--check', '--whitespace=error-all',
                                str(HERE / 'selection-encoding.patch')])
        # Source postcheck is done after both checks, not inferred from prior pins.
        for name, pin in pins['files'].items():
            if name.endswith('.vkf'):
                assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == pin['sha256'], name
        result['all_checks_passed'] = True
    except BaseException as error:
        result['all_checks_passed'] = False
        result['error'] = type(error).__name__ + ': ' + str(error)
        raise
    finally:
        result['child_maxrss_kib'] = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
        result['self_maxrss_kib'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        result['owned_children_joined'] = all(c['joined'] for c in result['checks'])
        (HERE / 'validation.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
