"""Read-only post-failure authentication; writes only the granted evidence directory."""
import argparse, json, os, pathlib, time
from preflight import OUT, OLD, V2, STATE, REPO, save, pin, pinned, pinned_json, proc, Linux, run
from qualify import context, unchanged
from storage_controller import Controller
from storage_paths import allocated
start=time.monotonic();unchanged();cp,c,l,data=context();l.check(data)
r=data['phases']['F:live09-f-success-01'];gp,mp=r['grant'],r['manifest']
a=argparse.Namespace(config_sha256=cp['sha256'],grant=pathlib.Path(gp['path']),grant_sha256=gp['sha256'],manifest=pathlib.Path(mp['path']),manifest_sha256=mp['sha256'])
controller=Controller(a);receipt=pinned_json(r['join']);jt=time.monotonic();assert controller.verify_join(r,receipt);join_seconds=time.monotonic()-jt
assert r['stage']=='joined' and r['inner_result']['exit']==1
assert not l.active_rows(data)
assert set(data['phases'])=={'F:live04-f-success-01','F:live07-f-success-01','F:live09-f-success-01'}
before=json.loads((OUT/'preflight.json').read_text())['initial_state']
assert all(data['phases'][key]==row for key,row in before['phases'].items())
assert data['lanes']==before['lanes'] and data['recovery_events']==before['recovery_events']
original=pinned_json(data['recovery_events'][0]['original_state'])
assert data['phases']['F:live04-f-success-01']==original['phases']['F:live04-f-success-01']
adapter=Linux();assert not adapter.units('vkfworkers-*.service') and not adapter.units('vkfs0-*.service')
idents=[r['custody']['identity'],r['service']['identity'],*r['inner_result']['tracked']]
joins=[]
for ident in idents:
    actual=proc(ident['pid']);assert actual is None or actual['starttime']!=ident['starttime']
    joins.append(dict(saved=ident,observed=actual,absent_or_replaced=True))
root=pathlib.Path(pinned_json(mp)['attempt_root'])
files=[]
for p in sorted(root.rglob('*')):
    if p.is_file():files.append(pin(p))
logs={p.name:p.read_text() for p in (root/'receipts').iterdir() if p.name in ['stdout','stderr','outer.stdout','outer.stderr']}
unit=r['custody']['unit']
metrics=run(['systemctl','--user','show',unit,'-p','MemoryPeak','-p','MemorySwapPeak','-p','CPUUsageNSec','-p','ExecMainStartTimestampMonotonic','-p','ExecMainExitTimestampMonotonic'])
cgroups={}
for w in 'FA':
    cg=pathlib.Path('/sys/fs/cgroup')/c['lane_cgroups'][w].lstrip('/')
    cgroups[w]={n:(cg/n).read_text().strip() for n in ['memory.max','memory.high','memory.swap.max','pids.max','cgroup.events','cgroup.procs']}
    assert cgroups[w]['memory.max']==str((8 if w=='A' else 3)*1024**3)
    assert cgroups[w]['memory.swap.max']=='0'
    if w=='A': assert cgroups[w]['memory.high']==str(3*1024**3)
    cgroups['parent']={n:(cg.parent/n).read_text().strip() for n in ['memory.max','memory.swap.max','pids.max']}
assert cgroups['parent']['memory.max']==str(21*1024**3) and cgroups['parent']['memory.swap.max']=='0'
charges={w:dict(historical=data['lanes'][w]['policy']['historical_charge'],phase_bytes=sum(x['phase_bytes'] for x in data['phases'].values() if x['worker']==w),cumulative=data['lanes'][w]['policy']['historical_charge']+sum(x['phase_bytes'] for x in data['phases'].values() if x['worker']==w),root_allocated=allocated(data['lanes'][w]['policy']['root']['path'])) for w in 'FA'}
# Seal the exact current execution inputs and immutable baseline pins, without
# traversing unrelated historical provenance graphs containing symlink paths.
inputs=json.loads((OUT/'preflight.json').read_text())['pins']+files
for rr in json.loads((OUT/'prepared.json').read_text())['records']:
    gg=pinned_json(rr['grant'])
    inputs += [rr['grant'],rr['manifest'],gg['controller'],*gg['helpers'],gg['runtime_config'],gg['owner_transition'],*gg['inputs']]
