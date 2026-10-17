"""Small files only. All fixtures are below this candidate's own directory.

Filesystem inventory/free/RAM/service custody are MOCKED. Real no-follow walks,
allocated-block scans, flock, atomic replacement and fsync run on tiny local files.
"""
import copy
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from storage_admission import BASE, GIB, VERSION, POLICY_VERSION, Ledger
from storage_paths import Rejected, allocated, contained, identity, pinned

HERE = Path(__file__).resolve().parent


class Fixture:
    def __init__(self, base):
        self.base = Path(base)
        self.seq = 0
        self.free = 10**15
        self.old_used = BASE - 100_000
        self.legacy = self.pin('old-ledger', {'worker_budget_bytes_by_lane': {'A': BASE, 'F': BASE}})
        self.controller = self.pin('old-controller', 'inert source')
        self.source = self.pin('input', 'tiny source')
        self.database = self.base/'extension-state.json'
        self.lock = self.base/'capacity.lock'
        self.ledger = self.open()
        self.ledger.initialize()
        self.policies = {}
        self.requests = {}

    def pin(self, name, value):
        self.seq += 1
        p = self.base/f'{name}-{self.seq}.json'
        p.write_text(json.dumps(value))
        return {'path': str(p), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}

    def observe(self, path):
        s = os.stat(path, follow_symlinks=False)
        old = Path(path).parts[-1].startswith('old-')
        return dict(path=str(path), dev=11 if old else 22, ino=s.st_ino,
                    uid=s.st_uid, gid=s.st_gid, uuid='old-fs' if old else 'development',
                    size=23_000_000_000 if old else 2_000_000_000_000,
                    mount_id=11 if old else 22, source='mock-source',
                    mount_target='/mock', mount_root='/', boot='mock-boot')

    def space(self, path):
        return dict(free=self.free, used=self.old_used if Path(path).name.startswith('old-') else 0)

    def open(self):
        return Ledger(self.database, self.lock, observe=self.observe, space=self.space)

    def enroll(self, lane='A', addition=200_000):
        root, volume, workspace = (self.base/f'{n}-{lane}' for n in ('root', 'old-volume', 'old-workspace'))
        for p in (root, volume, workspace):
            p.mkdir()
        p = dict(version=POLICY_VERSION, worker=lane, coordinator='coordinator', owner=f'owner-{lane}',
                 predecessor_ledger=self.legacy, predecessor_controller=self.controller,
                 historical_charge=self.old_used,
                 historical_evidence=self.pin('history', dict(worker=lane, old_used=self.old_used,
                                                             carried_charge=self.old_used)),
                 root=self.observe(root), old_volume=self.observe(volume),
                 old_workspace=self.observe(workspace), old_workspace_alias=self.observe(workspace),
                 increments=[])
        self.increment(p, addition, 'inc1')
        pin = self.pin('policy', p)
        self.ledger.enroll(pin)
        self.policies[lane] = (p, pin)
        return p, pin

    def increment(self, p, amount, ident):
        authority = self.pin('authority', dict(worker=p['worker'], coordinator=p['coordinator'],
                                             owner=p['owner'], id=ident, additional_bytes=amount))
        p['increments'].append(dict(id=ident, bytes=amount, authority=authority))

    def request(self, lane='A', phase=100_000, attempt='attempt1'):
        p, policy_pin = self.policies[lane]
        root = Path(p['root']['path'])/attempt
        root.mkdir()
        g = dict(storage_admission_version=VERSION, worker=lane, owner=p['owner'],
                 coordinator=p['coordinator'], iteration=1, attempt=attempt,
                 phase_scope='small mocked check', phase_bytes=phase, ram_peak_bytes=3*GIB,
                 timeout_seconds=30, source_commit='mock-source-commit', inputs=[self.source],
                 argv=['/usr/bin/true'], storage_policy=policy_pin,
                 predecessor_controller=self.controller, resource_ledger=self.legacy,
                 controller=self.controller, owned_processes=self.controller, helpers=[self.controller], owner_transition=None)
        gp = self.pin('grant', g)
        m = {k: g[k] for k in ('owner','worker','iteration','attempt','phase_scope','phase_bytes',
                              'ram_peak_bytes','timeout_seconds','source_commit','inputs','argv','controller')}
        m.update(grant=gp, attempt_root=str(root), cwd=str(root), tmpdir=str(root/'tmp'),
                 cache=str(root/'cache'), ccache=str(root/'ccache'), receipts=str(root/'receipts'),
                 output_paths=[str(root/'output')])
        mp = self.pin('manifest', m)
        entry = dict(grant=gp, thread=g['owner'], iteration=1)
        self.requests[lane] = (g, m, gp, mp, entry)
        return gp, mp, entry

    def reserve(self, lane='A', *, available=20*GIB, entry=None):
        _, _, gp, mp, e = self.requests[lane]
        return self.ledger.reserve(gp, mp, current=lambda: entry or e,
                                   host=lambda data: (available, 0), custody=self.custody)

    def custody(self, g, m):
        return dict(unit='mock-'+g['worker']+'-'+g['attempt']+'.service',
                    identity=dict(pid=99,starttime=1,boot='mock',cgroup='/outer',argv=['outer']),
                    service_argv=['mock-controller'], cgroup='/mock/service', controller=g['controller'])

    def finish(self, key):
        self.ledger.claim_launch(key, authenticate=lambda d,r: None, host=lambda d:(20*GIB,0))
        self.ledger.attach_service(key, authenticate=lambda d,r:dict(identity={'pid':100},invocation='mock'))
        self.ledger.finish_service(key, dict(remaining_identities=[],inputs_reverified=True,tracked=[],exit=0),
                                   authenticate=lambda d,r:None)

    def join(self, key, **changes):
        if self.ledger.snapshot()['phases'][key]['stage'] == 'reserved': self.finish(key)
        r = self.ledger.snapshot()['phases'][key]
        receipt = dict(grant=r['grant'], manifest=r['manifest'], main_pid=0,
                       cgroup_empty=True, remaining_identities=[], actual_service_joined=True)
        receipt.update(changes)
        rp = self.pin('join', receipt)
        self.ledger.join(key, rp, verify_join=lambda record, actual: True)


