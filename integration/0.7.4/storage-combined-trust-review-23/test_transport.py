"""TEST_ONLY ordinary Python processes/pipes. No namespace/service/native workload.

Exercise the real wire implementation and pinned wait_owned. _accept is a
deliberate transport-only verifier here, never runtime qualification authority.
"""
import copy
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import unittest

HERE = Path(__file__).resolve().parent
CANDIDATE = HERE.parent/'storage-namespace-trust-repair-20/combined-review'
sys.path.insert(0, str(CANDIDATE))
import private_workload as p

OWNED = Path('/home/viktor/Projects/Vektor Flow/.coordination/s0-plan-20261012/synchronized-contexts/independent-workers/storage20gb/owned-processes.py')
assert hashlib.sha256(OWNED.read_bytes()).hexdigest() == 'bdc2ccd9861d5a49f80875144963037255afef29f7ed932fea8da28ccb76c442'
spec = importlib.util.spec_from_file_location('test_only_owned', OWNED)
owned = importlib.util.module_from_spec(spec)
spec.loader.exec_module(owned)
DATA = json.loads((HERE/'TEST_ONLY-transport-data.json').read_text())
RESULTS = []


def child(mode, origin):
    channel = origin['trust_channel']
    if mode == 'exit':
        return
    if mode == 'partial':
        os.write(channel['request_fd'], b'{"stage":')
        return
    if mode == 'hang':
        time.sleep(10)
        return
    stage = 'post' if mode == 'post' else 'pre'
    launch = p.command(DATA['manifest'], origin)
    argv = launch[launch.index('pre')+4:] if stage == 'pre' else DATA['manifest']['argv']
    p.namespace_trust(stage, origin, DATA['manifest']['attempt_root'], argv,
                      DATA['origin'], DATA['observation'])
    if stage == 'pre':
        # Popen -> ordinary exec -> second ordinary exec: descriptor flags and
        # Python isolated startup are real; unshare/bwrap are NOT executed.
        os.execv(sys.executable, [sys.executable, '-I', '-B', str(Path(__file__).resolve()),
                                 '--child', 'post', json.dumps(origin)])
    for fd in (channel['request_fd'], channel['reply_fd']):
        try:
            os.fstat(fd)
        except OSError:
            continue
        raise AssertionError('payload inherited transport endpoint')


class Transport(unittest.TestCase):
    def run_wire(self, mode='pre', fail_guard=False, reject=False, timeout=5):
        trust = p.HostTrust.__new__(p.HostTrust)
        trust.host_fds, trust.pre_fds = {}, None
        trust.request_read, trust.request_write = os.pipe()
        trust.reply_read, trust.reply_write = os.pipe()
        # Force fragmentation of the real 12-14 KiB frames, without changing
        # the implementation's frame bound or relying on current pipe capacity.
        fcntl.fcntl(trust.request_read, fcntl.F_SETPIPE_SZ, 4096)
        os.set_blocking(trust.request_read, False)
        os.set_blocking(trust.reply_write, False)
        trust.buffer, trust.stages, trust.proofs = b'', [], []
        trust.origin = copy.deepcopy(DATA['origin'])
        trust.origin['trust_channel'] = dict(request_fd=trust.request_write,
            reply_fd=trust.reply_read, nonce='b'*64)
        accepted, frame_sizes, polls = [], [], [0]

        def accept(request):
            stage = 'pre' if not accepted else 'post'
            self.assertEqual(request['stage'], stage)
            self.assertEqual(request['origin'], trust.origin)
            self.assertEqual(request['nonce'], 'b'*64)
            self.assertEqual(request['observation'], DATA['observation'])
            self.assertEqual(request['context'], DATA['origin'])
            launch = p.command(DATA['manifest'], trust.origin)
            expected = launch[launch.index('pre')+4:] if stage == 'pre' else DATA['manifest']['argv']
            self.assertEqual(request['argv'], expected)
            self.assertEqual(request['attempt'], DATA['manifest']['attempt_root'])
            frame_sizes.append(len(p._frame(request)))
            if reject:
                raise PermissionError('TEST_ONLY observation rejection')
            accepted.append(stage)
        trust._accept = accept
        attached = False

        def guard():
            nonlocal attached
            polls[0] += 1
            if not attached:
                trust.attach(process)
                attached = True
            trust.poll()
            if fail_guard:
                raise RuntimeError('TEST_ONLY unchanged resource guard rejection')

        start = time.monotonic()
        with open(HERE/('TEST_ONLY-'+mode+str(fail_guard)+str(reject)+'.stderr'), 'wb') as err:
            process = subprocess.Popen([sys.executable, '-I', '-B', str(Path(__file__).resolve()),
                '--child', mode, json.dumps(trust.origin)], pass_fds=trust.pass_fds,
                start_new_session=True, stdout=subprocess.DEVNULL, stderr=err)
            pid = process.pid
            try:
                code, joined = owned.wait_owned(process, timeout, guard=guard)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=5)
                trust.close()
        self.assertFalse(Path('/proc', str(pid)).exists())
        self.assertEqual(joined.get('remaining_identities', []), [])
        RESULTS.append(dict(mode=mode, fail_guard=fail_guard, reject=reject, pid=pid,
            code=code, accepted=accepted, stages=trust.stages, frame_sizes=frame_sizes,
            polls=polls[0], elapsed=time.monotonic()-start, joined=joined))
        return code, trust, joined

    def test_two_full_frames_real_execs_and_normal_join(self):
        code, trust, joined = self.run_wire()
        self.assertEqual(code, 0)
        trust.complete()
        self.assertIsNone(joined['guard_error'])
        self.assertFalse(joined['timed_out'])

    def test_partial_frame_cannot_complete(self):
        code, trust, joined = self.run_wire('partial')
        self.assertIn(code, (0, 126))  # fast exit may precede next guard poll
        with self.assertRaises(p.require.__globals__['Rejected']):
            trust.complete()
        self.assertEqual(trust.stages, [])

    def test_guard_exception_joins_blocked_child(self):
        code, trust, joined = self.run_wire(fail_guard=True)
        self.assertEqual(code, 126)
        self.assertIn('resource guard rejection', joined['guard_error'])
        self.assertEqual(trust.stages, [])

    def test_observer_failure_sends_no_release_and_joins(self):
        code, trust, joined = self.run_wire(reject=True)
        self.assertEqual(code, 126)
        self.assertIn('observation rejection', joined['guard_error'])
        self.assertEqual(trust.stages, [])

    def test_timeout_joins_child_without_request(self):
        code, trust, joined = self.run_wire('hang', timeout=0.35)
        self.assertEqual(code, 124)
        self.assertTrue(joined['timed_out'])
        self.assertEqual(trust.stages, [])


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--child':
        child(sys.argv[2], json.loads(sys.argv[3]))
    else:
        result = unittest.main(exit=False)
        (HERE/'TEST_ONLY-transport-results.json').write_text(json.dumps(RESULTS, indent=2)+'\n')
        sys.exit(not result.result.wasSuccessful())
