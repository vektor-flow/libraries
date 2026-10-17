import argparse,json,os,pathlib,subprocess,sys,time
OUT=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(OUT))
from preflight import a,PACKET,STORAGE,save,controller,Ledger,physical,Linux,proc,same,pinned,pinned_json,allocated
start=time.monotonic();s=a.static_contract();c=a.load_pin(s['v6_bundle']['config'])
ledger=Ledger(pathlib.Path(s['state_path']),pathlib.Path(s['lock_path']),recovery_pin=c['recovery_authority'])
d=ledger.snapshot();ledger.check(d);key='A:compiler-native13-01';row=d['phases'][key];ctrl=controller(s,row)
assert row['stage']=='joined' and ctrl.verify_join(row,pinned_json(row['join'])) is True
identities=[]
for saved in [row['custody']['identity'],row['service']['identity'],*row['inner_result']['tracked']]:
 current=proc(saved['pid']);assert current is None or current['starttime']!=saved['starttime'] or current['boot']!=row['service']['identity']['boot']
 identities.append(dict(saved=saved,observed=current))
osapi=Linux();props=osapi.show(row['custody']['unit'])
assert osapi.empty(row['custody']['cgroup']) and props['MainPID']=='0' and props['TasksMax']=='128' and props['MemoryMax']==str(8*2**30) and props['MemorySwapMax']=='0'
assert osapi.argv(row['custody']['unit'])==row['custody']['service_argv']
inner=row['inner_result'];owned=inner['owned_join']
assert inner['exit']==1 and inner['inputs_reverified'] is True and inner['remaining_identities']==[]
assert owned['no_live_descendants'] is True and not owned['timed_out'] and not owned['guard_error'] and not owned['orphaned_descendant_on_exit']
assert not ledger.active_rows(d) and not osapi.units('vkfworkers-*.service') and not osapi.units('vkfs0-*.service')
assert inner['system_trust_error'] is None and len(inner['system_trust_proofs'])==2
before=a.read(OUT/'initial-state.json');assert {k:v for k,v in d['phases'].items() if k!=key}==before['phases']
assert d['recovery_events']==before['recovery_events'] and d['lanes']['F']==before['lanes']['F']
assert d['lanes']['A']['transitions'][:-1]==before['lanes']['A']['transitions']
assert len(d['phases'])==13 and sum(r['phase_bytes'] for k,r in d['phases'].items() if k!=key)==50331648
lanes={}
for w in 'AF':
 cg=pathlib.Path('/sys/fs/cgroup')/c['lane_cgroups'][w].lstrip('/')
 vals={n:(cg/n).read_text().strip() for n in ('memory.max','memory.high','memory.swap.max','pids.max','cgroup.events','cgroup.procs')}
 assert osapi.empty(c['lane_cgroups'][w]) and vals['memory.max']==str((8 if w=='A' else 3)*2**30) and vals['memory.swap.max']=='0' and vals['pids.max']=='160'
 assert (cg.parent/'memory.max').read_text().strip()==str(21*2**30) and (cg.parent/'memory.swap.max').read_text().strip()=='0'
 if w=='A':assert vals['memory.high']==str(3*2**30)
 p=d['lanes'][w]['policy'];charge=p['historical_charge']+sum(r['phase_bytes'] for r in d['phases'].values() if r['worker']==w)
 assert charge==({'A':19864543232,'F':19821273088}[w])
 lanes[w]=dict(properties=vals,charge=charge,remaining=21900000000+sum(x['bytes'] for x in p['increments'])-charge,old_volume=physical(p['old_volume']['path']),root_allocated=allocated(p['root']['path']))
