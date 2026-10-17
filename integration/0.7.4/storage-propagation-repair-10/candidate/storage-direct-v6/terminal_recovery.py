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


def validate_state(data, authority_pin, state, lock):
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
