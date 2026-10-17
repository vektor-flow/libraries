"""Sequential bounded host checks; no native execution. Every child is waited."""
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
PYTHON = '/home/viktor/.local/share/cuvami-vkf/reference-venv-314/bin/python'


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024,) * 2)
    resource.setrlimit(resource.RLIMIT_CPU, (55, 55))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def main():
    # Reset inherited high-water accounting with child exec; ru_maxrss is not a
    # process-tree aggregate. Address-space caps apply independently to each child.
    stages = []
    manifest_path = HERE / 'fixtures.json'
    commands = []
    if not manifest_path.exists():
        commands.append(('prepare', [PYTHON, '-B', str(HERE / 'prepare.py')], 0))
    commands += [
        ('host-tests', [PYTHON, '-B', str(HERE / 'test_acceptance_path.py')], 0),
        ('api-surface', [PYTHON, '-B', str(REPO / 'integration/0.7.4/pdf-api-acceptance/check_surface.py'), '--repo', str(REPO)], 2),
    ]
    for name, command, expected in commands:
        start = time.monotonic()
        with (HERE / (name + '.stdout')).open('xb') as stdout, (HERE / (name + '.stderr')).open('xb') as stderr:
            child = subprocess.Popen(command, cwd=HERE, env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'},
                stdout=stdout, stderr=stderr, start_new_session=True, preexec_fn=limits)
            timed_out = False
            try:
                child.wait(timeout=60)
            except subprocess.TimeoutExpired:
                timed_out = True
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()
            stages.append({'name': name, 'argv': command, 'pid': child.pid,
                'exit': child.returncode, 'expected_exit': expected, 'seconds': time.monotonic() - start,
                'joined': True, 'timed_out': timed_out, 'as_limit_bytes': 512 * 1024 * 1024})
        if timed_out or child.returncode != expected:
            break
    result = {'stages': stages, 'passed': all(x['exit'] == x['expected_exit'] and not x['timed_out'] for x in stages),
              'child_maxrss_kib': resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
              'native_execution': False, 'all_children_joined': True, 'native_save_seconds': None}
    with (HERE / 'host-results.json').open('x') as stream:
        json.dump(result, stream, indent=2)
    print(json.dumps(result))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
