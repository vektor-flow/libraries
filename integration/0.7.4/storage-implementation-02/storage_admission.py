"""Inactive candidate storage core. Caller supplies authority, paths and budgets.

No launcher/CLI and no implicit enrollment. One protected state file for ALL direct
lanes; use the existing capacity.lock. The atomic state includes full disk charges
and RAM intents. It must be consulted by every successor admission path. Direct
directories have NO kernel physical quota; runtime monitoring remains mandatory.
"""
import copy
import fcntl
import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path

from storage_paths import (allocated, contained, directory, identity, pinned,
                           pinned_json, require)

VERSION = 'direct-directory-v1'
GIB = 2**30
BASE = 21_900_000_000


def integer(value, minimum=0):
    require(type(value) is int and value >= minimum, 'invalid byte/count value')
    return value


def physical(path):
    v = os.statvfs(path)
    return dict(free=v.f_bavail*v.f_frsize, used=(v.f_blocks-v.f_bfree)*v.f_frsize)


class Ledger:
    """Trusted-controller API, not a security boundary against its own OS user.

    observe/current/host/join callbacks are dependency injection seams for tests
    and the reviewed successor controller, never values taken from a job manifest.
    Production identity/allocated functions are defaults; no operational caller
    is included. Missing/corrupt state fails closed, never auto-initializes.
    """
    def __init__(self, state, lock, *, observe=identity, usage=allocated, space=physical):
        self.state, self.lock = Path(state), Path(lock)
        self.observe, self.usage, self.space = observe, usage, space

    @contextmanager
    def transaction(self, *, initialize=False):
        # State/lock parents must be coordinator-owned, outside all job RW binds.
        with directory(self.lock.parent) as parent:
            fd = os.open(self.lock.name, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW,
                         0o600, dir_fd=parent)
            try:
                fcntl.flock(fd, fcntl.LOCK_EX)
                require(os.fstat(fd).st_ino == os.stat(self.lock.name, dir_fd=parent,
                        follow_symlinks=False).st_ino, 'lock replaced')
                if initialize:
                    require(not self.state.exists() and not self.state.is_symlink(),
                            'state already exists; no reset')
                    data = dict(version=VERSION, lanes={}, phases={})
                else:
                    with directory(self.state.parent) as sp:
                        sf = os.open(self.state.name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=sp)
                        with os.fdopen(sf) as f:
                            data = json.load(f)
                    require(data['version'] == VERSION, 'unknown state version')
                yield data
            finally:
                os.close(fd)

    def save(self, data):
        """Only under transaction: file fsync, atomic replace, parent fsync."""
        with directory(self.state.parent) as parent:
            fd, name = tempfile.mkstemp(prefix='.storage-txn-', dir=self.state.parent)
            try:
                with os.fdopen(fd, 'w') as f:
                    json.dump(data, f, sort_keys=True)
                    f.write('\n')
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(Path(name).name, self.state.name,
                           src_dir_fd=parent, dst_dir_fd=parent)
                os.fsync(parent)
            finally:
                if os.path.exists(name):
                    os.unlink(name)

    def initialize(self):
        """Explicit one-time coordinator action only; never called by reserve."""
        with self.transaction(initialize=True) as data:
            self.save(data)

    def policy(self, pin):
        p = pinned_json(pin)
        require(p['version'] == VERSION and p['worker'] in ('A', 'F'), 'unreviewed lane/version')
        require(p['owner'] and p['coordinator'], 'missing ownership')
        old = pinned_json(p['predecessor_ledger'])
        require(old['worker_budget_bytes_by_lane'][p['worker']] == BASE, 'old budget mismatch')
        pinned(p['predecessor_controller'])
        evidence = pinned_json(p['historical_evidence'])
        require(evidence['worker'] == p['worker'], 'historical lane mismatch')
        h = integer(p['historical_charge'])
        require(h == max(integer(evidence['old_used']), integer(evidence['carried_charge'])),
                'historical floor mismatch')
        require(p['increments'], 'explicit additional capacity required')
        ids = set()
        for inc in p['increments']:
            require(inc['id'] not in ids, 'duplicate increment')
            ids.add(inc['id'])
            amount = integer(inc['bytes'], 1)
            authority = pinned_json(inc['authority'])
            require(all(authority[k] == p[k] for k in ('worker', 'coordinator', 'owner'))
                    and authority['id'] == inc['id'] and authority['additional_bytes'] == amount,
                    'additive authority mismatch')
        require(h <= BASE + sum(i['bytes'] for i in p['increments']), 'floor exceeds budget')
        require(p['old_volume']['dev'] != p['root']['dev'], 'old volume is not separate')
        require(22_000_000_000 <= p['old_volume']['size'] <= 24*GIB, 'old volume size')
        require(p['old_workspace']['dev'] == p['old_volume']['dev'], 'old workspace device')
        require((p['old_workspace']['dev'], p['old_workspace']['ino']) ==
                (p['old_workspace_alias']['dev'], p['old_workspace_alias']['ino']), 'old workspace alias')
        return p

    def enroll(self, policy_pin):
        """Explicit registration/amendment; consumes no phase and creates no root.

        A root must already be an empty reviewed directory. Its metadata is charged
        to physical capacity. Increment amendments cannot change history or identity.
        """
        with self.transaction() as data:
            p = self.policy(policy_pin)
            lane = p['worker']
            if lane in data['lanes']:
                previous = data['lanes'][lane]['policy']
                require({k:v for k,v in p.items() if k != 'increments'} ==
                        {k:v for k,v in previous.items() if k != 'increments'}, 'immutable policy changed')
                n = len(previous['increments'])
                require(p['increments'][:n] == previous['increments']
                        and len(p['increments']) > n, 'increments must append')
            else:
                with directory(p['root']['path']) as fd:
                    require(not os.listdir(fd), 'new root is not empty')
                for other in data['lanes'].values():
                    a, b = p['root'], other['policy']['root']
                    require((a['dev'], a['ino']) != (b['dev'], b['ino']), 'aliased root')
                    ap, bp = Path(a['path']), Path(b['path'])
                    require(not ap.is_relative_to(bp) and not bp.is_relative_to(ap), 'overlapping roots')
            data['lanes'][lane] = dict(policy=p, pin=policy_pin)
            self.check(data)
            self.save(data)

    def check(self, data):
        """Revalidate all roots; UUID dedup, physical use, charge and free floors.

        Keep the ENTIRE explicit extension commitment reserved, even after join.
        This deliberately over-reserves versus the proposal's allocation credit:
        no sampled allocated bytes can incorrectly refund backing demand.
        """
        groups, devices = {}, {}
        require(self.space('/')['free'] - 800_000_000 >= 50_000_000_000, 'internal free floor')
        for lane, rec in data['lanes'].items():
            p = self.policy(rec['pin'])
            require(p == rec['policy'], 'stored policy mismatch')
            for key in ('root', 'old_volume', 'old_workspace', 'old_workspace_alias'):
                require(self.observe(p[key]['path']) == p[key], f'{key} identity changed')
            old = self.space(p['old_volume']['path'])
            require(old['used'] <= p['historical_charge'], 'unexplained old-volume growth')
            require(old['free'] > GIB, 'old loop free floor')
            additions = sum(i['bytes'] for i in p['increments'])
            budget = BASE + additions
            phases = [r for r in data['phases'].values() if r['worker'] == lane]
            charge = p['historical_charge'] + sum(r['phase_bytes'] for r in phases)
            require(charge <= budget, 'cumulative lane budget')
            root_used = self.usage(p['root']['path'])
            require(old['used'] + root_used <= budget, 'retained physical lane budget')
            if phases:
                require(root_used <= sum(r['phase_bytes'] for r in phases), 'root metadata/phase budget')
            uuid, dev = p['root']['uuid'], p['root']['dev']
            require(dev not in devices or devices[dev] == uuid, 'device UUID conflict')
            devices[dev] = uuid
            group = groups.setdefault(uuid, dict(dev=dev, size=p['root']['size'],
                                                free=self.space(p['root']['path'])['free'], demand=0))
            require((group['dev'], group['size']) == (dev, p['root']['size']), 'UUID identity conflict')
            group['free'] = min(group['free'], self.space(p['root']['path'])['free'])
            # Old unused capacity is already covered by the preserved 250GB.
            group['demand'] += additions
            for r in phases:
                path = r['attempt_identity']['path']
                require(self.observe(path) == r['attempt_identity'], 'attempt identity changed')
                amount = self.usage(path)
                require(amount <= r['phase_bytes'], 'phase physical bound')
                if 'join' not in r:
                    require(self.space(path)['free'] > r['phase_bytes'] + GIB, 'target free floor')
        for g in groups.values():
            require(g['free'] >= 250_000_000_000 + 10*GIB + g['demand'], 'backing free floor')

    def reserve(self, grant_pin, manifest_pin, *, current, host):
        """All authority/space/RAM checks run under the SAME legacy capacity lock.

        current() returns freshly authenticated state worker entry. host() must run
        existing offload/exact-argv/cgroup/unregistered-service checks and returns
        (MemAvailable, remaining legacy RAM demand). No launch inside this method.
        Active extension intents count their FULL RAM until authenticated join.
        """
        with self.transaction() as data:
            g, m = pinned_json(grant_pin), pinned_json(manifest_pin)
            require(g.get('storage_admission_version') == VERSION, 'not a direct grant')
            lane = g['worker']
            require(lane in data['lanes'], 'lane not enrolled')
            rec = data['lanes'][lane]
            p = rec['policy']
            e = current()
            require(e['grant'] == grant_pin and e['thread'] == g['owner'] == p['owner']
                    and e['iteration'] == g['iteration'], 'owner/state mismatch')
            require(g['storage_policy'] == rec['pin'] and g['coordinator'] == p['coordinator'],
                    'policy/owner mismatch')
            require(g['predecessor_controller'] == p['predecessor_controller']
                    and g['resource_ledger'] == p['predecessor_ledger'], 'predecessor mismatch')
            pinned(g['controller']); pinned(g['owned_processes']); pinned(g['helper'])
            require(m['grant'] == grant_pin and m['controller'] == g['controller'], 'manifest pins')
            for key in ('owner', 'worker', 'iteration', 'attempt', 'phase_scope',
                        'phase_bytes', 'ram_peak_bytes', 'timeout_seconds', 'source_commit'):
                require(m[key] == g[key], f'manifest/grant {key}')
            require(g['source_commit'] and g['phase_scope'] and m['inputs'], 'missing scope/source')
            require(m['inputs'] == g['inputs'], 'input set mismatch')
            for pin in m['inputs']:
                pinned(pin)
            size = integer(g['phase_bytes'], 1)
            ram = integer(g['ram_peak_bytes'], 1)
            require(ram in (3*GIB, 8*GIB), 'RAM profile')
            require(0 < integer(g['timeout_seconds'], 1) <= 3600, 'timeout')
            require(m['argv'] == g['argv'] and m['argv'] and m['output_paths'], 'exact argv/outputs')
            require(all(Path(x).name not in ('bwrap', 'systemd-run') for x in m['argv']), 'nested launcher')
            attempt = g['attempt']
            require(isinstance(attempt, str) and attempt and all(c.isalnum() or c in '_.-' for c in attempt)
                    and attempt not in ('.', '..'), 'attempt name')
            path = str(Path(p['root']['path']) / attempt)
            require(m['attempt_root'] == path, 'attempt root mismatch')
            require(m['cwd'] and m['tmpdir'] and m['cache'] and m['ccache'] and m['receipts'], 'charged paths')
            for dest in [m[k] for k in ('cwd', 'tmpdir', 'cache', 'ccache', 'receipts')] + m['output_paths']:
                contained(path, dest)
            ai = self.observe(path)
            require((ai['dev'], ai['uuid'], ai['mount_id']) ==
                    (p['root']['dev'], p['root']['uuid'], p['root']['mount_id']), 'attempt filesystem')
            key = lane + ':' + attempt
            require(key not in data['phases'], 'attempt already permanently charged')
            require(not any(r['worker'] == lane and 'join' not in r for r in data['phases'].values()),
                    'lane has outstanding phase')
            # Bootstrap root/empty attempt metadata must be covered by the phase.
            require(self.usage(p['root']['path']) <= size + sum(
                    r['phase_bytes'] for r in data['phases'].values() if r['worker'] == lane),
                    'uncharged setup bytes')
            available, legacy_remaining = host()
            required = integer(legacy_remaining) + ram + 2*GIB + sum(
                r['ram_bytes'] for r in data['phases'].values() if 'join' not in r)
            require(integer(available) >= required, 'RAM admission floor')
            data['phases'][key] = dict(worker=lane, owner=g['owner'], phase_bytes=size,
                                      ram_bytes=ram, grant=grant_pin, manifest=manifest_pin,
                                      attempt_identity=ai, ram_required_at_admission=required)
            self.check(data)
            self.save(data)
            return key

    def monitor(self, key, *, current, host_available):
        with self.transaction() as data:
            r = data['phases'][key]
            require('join' not in r, 'phase already joined')
            e = current()
            g = pinned_json(r['grant']); m = pinned_json(r['manifest'])
            require(e['grant'] == r['grant'] and e['thread'] == r['owner']
                    and e['iteration'] == g['iteration'], 'runtime ownership')
            for pin in m['inputs']:
                pinned(pin)
            require(host_available() >= GIB, 'host RAM emergency floor')
            self.check(data)

    def join(self, key, receipt_pin, *, verify_join):
        """Trusted verifier MUST check service/cgroup/descendants and exact custody.

        Only RAM liveness is released. Disk bytes are never subtracted; failures,
        deletion, restart, or an ambiguous outcome cannot refund a phase charge.
        """
        with self.transaction() as data:
            r = data['phases'][key]
            require('join' not in r, 'already joined')
            receipt = pinned_json(receipt_pin)
            require(receipt['grant'] == r['grant'] and receipt['manifest'] == r['manifest'], 'join pins')
            require(receipt['main_pid'] == 0 and receipt['cgroup_empty'] is True
                    and receipt['remaining_identities'] == []
                    and receipt['actual_service_joined'] is True, 'ambiguous join')
            require(verify_join(copy.deepcopy(r), receipt) is True, 'join custody not authenticated')
            r['join'] = receipt_pin
            self.save(data)

    def snapshot(self):
        with self.transaction() as data:
            return copy.deepcopy(data)
