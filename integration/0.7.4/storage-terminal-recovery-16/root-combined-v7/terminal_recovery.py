"""Exact live04 recovery and immutable historical authority; no generic release."""
import copy
import hashlib
import json
import os
import time
from pathlib import Path
from storage_paths import pinned, pinned_json, require

STATE_VERSION = 'direct-directory-v4'
EVENT_SCHEMA = 'live04-terminal-pre-attach-ram-release-v1'
ANCHORS = {'coordinator': '01a14893-cb1e-7203-97dd-de3da44dcf31', 'state': {'path': '/home/viktor/Projects/Vektor Flow/.coordination/s0-plan-20261012/synchronized-contexts/independent-workers/storage20gb/storage-direct-v2/direct-state-v2.json', 'sha256': 'cb52d84bc7aaf832314970a2e04fd31083923d22ef98dd0556eeb40c2aa4cc34'}, 'result': {'path': '/home/viktor/Projects/Vektor Flow/.worktrees/gpu-math-20261014-libraries/integration/0.7.4/storage-live-04/live04-f-success-01-result.json', 'sha256': '88c4bd18b63d8ed9d77468c2a8088e6bb2f52c9428b8d8b5f3266a870ebf59dc'}, 'stop': {'path': '/home/viktor/Projects/Vektor Flow/.worktrees/gpu-math-20261014-libraries/integration/0.7.4/storage-live-04/STOP.json', 'sha256': '25e123fb92f61ff6da768fd3f6c062b49a82b850fab809573e9fd34e3756f4c9'}, 'root_review': {'path': '/home/viktor/Projects/Vektor Flow/.worktrees/gpu-math-20261014-libraries/integration/0.7.4/storage-live-04/root-review.json', 'sha256': '2c10d1c061aeaddfbf5403b382b2f0cc0521295d33093c7b17e86f4c99805741'}, 'historical_source_commit': '5747ff8008ccd580b1b45ebc26560ffb0cda33fa', 'preserved_authority': {'controller': {'path': '/home/viktor/Projects/Vektor Flow/.coordination/s0-plan-20261012/synchronized-contexts/independent-workers/storage20gb/storage-direct-v2/storage_controller.py', 'sha256': '351b205d529f25ce4868132e47736645965b2b000504501d51f9cd91e2b69418'}, 'helpers': [{'path': '/home/viktor/Projects/Vektor Flow/.coordination/s0-plan-20261012/synchronized-contexts/independent-workers/storage20gb/storage-direct-v2/storage_admission.py', 'sha256': '9b409eb4cf7f0b34b1cf2f17d8e709877878afcb8a116dbe141116160fd4b6a8'}, {'path': '/home/viktor/Projects/Vektor Flow/.coordination/s0-plan-20261012/synchronized-contexts/independent-workers/storage20gb/storage-direct-v2/storage_paths.py', 'sha256': '3c7eee8d5c96d79fb70641749d6d1daae740578f2cc4666dc2c01d6e71ae1a92'}], 'config': {'path': '/home/viktor/Projects/Vektor Flow/.coordination/s0-plan-20261012/synchronized-contexts/independent-workers/storage20gb/storage-direct-v2/runtime-config.json', 'sha256': 'c74c25834ac8ed6c277bed856d538bbce30d5a959515c347f065f792a8888220'}}}

KEY = 'F:live04-f-success-01'
INVOCATION = '909c5163c9744502a918d265f61b8f71'


