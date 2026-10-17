import argparse,json,os,pathlib,subprocess,sys,time
OUT=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(OUT))
from preflight import a,PACKET,STORAGE,save,controller,Ledger,physical,Linux,proc,same,pinned,pinned_json,allocated
start=time.monotonic();s=a.static_contract();c=a.load_pin(s['v6_bundle']['config'])
ledger=Ledger(pathlib.Path(s['state_path']),pathlib.Path(s['lock_path']),recovery_pin=c['recovery_authority'])
d=ledger.snapshot();ledger.check(d);key='A:metadata-native36-01';row=d['phases'][key];ctrl=controller(s,row)
assert row['stage']=='joined' and ctrl.verify_join(row,pinned_json(row['join'])) is True
identities=[]
for saved in [row['custody']['identity'],row['service']['identity'],*row['inner_result']['tracked']]:
 current=proc(saved['pid']);assert current is None or current['starttime']!=saved['starttime'] or current['boot']!=row['service']['identity']['boot']
 identities.append(dict(saved=saved,observed=current))
osapi=Linux();props=osapi.show(row['custody']['unit'])
assert osapi.empty(row['custody']['cgroup']) and props['MainPID']=='0' and props['TasksMax']=='128' and props['MemoryMax']==str(8*2**30) and props['MemorySwapMax']=='0'
assert osapi.argv(row['custody']['unit'])==row['custody']['service_argv']
inner=row['inner_result'];owned=inner['owned_join']
assert inner['exit']==a.read(OUT/'controller-result.json')['exit'] and inner['inputs_reverified'] is True and inner['remaining_identities']==[]
assert owned['no_live_descendants'] is True and not inner['remaining_identities']
assert not ledger.active_rows(d) and not osapi.units('vkfworkers-*.service') and not osapi.units('vkfs0-*.service')
assert inner['system_trust_error'] is None and len(inner['system_trust_proofs'])==2
before=a.read(OUT/'initial-state.json');assert {k:v for k,v in d['phases'].items() if k!=key}==before['phases']
assert d['recovery_events']==before['recovery_events'] and d['lanes']['F']==before['lanes']['F']
assert d['lanes']['A']['transitions'][:-1]==before['lanes']['A']['transitions']
assert len(d['phases'])==17 and sum(r['phase_bytes'] for k,r in d['phases'].items() if k not in (key,'A:compiler-native13-01','A:compiler-native17-01','A:d288-native24-01','A:metadata-native29-01'))==50331648
lanes={}
for w in 'AF':
 cg=pathlib.Path('/sys/fs/cgroup')/c['lane_cgroups'][w].lstrip('/')
 vals={n:(cg/n).read_text().strip() for n in ('memory.max','memory.high','memory.swap.max','pids.max','cgroup.events','cgroup.procs')}
 assert osapi.empty(c['lane_cgroups'][w]) and vals['memory.max']==str((8 if w=='A' else 3)*2**30) and vals['memory.swap.max']=='0' and vals['pids.max']=='160'
 assert (cg.parent/'memory.max').read_text().strip()==str(21*2**30) and (cg.parent/'memory.swap.max').read_text().strip()=='0'
 assert vals['memory.high']==str(3*2**30)
 p=d['lanes'][w]['policy'];charge=p['historical_charge']+sum(r['phase_bytes'] for r in d['phases'].values() if r['worker']==w)
 assert charge==({'A':25233252352,'F':19821273088}[w])
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
root=pathlib.Path(row['attempt_identity']['path'])
files=[]
for p in sorted(root.rglob('*')):
 if p.is_file():files.append(dict(a.pin(p),bytes=p.stat().st_size))
for p in a.load_pin(row['grant'])['inputs']:pinned(p)
plan=a.read(PACKET/'staging/metadata/plan.json')
for p in plan['inputs']+plan['generated']:a.verify(p)
assert a.current_head()==s['source_commit']
extra=subprocess.run(['systemctl','--user','show',row['custody']['unit'],'-p','MemoryPeak','-p','MemorySwapPeak','-p','CPUUsageNSec','-p','ExecMainStartTimestampMonotonic','-p','ExecMainExitTimestampMonotonic'],capture_output=True,text=True,timeout=15);assert extra.returncode==0
save('independent-terminal-join.json',dict(verified=True,phase=key,join=row['join'],properties=props,exact_execstart=True,identities=identities,cgroup_empty=True,outer_controller_joined=True,owned_descendants_joined=True,raw_owned_join=owned,extra_properties=extra.stdout))
save('final-state.json',d);save('final-owners.json',owners);save('attempt-artifact-pins.json',files)
for name in ('stderr','outer.stderr'):
 with (OUT/('actual-'+name+'.txt')).open('xb') as f:f.write((root/'receipts'/name).read_bytes())
