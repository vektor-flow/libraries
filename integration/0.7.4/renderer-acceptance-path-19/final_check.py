"""Exercise delivered host CLIs and independently inspect retained reference only."""
import ast
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import time
from prepare import HERE, REPO, check, pin, save
from run_host import PYTHON, limits


def main():
    manifest = json.loads((HERE / 'fixtures.json').read_text())
    stages = []
    commands = [
        ('stdin-original', [PYTHON, '-B', str(HERE / 'write_stdin.py'), '--case', 'original', '--run-dir', str(HERE / 'future-not-created')]),
        ('stdin-edited', [PYTHON, '-B', str(HERE / 'write_stdin.py'), '--case', 'edited-full', '--layout', '--run-dir', str(HERE / 'future-not-created')]),
        ('reference-checker', [PYTHON, '-B', str(HERE / 'verify_artifacts.py'), '--case', 'original', '--pdf', manifest['legacy_pdf']['path'], '--report', manifest['legacy_report']['path']]),
        ('reference-pdfinfo', ['/usr/bin/pdfinfo', manifest['legacy_pdf']['path']]),
    ]
    for name, argv in commands:
        start = time.monotonic()
        with (HERE / (name + '.stdout')).open('xb') as out, (HERE / (name + '.stderr')).open('xb') as err:
            child = subprocess.Popen(argv, cwd=HERE, stdout=out, stderr=err,
                env={**os.environ, 'LC_ALL': 'C', 'PYTHONDONTWRITEBYTECODE': '1'},
                preexec_fn=limits, start_new_session=True)
            timeout = False
            try:
                child.wait(timeout=60)
            except subprocess.TimeoutExpired:
                timeout = True
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()
            stages.append({'name': name, 'argv': argv, 'pid': child.pid,
                'exit': child.returncode, 'seconds': time.monotonic() - start,
                'joined': True, 'timed_out': timeout, 'as_limit_bytes': 536870912})
        if timeout or child.returncode != 0:
            save(HERE / 'final-validation.json', {'passed': False, 'stages': stages})
            raise RuntimeError('Host CLI failed: ' + name)
    original = (HERE / 'stdin-original.stdout').read_text().splitlines()
    edited = (HERE / 'stdin-edited.stdout').read_text().splitlines()
    assert len(original) == len(edited) == 11
    assert original[1:10] == edited[1:10]
    assert original[0] == manifest['original']['path'] and edited[0] == manifest['edited']['path']
    assert original[-1] == '' and edited[-1].endswith('/layout.json')
    assert not (HERE / 'future-not-created').exists()
    assert [int(line.split(':')[1]) for line in (HERE / 'reference-pdfinfo.stdout').read_text().splitlines() if line.startswith('Pages:')] == [40]
    control = json.loads((HERE / 'reference-checker.stdout').read_text())
    assert control['artifact_checks_passed'] and not control['native_provenance_verified']
    refs = []
    for filename in ('input-pins.json', 'review-input-pins.json'):
        refs += json.loads((HERE / filename).read_text())
    for ref in refs:
        check(ref)
    for path in HERE.glob('*.py'):
        ast.parse(path.read_text(), filename=str(path))
    # Read-only repository checks; no commit/index/staging mutation.
    head = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True, capture_output=True, timeout=5, check=True).stdout.strip()
    diff = subprocess.run(['git', 'diff', '--exit-code'], cwd=REPO, capture_output=True, timeout=5)
    assert diff.returncode == 0 and head == '4302f7a03a5d812bf1eaf35848557d157d2e5aae'
    save(HERE / 'final-validation.json', {'passed': True, 'stages': stages, 'all_children_joined': True,
         'git_read_children_joined': True, 'source_commit': head, 'tracked_diff_empty': True,
         'input_pins_verified': len(refs), 'native_execution': False, 'reference_only': True,
         'child_maxrss_kib': resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss})
    print(json.dumps({'passed': True, 'inputs_verified': len(refs), 'children_joined': len(stages) + 2, 'native_execution': False}))


if __name__ == '__main__':
    main()
