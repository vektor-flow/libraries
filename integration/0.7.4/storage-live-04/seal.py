import datetime,json,os,pathlib,subprocess,time
from preflight import OUT,OLD,V2,REPO,save,pin,pinned,proc,run,Linux,physical
from storage_paths import allocated

start=time.monotonic();unit='vkfworkers-f-live04-f-success-01.service'
state=json.loads((V2/'direct-state-v2.json').read_text());r=state['phases']['F:live04-f-success-01']
obj=run(['busctl','--user','--json=short','call','org.freedesktop.systemd1','/org/freedesktop/systemd1','org.freedesktop.systemd1.Manager','GetUnit','s',unit])
assert obj['exit']==0
path=json.loads(obj['stdout'])['data'][0]
raw=run(['busctl','--user','--json=short','get-property','org.freedesktop.systemd1',path,'org.freedesktop.systemd1.Service','ExecStart'])
assert raw['exit']==0
value=json.loads(raw['stdout'])
save('dbus-execstart.json',dict(get_unit=obj,execstart=raw,actual_type=value['type'],
    data_length=len(value['data']),first_entry_length=len(value['data'][0]),
    expected_argv=r['custody']['service_argv'],
    independently_compared_argv=value['data'][0][1]==r['custody']['service_argv'],
    limitation='Read-only terminal evidence only. Does not repair controller or authorize RAM release.'))
props=run(['systemctl','--user','show',unit,'-p','MainPID','-p','ExecMainPID','-p','ActiveState','-p','InvocationID','-p','ExecMainCode','-p','ExecMainStatus','-p','ControlGroup','-p','MemoryPeak','-p','MemorySwapPeak','-p','TasksMax','-p','MemoryMax','-p','MemorySwapMax','-p','Result','-p','ExecMainStartTimestamp','-p','ExecMainExitTimestamp'])
d=dict(x.split('=',1) for x in props['stdout'].splitlines());assert d['MainPID']=='0'
adapter=Linux();cg=r['custody']['cgroup'];assert adapter.empty(cg)
pid=int(d['ExecMainPID'])
out=json.loads((OUT/'live04-f-success-01-result.json').read_text())
assert proc(out['outer_identity']['pid']) is None
join=dict(outer_identity=out['outer_identity'],outer_wait_exit=out['outer_exit'],outer_pid_observed=proc(out['outer_identity']['pid']),
    terminal_properties=props,service_exec_pid=pid,service_exec_pid_observed=proc(pid),
    service_starttime='NOT CAPTURED: rejection precedes attach_service durable identity',
    expected_cgroup=cg,cgroup_exists=(pathlib.Path('/sys/fs/cgroup')/cg.lstrip('/')).exists(),cgroup_empty=True,
    inner_finished=False,authenticated_controller_join=False,payload_launched=False,
    limitation='Terminal/empty observations do not substitute for missing inner custody. Full disk and RAM held.')
save('owned-joins.json',join)
pf=json.loads((OUT/'preflight.json').read_text());changes=[]
for p in pf['pins']:
    try:pinned(p)
    except Exception as e:changes.append(dict(pin=p,error=repr(e)))
assert not changes,changes
head=run(['git','-C',str(REPO),'rev-parse','HEAD']);assert head['stdout'].strip()=='5747ff8008ccd580b1b45ebc26560ffb0cda33fa'
assert not adapter.units('vkfworkers-*.service') and not adapter.units('vkfs0-*.service')
a=pathlib.Path('/sys/fs/cgroup/user.slice/user-1000.slice/user@1000.service/vkfworkers.slice/vkfworkers-a.slice')
limits={str(p):{n:(p/n).read_text().strip() for n in ['memory.max','memory.high','memory.swap.max','pids.max']} for p in [a,a.parent,a.parent/'vkfworkers-f.slice']}
assert limits[str(a)]['memory.high']=='3221225472'
root=pathlib.Path(r['attempt_identity']['path'])
pins=[]
for p in [V2/'direct-state-v2.json',V2/'runtime-config.json',*sorted((V2/'storage-live-04').glob('*.json')),
          *sorted((root/'receipts').glob('*'))]:
    if p.is_file():pins.append(pin(p))
save('live-output-pins.json',pins)
result=dict(result='FAILED_FIRST_F_SERVICE_DBUS_EXECSTART_SHAPE',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    source_head=head['stdout'].strip(),attempts=1,services=1,payloads_started=0,passed_phases=0,
    unrun=['F success payload/namespace','F intended nonzero','F timeout/child join','A success/namespace','A intended nonzero','A timeout/child join'],
    root_cause="Linux.argv expects data[0] to contain one command; actual busctl data[0] is the 10-field command struct.",
    secondary_failure="outer() assumes r['service'] exists after systemd-run; KeyError masks inner attachment rejection.",
    phase_stage=r['stage'],qualification_charge_bytes=r['phase_bytes'],held_ram_bytes=r['ram_bytes'],
    historical_H={w:state['lanes'][w]['policy']['historical_charge'] for w in 'AF'},
    additions={w:sum(i['bytes'] for i in state['lanes'][w]['policy']['increments']) for w in 'AF'},
    cumulative_charge={w:state['lanes'][w]['policy']['historical_charge']+sum(p['phase_bytes'] for p in state['phases'].values() if p['worker']==w) for w in 'AF'},
    attempt_allocated_bytes=allocated(root),service_wall=out['elapsed_seconds'],service_runtime_reported='180ms',
    service_memory_peak=d['MemoryPeak'],limits=limits,legacy_and_installed_pins_unchanged=True,
    active_worker_services=[],active_legacy_services=[],native47='18 passed / 29 unqualified',original419_credited=293,
    stop='No retry, no source edits, no join/rotation/recovery/charge reset; coordinator assigns fresh repair chat.',
    next_step='Repair typed D-Bus response decoding and missing-attach error reporting in a fresh source iteration. Separately review safe custody recovery for held F phase; never reset/replay it.',
    own_terminal_evidence=pin(OUT/'owned-joins.json'),raw_dbus=pin(OUT/'dbus-execstart.json'),
    preflight_elapsed=json.loads((OUT/'preflight.json').read_text())['elapsed_seconds'],
    preparation_elapsed=json.loads((OUT/'enrollment.json').read_text())['elapsed_seconds'])
save('qualification-result.json',result)
print(json.dumps({k:result[k] for k in ['result','qualification_charge_bytes','held_ram_bytes','historical_H','cumulative_charge','attempt_allocated_bytes','service_memory_peak']},indent=2))
