import pathlib,sys,json,os,stat,subprocess,time
OUT=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(OUT))
from preflight import a,PACKET,STORAGE,save,controller,Ledger,Linux,proc,same,pinned,pinned_json,allocated,physical
start=time.monotonic();s=a.static_contract();c=a.load_pin(s['v6_bundle']['config']);g=a.read(STORAGE/'metadata-native-36-visible-chat-grant.json');decision=a.load_pin(g['root_decision'])
ledger=Ledger(pathlib.Path(s['state_path']),pathlib.Path(s['lock_path']),recovery_pin=c['recovery_authority']);data=ledger.snapshot();ledger.check(data)
assert data==a.read(OUT/'final-state.json');owners=a.read(c['owner_state']);assert owners==a.read(OUT/'final-owners.json')
assert data==a.read(OUT.parent/'metadata-native-29/final-state.json')
assert owners==a.read(OUT.parent/'metadata-native-29/final-owners.json')
active=ledger.active_rows(data);assert not active
osapi=Linux();assert not osapi.units('vkfworkers-*.service') and not osapi.units('vkfs0-*.service')
assert pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip()==decision['boot']
checks={};lanes={};all_identities=[]
for key,row in data['phases'].items():
 candidates=[]
 for field in ('custody','service'):
  if 'identity' in row.get(field,{}):candidates.append(row[field]['identity'])
 candidates.extend(row.get('inner_result',{}).get('tracked',[]))
 for ident in candidates:
  observed=proc(ident['pid']);absent=observed is None or observed['starttime']!=ident['starttime'] or observed['boot']!=ident['boot']
  all_identities.append(dict(phase=key,saved=ident,observed=observed,absent=absent));assert absent
for w in 'AF':
 key,row=max(((k,r) for k,r in data['phases'].items() if r['worker']==w),key=lambda x:x[1]['sequence'])
 ctrl=controller(s,row);props=ctrl.authenticate_record(row,terminal=True);receipt=pinned_json(row['join'])
 assert row['stage']=='joined' and receipt['custody']==row['custody'] and receipt['service']==row['service'] and receipt['inner_result']==row['inner_result']
 assert receipt['main_pid']==int(props['MainPID'])==0 and receipt['cgroup_empty'] is True and receipt['actual_service_joined'] is True and receipt['remaining_identities']==[]
 assert osapi.empty(row['custody']['cgroup']) and not same(row['custody']['identity']) and not same(row['service']['identity'])
 assert osapi.argv(row['custody']['unit'])==row['custody']['service_argv'] and props['TasksMax']=='128' and props['MemorySwapMax']=='0'
 manifest=pinned_json(row['manifest']);mismatches=[]
 for ref in manifest['inputs']:
  try:pinned(ref)
  except Exception as exc:mismatches.append(dict(expected=ref,actual=a.pin(ref['path']),error=type(exc).__name__+': '+str(exc)))
 if w=='A':
  assert len(mismatches)==1 and mismatches[0]['expected']['path'].endswith('/compiler-build-preparation-03/prepare.py')
  assert mismatches[0]['actual']['sha256']=='400a56b07d9cb67c7d4d9331a787d13af43fd60dfba56a09481e88b9f66de169'
 else:assert not mismatches and ctrl.verify_join(row,receipt) is True
 checks[w]=dict(key=key,join=row['join'],custody_service_descendants_verified=True,properties=props,exact_execstart=True,cgroup_empty=True,join_input_pins_passed=not mismatches,manifest_inputs=len(manifest['inputs']),mismatches=mismatches)
 cg=pathlib.Path('/sys/fs/cgroup')/c['lane_cgroups'][w].lstrip('/')
 vals={n:(cg/n).read_text().strip() for n in ('memory.max','memory.high','memory.swap.max','pids.max','cgroup.events','cgroup.procs')}
 assert vals['memory.high']==str(3*2**30) and vals['memory.max']==str((8 if w=='A' else 3)*2**30) and vals['memory.swap.max']=='0' and vals['pids.max']=='160' and osapi.empty(c['lane_cgroups'][w])
 assert (cg.parent/'memory.max').read_text().strip()==str(21*2**30) and (cg.parent/'memory.swap.max').read_text().strip()=='0'
 policy=data['lanes'][w]['policy'];charge=policy['historical_charge']+sum(r['phase_bytes'] for r in data['phases'].values() if r['worker']==w)
 assert charge==dict(A=24159510528,F=19821273088)[w]
 lanes[w]=dict(owner=ledger.owner(data,w),properties=vals,charge=charge,root_allocated=allocated(policy['root']['path']),old_volume=physical(policy['old_volume']['path']))
