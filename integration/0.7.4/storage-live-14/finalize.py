"""Authenticate real terminal failure, retain all intent/charges, seal evidence only."""
import argparse,datetime,json,os,pathlib,time
from preflight import OUT,OLD,V2,STATE,OWNER,HEAD,save,pin,pinned,pinned_json,run,Linux,proc
from storage_admission import Ledger
from storage_controller import Controller,parse_get_unit,parse_exec_start
start=time.monotonic();assert (OUT/'STOP.json').exists()
cp=pin(V2/'runtime-config.json');c=pinned_json(cp);l=Ledger(STATE/'direct-state-v4.json',OLD/'capacity.lock',recovery_pin=c['recovery_authority'])
s=l.snapshot();statepin=pin(l.state);l.check(s)
pre=json.loads((OUT/'preflight-before-transitions.json').read_text());final=json.loads((OUT/'final-resources.json').read_text())
assert final['initial_state']==s and final['initial_state_pin']==statepin
assert len(s['phases'])==4 and all(s['phases'][k]==v for k,v in pre['initial_state']['phases'].items())
assert s['recovery_events']==pre['initial_state']['recovery_events']
assert all(l.owner(s,w)==OWNER for w in 'FA')
trans=json.loads((OUT/'owner-transitions.json').read_text())
for w in 'FA':
 assert s['lanes'][w]==dict(pre['initial_state']['lanes'][w],transitions=pre['initial_state']['lanes'][w]['transitions']+[trans['transitions'][w]])
ownerpin=pin(pathlib.Path(c['owner_state']));owners=pinned_json(ownerpin)
last=json.loads(sorted(OUT.glob('publication-*-receipt.json'))[-1].read_text())
assert ownerpin['sha256']==last['after_sha256'] and pathlib.Path(c['owner_state']).read_bytes()==bytes.fromhex(last['after_hex'])
r=s['phases']['F:live14-f-success-01'];g,m=pinned_json(r['grant']),pinned_json(r['manifest'])
ctrl=Controller(argparse.Namespace(config_sha256=cp['sha256'],grant=pathlib.Path(r['grant']['path']),grant_sha256=r['grant']['sha256'],manifest=pathlib.Path(r['manifest']['path']),manifest_sha256=r['manifest']['sha256']))
t=time.monotonic();props=ctrl.authenticate_record(r);adapter=Linux();cg=r['custody']['cgroup'];unit=r['custody']['unit']
obj=adapter.output(['busctl','--user','--json=short','call','org.freedesktop.systemd1','/org/freedesktop/systemd1','org.freedesktop.systemd1.Manager','GetUnit','s',unit])
raw=adapter.output(['busctl','--user','--json=short','get-property','org.freedesktop.systemd1',parse_get_unit(obj),'org.freedesktop.systemd1.Service','ExecStart'])
parsed=parse_exec_start(raw)
assert parsed[1]==r['custody']['service_argv'] and parsed[7]==r['service']['identity']['pid']
assert props['InvocationID']==r['service']['invocation'] and props['MainPID']=='0' and props['ActiveState']=='failed'
assert props['Result']=='exit-code' and props['ExecMainCode']=='1' and props['ExecMainStatus']=='1'
assert props['ControlGroup'] in ('',cg) and adapter.empty(cg)
assert props['MemoryMax']==str(3*2**30) and props['MemorySwapMax']=='0' and props['TasksMax']=='128'
ids=[r['custody']['identity'],r['service']['identity']]
observed=[dict(saved=i,observed=proc(i['pid'])) for i in ids]
assert all(x['observed'] is None or x['observed']['starttime']!=x['saved']['starttime'] for x in observed)
# A real terminal observation, expressly NOT a normal Ledger.join receipt.
terminal=dict(authenticated_record=True,independent_terminal_observation=True,ledger_join=False,
 normal_verify_join_inapplicable='stage running, missing inner_result, actual service exit1 instead of custody exit199',
 properties=props,dbus_get_unit=obj,dbus_execstart=raw,parsed_execstart=parsed,identities=observed,cgroup=cg,cgroup_empty=True,
 seconds=time.monotonic()-t)
save('independent-terminal-observation.json',terminal)
receiptroot=pathlib.Path(m['receipts']);rawpins=[]
for source in sorted(receiptroot.iterdir()):
 pp=pin(source);pinned(pp);rawpins.append(pp)
 with (OUT/('raw-'+source.name)).open('xb') as f:f.write(source.read_bytes());f.flush();os.fsync(f.fileno())