inputs += [data['recovery_events'][0]['original_state'],pin(STATE/'owners-v4.json'),pin(STATE/'direct-state-v4.json')]
for pp in (V2/'storage-live-09').glob('*.json'): inputs.append(pin(pp))
pins={}
for pp in inputs:
    pinned(pp);pins[pp['path']]=pp
save('authenticated-input-pins.json',list(pins.values()))
save('final-state.json',data)
result=dict(result='FAILED_FIRST_REAL_F_PHASE_STOPPED',qualified_phases=0,native_credit=False,
    service_join_independently_authenticated=True,owned_joins=joins,active_ram=0,charges=charges,
    total_consumed_attempts=len(data['phases']),total_consumed_bytes=sum(x['phase_bytes'] for x in data['phases'].values()),
    remaining_attempts=16-len(data['phases']),remaining_bytes=67108864-sum(x['phase_bytes'] for x in data['phases'].values()),
    both_prior_phase_rows_unchanged=True,original_v2_state_unchanged=True,installed_inputs_unchanged=True,head=run(['git','-C',str(REPO),'rev-parse','HEAD'])['stdout'].strip(),
    properties=adapter.show(unit),cgroup_empty=adapter.empty(r['custody']['cgroup']),service_metrics=metrics,cgroups=cgroups,
    attempt_files=files,logs=logs,payload_file_exists=(root/'cwd/payload.bin').exists(),
    failure='effective_storage.Rejected: propagating mount topology; strict checker stopped before payload creation',
    unrun=['F nonzero','F timeout','A success','A nonzero','A timeout'],A_high_activation=False,
    controller_wall_seconds=json.loads((OUT/'live09-f-success-01-result.json').read_text())['controller_wall_seconds'],
    preflight_seconds=json.loads((OUT/'preflight.json').read_text())['elapsed_seconds'],read_only_seal_seconds=time.monotonic()-start)
raw=(OUT/'live09-f-success-01-mountinfo.txt').read_text()
rows=[]
for line in raw.splitlines():
    left,right=line.split(' - ')
    fields=left.split(' ')
    flags=[x for x in fields[6:] if x.startswith(('shared:','master:','propagate_from:'))]
    if flags: rows.append(dict(mount_id=int(fields[0]),path=fields[4],flags=flags,raw=line))
result['mount_snapshot']=dict(pin=pin(OUT/'live09-f-success-01-mountinfo.txt'),line_count=len(raw.splitlines()),propagating_rows=len(rows),first_propagating_row=rows[0])
result['owner_transitions']=json.loads((OUT/'owner-transitions.json').read_text())
result['wrapper']=json.loads((OUT/'live09-f-success-01-wrapper.json').read_text())
result['post_run_independent_join_seconds']=join_seconds
values=dict(line.split('=',1) for line in metrics['stdout'].splitlines())
result['service_seconds']=(int(values['ExecMainExitTimestampMonotonic'])-int(values['ExecMainStartTimestampMonotonic']))/1000000
result['payload_exit']=r['inner_result']['exit']
result['owner_ids']={w:l.owner(data,w) for w in 'FA'}
result['final_combined_host']=controller.host(data)
assert result['final_combined_host'][1]==0
result['final_dispatcher_holds']={}
for unit in ['vkf-s0-synchronized-contexts.service','vkf-s0-synchronized-contexts.timer','vkf-s0-worker-done.path']:
    obs=run(['systemctl','--user','show',unit,'-p','ActiveState','-p','MainPID'])
    assert obs['exit']==0 and 'ActiveState=inactive' in obs['stdout']
    result['final_dispatcher_holds'][unit]=obs
assert os.readlink('/run/user/1000/systemd/user/vkf-s0-synchronized-contexts.service')=='/dev/null'
result['read_only_seal_seconds']=time.monotonic()-start
save('qualification-result.json',result)
print(json.dumps({k:result[k] for k in ['result','active_ram','charges','total_consumed_attempts','total_consumed_bytes','remaining_attempts','remaining_bytes','service_metrics','read_only_seal_seconds']},indent=2))