# Independently inspect every saved payload stage descendant from the failed predecessor.
row=data['phases']['A:metadata-native29-01'];attempt=pathlib.Path(row['attempt_identity']['path']);stage_results=a.read(attempt/'metadata/results.json');stage_checks=[]
for stage in stage_results:
 for ref in stage.get('logs',[])+stage.get('outputs',[]):a.verify(ref)
 for ident in stage['join']['tracked']:
  observed=proc(ident['pid']);assert observed is None or observed['starttime']!=ident['starttime'] or observed['boot']!=ident['boot']
 assert stage['join']['no_live_descendants'] and not stage['join'].get('remaining_identities')
 stage_checks.append(dict(name=stage['name'],join=stage['join'],exit=stage['exit'],seconds=stage['seconds']))
available,offload=ctrl.host(data);assert offload==0
holds={}
for u in ('vkf-s0-synchronized-contexts.service','vkf-s0-synchronized-contexts.timer','vkf-s0-worker-done.path'):
 p=subprocess.run(['systemctl','--user','show',u,'-p','ActiveState','-p','MainPID'],capture_output=True,text=True,timeout=15)
 assert p.returncode==0 and 'ActiveState=inactive' in p.stdout and (not u.endswith('.service') or 'MainPID=0' in p.stdout);holds[u]=p.stdout
assert os.readlink('/run/user/1000/systemd/user/vkf-s0-synchronized-contexts.service')=='/dev/null'
sys.modules.pop('preflight',None);sys.path.insert(0,str(OUT.parent/'storage-live-24'));import check_loaded
check_loaded.save=save;assert check_loaded.check('final')
for path in [pathlib.Path(decision['protected_directory']),PACKET/'root-inputs.json',PACKET/'root-packet',pathlib.Path(data['lanes']['A']['policy']['root']['path'])/decision['attempt']]:assert not path.exists() and not path.is_symlink(),str(path)
assert 'A:'+decision['attempt'] not in data['phases'] and len(data['phases'])==16
assert sum(r['phase_bytes'] for k,r in data['phases'].items() if k not in ('A:compiler-native13-01','A:compiler-native17-01','A:d288-native24-01','A:metadata-native29-01'))==50331648
save('independent-stopped-terminal.json',dict(terminal_safety_verified=True,admission_allowed=False,predecessor_full_join_rejected=True,latest_joins=checks,all_historical_recorded_identities=all_identities,predecessor_stages=stage_checks,lanes=lanes,active_rows=active,active_ram=0,offload=offload,MemAvailable=available,holds=holds,seven_loaded_policies_verified=True,physical={p:physical(p) for p in ('/','/mnt/development','/mnt/vkf-storage-2tb')},prior_attempt_allocated=allocated(attempt),state_unchanged=True,owners_unchanged=True,no_new_attempt=True,no_rotation=True,no_publication=True,no_ram_release_performed=True,seconds=time.monotonic()-start))
print(json.dumps(dict(terminal_safety_verified=True,admission_allowed=False,predecessor_mismatches=checks['A']['mismatches'],active_ram=0,charges={w:lanes[w]['charge'] for w in 'AF'},seconds=time.monotonic()-start)))