failure=pinned_json(pin(receiptroot/'controller-failure.json'))
assert failure['grant']==r['grant'] and failure['custody']==r['custody'] and failure['ram_intent_retained']==3*2**30
assert failure['failure_kind']=='inner-completion-missing' and failure['missing']==['inner_result']
assert 'storage_paths.Rejected: nonzero CapInh' in (receiptroot/'outer.stderr').read_text()
assert not (receiptroot/'stdout').exists() and not (receiptroot/'stderr').exists()
assert not pathlib.Path(m['cwd'],'payload.bin').exists()
# Frozen inner source executes the rejecting origin gate before sandbox()/Popen().
save('raw-receipt-pins.json',rawpins)
since='@'+str(int(datetime.datetime.fromisoformat(pre['utc']).timestamp()))
save('apparmor-journal-readonly.json',run(['sudo','-n','journalctl','-k','--since',since,'--no-pager','-o','short-iso','--grep','apparmor|live14|vkf-storage']))
metrics=run(['systemctl','--user','show',unit,'-p','MemoryPeak','-p','MemorySwapPeak','-p','CPUUsageNSec','-p','ExecMainStartTimestampMonotonic','-p','ExecMainExitTimestampMonotonic','-p','AmbientCapabilities','-p','CapabilityBoundingSet','-p','NoNewPrivileges'])
assert metrics['exit']==0
save('terminal-service-metrics.json',metrics)
assert len(l.active_rows(s))==1 and sum(x['ram_bytes'] for x in l.active_rows(s))==3*2**30
assert not adapter.units('vkfworkers-*.service') and not adapter.units('vkfs0-*.service')
assert all(adapter.empty(c['lane_cgroups'][w]) for w in 'FA')
assert pin(l.state)==statepin and l.snapshot()==s and pin(pathlib.Path(c['owner_state']))==ownerpin
save('final-state.json',s);save('final-owner-state.json',dict(pin=ownerpin,state=owners))
charges={w:dict(historical=s['lanes'][w]['policy']['historical_charge'],phase_bytes=sum(x['phase_bytes'] for x in s['phases'].values() if x['worker']==w)) for w in 'FA'}
for x in charges.values():x['cumulative']=x['historical']+x['phase_bytes']
ob=json.loads((OUT/'live14-f-success-01-result.json').read_text())
result=dict(result='STOP_ORIGIN_POLICY_GATE_NONZERO_CAPINH',owner=OWNER,head=HEAD,rotations=2,
 owner_publications=len(list(OUT.glob('publication-*-receipt.json'))),new_grants=6,new_manifests=6,new_attempts=1,new_phase_bytes=4194304,
 qualified_phases=0,unrun_cases=['F nonzero','F timeout','A success','A nonzero','A timeout'],
 total_consumed_attempts=4,total_consumed_bytes=16777216,remaining_attempts=12,remaining_bytes=50331648,
 retained_ram_intent=3221225472,ledger_stage=r['stage'],no_normal_join_or_release=True,terminal_observation=pin(OUT/'independent-terminal-observation.json'),
 mem_available_bytes=final['checks']['MemAvailable'],active_worker_services=[],active_legacy_services=[],offload_remaining_intent=0,
 A_high_raised=False,charges=charges,controller_wall_seconds=ob['controller_wall_seconds'],qualification_seconds=ob['elapsed_seconds'],
 attempt_allocated_bytes=ob['attempt_allocated_bytes'],initial_preflight_seconds=pre['elapsed_seconds'],final_resource_seconds=final['elapsed_seconds'],
 dry_validation=pin(OUT/'dry-validation.json'),publication_tests=pin(OUT/'publication-tests.json'),raw_receipts=rawpins,
 installed_files_unchanged=True,loaded_policy_bytes_reconfirmed=True,fixture_executed=False,namespace_helper_executed=False,
 payload_result=None,service_exit=1,outer_controller_exit=125,no_retry=True,no_recovery=True,no_native_credit=True,finalize_seconds=time.monotonic()-start)
save('qualification-result.json',result)
pins=pre['pins']+final['pins']+json.loads((OUT/'reviewed-context-pins.json').read_text())+rawpins+[statepin,ownerpin]
for path in (V2/'storage-live-14').iterdir():
 if path.is_file():pins.append(pin(path))
unique={}
for pp in pins:pinned(pp);unique[pp['path']]=pp
save('authenticated-input-pins.json',list(unique.values()))
print(json.dumps({k:result[k] for k in ['result','rotations','owner_publications','total_consumed_attempts','total_consumed_bytes','retained_ram_intent','mem_available_bytes','charges']},indent=2))