def racer(base, lane, gp, mp, e, start, result):
    # No services or grandchildren; parent joins these two tiny Python children.
    try:
        f = Fixture.__new__(Fixture)
        f.base = Path(base); f.database = f.base/'extension-state.json'; f.lock = f.base/'capacity.lock'
        f.free = 10**15; f.old_used = BASE - 100_000
        start.wait(5)
        key = f.open().reserve(gp, mp, current=lambda: e, host=lambda data: (7*GIB, 0), custody=f.custody)
        result.send(('admitted', key))
    except Rejected as exc:
        result.send(('rejected', str(exc)))
    finally:
        result.close()


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='fixture-', dir=HERE)
        self.addCleanup(self.tmp.cleanup)
        self.f = Fixture(self.tmp.name)

    def test_full_charge_retained_failure_restart_and_deletion(self):
        f = self.f; f.enroll(); f.request(phase=150_000)
        key = f.reserve()
        root = Path(f.policies['A'][0]['root']['path'])/'attempt1'
        (root/'small').write_bytes(b'x'*17)
        (root/'small').unlink()
        f.join(key, exit=1)
        fresh = f.open().snapshot()
        self.assertEqual(fresh['phases'][key]['phase_bytes'], 150_000)
        f.request(phase=150_000, attempt='attempt2')
        f.reserve()  # exact H + P + P == B
        f.join('A:attempt2', exit=0)
        f.request(phase=1, attempt='attempt3')
        with self.assertRaises(Rejected):
            f.reserve()
        self.assertEqual(sum(r['phase_bytes'] for r in f.open().snapshot()['phases'].values()), 300_000)

    def test_restart_outstanding_never_replays_or_frees_ram(self):
        f = self.f; f.enroll(); f.request(); f.reserve()
        f.ledger = f.open()
        with self.assertRaisesRegex(Rejected, 'permanently charged'):
            f.reserve()
        f.request(attempt='attempt2')
        with self.assertRaisesRegex(Rejected, 'outstanding'):
            f.reserve()

    def test_increment_append_only_and_historical_immutability(self):
        f = self.f; p, _ = f.enroll(); f.request(phase=300_000); f.reserve(); f.join('A:attempt1')
        changed = copy.deepcopy(p); f.increment(changed, 100_000, 'inc2')
        pp = f.pin('policy-more', changed); f.ledger.enroll(pp)
        f.policies['A'] = (changed, pp)
        f.request(attempt='attempt2'); f.reserve()
        for bad in (p, dict(changed, historical_charge=0), dict(changed, increments=[])):
            with self.assertRaises(Rejected):
                f.ledger.enroll(f.pin('bad-policy', bad))
        self.assertEqual(json.loads(Path(f.legacy['path']).read_text())['worker_budget_bytes_by_lane']['A'], BASE)

    def test_race_cross_lane_shared_ram_intents_and_join(self):
        f = self.f
        for lane in ('A', 'F'):
            f.enroll(lane); f.request(lane)
        ctx = multiprocessing.get_context('fork'); start = ctx.Event()
        children, pipes = [], []
        try:
            for lane in ('A', 'F'):
                _, _, gp, mp, e = f.requests[lane]
                receive, send = ctx.Pipe(duplex=False)
                child = ctx.Process(target=racer, args=(str(f.base), lane, gp, mp, e, start, send))
                child.start(); send.close(); children.append(child); pipes.append(receive)
            start.set()
            results = []
            for pipe in pipes:
                self.assertTrue(pipe.poll(10), 'tiny race child did not report')
                results.append(pipe.recv())
            self.assertEqual(sorted(x[0] for x in results), ['admitted', 'rejected'])
            self.assertIn('RAM admission floor', next(x[1] for x in results if x[0] == 'rejected'))
        finally:
            joined = []
            for child in children:
                child.join(10)
                if child.is_alive():
                    child.terminate(); child.join(5)
                joined.append(dict(pid=child.pid, exitcode=child.exitcode, alive=child.is_alive()))
                self.assertEqual(child.exitcode, 0)
            for pipe in pipes:
                pipe.close()
            log = HERE/'owned-job-joins.json'
            previous = json.loads(log.read_text()) if log.exists() else []
            log.write_text(json.dumps(previous + joined, indent=2)+'\n')
        self.assertEqual(len(f.open().snapshot()['phases']), 1)

    def test_uuid_aliases_share_backing_floor(self):
        f = self.f; f.enroll('A', addition=200_000)
        floor = 250_000_000_000 + 10*GIB
        f.free = floor + 300_000
        with self.assertRaisesRegex(Rejected, 'backing free floor'):
            f.enroll('F', addition=200_000)
        self.assertEqual(list(f.ledger.snapshot()['lanes']), ['A'])

    def test_positive_phase_exceeding_cumulative_capacity_is_rejected(self):
        f = self.f; f.enroll(); f.request(phase=300_001)
        with self.assertRaisesRegex(Rejected, 'cumulative lane budget'):
            f.reserve()
        self.assertEqual(f.open().snapshot()['phases'], {})

    def test_free_space_boundaries_and_ram_profile(self):
        f = self.f; f.enroll(); f.request()
        backing_floor = 250_000_000_000 + 10*GIB + 200_000
        f.free = backing_floor - 1
        with self.assertRaisesRegex(Rejected, 'backing free floor'):
            f.reserve()
        f.free = backing_floor
        with self.assertRaisesRegex(Rejected, 'RAM admission floor'):
            f.reserve(available=5*GIB-1)
        f.reserve(available=5*GIB)
        self.assertEqual(f.open().snapshot()['phases']['A:attempt1']['ram_bytes'], 3*GIB)

    def test_bad_authority_pin_and_no_default_addition(self):
        f = self.f; p, _ = f.enroll()
        q = copy.deepcopy(p)
        q['increments'] = []
        with self.assertRaisesRegex(Rejected, 'explicit additional'):
            f.ledger.enroll(f.pin('no-budget', q))
        q = copy.deepcopy(p); f.increment(q, 20_000, 'inc2')
        q['increments'][-1]['bytes'] += 1
        with self.assertRaisesRegex(Rejected, 'authority mismatch'):
            f.ledger.enroll(f.pin('bad-authority', q))
        Path(p['predecessor_controller']['path']).write_text('altered controller')
        f.request()
        with self.assertRaisesRegex(Rejected, 'source pin'):
            f.reserve()

    def test_root_alias_registration_rejected(self):
        f = self.f; p, _ = f.enroll('A')
        q = copy.deepcopy(p); q['worker'] = 'F'; q['owner'] = 'owner-F'
        q['historical_evidence'] = f.pin('history-f', dict(worker='F', old_used=f.old_used, carried_charge=f.old_used))
        q['increments'] = []; f.increment(q, 100_000, 'incF')
        with self.assertRaisesRegex(Rejected, 'aliased root'):
            f.ledger.enroll(f.pin('alias', q))

    def test_old_growth_and_identity_change_rejected(self):
        f = self.f; f.enroll(); f.request()
        f.old_used += 1
        with self.assertRaisesRegex(Rejected, 'old-volume growth'):
            f.reserve()
        f.old_used -= 1
        original = f.observe
        for field in ('uuid', 'ino', 'mount_id', 'boot', 'source', 'size'):
            with self.subTest(field=field):
                def altered(path):
                    value = original(path); value[field] = 'changed'; return value
                f.ledger.observe = altered
                with self.assertRaises(Rejected):
                    f.reserve()
        f.ledger.observe = original
        root = Path(f.policies['A'][0]['root']['path'])
        root.rename(root.with_name('replaced')); root.mkdir()
        with self.assertRaises((Rejected, FileNotFoundError)):
            f.reserve()

    def test_owner_unknown_version_manifest_and_source_rejected(self):
        f = self.f; f.enroll(); f.request()
        for field, value in [('storage_admission_version', 'old-loop'), ('owner', 'intruder'),
                             ('source_commit', 'other'), ('phase_bytes', -1), ('worker', 'B')]:
            g, m, gp, mp, e = f.requests['A']
            bad = dict(g); bad[field] = value
            bg = f.pin('bad-grant', bad); bm = f.pin('bad-manifest', dict(m, grant=bg))
            with self.subTest(field=field), self.assertRaises((Rejected, KeyError)):
                f.ledger.reserve(bg, bm, current=lambda: dict(e, grant=bg), host=lambda data: (20*GIB, 0), custody=f.custody)
        with self.assertRaisesRegex(Rejected, 'owner/state'):
            f.reserve(entry=dict(e, iteration=2))
        Path(f.source['path']).write_text('tampered')
        with self.assertRaisesRegex(Rejected, 'source pin'):
            f.reserve()
        self.assertEqual(f.ledger.snapshot()['phases'], {})

    def test_symlink_hardlink_parent_escape_and_special_file(self):
        base = self.f.base; root = base/'paths'; root.mkdir(); outside = base/'outside'; outside.mkdir()
        (outside/'source').write_text('tiny')
        (root/'link').symlink_to(outside, target_is_directory=True)
        with self.assertRaises(OSError):
            contained(root, root/'link'/'new')
        with self.assertRaises(Rejected):
            allocated(root)
        (root/'link').unlink()
        os.link(outside/'source', root/'hard')
        with self.assertRaises(Rejected):
            allocated(root)
        (root/'hard').unlink()
        os.mkfifo(root/'fifo')
        with self.assertRaises(Rejected):
            allocated(root)
        for dest in (root/'..'/'escape', outside/'new'):
            with self.assertRaises(Rejected):
                contained(root, dest)
        (base/'alias-parent').symlink_to(root, target_is_directory=True)
        with self.assertRaises(OSError):
            contained(base/'alias-parent', base/'alias-parent'/'new')

    def test_same_device_nested_bind_mock_rejected(self):
        root = self.f.base/'nested'; root.mkdir(); (root/'child').mkdir()
        import storage_paths
        original = storage_paths.mount_id
        root_inode = root.stat().st_ino
        with patch.object(storage_paths, 'mount_id', side_effect=lambda fd:
                          original(fd) if os.fstat(fd).st_ino == root_inode else -1):
            with self.assertRaisesRegex(Rejected, 'nested mount'):
                allocated(root)

    def test_runtime_bounds_free_ram_and_source(self):
        f = self.f; f.enroll(); f.request(phase=20_000); key = f.reserve()
        e = f.requests['A'][4]
        f.ledger.monitor(key, current=lambda: e, host_available=lambda: GIB)
        with self.assertRaisesRegex(Rejected, 'RAM emergency'):
            f.ledger.monitor(key, current=lambda: e, host_available=lambda: GIB-1)
        attempt = Path(f.policies['A'][0]['root']['path'])/'attempt1'
        (attempt/'small').write_bytes(b'x'*25_000)
        with self.assertRaisesRegex(Rejected, 'budget|bound'):
            f.ledger.monitor(key, current=lambda: e, host_available=lambda: GIB)
        (attempt/'small').unlink()
        f.free = 250_000_000_000
        with self.assertRaisesRegex(Rejected, 'backing'):
            f.ledger.monitor(key, current=lambda: e, host_available=lambda: GIB)

    def test_ambiguous_join_retains_both_reservations(self):
        f = self.f; f.enroll(); f.request(); key = f.reserve()
        for changes in ({'main_pid': 42}, {'cgroup_empty': False}, {'remaining_identities': [123]}):
            with self.assertRaisesRegex(Rejected, 'ambiguous join'):
                f.join(key, **changes)
        self.assertNotIn('join', f.ledger.snapshot()['phases'][key])

    def test_atomic_failures_before_and_after_replace(self):
        f = self.f; f.enroll(); f.request()
        with patch('storage_admission.os.replace', side_effect=OSError('injected before rename')):
            with self.assertRaises(OSError):
                f.reserve()
        self.assertEqual(f.open().snapshot()['phases'], {})
        real = os.fsync; calls = []
        def fail_directory(fd):
            calls.append(fd)
            if len(calls) == 2:
                raise OSError('injected directory sync failure after rename')
            real(fd)
        with patch('storage_admission.os.fsync', side_effect=fail_directory):
            with self.assertRaises(OSError):
                f.reserve()
        self.assertEqual(f.open().snapshot()['phases']['A:attempt1']['phase_bytes'], 100_000)
        with self.assertRaisesRegex(Rejected, 'permanently charged'):
            f.reserve()

    def test_missing_corrupt_state_no_auto_reset(self):
        f = self.f
        with self.assertRaisesRegex(Rejected, 'no reset'):
            f.ledger.initialize()
        f.database.write_text('{broken')
        with self.assertRaises(json.JSONDecodeError):
            f.open().snapshot()
        f.database.unlink()
        with self.assertRaises(FileNotFoundError):
            f.open().snapshot()


if __name__ == '__main__':
    unittest.main(verbosity=2)