def authenticate_sources(state, original, anchors, load=pinned_json, check=pinned):
    require(state == load(anchors['state']), 'state snapshot changed')
    require(original == load(anchors['result']), 'failure evidence changed')
    r = state['phases'][KEY]
    require(r == original['phase'] and r['stage'] == 'launch_claimed'
            and not {'service','inner_result','join','terminal_failure_release'} & r.keys(),
            'not the exact pre-attach failure')
    require(r['worker'] == 'F' and r['phase_bytes'] == 4*2**20 and r['ram_bytes'] == 3*2**30,
            'scope/accounting')
    require(original['passed'] is False and original['outer_exit'] == 1
            and original['outer_joined'] is True
            and original['outer_identity'] == r['custody']['identity'], 'outer failure evidence')
    stop = load(anchors['stop'])
    require(stop['phase'] == KEY and stop['result'] == anchors['result'], 'STOP binding')
    check(anchors['root_review'])
    g, m = load(r['grant']), load(r['manifest'])
    c = load(r['custody']['config'])
    bundle = dict(controller=g['controller'], helpers=g['helpers'], config=r['custody']['config'])
    require(bundle == anchors['preserved_authority'], 'historical source bundle')
    require(g['runtime_config'] == r['custody']['config'] and g['controller'] == r['custody']['controller']
            and m['controller'] == g['controller'] and m['grant'] == r['grant'], 'custody pins')
    require(g['storage_admission_version'] == c['version'] == state['version'] == 'direct-directory-v2'
            and g['coordinator'] == c['coordinator'] == anchors['coordinator'], 'historical authority')
    for key in ('owner','worker','iteration','attempt','phase_scope','phase_bytes','ram_peak_bytes',
                'timeout_seconds','source_commit','inputs','argv'):
        require(g[key] == m[key], 'historical manifest '+key)
    require(g['source_commit'] == anchors['historical_source_commit'], 'historical commit pin')
    require(g['owner'] == r['owner'] and g['attempt'] == 'live04-f-success-01', 'historical attempt')
    expected=['/usr/bin/python3','-B',g['controller']['path'],
        '--config-sha256',r['custody']['config']['sha256'],
        '--grant',r['grant']['path'],'--grant-sha256',r['grant']['sha256'],
        '--manifest',r['manifest']['path'],'--manifest-sha256',r['manifest']['sha256'],'--inside-service']
    require(expected == r['custody']['service_argv'] and expected[:-1] == r['custody']['identity']['argv'],
            'exact historical controller command')
    require(r['custody']['unit'] == original['unit'] == 'vkfworkers-f-live04-f-success-01.service'
            and r['custody']['cgroup'] == c['lane_cgroups']['F']+'/'+r['custody']['unit'], 'unit/cgroup')
    require(original['properties']['InvocationID'] == INVOCATION, 'original invocation')
    policy=load(g['storage_policy'])
    require(state['lanes']['F']['policy'] == policy and state['lanes']['F']['pin'] == g['storage_policy']
            and policy['historical_charge'] == 19783524352, 'preserved historical charge')
    for p in [g['controller'], *g['helpers'], g['owned_processes'], g['resource_ledger'],
              g['predecessor_controller'], g['storage_policy'], *g['inputs'],
              policy['historical_evidence'], *[i['authority'] for i in policy['increments']]]:
        check(p)
    return r


def validate_observation(r, observation):
    from storage_controller import parse_exec_start
    p=observation['properties_before']; q=observation['properties_after']
    require(p == q, 'unit changed during observation')
    row=parse_exec_start(observation['execstart_before'])
    require(row == parse_exec_start(observation['execstart_after']), 'ExecStart changed during observation')
    require(row[1] == r['custody']['service_argv'], 'exact observed argv')
    for key,value in dict(LoadState='loaded',ActiveState='failed',SubState='failed',MainPID='0',
                         Result='exit-code',ExecMainCode='1',ExecMainStatus='1',
                         InvocationID=INVOCATION,MemoryMax=str(3*2**30),MemorySwapMax='0',
                         TasksMax='128',KillMode='control-group',OOMPolicy='kill',
                         RuntimeMaxUSec='40s',TimeoutStopUSec='10s').items():
        require(p.get(key)==value,'terminal property '+key)
    require(p['ControlGroup'] in ('',r['custody']['cgroup']), 'observed cgroup')
    require(row[7] == int(p['ExecMainPID']) == 3956707 and row[8:] == [1,1], 'independent terminal PID/status')
    require(0 < row[3] <= row[5] and 0 < row[4] <= row[6], 'terminal ExecStart timestamps')
    require(observation['boot'] == r['custody']['identity']['boot'], 'boot changed')
    # Refuse even recycled PIDs: conservative and strictly bounded to this failure.
    require(observation['outer_pid'] == r['custody']['identity']['pid'] == 3956685
            and observation['outer_starttime'] == r['custody']['identity']['starttime']
            and observation['outer_absent_before'] is True and observation['outer_absent_after'] is True,
            'outer process identity not dead')
    require(observation['inner_absent_before'] is True and observation['inner_absent_after'] is True,
            'inner process not absent')
    require(observation['cgroup'] == r['custody']['cgroup']
            and observation['empty_before'] is True and observation['empty_after'] is True,
            'nonempty or unknown service cgroup')
    return dict(result='read-only-pre-attach-terminal-evidence-verified', phase=KEY,
        passed=False, workload_result=None, original_stage='launch_claimed',
        invocation=INVOCATION, operational_mutation=False, ram_released=False,
        permanent_phase_charge=r['phase_bytes'], preserved_historical_charge=19783524352,
        total_F_charge=19783524352+r['phase_bytes'], ram_intent_still_held=r['ram_bytes'],
        release_requires='fresh coordinator transaction and separately reviewed recovery protocol')


