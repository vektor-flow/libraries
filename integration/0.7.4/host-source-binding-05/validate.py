"""Bounded host-only validation. Writes only within this delivery directory."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
HOST = REPO / 'examples/gpu-math/native-vkf/host'
pins = json.loads((HERE / 'input-pins.json').read_text())['sha256']
def verify_pins():
    for path, digest in pins.items():
        assert hashlib.sha256((REPO / path).read_bytes()).hexdigest() == digest, path

verify_pins()
env = dict(os.environ, SOURCE_BINDING_NATIVE_ROOT=str(HOST.parent), PYTHONDONTWRITEBYTECODE='1')
env['PATH'] = '/home/viktor/.local/bin:' + env['PATH']
steps = []
def run(name, argv):
    start = time.monotonic()
    with (HERE / (name + '.stdout')).open('w') as out, (HERE / (name + '.stderr')).open('w') as err:
        child = subprocess.Popen(argv, cwd=REPO, env=env, stdout=out, stderr=err)
        try:
            code = child.wait(timeout=40)
        except subprocess.TimeoutExpired:
            child.kill(); child.wait(); raise
    steps.append(dict(name=name, argv=argv, pid=child.pid, returncode=code, joined=True, seconds=time.monotonic()-start))
    (HERE / 'validation.json').write_text(json.dumps({'steps': steps, 'passed': all(x['returncode'] == 0 for x in steps), 'native_executed': False}, indent=2)+'\n')
    assert code == 0, f'{name}: exit {code}; see {name}.stdout/stderr'

run('bridge-tests', ['node', '--experimental-loader', str(HERE / 'current-source-loader.mjs'), '--test',
    str(HERE / 'candidate/examples/gpu-math/native-vkf/host/tests/source-binding-bridge.mjs')])
run('revision-tests', ['node', '--test', str(REPO / 'examples/gpu-math/tests/source-revision.test.mjs')])
run('provenance-entry', ['node', str(HOST / 'tests/provenance-entry.mjs')])
run('provenance-revision', ['node', str(HOST / 'tests/provenance-revision.mjs')])
run('owner-transport', ['node', str(HOST / 'tests/pdf-owner-transport.mjs')])
if (HERE / 'source-binding.patch').exists():
    run('patch-check', ['git', 'apply', '--check', '--whitespace=error-all', str(HERE / 'source-binding.patch')])
verify_pins()
print(json.dumps({'passed': True, 'steps': len(steps), 'joined': True, 'native_executed': False}))
