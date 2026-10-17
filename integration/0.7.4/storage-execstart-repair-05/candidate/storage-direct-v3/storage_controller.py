#!/usr/bin/env python3
"""Inactive v3 code successor; preserved v2 ledger/grant protocol. No shipped config, policy, budget, root, or activation.

One controller handles the preserved 3GiB and A-only 8GiB profiles. Old loop
launchers are deliberately not dispatched by this executable. All managed
successors share direct-state-v2.json and the predecessor capacity.lock.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

from storage_admission import Ledger, VERSION, GIB
from storage_paths import contained, directory, pinned, pinned_json, require

HERE = Path(__file__).resolve().parent
STATE_HOME = HERE.parent/'storage-direct-v2'  # One preserved ledger; never initialize a new one.
PREDECESSORS = {
    3*GIB: ('run-worker-capacity21_9gb-20261015.py',
            '19946c775339233a9bb98b05e6a6fa6d46b7c224c00cde604a128b975b37f274'),
    8*GIB: ('run-worker-latex074-build8gb-20261017.py',
            '264c5c506b50d00f47ce78f6b8152254d5346ac1fb92a0a76225822c5c6624c3'),
}
OWNED_SHA = 'bdc2ccd9861d5a49f80875144963037255afef29f7ed932fea8da28ccb76c442'
LEDGER_SHA = '6088d3518a94a49fb23ddc4d5cd8e152779c50b74373cbb19ba26d97aa7f9531'
HELPERS = ('storage_admission.py', 'storage_paths.py')
CUSTODY_EXIT = 199  # Deliberately failed transient unit retains independent terminal properties.



def pin(path):
    path = Path(path)
    return dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def proc(pid):
    try:
        p = Path('/proc')/str(pid)
        s = (p/'stat').read_text().rsplit(')', 1)[1].split()
        return dict(pid=int(pid), starttime=int(s[19]),
                    boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                    cgroup=(p/'cgroup').read_text().split('::')[-1].strip(),
                    argv=[x.decode() for x in (p/'cmdline').read_bytes().split(b'\0') if x])
    except FileNotFoundError:
        return None


def same(saved):
    return proc(saved['pid']) == saved


def mem():
    return int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines()
                    if x.startswith('MemAvailable:')))*1024


def free(path):
    v = os.statvfs(path)
    return v.f_bavail*v.f_frsize


def resident(cgroup):
    cg = Path('/sys/fs/cgroup')/cgroup.lstrip('/')
    stats = dict((x.split()[0], int(x.split()[1])) for x in (cg/'memory.stat').read_text().splitlines())
    return min(int((cg/'memory.current').read_text()), sum(stats.get(k, 0) for k in
               ('anon', 'kernel', 'shmem', 'file_dirty', 'file_writeback')))


def sandbox(m):
    root = m['attempt_root']
    return ['/usr/bin/bwrap', '--ro-bind', '/', '/', '--dev', '/dev', '--proc', '/proc',
            '--ro-bind', '/dev/shm', '/dev/shm', '--bind', root, root,
            '--unshare-pid', '--unshare-net', '--die-with-parent', '--chdir', m['cwd'],
            '--', *m['argv']]


def run_command(r, g):
    gib = g['ram_peak_bytes']//GIB
    return ['systemd-run', '--user', '--wait', '--pipe', '--expand-environment=no', '--property=Type=exec',
            '--unit='+r['custody']['unit'], '--slice=vkfworkers-'+g['worker'].lower()+'.slice',
            f'--property=MemoryMax={gib}G', '--property=MemorySwapMax=0',
            '--property=TasksMax=128', '--property=KillMode=control-group',
            '--property=OOMPolicy=kill', '--property=TimeoutStopSec=10s',
            f"--property=RuntimeMaxSec={g['timeout_seconds']+30}", '--',
            *r['custody']['service_argv']]


def typed_json(raw, signature):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'duplicate D-Bus JSON key')
            result[key] = value
        return result
    try:
        obj = json.loads(raw, object_pairs_hook=pairs)
    except (ValueError, TypeError) as error:
        raise RuntimeError('invalid D-Bus JSON') from error
    require(type(obj) is dict and set(obj) == {'type', 'data'}
            and obj['type'] == signature and type(obj['data']) is list,
            'D-Bus signature/envelope')
    return obj['data']


def parse_get_unit(raw):
    data = typed_json(raw, 'o')
    require(len(data) == 1 and type(data[0]) is str
            and re.fullmatch(r'/org/freedesktop/systemd1/unit/[A-Za-z0-9_]+', data[0]),
            'GetUnit object path')
    return data[0]


def parse_exec_start(raw):
    # busctl get-property unwraps the property variant. data IS the array of
    # structs, unlike an extra message-body wrapper. Recorded systemd259 fixture.
    data = typed_json(raw, 'a(sasbttttuii)')
    require(len(data) == 1 and type(data[0]) is list and len(data[0]) == 10,
            'single ten-field ExecStart required')
    command = data[0]
    path, argv, ignore_failure = command[:3]
    require(type(path) is str and path.startswith('/') and '\0' not in path
            and type(argv) is list and len(argv) > 0
            and all(type(x) is str and '\0' not in x for x in argv)
            and path == argv[0] and ignore_failure is False, 'ExecStart flags/path/argv')
    for index, bits, signed in ((3,64,False),(4,64,False),(5,64,False),(6,64,False),
                                (7,32,False),(8,32,True),(9,32,True)):
        n = command[index]
        low, high = (-(2**(bits-1)), 2**(bits-1)) if signed else (0, 2**bits)
        require(type(n) is int and low <= n < high, 'ExecStart integer field')
    return command


class Linux:
    """Read-only authentication plus explicit outer/inner launch calls below."""
    def output(self, argv):
        return subprocess.check_output(argv, text=True, timeout=10)

    def show(self, unit):
        keys = ('LoadState', 'MainPID', 'ActiveState', 'ControlGroup', 'InvocationID',
                'MemoryMax', 'MemorySwapMax', 'TasksMax', 'KillMode', 'OOMPolicy',
                'RuntimeMaxUSec', 'TimeoutStopUSec', 'ExecMainCode', 'ExecMainStatus', 'Result')
        raw = self.output(['systemctl', '--user', 'show', unit, *['--property='+k for k in keys]])
        return dict(line.split('=', 1) for line in raw.splitlines())

    def argv(self, unit):
        # Typed D-Bus argv avoids substring authentication and space/escape ambiguity.
        obj = parse_get_unit(self.output(['busctl', '--user', '--json=short', 'call',
            'org.freedesktop.systemd1', '/org/freedesktop/systemd1',
            'org.freedesktop.systemd1.Manager', 'GetUnit', 's', unit]))
        value = self.output(['busctl', '--user', '--json=short', 'get-property',
            'org.freedesktop.systemd1', obj, 'org.freedesktop.systemd1.Service', 'ExecStart'])
        return parse_exec_start(value)[1]

    def units(self, pattern):
        raw = self.output(['systemctl', '--user', 'list-units', '--type=service',
            '--state=running,activating,deactivating', '--plain', '--no-legend', pattern])
        return {x.split()[0] for x in raw.splitlines()}

    def empty(self, cgroup):
        require(cgroup.startswith('/') and '..' not in Path(cgroup).parts, 'invalid cgroup')
        root = Path('/sys/fs/cgroup')/cgroup.lstrip('/')
        if not root.exists():
            return True
        events = dict(x.split() for x in (root/'cgroup.events').read_text().splitlines())
        return events['populated'] == '0' and all(not p.read_text().strip()
            for p in [root/'cgroup.procs', *root.glob('**/cgroup.procs')])

    def profile(self, r, g, props):
        require(int(props['MemoryMax']) == g['ram_peak_bytes']
                and int(props['MemorySwapMax']) == 0 and int(props['TasksMax']) == 128
                and props['KillMode'] == 'control-group' and props['OOMPolicy'] == 'kill',
                'service limits changed')
        cg = Path('/sys/fs/cgroup')/r['custody']['cgroup'].lstrip('/')
        for node, values in ((cg, {'memory.max': g['ram_peak_bytes'], 'memory.swap.max': 0, 'pids.max':128}),
                             (cg.parent, {'memory.max':g['ram_peak_bytes'], 'memory.swap.max':0}),
                             (cg.parent.parent, {'memory.max':21*GIB, 'memory.swap.max':0})):
            for name, value in values.items():
                require((node/name).read_text().strip() == str(value), 'cgroup hierarchy '+name)
        if g['ram_peak_bytes'] == 8*GIB:
            require((cg.parent/'memory.high').read_text().strip() == str(7*GIB), 'A active memory.high')

    def restore_high(self, r, g):
        if g['ram_peak_bytes'] == 8*GIB:
            # Called only after independently authenticated terminal join.
            self.output(['systemctl', '--user', 'set-property', '--runtime',
                         'vkfworkers-a.slice', 'MemoryHigh=3G'])
            cg = Path('/sys/fs/cgroup')/r['custody']['cgroup'].lstrip('/')
            require((cg.parent/'memory.high').read_text().strip() == str(3*GIB), 'A high restore')


class Controller:
    def __init__(self, args, *, adapter=None, ledger=None):
        self.a = args
        self.os = adapter or Linux()
        self.config_pin = dict(path=str(HERE/'runtime-config.json'), sha256=args.config_sha256)
        self.config = pinned_json(self.config_pin)
        self.gp = dict(path=str(args.grant), sha256=args.grant_sha256)
        self.mp = dict(path=str(args.manifest), sha256=args.manifest_sha256)
        self.g, self.m = pinned_json(self.gp), pinned_json(self.mp)
        self.ledger = ledger or Ledger(STATE_HOME/'direct-state-v2.json', STATE_HOME.parent/'capacity.lock')
        self.key = self.g['worker']+':'+self.g['attempt']

    def current(self):
        c, g, m = pinned_json(self.config_pin), pinned_json(self.gp), pinned_json(self.mp)
        require(c == self.config and g == self.g and m == self.m, 'changed execution inputs')
        require(c['version'] == VERSION and c['legacy_launchers_held'] is True, 'explicit v2/hold required')
        require(g['storage_admission_version'] == VERSION and g['coordinator'] == c['coordinator'], 'grant version/coordinator')
        require(g['runtime_config'] == self.config_pin, 'config pin')
        require(g['controller'] == pin(HERE/'storage_controller.py'), 'executing controller pin')
        require(g['helpers'] == [pin(HERE/n) for n in HELPERS], 'exact helper set')
        for p in [g['controller'], *g['helpers'], g['owned_processes'], g['resource_ledger'],
                  g['predecessor_controller'], g['storage_policy'], *g['inputs']]:
            pinned(p)
        ram = g['ram_peak_bytes']
        require(ram in PREDECESSORS and (ram != 8*GIB or g['worker'] == 'A'), 'preserved profile')
        name, digest = PREDECESSORS[ram]
        require(g['predecessor_controller'] == dict(path=str(HERE.parent/name), sha256=digest), 'predecessor source')
        require(g['resource_ledger'] == dict(path=str(HERE.parent/'resource-ledger21_9gb-20261015.json'),
                sha256=LEDGER_SHA), 'immutable resource ledger')
        require(g['owned_processes'] == dict(path=str(HERE.parent/'owned-processes.py'), sha256=OWNED_SHA), 'owned helper')
        policy = pinned_json(g['storage_policy'])
        require(g['storage_policy'] in c['approved_policies'], 'root not registered in trusted config')
        require(policy['root']['uuid'] == c['development_uuid']
                and Path(policy['root']['path']).is_relative_to(Path(c['development_root']))
                and policy['root']['path'] != c['development_root'], 'development root authorization')
        volumes = pinned_json(c['deployed_volumes'])
        require(volumes['allocations'][g['worker']]['filesystem_bytes'] == policy['old_volume']['size'], 'deployed volume size')
        require(free('/mnt/vkf-storage-2tb') >= 250_000_000_000 + 10*GIB, 'preserved old backing floor')
        # Config and authority cannot be controlled through ANY enrolled writable root.
        for pp in c['approved_policies']:
            root = Path(pinned_json(pp)['root']['path'])
            protected = [self.config_pin, self.gp, self.mp, g['controller'], *g['helpers'],
                         g['owned_processes'], g['resource_ledger'], g['storage_policy'],
                         c['deployed_volumes'], c['legacy_registry'], c['adopted_offload']]
            for path in [Path(x['path']) for x in protected] + [self.ledger.state, self.ledger.lock,
                                                               Path(c['owner_state'])]:
                require(not path.is_relative_to(root), 'authority in writable root')
        # Owner state is mutable, freshly read each call; its path is config-bound.
        with directory(Path(c['owner_state']).parent) as fd:
            f = os.open(Path(c['owner_state']).name, os.O_RDONLY|os.O_NOFOLLOW, dir_fd=fd)
            with os.fdopen(f) as stream: state = json.load(stream)
        e = state['workers'][g['worker']]
        require(e['grant'] == self.gp and e['thread'] == g['owner'] and e['iteration'] == g['iteration'], 'current owner/state')
        require(m['grant'] == self.gp and m['controller'] == g['controller'], 'manifest authority')
        for k in ('owner','worker','iteration','attempt','phase_scope','phase_bytes','ram_peak_bytes',
                  'timeout_seconds','source_commit','inputs','argv'):
            require(m[k] == g[k], 'manifest '+k)
        require(re.fullmatch('[A-Za-z0-9_.-]+', g['attempt']) and g['attempt'] not in ('.','..'), 'attempt')
        require(g['source_commit'] == self.os.output(['git','-C',c['source_repository'],'rev-parse','HEAD']).strip(), 'source HEAD pin')
        # Complete input list is grant-authorized; Git HEAD alone never authenticates a dirty file.
        require(g['inputs'] and g['argv'] and 0 < g['timeout_seconds'] <= 3600, 'source/argv/timeout')
        require(Path(g['argv'][0]).is_absolute() and g['argv'][0] in {p['path'] for p in g['inputs']},
                'executable must be explicitly pinned')
        require(not any(Path(x).name in ('bwrap','systemd-run') for x in g['argv']), 'nested launcher')
        require(m['attempt_root'] == str(Path(policy['root']['path'])/g['attempt']), 'attempt root')
        for path in [m[k] for k in ('cwd','tmpdir','cache','ccache','receipts')] + m['output_paths']:
            contained(m['attempt_root'], path)
        return dict(grant=e['grant'], thread=e['thread'], iteration=e['iteration'])

    def service_argv(self):
        return ['/usr/bin/python3', '-B', str(HERE/'storage_controller.py'),
                '--config-sha256', self.a.config_sha256,
                '--grant', str(self.a.grant), '--grant-sha256', self.a.grant_sha256,
                '--manifest', str(self.a.manifest), '--manifest-sha256', self.a.manifest_sha256,
                '--inside-service']

    def custody(self, g, m):
        self.current()
        unit = 'vkfworkers-'+g['worker'].lower()+'-'+g['attempt']+'.service'
        require(self.os.show(unit)['LoadState'] == 'not-found', 'unit already exists')
        ident = proc(os.getpid()); require(ident is not None, 'outer identity missing')
        # Exact parent location is root-reviewed config; unit tail is derived, not job-controlled.
        parent = self.config['lane_cgroups'][g['worker']]
        require(parent.endswith('/vkfworkers-'+g['worker'].lower()+'.slice'), 'lane cgroup')
        return dict(identity=ident, unit=unit, service_argv=self.service_argv(),
                    cgroup=parent+'/'+unit, controller=g['controller'], config=self.config_pin)

    def authenticate_record_sources(self, r):
        g = pinned_json(r['grant'])
        c = r['custody']
        bundle = dict(controller=g['controller'], helpers=g['helpers'], config=c['config'])
        own = dict(controller=pin(HERE/'storage_controller.py'),
                   helpers=[pin(HERE/n) for n in HELPERS], config=self.config_pin)
        require(bundle == own or bundle in self.config.get('preserved_record_authorities', []),
                'unapproved historical controller/helper/config bundle')
        for p in [bundle['controller'], *bundle['helpers'], bundle['config']]:
            pinned(p)

    def authenticate_record(self, r, *, terminal=False):
        """Authenticate every active record, including records from other owners."""
        self.authenticate_record_sources(r)
        g, m = pinned_json(r['grant']), pinned_json(r['manifest'])
        c = r['custody']
        config = pinned_json(c['config'])
        expected_argv = ['/usr/bin/python3', '-B', g['controller']['path'],
            '--config-sha256', c['config']['sha256'],
            '--grant', r['grant']['path'], '--grant-sha256', r['grant']['sha256'],
            '--manifest', r['manifest']['path'], '--manifest-sha256', r['manifest']['sha256'],
            '--inside-service']
        require(g['storage_admission_version'] == VERSION and g['runtime_config'] == c['config']
                and config['coordinator'] == self.config['coordinator']
                and r['worker'] == g['worker'] and r['owner'] == g['owner']
                and c['service_argv'] == expected_argv
                and c['unit'] == 'vkfworkers-'+g['worker'].lower()+'-'+g['attempt']+'.service'
                and c['cgroup'] == config['lane_cgroups'][g['worker']]+'/'+c['unit'], 'combined registry identity')
        require(c['controller'] == g['controller'] and m['grant'] == r['grant']
                and m['controller'] == g['controller'] and r['ram_bytes'] == g['ram_peak_bytes'], 'registry pins')
        for p in [g['controller'], *g['helpers'], g['owned_processes'], c['config']]: pinned(p)
        props = self.os.show(c['unit'])
        pid = int(props['MainPID'])
        if r['stage'] == 'reserved' or (r['stage'] == 'launch_claimed' and props['LoadState'] == 'not-found'):
            require(props['LoadState'] == 'not-found' and same(c['identity']), 'reserved custody')
            return props
        require(props['LoadState'] == 'loaded' and self.os.argv(c['unit']) == c['service_argv'], 'exact ExecStart')
        if pid:
            ident = proc(pid)
            require(ident is not None and ident['cgroup'] == c['cgroup'] == props['ControlGroup'], 'service cgroup')
            if 'service' in r:
                require(ident == r['service']['identity'] and props['InvocationID'] == r['service']['invocation'], 'service identity replaced')
            else:
                require(ident['argv'] == c['service_argv'], 'service executable not yet authenticated')
            self.os.profile(r, g, props)
        if terminal:
            require('service' in r and pid == 0 and props['ActiveState'] in ('inactive','failed')
                    and props['InvocationID'] == r['service']['invocation']
                    and props['ActiveState'] == 'failed' and props['Result'] == 'exit-code'
                    and int(props['ExecMainCode']) == 1 and int(props['ExecMainStatus']) == CUSTODY_EXIT
                    and props['ControlGroup'] in ('', c['cgroup']) and self.os.empty(c['cgroup']), 'terminal service/cgroup join')
        return props

    def host(self, data):
        """Combined registry authentication under capacity.lock; never prune by PID."""
        c = self.config
        legacy = pinned_json(c['legacy_registry'])
        units = set()
        # Frozen legacy registry remains evidence; live legacy launchers cannot participate
        # because their admission code cannot account for v2 intents.
        for worker, r in legacy.items():
            old_grant, old_manifest = pinned_json(r['grant']), pinned_json(r['manifest'])
            require(old_grant['worker'] == worker and old_manifest['grant'] == r['grant']
                    and old_manifest['controller'] == old_grant['controller'], 'legacy registry pins')
            pinned(old_grant['controller'])
            require(old_grant['controller']['sha256'] in {x[1] for x in PREDECESSORS.values()}, 'legacy controller pin')
            props = self.os.show(r['unit'])
            require(not same(r['identity']) and int(props['MainPID']) == 0
                    and props['ActiveState'] in ('inactive','failed')
                    and props['ControlGroup'] in ('', c['legacy_cgroups'][worker])
                    and self.os.empty(c['legacy_cgroups'][worker]), 'live or ambiguous legacy custody')
            if props['LoadState'] == 'loaded':
                require(self.os.argv(r['unit']) == r['service_argv'], 'legacy exact ExecStart')
            else:
                # Collected units have lost independent ExecStart evidence. Explicit
                # root-reviewed terminal receipts are required instead of guessing.
                receipt = pinned_json(c['legacy_joins'][worker])
                require(receipt['identity'] == r['identity'] and receipt['unit'] == r['unit']
                        and receipt['service_argv'] == r['service_argv']
                        and receipt['actual_service_joined'] is True, 'legacy terminal receipt')
            require(r['unit'] not in units, 'duplicate legacy unit'); units.add(r['unit'])
        for r in data['phases'].values():
            if 'join' in r: continue
            require(r['custody']['unit'] not in units, 'combined registry duplicate unit')
            self.authenticate_record(r)
            units.add(r['custody']['unit'])
        require(self.os.units('vkfworkers-*.service') <= units, 'unreserved worker service')
        adopted = pinned_json(c['adopted_offload'])
        pinned(adopted['continuation_manifest'])
        phase = pinned_json(adopted['continuation_manifest'])
        pinned(dict(path=str(Path(adopted['continuation_manifest']['path']).parent/'offload.py'), sha256=phase['script_sha256']))
        props = self.os.show(adopted['service']); pid = int(props['MainPID'])
        if pid:
            i = adopted['main_identity']
            require(pid == i['pid'] and same(i) and props['ControlGroup'] == adopted['service_properties']['ControlGroup']
                    and self.os.argv(adopted['service']) == i['argv'], 'offload custody')
            remaining = max(0, 3*GIB-resident(props['ControlGroup']))
        else:
            require(props['ActiveState'] in ('inactive','failed')
                    and self.os.empty(adopted['service_properties']['ControlGroup']), 'offload terminal join')
            remaining = 0
        require(self.os.units('vkfs0-*.service') <= {adopted['service']}, 'unknown legacy demand')
        return mem(), remaining

    def authenticate(self, data, r):
        self.current()
        require(r['grant'] == self.gp and r['manifest'] == self.mp
                and r['owner'] == self.ledger.owner(data, self.g['worker']), 'record ownership')
        self.authenticate_record(r)

    def attach(self, data, r):
        self.authenticate(data, r)
        props = self.os.show(r['custody']['unit'])
        ident = proc(os.getpid())
        require(int(props['MainPID']) == os.getpid() and ident['argv'] == r['custody']['service_argv']
                and ident['cgroup'] == r['custody']['cgroup'] and same(r['custody']['identity']), 'inner/outer custody')
        return dict(identity=ident, invocation=props['InvocationID'])

    def verify_join(self, r, receipt):
        props = self.authenticate_record(r, terminal=True)
        require(r['stage'] in ('inner_finished','joined') and 'inner_result' in r, 'missing authenticated inner finish')
        require(receipt['custody'] == r['custody'] and receipt['service'] == r['service']
                and receipt['inner_result'] == r['inner_result'], 'join custody mismatch')
        require(receipt['main_pid'] == int(props['MainPID']) == 0 and receipt['cgroup_empty'] is True
                and receipt['actual_service_joined'] is True and receipt['remaining_identities'] == [], 'join receipt')
        require(not same(r['service']['identity']), 'inner controller remains')
        for saved in r['inner_result']['tracked']:
            actual = proc(saved['pid'])
            require(actual is None or actual['starttime'] != saved['starttime']
                    or actual['boot'] != r['service']['identity']['boot'], 'owned PID remains')
        for p in pinned_json(r['manifest'])['inputs']: pinned(p)
        return True

    def write_receipt(self, name, value):
        dest = Path(self.m['receipts'])/name
        contained(self.m['attempt_root'], dest)
        # Exclusive, durable evidence; existing receipt never overwritten on restart.
        with directory(dest.parent) as parent:
            fd = os.open(dest.name, os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW, 0o600, dir_fd=parent)
            with os.fdopen(fd, 'w') as stream:
                json.dump(value, stream, sort_keys=True); stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
            os.fsync(parent)
        return pin(dest)

    def seal_incomplete(self, r, *, outer_exit=None, transport_error=None):
        failure = dict(schema='storage-controller-failure-v1', phase=self.key,
            result='controller-failed-before-authenticated-completion', passed=False,
            failure_kind=('service-attach-missing' if 'service' not in r else
                          'inner-completion-missing' if 'inner_result' not in r else 'unexpected-stage'),
            workload_result=None, stage=r['stage'], grant=self.gp, manifest=self.mp,
            custody=r['custody'], missing=[k for k in ('service', 'inner_result') if k not in r],
            outer_exit=outer_exit, transport_error=transport_error,
            disk_charge_retained=r['phase_bytes'], ram_intent_retained=r['ram_bytes'],
            recovery_required=True)
        failure['transport_logs'] = [pin(p) for p in
            [Path(self.m['receipts'])/'outer.stdout', Path(self.m['receipts'])/'outer.stderr']
            if p.is_file()]
        # Observations aid diagnosis; they are never a join or release authority.
        try:
            failure['observed_service'] = self.os.show(r['custody']['unit'])
        except Exception as error:
            failure['observation_error'] = type(error).__name__+': '+str(error)
        try:
            receipt = self.write_receipt('controller-failure.json', failure)
        except Exception as error:
            raise RuntimeError('controller failed; failure receipt NOT sealed; '
                               'disk and RAM retained; no authenticated completion') from error
        print(json.dumps(dict(result=failure['result'], passed=False, failure_receipt=receipt)),
              file=sys.stderr)
        return 125

    def outer(self):
        self.current()
        key = self.ledger.reserve(self.gp, self.mp, current=self.current, host=self.host, custody=self.custody)
        # All further bytes are inside the already charged attempt.
        for name in ('cwd','tmpdir','cache','ccache','receipts'):
            Path(self.m[name]).mkdir(parents=True, exist_ok=True)
        r = self.ledger.claim_launch(key, authenticate=self.authenticate, host=self.host)
        self.write_receipt('admission.json', r)
        # Command/receipt failure after the claim cannot replay or release reservations.
        self.ledger.preexec(key, authenticate=self.authenticate, host=self.host)
        try:
            with open(Path(self.m['receipts'])/'outer.stdout', 'xb') as out, open(Path(self.m['receipts'])/'outer.stderr', 'xb') as err:
                result = subprocess.run(run_command(r, self.g), timeout=self.g['timeout_seconds']+60,
                                        stdout=out, stderr=err)
        except (OSError, subprocess.TimeoutExpired) as error:
            r = self.ledger.snapshot()['phases'][key]
            return self.seal_incomplete(r, transport_error=type(error).__name__+': '+str(error))
        r = self.ledger.snapshot()['phases'][key]
        if r['stage'] != 'inner_finished' or 'service' not in r or 'inner_result' not in r:
            return self.seal_incomplete(r, outer_exit=result.returncode)
        receipt = dict(grant=self.gp, manifest=self.mp, custody=r['custody'], service=r['service'],
                       inner_result=r['inner_result'], main_pid=0, cgroup_empty=True,
                       remaining_identities=[], actual_service_joined=True, outer_exit=result.returncode)
        self.verify_join(r, receipt)
        rp = self.write_receipt('service-join.json', receipt)
        # Restore A high only after verified join, before RAM intent release.
        self.os.restore_high(r, self.g)
        self.ledger.join(key, rp, verify_join=self.verify_join)
        return r['inner_result']['exit']

    def inner(self):
        self.current()
        self.ledger.attach_service(self.key, authenticate=self.attach)
        spec = importlib.util.spec_from_file_location('owned_cleanup', self.g['owned_processes']['path'])
        cleanup = importlib.util.module_from_spec(spec); spec.loader.exec_module(cleanup)
        cleanup.enable_subreaper()
        argv = sandbox(self.m)
        env = {**os.environ, 'PATH':'/home/viktor/.local/bin:'+os.environ['PATH'],
               'TMPDIR':self.m['tmpdir'], 'XDG_CACHE_HOME':self.m['cache'],
               'CCACHE_DIR':self.m['ccache'], 'PYTHONDONTWRITEBYTECODE':'1'}
        self.ledger.guard_service(self.key, authenticate=self.authenticate, host=self.host)
        last = [0.0]
        def guard():
            if time.monotonic()-last[0] >= 1:
                self.ledger.guard_service(self.key, authenticate=self.authenticate, host=self.host)
                last[0] = time.monotonic()
        with open(Path(self.m['receipts'])/'stdout', 'xb') as out, open(Path(self.m['receipts'])/'stderr', 'xb') as err:
            child = subprocess.Popen(argv, stdout=out, stderr=err, env=env, start_new_session=True)
            code, joined = cleanup.wait_owned(child, self.g['timeout_seconds'], guard=guard)
        # The predecessor's fast-exit result omitted the empty remaining list.
        require(joined.get('remaining_identities', []) == [], 'descendants remain')
        for p in self.m['inputs']: pinned(p)
        result = dict(exit=code, tracked=joined['tracked'], remaining_identities=[],
                      inputs_reverified=True, owned_join=joined, sandbox_argv=argv)
        self.ledger.finish_service(self.key, result, authenticate=self.authenticate)
        return code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config-sha256', required=True)
    parser.add_argument('--grant', type=Path, required=True)
    parser.add_argument('--grant-sha256', required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--manifest-sha256', required=True)
    parser.add_argument('--inside-service', action='store_true')
    a = parser.parse_args()
    require(a.grant.is_absolute() and a.manifest.is_absolute(), 'absolute authority paths')
    controller = Controller(a)
    if a.inside_service:
        controller.inner()  # Real result is durably stored in inner_result, even for failure/timeout.
        return CUSTODY_EXIT  # Do not let successful transient-unit garbage collection erase custody.
    return controller.outer()


if __name__ == '__main__':
    sys.exit(main())