def observe(r):
    from storage_controller import Linux, parse_get_unit
    linux=Linux(); u=r['custody']['unit']; cg=r['custody']['cgroup']; outer=r['custody']['identity']
    def properties():
        keys='LoadState,ActiveState,SubState,MainPID,ControlGroup,InvocationID,Result,ExecMainCode,ExecMainStatus,MemoryMax,MemorySwapMax,TasksMax,KillMode,OOMPolicy,RuntimeMaxUSec,TimeoutStopUSec,ExecMainPID'
        return dict(x.split('=',1) for x in linux.output(['systemctl','--user','show',u,'-p',keys]).splitlines())
    def command():
        obj=parse_get_unit(linux.output(['busctl','--user','--json=short','call','org.freedesktop.systemd1',
            '/org/freedesktop/systemd1','org.freedesktop.systemd1.Manager','GetUnit','s',u]))
        return linux.output(['busctl','--user','--json=short','get-property','org.freedesktop.systemd1',
                             obj,'org.freedesktop.systemd1.Service','ExecStart'])
    result=dict(boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),outer_pid=outer['pid'],
                outer_starttime=outer['starttime'],cgroup=cg)
    for suffix in ('before','after'):
        result['properties_'+suffix]=properties(); result['execstart_'+suffix]=command()
        result['outer_absent_'+suffix]=absent(Path('/proc')/str(outer['pid']))
        result['inner_absent_'+suffix]=absent(Path('/proc/3956707'))
        result['empty_'+suffix]=empty_cgroup(cg)
    return result


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def exact(a, b):
    # Python equality alone accepts True == 1 in authority/proof fields.
    return canonical(a) == canonical(b)


def absent(path):
    try:
        path.lstat()
    except FileNotFoundError:
        return True
    return False


def empty_cgroup(cg):
    root = Path('/sys/fs/cgroup') / cg.lstrip('/')
    require(cg.startswith('/') and '..' not in root.parts, 'invalid cgroup')
    # An absent leaf is evidence only while its known hierarchy is readable.
    require((root.parent/'cgroup.procs').is_file(), 'cgroup hierarchy unavailable')
    (root.parent/'cgroup.procs').read_text()
    if absent(root):
        return True
    from storage_controller import Linux
    return Linux().empty(cg)


def historical():
    baseline = pinned_json(ANCHORS['state'])
    original = pinned_json(ANCHORS['result'])
    r = authenticate_sources(baseline, original, ANCHORS)
    require(set(baseline['phases']) == {KEY} and set(baseline['lanes']) == {'A','F'}, 'exact baseline scope')
    require(all(not x['transitions'] for x in baseline['lanes'].values()), 'baseline owners')
    for rec in baseline['lanes'].values():
        require(exact(pinned_json(rec['pin']), rec['policy']), 'historical policy bytes')
        p = rec['policy']
        for pin in [p['predecessor_ledger'], p['predecessor_controller'], p['historical_evidence'],
                    *[i['authority'] for i in p['increments']]]:
            pinned(pin)
    return baseline, r


def authority(pin, state, lock):
    a = pinned_json(pin)
    require(exact(a, dict(schema=EVENT_SCHEMA, coordinator=ANCHORS['coordinator'],
        anchors=ANCHORS, successor_state=str(state), capacity_lock=str(lock),
        predecessor_writers_held=True, external_unit_mutations_excluded=True)), 'recovery authority')
    require(Path(state) != Path(ANCHORS['state']['path']), 'historical state cannot be overwritten')
    return a


def validate_proof(r, proof):
    validate_observation(r, proof)
    require(type(proof) is dict and set(proof) == {
        'boot','outer_pid','outer_starttime','cgroup','properties_before','properties_after',
        'execstart_before','execstart_after','outer_absent_before','outer_absent_after',
        'inner_absent_before','inner_absent_after','empty_before','empty_after'}, 'proof schema')
    require(type(proof['outer_pid']) is int and type(proof['outer_starttime']) is int,
            'proof identity types')
    require(exact(proof['properties_before'], proof['properties_after']), 'typed property mismatch')
    require(all(type(k) is str and type(v) is str for k,v in proof['properties_before'].items()),
            'property types')
    require(proof['boot'] == '36e567a7-0fa2-44a9-b95d-d93702c4b628'
            and proof['outer_starttime'] == 73984099, 'exact old identity')


