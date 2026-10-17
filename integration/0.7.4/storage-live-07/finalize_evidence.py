"""Read-only post-failure authentication; writes only the granted evidence directory."""
import argparse, json, os, pathlib, time
from preflight import OUT, OLD, V2, REPO, save, pin, pinned, pinned_json, proc, Linux, run
from qualify import context, unchanged
from storage_controller import Controller
from storage_paths import allocated
start=time.monotonic();unchanged();cp,c,l,data=context();l.check(data)
r=data['phases']['F:live07-f-success-01'];gp,mp=r['grant'],r['manifest']
a=argparse.Namespace(config_sha256=cp['sha256'],grant=pathlib.Path(gp['path']),grant_sha256=gp['sha256'],manifest=pathlib.Path(mp['path']),manifest_sha256=mp['sha256'])
controller=Controller(a);receipt=pinned_json(r['join']);assert controller.verify_join(r,receipt)
assert r['stage']=='joined' and r['inner_result']['exit']==1
assert not l.active_rows(data)
assert set(data['phases'])=={'F:live04-f-success-01','F:live07-f-success-01'}
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
inputs += [data['recovery_events'][0]['original_state'],pin(V2/'owners-v4.json'),pin(V2/'direct-state-v4.json')]
pins={}
for pp in inputs:
    pinned(pp);pins[pp['path']]=pp
save('authenticated-input-pins.json',list(pins.values()))
save('final-state.json',data)
result=dict(result='FAILED_FIRST_REAL_F_PHASE_STOPPED',qualified_phases=0,native_credit=False,
    service_join_independently_authenticated=True,owned_joins=joins,active_ram=0,charges=charges,
    total_consumed_attempts=len(data['phases']),total_consumed_bytes=sum(x['phase_bytes'] for x in data['phases'].values()),
    remaining_attempts=16-len(data['phases']),remaining_bytes=67108864-sum(x['phase_bytes'] for x in data['phases'].values()),
    old_phase_unchanged=True,old_state_unchanged=True,installed_inputs_unchanged=True,head=run(['git','-C',str(REPO),'rev-parse','HEAD'])['stdout'].strip(),
    properties=adapter.show(unit),cgroup_empty=adapter.empty(r['custody']['cgroup']),service_metrics=metrics,cgroups=cgroups,
    attempt_files=files,logs=logs,payload_file_exists=(root/'cwd/payload.bin').exists(),
    failure='Fixture line22 single writable storage mount assertion failed; no attempt to write the additional listed mounts',
    unrun=['F nonzero','F timeout','A success','A nonzero','A timeout'],A_high_activation=False,
    controller_wall_seconds=json.loads((OUT/'live07-f-success-01-result.json').read_text())['controller_wall_seconds'],
    preflight_seconds=json.loads((OUT/'preflight.json').read_text())['elapsed_seconds'],read_only_seal_seconds=time.monotonic()-start)
save('qualification-result.json',result)
print(json.dumps({k:result[k] for k in ['result','active_ram','charges','total_consumed_attempts','total_consumed_bytes','remaining_attempts','remaining_bytes','service_metrics','read_only_seal_seconds']},indent=2))
