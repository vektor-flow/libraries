"""Inactive v5 storage transaction core; paired with storage_controller.py.

V1 policies retain their original owner/history. V2 grants/state add custody,
launch claims, authenticated inner completion and append-only owner transitions.
One protected state and the existing capacity.lock cover every direct lane.
Only exact terminal_recovery.recover may create successor state; no reset or refund.
All readers require the authenticated recovery event; original v2 stays unchanged.
"""
import copy
import datetime
import fcntl
import json
import os
import tempfile
import terminal_recovery as recovery
from contextlib import contextmanager
from pathlib import Path

from storage_paths import (allocated, contained, directory, identity, pinned,
                           pinned_json, require, strict_json)

POLICY_VERSION = 'direct-directory-v1'
VERSION = 'direct-directory-v2'
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
    Production identity/allocated functions are defaults; the successor supplies
    trusted service/ownership callbacks. Missing/corrupt state fails closed, never auto-initializes.
    """
    def __init__(self, state, lock, *, recovery_pin, observe=identity, usage=allocated, space=physical):
        self.state, self.lock = Path(state), Path(lock)
        self.recovery_pin = recovery_pin
        self.observe, self.usage, self.space = observe, usage, space

    @contextmanager
    def transaction(self, *, initialize=False):
        # State/lock parents must be coordinator-owned, outside all job RW binds.
        with directory(self.lock.parent) as parent:
            fd = os.open(self.lock.name, os.O_RDWR | os.O_NOFOLLOW,
                         0o600, dir_fd=parent)
            try:
                fcntl.flock(fd, fcntl.LOCK_EX)
                require(os.fstat(fd).st_ino == os.stat(self.lock.name, dir_fd=parent,
                        follow_symlinks=False).st_ino, 'lock replaced')
                if initialize:
                    require(not self.state.exists() and not self.state.is_symlink(),
                            'state already exists; no reset')
                    recovery.authority(self.recovery_pin, self.state, self.lock)
                    data = {}
                else:
                    with directory(self.state.parent) as sp:
                        sf = os.open(self.state.name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=sp)
                        with os.fdopen(sf) as f:
                            data = strict_json(f.read())
                            os.fsync(f.fileno())
                        os.fsync(sp)  # Settle a previous post-rename durability uncertainty.
                    self.released(data)
                    for lane in data['lanes']: self.owner(data, lane)
                yield data
            finally:
                os.close(fd)

    def save(self, data, *, before_publish=None):
        """Only under transaction: file fsync, atomic replace, parent fsync."""
        self.released(data)
        for lane in data['lanes']: self.owner(data, lane)
        with directory(self.state.parent) as parent:
            fd, name = tempfile.mkstemp(prefix='.storage-txn-', dir=self.state.parent)
            try:
                with os.fdopen(fd, 'w') as f:
                    json.dump(data, f, sort_keys=True)
                    f.write('\n')
                    f.flush()
                    os.fsync(f.fileno())
                if before_publish is not None: before_publish()
                os.replace(Path(name).name, self.state.name,
                           src_dir_fd=parent, dst_dir_fd=parent)
                os.fsync(parent)
            finally:
                if os.path.exists(name):
                    os.unlink(name)

    def initialize(self):
        raise RuntimeError('only exact terminal_recovery.recover may create v4 state')

    def released(self, data):
        return recovery.validate_state(data, self.recovery_pin, self.state, self.lock)

    def active_rows(self, data):
        released = self.released(data)
        return [r for key, r in data['phases'].items() if key not in released and 'join' not in r]

    def require_active_target(self, data, key):
        require(key not in self.released(data), 'recovered failed attempt permanently consumed')

    def policy(self, pin):
        p = pinned_json(pin)
        require(p['version'] == POLICY_VERSION and p['worker'] in ('A', 'F'), 'unreviewed lane/version')
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
                require(not data['lanes'][lane]['transitions'], 'capacity amendment after rotation needs reviewed extension')
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
            data['lanes'][lane] = dict(policy=p, pin=policy_pin,
                transitions=data['lanes'].get(lane, {}).get('transitions', []))
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
            self.owner(data, lane)
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
                if r in self.active_rows(data):
                    require(self.space(path)['free'] > r['phase_bytes'] + GIB, 'target free floor')
        for g in groups.values():
            require(g['free'] >= 250_000_000_000 + 10*GIB + g['demand'], 'backing free floor')

    def reserve(self, grant_pin, manifest_pin, *, current, host, custody):
        """All authority/space/RAM checks run under the SAME legacy capacity lock.

        current() returns freshly authenticated state worker entry. host(data) must run
        existing offload/exact-argv/cgroup/unregistered-service checks and returns
        (MemAvailable, remaining legacy RAM demand). custody(g,m) supplies the exact
        controller/service record saved alongside P and RAM. No launch here.
        Active extension intents count their FULL RAM until authenticated join.
        """
        with self.transaction() as data:
            g, m = pinned_json(grant_pin), pinned_json(manifest_pin)
            require(g.get('storage_admission_version') == VERSION, 'not a direct grant')
            lane = g['worker']
            require(lane in data['lanes'], 'lane not enrolled')
            rec = data['lanes'][lane]
            if lane == 'F' and recovery.LIVE14_KEY in self.released(data):
                require(self.owner(data, lane) != data['phases'][recovery.LIVE14_KEY]['owner'],
                        'live14 recovered F requires explicit owner succession')
            require(rec['transitions'], 'explicit successor owner transition required')
            p = rec['policy']
            e = current()
            require(e['grant'] == grant_pin and e['thread'] == g['owner'] == self.owner(data, lane)
                    and e['iteration'] == g['iteration'], 'owner/state mismatch')
            require(g['storage_policy'] == rec['pin'] and g['coordinator'] == p['coordinator'],
                    'policy/owner mismatch')
            require(g['predecessor_controller'] == p['predecessor_controller']
                    and g['resource_ledger'] == p['predecessor_ledger'], 'predecessor mismatch')
            pinned(g['controller']); pinned(g['owned_processes'])
            for helper in g['helpers']: pinned(helper)
            require(g['owner_transition'] == (rec['transitions'][-1] if rec['transitions'] else None),
                    'owner transition pin')
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
            require(not any(r['worker'] == lane for r in self.active_rows(data)),
                    'lane has outstanding phase')
            with directory(path) as attempt_fd:
                require(not os.listdir(attempt_fd), 'attempt must be empty before charge')
            # Bootstrap root/empty attempt metadata must be covered by the phase.
            require(self.usage(p['root']['path']) <= size + sum(
                    r['phase_bytes'] for r in data['phases'].values() if r['worker'] == lane),
                    'uncharged setup bytes')
            service = custody(g, m)
            require(service['controller'] == g['controller'] and service['service_argv']
                    and service['unit'].endswith('.service') and service['cgroup'].startswith('/'),
                    'invalid service custody')
            for field in ('pid', 'starttime', 'boot', 'cgroup', 'argv'):
                require(service['identity'][field], 'incomplete controller identity')
            require(service['unit'] not in {r['custody']['unit'] for r in data['phases'].values()},
                    'service unit reused')
            available, legacy_remaining = host(data)
            required = integer(legacy_remaining) + ram + 2*GIB + sum(
                r['ram_bytes'] for r in self.active_rows(data))
            require(integer(available) >= required, 'RAM admission floor')
            data['phases'][key] = dict(worker=lane, owner=g['owner'], phase_bytes=size,
                                      ram_bytes=ram, grant=grant_pin, manifest=manifest_pin,
                                      custody=copy.deepcopy(service), stage='reserved', sequence=len(data['phases']),
                                      attempt_identity=ai, ram_required_at_admission=required,
                                      admission=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                                          available=available, required=required,
                                          remaining_demand=legacy_remaining,
                                          policy='Full v2 RAM intents plus measured adopted-offload demand'))
            self.check(data)
            self.save(data)
            return key

    def monitor(self, key, *, current, host_available):
        with self.transaction() as data:
            self.require_active_target(data, key)
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
            self.require_active_target(data, key)
            r = data['phases'][key]
            require('join' not in r and r['stage'] == 'inner_finished', 'join requires authenticated inner finish')
            receipt = pinned_json(receipt_pin)
            require(receipt['grant'] == r['grant'] and receipt['manifest'] == r['manifest'], 'join pins')
            require(receipt['main_pid'] == 0 and receipt['cgroup_empty'] is True
                    and receipt['remaining_identities'] == []
                    and receipt['actual_service_joined'] is True, 'ambiguous join')
            require(verify_join(copy.deepcopy(r), receipt) is True, 'join custody not authenticated')
            r['join'] = receipt_pin
            r['stage'] = 'joined'
            self.save(data)

    def snapshot(self):
        with self.transaction() as data:
            return copy.deepcopy(data)

    def owner(self, data, lane):
        """Authenticate the append-only owner chain without rewriting the policy."""
        self.released(data)
        rec = data['lanes'][lane]
        owner, previous, seen = rec['policy']['owner'], None, {rec['policy']['owner']}
        barrier = 0
        for index, pin in enumerate(rec['transitions']):
            t = pinned_json(pin)
            require(t['version'] == VERSION and t['worker'] == lane
                    and t['coordinator'] == rec['policy']['coordinator']
                    and t['policy'] == rec['pin'] and t['previous'] == previous
                    and t['from_owner'] == owner and t['to_owner'] not in seen
                    and bool(t['to_owner']), 'owner chain mismatch')
            kind = t.get('kind', 'joined')
            if kind == 'recovered-terminal-failure':
                require(lane == 'F' and previous is None and t['prior_phase'] == recovery.KEY
                        and t['recovery_event'] == data['recovery_events'][0]['sha256']
                        and t['prior_phase'] in self.released(data)
                        and data['phases'][t['prior_phase']]['owner'] == owner
                        and type(t['phase_sequence']) is int and t['phase_sequence'] == 1, 'exact recovered owner anchor')
                require(all(r['worker'] != lane or k == recovery.KEY or r['sequence'] >= t['phase_sequence']
                            for k,r in data['phases'].items()), 'recovered owner history')
                require('prior_join' not in t, 'recovery is not a normal join')
            elif kind == 'live14-recovered-terminal-failure':
                recovery.validate_live14_transition(data, lane, index, t, owner)
            elif kind == 'enrolled-unused':
                require(lane == 'A' and previous is None
                        and t['enrollment'] == recovery.ANCHORS['state']
                        and type(t['phase_sequence']) is int and 1 <= t['phase_sequence'] <= len(data['phases'])
                        and all(r['worker'] != lane or r['sequence'] >= t['phase_sequence']
                                for r in data['phases'].values()), 'unused owner anchor')
                require('prior_join' not in t and 'prior_phase' not in t, 'unused is not joined')
            elif kind == 'unused-owner-revocation':
                # Append-only UNUSED chain: authenticate the exact prefix and
                # immutable quiescent snapshot; never invent a phase or join.
                before = pinned_json(t['unused_state'])
                for authority in (pin, t['unused_state']):
                    require(all(not Path(authority['path']).is_relative_to(r['policy']['root']['path'])
                                for r in data['lanes'].values()), 'unused authority in writable root')
                require(lane == 'A' and previous is not None
                        and index > 0
                        and pinned_json(previous)['kind'] in ('enrolled-unused', 'unused-owner-revocation'),
                        'unused A chain predecessor required')
                self.released(before)
                require(recovery.exact(before['lanes'][lane], dict(rec, transitions=rec['transitions'][:index]))
                        and not any(r['worker'] == lane for r in before['phases'].values())
                        and not self.active_rows(before), 'unused snapshot anchor')
                require(type(t['phase_sequence']) is int
                        and barrier <= t['phase_sequence'] == len(before['phases']) <= len(data['phases'])
                        and all(k in data['phases'] and recovery.exact(data['phases'][k], r)
                                for k,r in before['phases'].items())
                        and all(r['worker'] != lane or
                                (r['sequence'] >= t['phase_sequence'] and r['owner'] != owner)
                                for r in data['phases'].values()), 'unused owner history')
                require(not any(k in t for k in ('prior_join','prior_phase','recovery_event')),
                        'unused revocation is not phase completion')
                require(recovery.history_prefix(before, data),
                        'unused snapshot global history changed')
                require(set(before['lanes']) == set(data['lanes']), 'unused snapshot lanes')
                for other, old in before['lanes'].items():
                    now = data['lanes'][other]
                    require(recovery.exact(old, dict(now, transitions=
                        now['transitions'][:len(old['transitions'])])), 'unused snapshot lane history changed')
            else:
                require(kind == 'joined', 'unknown owner transition kind')
                prior = data['phases'][t['prior_phase']]
                require(prior['worker'] == lane and prior['owner'] == owner
                        and prior.get('join') == t['prior_join'] and prior['stage'] == 'joined',
                        'owner transition requires joined prior phase')
                pinned(t['prior_join'])
            if kind in ('enrolled-unused', 'unused-owner-revocation'):
                require(type(t['phase_sequence']) is int and t['phase_sequence'] >= barrier,
                        'unused phase barrier decreased')
                barrier = t['phase_sequence']
            owner, previous = t['to_owner'], pin
            seen.add(owner)
        return owner

    def rotate_owner(self, transition_pin, *, verify_join):
        """Explicit trusted coordinator API. No state reset and no budget amendment."""
        with self.transaction() as data:
            t = pinned_json(transition_pin)
            lane = t['worker']; rec = data['lanes'][lane]
            require(t['from_owner'] == self.owner(data, lane), 'stale owner transition')
            phases = [(k, r) for k, r in data['phases'].items() if r['worker'] == lane]
            kind = t.get('kind', 'joined')
            require(not any(r['worker'] == lane for r in self.active_rows(data)), 'outstanding phase')
            if kind == 'recovered-terminal-failure':
                require(lane == 'F' and [k for k,_ in phases] == [recovery.KEY]
                        and not rec['transitions'] and t['phase_sequence'] == 1,
                        'exact recovered F transition only')
            elif kind == 'live14-recovered-terminal-failure':
                recovery.validate_live14_transition(data, lane, len(rec['transitions']), t,
                                                    self.owner(data, lane))
                require(max(phases, key=lambda item: item[1]['sequence'])[0] == recovery.LIVE14_KEY
                        and len(data['phases']) == 4 and not self.active_rows(data),
                        'live14 latest quiescent owner succession required')
                recovery.live14_current_owner()
                started = recovery.time.monotonic()
                proof = recovery.observe_live14(data['phases'][recovery.LIVE14_KEY])
                recovery.validate_live14_proof(data['phases'][recovery.LIVE14_KEY], proof)
                require(recovery.time.monotonic()-started <= 5.0, 'stale live14 succession proof')
            elif kind == 'enrolled-unused':
                require(lane == 'A' and not phases and not rec['transitions']
                        and t['phase_sequence'] == len(data['phases']), 'exact unused A transition only')
            elif kind == 'unused-owner-revocation':
                require(lane == 'A' and not phases and bool(rec['transitions'])
                        and not self.active_rows(data), 'exact quiescent unused A only')
                require(recovery.exact(pinned_json(t['unused_state']), data),
                        'unused snapshot no longer current')
            else:
                require(kind == 'joined' and phases, 'absent prior phase')
                key, prior = max(phases, key=lambda item: item[1]['sequence'])
                require(t['prior_phase'] == key and t['prior_join'] == prior['join'], 'latest phase anchor')
                require(verify_join(copy.deepcopy(prior), pinned_json(prior['join'])) is True,
                        'prior join not independently authenticated')
            rec['transitions'].append(transition_pin)
            self.owner(data, lane)
            self.check(data)
            def final_succession_check():
                recovery.live14_current_owner()
                pinned(transition_pin)
                last = recovery.observe_live14(data['phases'][recovery.LIVE14_KEY])
                recovery.validate_live14_proof(data['phases'][recovery.LIVE14_KEY], last)
                require(recovery.exact(last, proof) and recovery.time.monotonic()-started <= 5.0,
                        'changed/expired live14 succession proof')
            self.save(data, before_publish=final_succession_check
                      if kind == 'live14-recovered-terminal-failure' else None)

    def claim_launch(self, key, *, authenticate, host):
        """Commit one launch claim. A crash consumes it; retry cannot execute."""
        with self.transaction() as data:
            self.require_active_target(data, key)
            r = data['phases'][key]
            require(r['stage'] == 'reserved', 'launch already claimed')
            authenticate(data, r)
            available, legacy = host(data)
            require(available >= integer(legacy) + 2*GIB + sum(
                x['ram_bytes'] for x in self.active_rows(data)),
                'preexec RAM floor')
            self.check(data)
            r['stage'] = 'launch_claimed'
            self.save(data)
            return copy.deepcopy(r)

    def attach_service(self, key, *, authenticate):
        with self.transaction() as data:
            self.require_active_target(data, key)
            r = data['phases'][key]
            require(r['stage'] == 'launch_claimed', 'service already attached or unclaimed')
            service = authenticate(data, r)
            require(service['invocation'] and service['identity'], 'missing service identity')
            r['service'] = copy.deepcopy(service)
            r['stage'] = 'running'
            self.check(data)
            self.save(data)

    def guard_service(self, key, *, authenticate, host):
        with self.transaction() as data:
            self.require_active_target(data, key)
            r = data['phases'][key]
            require(r['stage'] == 'running', 'service not running')
            authenticate(data, r)
            available, _ = host(data)
            require(available >= GIB, 'host RAM emergency floor')
            self.check(data)

    def finish_service(self, key, result, *, authenticate):
        """Save inner custody before terminal unit observation; never release RAM."""
        with self.transaction() as data:
            self.require_active_target(data, key)
            r = data['phases'][key]
            require(r['stage'] == 'running', 'inner finish stage')
            authenticate(data, r)
            require(result['remaining_identities'] == [] and result['inputs_reverified'] is True,
                    'inner join incomplete')
            require(isinstance(result['tracked'], list), 'missing descendant identities')
            r['inner_result'] = copy.deepcopy(result)
            r['stage'] = 'inner_finished'
            self.save(data)

    def preexec(self, key, *, authenticate, host):
        """Last locked check after writing admission evidence, immediately before exec."""
        with self.transaction() as data:
            self.require_active_target(data, key)
            r = data['phases'][key]
            require(r['stage'] == 'launch_claimed', 'preexec stage')
            authenticate(data, r)
            available, legacy = host(data)
            require(available >= integer(legacy) + 2*GIB + sum(
                x['ram_bytes'] for x in self.active_rows(data)), 'preexec RAM floor')
            self.check(data)
