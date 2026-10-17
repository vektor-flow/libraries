"""Read-only verifier for exactly live04-f-success-01; NEVER releases a reservation.

Trust anchors are sealed in recovery-anchors.json and must be pinned by root along
with this script. No execution CLI, ledger mutation API, lock creation, or recovery
receipt that existing code could mistake for a normal join is provided.
"""
import copy
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE/'candidate'/'storage-direct-v3'))
from storage_controller import Linux, parse_exec_start, parse_get_unit
from storage_paths import pinned_json, pinned, require

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
        result['outer_absent_'+suffix]=not (Path('/proc')/str(outer['pid'])).exists()
        result['inner_absent_'+suffix]=not Path('/proc/3956707').exists()
        result['empty_'+suffix]=linux.empty(cg)
    return result


def main():
    anchors=json.loads((HERE/'recovery-anchors.json').read_text())
    state=pinned_json(anchors['state']); original=pinned_json(anchors['result'])
    r=authenticate_sources(state,original,anchors)
    observation=observe(r)
    result=validate_observation(r,observation)
    authenticate_sources(state,original,anchors)  # Detect state or pin changes across sample.
    print(json.dumps(dict(result=result,observation=observation),indent=2))

if __name__ == '__main__': main()