frow=d['phases']['F:live24-f-timeout-01'];assert controller(s,frow).verify_join(frow,pinned_json(frow['join']))
owners=a.read(c['owner_state']);oldowners=json.loads((pathlib.Path(a.read(PACKET/'root-inputs.json')['publication_receipt_path']).parent/'owners-before.raw').read_text());assert owners['workers']['F']==oldowners['workers']['F']
available,offload=ctrl.host(d);assert offload==0
holds={}
for unit in ('vkf-s0-synchronized-contexts.service','vkf-s0-synchronized-contexts.timer','vkf-s0-worker-done.path'):
 p=subprocess.run(['systemctl','--user','show',unit,'-p','ActiveState','-p','MainPID'],text=True,capture_output=True,timeout=15)
 assert p.returncode==0 and 'ActiveState=inactive' in p.stdout;holds[unit]=p.stdout
assert os.readlink('/run/user/1000/systemd/user/vkf-s0-synchronized-contexts.service')=='/dev/null'
sys.modules.pop('preflight',None)  # Load live24's own preflight so original OUT/ROOT stay intact.
sys.path.insert(0,str(OUT.parent/'storage-live-24'));import check_loaded
check_loaded.save=save;assert check_loaded.check('final')
root=pathlib.Path(row['attempt_identity']['path']);assert not (root/'compiler').exists()
stderr=(root/'receipts/stderr').read_text();assert 'BlockingIOError: [Errno 11] Resource temporarily unavailable' in stderr and 'fcntl.flock(lock, fcntl.LOCK_SH | fcntl.LOCK_NB)' in stderr
files=[]
for p in sorted(root.rglob('*')):
 if p.is_file():files.append(dict(a.pin(p),bytes=p.stat().st_size))
for p in a.load_pin(row['grant'])['inputs']:pinned(p)
plan=a.read(PACKET/'staging/plan.json')
for p in plan['inputs']+plan['generated']:a.verify(p)
assert a.current_head()==s['source_commit']
extra=subprocess.run(['systemctl','--user','show',row['custody']['unit'],'-p','MemoryPeak','-p','MemorySwapPeak','-p','CPUUsageNSec','-p','ExecMainStartTimestampMonotonic','-p','ExecMainExitTimestampMonotonic'],capture_output=True,text=True,timeout=15);assert extra.returncode==0
save('independent-terminal-join.json',dict(verified=True,phase=key,join=row['join'],properties=props,exact_execstart=True,identities=identities,cgroup_empty=True,outer_controller_joined=True,owned_descendants_joined=True,raw_owned_join=owned,extra_properties=extra.stdout))
save('final-state.json',d);save('final-owners.json',owners);save('attempt-artifact-pins.json',files)
for name in ('stderr','outer.stderr'):
 with (OUT/('actual-'+name+'.txt')).open('xb') as f:f.write((root/'receipts'/name).read_bytes())
result=dict(result='FAILED_BEFORE_COMPILER_MATERIALIZATION',attempt=key,controller_exit=1,controller_seconds=a.read(OUT/'controller-result.json')['seconds'],native_build_passed=False,core_regression_passed=False,compiler_stages_executed=0,baseline_oracle_executed=False,candidate_oracle_executed=False,actual_MD_link_ELF='not produced',error='adapter.py:352 nonblocking shared capacity.lock acquisition: BlockingIOError EAGAIN',lock_holder_at_failure='not captured; no attribution claimed',terminal_join_verified=True,join=row['join'],A_high_restored_bytes=3*2**30,permanent_charge_retained_bytes=2**30,attempt_allocated_bytes=allocated(root),lanes=lanes,tiny_attempts_unchanged=12,tiny_bytes_unchanged=50331648,active_ram=0,overlap=0,MemAvailable=available,offload=offload,holds=holds,physical={p:physical(p) for p in ('/','/mnt/development','/mnt/vkf-storage-2tb')},posthash=dict(plan_inputs=727,static_pins=229,grant_inputs=len(a.load_pin(row['grant'])['inputs']),passed=True),head=a.current_head(),seconds=time.monotonic()-start)
save('result.json',result);print(json.dumps(result))