def event_body(r, proof, authority_pin):
    return dict(schema=EVENT_SCHEMA, phase=KEY, original_phase_sha256=digest(r),
        authority=authority_pin, original_state=ANCHORS['state'], original_failure=ANCHORS['result'],
        historical_authority=ANCHORS['preserved_authority'], invocation=INVOCATION,
        result='terminal-failed-before-attach', passed=False, workload_result=None,
        original_stage='launch_claimed', ram_released=3221225472,
        permanent_phase_charge=4194304, cumulative_at_recovery=19787718656,
        attempt_consumed=True, observation=proof)


def _validate_legacy_state(data, authority_pin, state, lock):
    authority(authority_pin, state, lock)
    baseline, r = historical()
    require(data['version'] == STATE_VERSION, 'mandatory v4 state')
    require(set(data) == {'version','lanes','phases','recovery_events'}, 'state schema')
    require(set(data['lanes']) == set(baseline['lanes']), 'historical lane set')
    for lane, rec in baseline['lanes'].items():
        current = data['lanes'][lane]
        require(set(current) == set(rec) and exact(current['policy'], rec['policy'])
                and exact(current['pin'], rec['pin']), 'historical policy/charge changed')
    require(exact(data['phases'][KEY], r), 'original phase/history changed')
    events = data['recovery_events']
    require(type(events) is list and len(events) == 1, 'missing/duplicate recovery event')
    event = events[0]
    validate_proof(r, event['observation'])
    body = event_body(r, event['observation'], authority_pin)
    require(exact(event, dict(body, sha256=digest(body))), 'recovery event authentication')
    # New phases have unique monotonic sequence; history may not alias old attempt.
    seqs = [x['sequence'] for x in data['phases'].values()]
    require(all(type(x) is int for x in seqs) and sorted(seqs) == list(range(len(seqs))),
            'phase sequence/history')
    for key, phase in data['phases'].items():
        require(phase['worker'] in ('A','F') and key.startswith(phase['worker']+':'), 'phase lane')
        if key != KEY:
            require(type(phase['ram_bytes']) is int and phase['ram_bytes'] in (3*2**30,8*2**30)
                    and type(phase['phase_bytes']) is int and phase['phase_bytes'] > 0, 'phase accounting')
    return {KEY}


def recover(ledger):
    """Single locked publication: absent successor -> full baseline + one RAM event.

    No proof/phase selector input. Never appends to or edits the historical v2 file.
    No reader accepts a partial enrollment or missing release journal. A post-rename
    fsync error is UNCERTAIN; authenticated fsynced reread settles it, never a retry.
    """
    with ledger.transaction(initialize=True) as data:
        authority(ledger.recovery_pin, ledger.state, ledger.lock)
        baseline, r = historical()
        started = time.monotonic()
        proof = observe(r)
        validate_proof(r, proof)
        require(time.monotonic() - started <= 5.0, 'stale recovery observation')
        require(exact(historical()[0], baseline), 'source/state changed during proof')
        body = event_body(r, proof, ledger.recovery_pin)
        data.update(copy.deepcopy(baseline))
        data['version'] = STATE_VERSION
        data['recovery_events'] = [dict(body, sha256=digest(body))]
        validate_state(data, ledger.recovery_pin, ledger.state, ledger.lock)
        def final_check():
            # After temp file fsync, immediately before the one atomic publication.
            last = observe(r)
            validate_proof(r, last)
            require(exact(last, proof) and time.monotonic() - started <= 5.0,
                    'changed/expired final proof')
            historical()
        ledger.save(data, before_publish=final_check)
        return copy.deepcopy(data['recovery_events'][0])


