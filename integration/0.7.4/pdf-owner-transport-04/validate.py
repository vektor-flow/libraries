"""Bounded host-only checks; never applies the patch or invokes VKF/native."""
import difflib
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import time

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
NATIVE = REPO / 'examples/gpu-math/native-vkf'
CANDIDATE = HERE / 'candidate/examples/gpu-math/native-vkf'


def main():
    result = {'runner_pid': os.getpid(), 'checks': [], 'native': 'UNEXECUTED',
              'renderer': 'NOT RUN', 'patch_applied': False, 'pdf_generated': False}

    def command(name, argv):
        start = time.monotonic()
        p = subprocess.Popen(argv, cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        timed_out = False
        try:
            stdout, stderr = p.communicate(timeout=30)
        except subprocess.TimeoutExpired:
            timed_out = True
            p.kill()
            stdout, stderr = p.communicate()
        finally:
            p.wait()
        (HERE / (name + '.stdout')).write_bytes(stdout)
        (HERE / (name + '.stderr')).write_bytes(stderr)
        result['checks'].append({'name': name, 'argv': argv, 'pid': p.pid,
                                 'exit': p.returncode, 'seconds': time.monotonic() - start,
                                 'joined': True, 'timeout': timed_out})
        assert not timed_out and p.returncode == 0, name
        return stdout

    def check_pins():
        pins = json.loads((HERE / 'input-pins.json').read_text())['files']
        changed = [path for path, sha in pins.items()
                   if hashlib.sha256(Path(path).read_bytes()).hexdigest() != sha]
        assert all(path == str(REPO / 'integration/0.7.4/COORDINATOR-STATUS.txt') for path in changed), changed
        result['changed_nonproduction_pins'] = changed
        for path, sha in json.loads((HERE / 'additional-input-pins.json').read_text()).items():
            assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == sha, path

    try:
        result['head'] = command('head', ['git', 'rev-parse', 'HEAD']).decode().strip()
        assert result['head'] in {'b7a52f790aa9334689200103d5616421869495bf', '897e3802cb1d61c7a6437eb2ae1c266d9dbdfc4e'}
        check_pins()
        paths = sorted(p for p in (HERE / 'candidate').rglob('*') if p.is_file())
        expected = {'document_materialize.vkf', 'latex_library.vkf', 'latex.vkf', 'host/tests/pdf-owner-transport.mjs'}
        assert {p.relative_to(CANDIDATE).as_posix() for p in paths} == expected
        patch = []
        for path in paths:
            rel = path.relative_to(HERE / 'candidate').as_posix()
            before = REPO / rel
            patch.append(f'diff --git a/{rel} b/{rel}\n')
            if not before.exists():
                patch.append('new file mode 100644\n')
            patch.extend(difflib.unified_diff(before.read_text().splitlines(keepends=True) if before.exists() else [],
                                            path.read_text().splitlines(keepends=True),
                                            fromfile='a/' + rel if before.exists() else '/dev/null', tofile='b/' + rel))
        assert (HERE / 'owner-transport.patch').read_text() == ''.join(patch)
        result['patch_matches_candidate'] = True
        result['patch_sha256'] = hashlib.sha256((HERE / 'owner-transport.patch').read_bytes()).hexdigest()
        command('forwarding-model', ['node', str(CANDIDATE / 'host/tests/pdf-owner-transport.mjs'), str(CANDIDATE), str(NATIVE)])
        command('host-provenance-entry', ['node', str(NATIVE / 'host/tests/provenance-entry.mjs')])
        command('patch-check', ['git', 'apply', '--check', '--whitespace=error-all', str(HERE / 'owner-transport.patch')])
        check_pins()
        result['production_inputs_unchanged'] = True
        result['all_checks_passed'] = True
    except BaseException as error:
        result['all_checks_passed'] = False
        result['error'] = type(error).__name__ + ': ' + str(error)
        raise
    finally:
        result['owned_children_joined'] = all(c['joined'] for c in result['checks'])
        result['child_maxrss_kib'] = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
        result['self_maxrss_kib'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        (HERE / 'validation.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