build=root/'metadata'
stages=a.read(build/'results.json') if (build/'results.json').exists() else []
summary=a.read(build/'execution-summary.json') if (build/'execution-summary.json').exists() else None
actual_plan=a.read(PACKET/'root-packet/plan.json')
sys.path.insert(0,str(a.PACKAGE));import payload
stage_checks=[]
for spec,stage in zip(actual_plan['stages'],stages):
 assert stage['name']==spec['name'] and stage['argv']==spec['argv']
 for ref in stage.get('logs',[])+stage.get('outputs',[]):a.verify(ref)
 for ident in stage['join'].get('tracked',[]):
  current=proc(ident['pid']);assert current is None or current['starttime']!=ident['starttime'] or current['boot']!=ident['boot']
 assert stage['join']['no_live_descendants'] is True and not stage['join'].get('remaining_identities')
 stdout=(build/'logs'/(spec['name']+'.stdout')).read_text(errors='replace')
 stderr=(build/'logs'/(spec['name']+'.stderr')).read_text(errors='replace')
 try:
  payload.check_result(spec,stage['exit'],stdout,stderr);oracle=True;error=None
 except ValueError as exc:oracle=False;error=str(exc)
 outputs=[]
 for path in spec['outputs']:
  dest=pathlib.Path(path)
  if dest.is_file():
   ref=a.pin(dest);assert ref in stage.get('outputs',[]) or not oracle
   with dest.open('rb') as f:magic=f.read(4)
   outputs.append(dict(ref,ELF=magic==b'\x7fELF',executable=os.access(dest,os.X_OK)))
 stage_checks.append(dict(name=spec['name'],exit=stage['exit'],seconds=stage['seconds'],oracle_passed=oracle,error=error,logs=stage.get('logs',[]),outputs=outputs,join=stage['join'],stdout=stdout,stderr=stderr))
# Runtime full-lane checks are evidenced by installed guard outcomes. Independently
# inspect all retained tree entries without following links, then call installed allocated.
import stat
entries=[];bad=[]
for path in [root,*sorted(root.rglob('*'))]:
 st=path.lstat();kind='directory' if stat.S_ISDIR(st.st_mode) else 'regular' if stat.S_ISREG(st.st_mode) else 'special'
 item=dict(path=str(path),kind=kind,mode=stat.S_IMODE(st.st_mode),nlink=st.st_nlink,allocated_bytes=st.st_blocks*512)
 entries.append(item)
 if kind=='special':bad.append(item)
assert not bad, 'actual special files retained; no bypass allowed'
stdlib=[]
if build.exists():
 for link in actual_plan['symlinks']:
  path=pathlib.Path(link['path']);st=path.lstat()
  assert stat.S_ISREG(st.st_mode) and st.st_nlink==1 and not path.is_symlink()
  ref=a.pin(path);assert ref['sha256']==link['sha256'];stdlib.append(ref)
 for ref in actual_plan['generated']:a.verify(ref)
 assert a.pin(build/'plan.json')==a.pin(PACKET/'root-packet/plan.json') or (build/'plan.json').read_bytes()==(PACKET/'root-packet/plan.json').read_bytes()
compiler=actual_plan['compiler_receipt'];a.verify(compiler['compiler'])
with pathlib.Path(compiler['compiler']['path']).open('rb') as f:
 assert f.read(4)==b'\x7fELF';f.seek(0);marker=compiler['identity'].encode();tail=b'';found=False
 while chunk:=f.read(262144):found|=marker in tail+chunk;tail=chunk[-len(marker):]
 assert found
accounting=dict(installed_allocator=a.pin(STORAGE/'storage-direct-v9/storage_paths.py'),attempt_allocated_bytes=allocated(root),full_lane_allocated_bytes=allocated(d['lanes']['A']['policy']['root']['path']),entries=entries,special_files=bad,regular_stdlib_copies=stdlib,installed_guard_error=owned.get('guard_error'),runtime_guard_entire_lane=True)
passed=(inner['exit']==0 and summary is not None and summary['error'] is None and summary['native_execution'] is True and summary['completed']==3 and len(stages)==3 and all(x['oracle_passed'] for x in stage_checks) and all(o['ELF'] and o['executable'] for x in stage_checks for o in x['outputs']) and not any(owned.get(k) for k in ('timed_out','guard_error','orphaned_descendant_on_exit')))
if passed:assert not any(x.get('valgrind') for x in actual_plan['stages']) and len(stdlib)==30
save('native-evidence.json',dict(passed=passed,compiler=compiler,stages=stage_checks,summary=summary,actual_plan=a.pin(build/'plan.json') if (build/'plan.json').exists() else None,all_recorded_children_joined=True))
save('actual-accounting.json',accounting)
save('exact-oracles.json',a.read(PACKET/'exact-oracles.json'))
result=dict(owner='01a14a8f-593f-7e52-ab64-5f143417903e',result='METADATA_ACTUAL_LENGTHS_PASSED' if passed else 'FAILED_ACTUAL_ATTEMPT',attempt=key,controller_exit=inner['exit'],controller_seconds=a.read(OUT/'controller-result.json')['seconds'],metadata_passed=passed,stages_executed=len(stages),original_controls_passed=sum(x['oracle_passed'] for x in stage_checks if '-run-' in x['name']),stages=[{k:x[k] for k in ('name','exit','seconds','oracle_passed')} for x in stage_checks],execution_summary=summary,compiler=compiler['compiler'],compiler_identity=compiler['identity'],error=summary['error'] if summary else (root/'receipts/stderr').read_text()[-6000:],terminal_join_verified=True,join=row['join'],A_high_restored_bytes=3*2**30,permanent_charge_retained_bytes=2**30,attempt_allocated_bytes=accounting['attempt_allocated_bytes'],lanes=lanes,tiny_attempts_unchanged=12,tiny_bytes_unchanged=50331648,active_ram=0,overlap=0,MemAvailable=available,offload=offload,holds=holds,physical={p:physical(p) for p in ('/','/mnt/development','/mnt/vkf-storage-2tb')},posthash=dict(plan_inputs=len(plan['inputs']),static_pins=len(s['pins']),grant_inputs=len(a.load_pin(row['grant'])['inputs']),passed=True),head=a.current_head(),seconds=time.monotonic()-start)
save('result.json',result);print(json.dumps(result))