# Exact attached-service recovery16 extension. Historical v4 event stays intact.
LIVE14_KEY = "F:live14-f-success-01"
LIVE14_SCHEMA = "live14-origin-failure-ram-release-v1"
LIVE14_AUTH_SCHEMA = "live14-exact-recovery-authority-v1"
LIVE14_ANCHORS = {'state': {'path': '/home/viktor/Projects/Vektor Flow/.worktrees/gpu-math-20261014-libraries/integration/0.7.4/storage-live-14/final-state.json', 'sha256': 'f943f65d2bbfd68324478286635d6ac8d6aa58265b76dec1b57d724ccf0f4e9f'}, 'owners': {'path': '/home/viktor/Projects/Vektor Flow/.worktrees/gpu-math-20261014-libraries/integration/0.7.4/storage-live-14/final-owner-state.json', 'sha256': '3112d1246009b72867555e067bdde675a42726625ba55611c287448eb4983f6f'}, 'failure': {'path': '/home/viktor/Projects/Vektor Flow/.worktrees/gpu-math-20261014-libraries/integration/0.7.4/storage-live-14/raw-controller-failure.json', 'sha256': '46e42dd511bd8c934a40d4954ce9099cce8e8f2b61a4f0ee7be75ec5bd9c09c7'}, 'stderr': {'path': '/home/viktor/Projects/Vektor Flow/.worktrees/gpu-math-20261014-libraries/integration/0.7.4/storage-live-14/raw-outer.stderr', 'sha256': 'a5441aa3a0d0da8b99316f488258cb3ab7e8b371843e6ea512292e8c160bc997'}, 'observation': {'path': '/home/viktor/Projects/Vektor Flow/.worktrees/gpu-math-20261014-libraries/integration/0.7.4/storage-live-14/independent-terminal-observation.json', 'sha256': '0b50464f1725f6eef814a152fa73cab3171b6cfae8ac8cf07fd42f314817ad4a'}, 'result': {'path': '/home/viktor/Projects/Vektor Flow/.worktrees/gpu-math-20261014-libraries/integration/0.7.4/storage-live-14/live14-f-success-01-result.json', 'sha256': '40861b12358a963c797a5e0ad6a52ae5e30aa6bb70ee5912fc61ea04e210520d'}, 'stop': {'path': '/home/viktor/Projects/Vektor Flow/.worktrees/gpu-math-20261014-libraries/integration/0.7.4/storage-live-14/STOP.json', 'sha256': '0e2b272350d73b423c9213f242acf0e5f197203c52357341ef195d8754d13394'}, 'legacy_authority': {'path': '/home/viktor/Projects/Vektor Flow/.coordination/s0-plan-20261012/synchronized-contexts/independent-workers/storage20gb/storage-direct-v4/recovery-authority.json', 'sha256': 'e4253476c985463453aa469aac2dd2b7111a3ac67782007b6e935688c36f268f'}}
LIVE14_STATE = '/home/viktor/Projects/Vektor Flow/.coordination/s0-plan-20261012/synchronized-contexts/independent-workers/storage20gb/storage-direct-v4/direct-state-v4.json'
LIVE14_LOCK = '/home/viktor/Projects/Vektor Flow/.coordination/s0-plan-20261012/synchronized-contexts/independent-workers/storage20gb/capacity.lock'


def protected_pin(pin):
    """No symlink components; ordinary-owner regular, single-link authority."""
    import stat
    from storage_paths import directory, strict_json
    with directory(Path(pin['path']).parent) as parent:
        ps = os.fstat(parent)
        fd = os.open(Path(pin['path']).name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        try:
            fs = os.fstat(fd)
            require(ps.st_uid == fs.st_uid == os.getuid()
                    and not (ps.st_mode | fs.st_mode) & 0o022
                    and stat.S_ISREG(fs.st_mode) and fs.st_nlink == 1, 'unprotected recovery authority')
            with os.fdopen(os.dup(fd), 'rb') as stream:
                raw = stream.read()
            require(hashlib.sha256(raw).hexdigest() == pin['sha256'], 'protected pin changed')
        finally:
            os.close(fd)
    return strict_json(raw)


def live14_authority(pin, state, lock):
    a = protected_pin(pin)
    require(exact(a, dict(schema=LIVE14_AUTH_SCHEMA, coordinator=ANCHORS['coordinator'],
        anchors=LIVE14_ANCHORS, successor_state=LIVE14_STATE, capacity_lock=LIVE14_LOCK,
        predecessor_writers_held=True, external_unit_mutations_excluded=True)),
        'exact live14 recovery authority required')
    require(str(state) == LIVE14_STATE and str(lock) == LIVE14_LOCK, 'live14 state/lock target')
    authority(LIVE14_ANCHORS['legacy_authority'], state, lock)
    return a


def live14_sources():
    """Immutable evidence only: this function never declares current custody dead."""
    from storage_controller import parse_exec_start
    a = LIVE14_ANCHORS
    baseline = pinned_json(a['state']); r = baseline['phases'][LIVE14_KEY]
    result, failure = pinned_json(a['result']), pinned_json(a['failure'])
    independent = pinned_json(a['observation']); owners = pinned_json(a['owners'])
    pinned(a['stop'])
    require(exact(r, result['phase']) and r['stage'] == 'running'
            and not {'inner_result','join','terminal_failure_release'} & r.keys(), 'exact incomplete live14 row')
    require(r['worker'] == 'F' and r['owner'] == '01a14978-0c64-7903-aea1-f81eb80b1cf4'
            and r['sequence'] == 3 and r['phase_bytes'] == 4194304
            and r['ram_bytes'] == 3221225472 and len(baseline['phases']) == 4, 'live14 scope/charges')
    require(result['passed'] is False and result['outer_exit'] == 125
            and result['outer_joined'] is True and exact(result['outer_identity'], r['custody']['identity'])
            and result['private_snapshots'] == [], 'real outer125 failure')
    require(failure['schema'] == 'storage-controller-failure-v1' and failure['phase'] == LIVE14_KEY
            and failure['stage'] == 'running' and failure['missing'] == ['inner_result']
            and failure['outer_exit'] == 1 and failure['passed'] is False
            and failure['workload_result'] is None and failure['recovery_required'] is True
            and failure['disk_charge_retained'] == r['phase_bytes']
            and failure['ram_intent_retained'] == r['ram_bytes'], 'original transport exit1 failure')
    for key in ('custody','grant','manifest'):
        require(exact(failure[key], r[key]), 'failure custody '+key)
    # Authenticate original failure receipt as well as the retained copy.
    receipt = json.loads(result['stderr'])['failure_receipt']
    require(exact(pinned_json(receipt), failure), 'original failure receipt')
    for p in failure['transport_logs']: pinned(p)
    stderr = pinned(a['stderr']).decode()
    require("private_workload.policy_gate('origin', context)" in stderr
            and 'storage_paths.Rejected: nonzero CapInh' in stderr, 'pre-child origin traceback')
    g, m = pinned_json(r['grant']), pinned_json(r['manifest'])
    c = pinned_json(r['custody']['config'])
    require(g['attempt'] == 'live14-f-success-01' and g['source_commit'] == 'b1aaaecb3702d86341c4366c91e09de2d8dd8e19'
            and g['runtime_config'] == r['custody']['config'] and g['controller'] == r['custody']['controller']
            and m['grant'] == r['grant'] and g['owner'] == r['owner']
            and g['coordinator'] == c['coordinator'] == ANCHORS['coordinator'], 'live14 source authority')
    for key in ('owner','worker','iteration','attempt','phase_scope','phase_bytes','ram_peak_bytes',
                'timeout_seconds','source_commit','inputs','argv','controller'):
        require(exact(g[key], m[key]), 'live14 manifest '+key)
    for p in [g['controller'], *g['helpers'], *g['inputs'], *m['inputs'], g['owned_processes'],
              g['resource_ledger'], g['predecessor_controller'], g['storage_policy']]: pinned(p)
    controller = pinned(g['controller']).decode()
    inner = controller[controller.index('    def inner(self):'):]
    require(inner.index("private_workload.policy_gate('origin', context)") < inner.index('subprocess.Popen('),
            'frozen failure must precede child launch')
    expected = ['/usr/bin/python3','-B',g['controller']['path'],
        '--config-sha256',r['custody']['config']['sha256'],'--grant',r['grant']['path'],
        '--grant-sha256',r['grant']['sha256'],'--manifest',r['manifest']['path'],
        '--manifest-sha256',r['manifest']['sha256'],'--inside-service']
    outer, inner = r['custody']['identity'], r['service']['identity']
    require(exact(outer['argv'], expected[:-1]) and exact(inner['argv'], expected)
            and exact(r['custody']['service_argv'], expected)
            and outer['pid'] == 4130800 and outer['starttime'] == 74671153
            and inner['pid'] == 4130900 and inner['starttime'] == 74671625
            and inner['boot'] == outer['boot'] == '36e567a7-0fa2-44a9-b95d-d93702c4b628'
            and inner['cgroup'] == r['custody']['cgroup'] == c['lane_cgroups']['F']+'/'+r['custody']['unit']
            and r['service']['invocation'] == '83ab2d1849dd46768d1a150d473bbb1a', 'live14 identities')
    row = parse_exec_start(independent['dbus_execstart'])
    require(exact(row, result['dbus_execstart']['parsed']) and row[1] == expected
            and row[7:] == [inner['pid'],1,1] and row[4] // 10000 == inner['starttime']
            and independent['ledger_join'] is False, 'independent attached identity')
    require(owners['state']['workers']['F'] == dict(thread=r['owner'], iteration=14, grant=r['grant'])
            and c['owner_state'] == owners['pin']['path'], 'live14 owner evidence')
    # All history is authenticated by the original protocol too, without rewriting it.
    _validate_legacy_state(baseline, a['legacy_authority'], LIVE14_STATE, LIVE14_LOCK)
    return baseline, r, independent, owners


def live14_current_owner():
    owners = pinned_json(LIVE14_ANCHORS['owners'])
    require(exact(protected_pin(owners['pin']), owners['state']), 'current owner changed')


def validate_live14_proof(r, proof):
    from storage_controller import parse_exec_start
    require(type(proof) is dict and set(proof) == {
        'boot','outer_identity','inner_identity','cgroup','lane_cgroups',
        'properties_before','properties_after','execstart_before','execstart_after',
        'outer_absent_before','outer_absent_after','inner_absent_before','inner_absent_after',
        'empty_before','empty_after','lanes_empty_before','lanes_empty_after',
        'payload_files_absent_before','payload_files_absent_after'}, 'live14 proof schema')
    require(exact(proof['outer_identity'], r['custody']['identity'])
            and exact(proof['inner_identity'], r['service']['identity'])
            and proof['boot'] == r['service']['identity']['boot']
            and proof['cgroup'] == r['custody']['cgroup'], 'live14 proof custody')
    config = pinned_json(r['custody']['config'])
    require(exact(proof['lane_cgroups'], config['lane_cgroups']), 'proof lanes')
    independent = pinned_json(LIVE14_ANCHORS['observation'])
    props = dict(independent['properties'], SubState='failed', ExecMainPID='4130900')
    for suffix in ('before','after'):
        require(exact(proof['properties_'+suffix], props), 'live14 terminal properties '+suffix)
        require(exact(parse_exec_start(proof['execstart_'+suffix]), independent['parsed_execstart']),
                'live14 exact ExecStart '+suffix)
        for field in ('outer_absent','inner_absent','empty','lanes_empty','payload_files_absent'):
            require(proof[field+'_'+suffix] is True, 'live14 not terminal: '+field)


def observe_live14(r):
    """Fresh dual systemd/DBus/proc/cgroup observations. No caller-supplied proof."""
    from storage_controller import Linux, parse_get_unit
    linux = Linux(); c = r['custody']; inner = r['service']['identity']
    config = pinned_json(c['config']); m = pinned_json(r['manifest'])
    proof = dict(boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
        outer_identity=copy.deepcopy(c['identity']), inner_identity=copy.deepcopy(inner),
        cgroup=c['cgroup'], lane_cgroups=config['lane_cgroups'])
    keys = 'LoadState,ActiveState,SubState,MainPID,ControlGroup,InvocationID,Result,ExecMainCode,ExecMainStatus,MemoryMax,MemorySwapMax,TasksMax,KillMode,OOMPolicy,RuntimeMaxUSec,TimeoutStopUSec,ExecMainPID'
    for suffix in ('before','after'):
        proof['properties_'+suffix] = dict(line.split('=',1) for line in linux.output(
            ['systemctl','--user','show',c['unit'],'-p',keys]).splitlines())
        obj = parse_get_unit(linux.output(['busctl','--user','--json=short','call',
            'org.freedesktop.systemd1','/org/freedesktop/systemd1','org.freedesktop.systemd1.Manager',
            'GetUnit','s',c['unit']]))
        proof['execstart_'+suffix] = linux.output(['busctl','--user','--json=short','get-property',
            'org.freedesktop.systemd1',obj,'org.freedesktop.systemd1.Service','ExecStart'])
        proof['outer_absent_'+suffix] = absent(Path('/proc')/str(c['identity']['pid']))
        proof['inner_absent_'+suffix] = absent(Path('/proc')/str(inner['pid']))
        proof['empty_'+suffix] = empty_cgroup(c['cgroup'])
        proof['lanes_empty_'+suffix] = all(empty_cgroup(cg) for cg in config['lane_cgroups'].values())
        # Frozen source opens these exclusive files before Popen. Absence supplements
        # the pinned traceback/source ordering; missing files alone prove nothing.
        from storage_paths import directory
        with directory(m['receipts']):
            proof['payload_files_absent_'+suffix] = all(absent(Path(m['receipts'])/n) for n in ('stdout','stderr'))
    return proof


def live14_event(r, proof, pin):
    body = dict(schema=LIVE14_SCHEMA, phase=LIVE14_KEY, original_phase_sha256=digest(r),
        original_state=LIVE14_ANCHORS['state'], authority=pin, anchors=LIVE14_ANCHORS,
        result='terminal-failed-at-origin-before-child', passed=False, workload_result=None,
        original_stage='running', invocation=r['service']['invocation'],
        ram_released=3221225472, permanent_phase_charge=4194304,
        cumulative_at_recovery=19800301568, attempts_consumed=4, permanent_attempt_bytes=16777216,
        attempt_consumed=True, observation=proof)
    return dict(body, sha256=digest(body))


def validate_state(data, authority_pin, state, lock):
    """Old authority still reads old states; extension requires explicit new authority."""
    a = pinned_json(authority_pin)
    if a.get('schema') != LIVE14_AUTH_SCHEMA:
        return _validate_legacy_state(data, authority_pin, state, lock)
    live14_authority(authority_pin, state, lock)
    events = data['recovery_events']
    require(type(events) is list and len(events) in (1,2), 'exact recovery event count')
    legacy = dict(data, recovery_events=events[:1])
    released = _validate_legacy_state(legacy, LIVE14_ANCHORS['legacy_authority'], state, lock)
    if len(events) == 1:
        return released  # Also permits immutable pre-live14 owner-chain snapshots.
    baseline, r, _, _ = live14_sources()
    require(exact(events[:1], baseline['recovery_events']), 'historical v4 event changed')
    require(all(k in data['phases'] and exact(data['phases'][k], v)
                for k,v in baseline['phases'].items()), 'live14 full phase history changed')
    for lane, old in baseline['lanes'].items():
        now = data['lanes'][lane]
        require(exact(old, dict(now, transitions=now['transitions'][:len(old['transitions'])])),
                'live14 lane history changed')
    validate_live14_proof(r, events[1]['observation'])
    require(exact(events[1], live14_event(r, events[1]['observation'], authority_pin)),
            'live14 exact recovery event')
    return released | {LIVE14_KEY}


def recover_live14(ledger):
    """Append exactly one event to the existing ledger under its original lock."""
    with ledger.transaction() as data:
        live14_authority(ledger.recovery_pin, ledger.state, ledger.lock)
        baseline, r, _, _ = live14_sources()
        require(exact(data, baseline), 'live14 exact current full snapshot required; no replay')
        require(ledger.owner(data, 'F') == r['owner'], 'live14 ledger owner changed')
        live14_current_owner()
        before = hashlib.sha256(ledger.state.read_bytes()).hexdigest()
        started = time.monotonic()
        proof = observe_live14(r); validate_live14_proof(r, proof)
        require(time.monotonic()-started <= 5.0, 'stale live14 proof')
        event = live14_event(r, proof, ledger.recovery_pin)
        data['recovery_events'].append(event)
        def final_check():
            live14_sources(); live14_current_owner()
            live14_authority(ledger.recovery_pin, ledger.state, ledger.lock)
            last = observe_live14(r); validate_live14_proof(r, last)
            require(exact(last, proof) and time.monotonic()-started <= 5.0, 'changed/expired live14 proof')
            require(hashlib.sha256(ledger.state.read_bytes()).hexdigest() == before,
                    'state changed before live14 publication')
        ledger.save(data, before_publish=final_check)
        return copy.deepcopy(event)


def validate_live14_transition(data, lane, index, transition, owner):
    baseline, r, _, _ = live14_sources()
    require(lane == 'F' and index == len(baseline['lanes']['F']['transitions'])
            and transition['kind'] == 'live14-recovered-terminal-failure'
            and transition['prior_phase'] == LIVE14_KEY and owner == r['owner']
            and len(data['recovery_events']) == 2
            and transition['recovery_event'] == data['recovery_events'][1]['sha256']
            and type(transition['phase_sequence']) is int and transition['phase_sequence'] == 4
            and 'prior_join' not in transition, 'exact live14 recovered owner anchor')
    require(all(k in baseline['phases'] or p['worker'] != 'F' or
                (p['sequence'] >= 4 and p['owner'] != owner) for k,p in data['phases'].items()),
            'live14 retired owner reused')


def history_prefix(before, after):
    """Called only after both snapshots have authenticated event chains."""
    left = {k:v for k,v in before.items() if k not in ('lanes','phases','recovery_events')}
    right = {k:v for k,v in after.items() if k not in ('lanes','phases','recovery_events')}
    return exact(left, right) and exact(before['recovery_events'],
        after['recovery_events'][:len(before['recovery_events'])])
