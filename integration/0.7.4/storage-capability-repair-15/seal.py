"""Read-only final input/resource seal; writes only this owned output."""
import ast, datetime, hashlib, json, pathlib, subprocess
H=pathlib.Path(__file__).resolve().parent
V=pathlib.Path('/home/viktor/Projects/Vektor Flow/.coordination/s0-plan-20261012/synchronized-contexts/independent-workers/storage20gb/storage-direct-v6')
def pin(p):return dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
for p in json.loads((H/'sourcepins.json').read_text()):assert pin(pathlib.Path(p['path']))==p
context=[H.parent/'HANDOVER.txt',H.parent/'baseline-results.json',pathlib.Path('/home/viktor/Projects/AGENTS.md'),V.parent/'storage-capability-repair-15-visible-chat-grant.json',V.parent/'storage-direct-v6-installed-20261017.json',pathlib.Path('/usr/include/linux/capability.h')]
for directory,names in {
 'storage-live-14':['HANDOFF.txt','raw-outer.stderr','raw-controller-failure.json','root-capability-observation.json','independent-terminal-observation.json','final-state.json'],
 'storage-live-13':['HANDOFF.txt'], 'storage-live-12':['HANDOFF.txt'],
 'storage-policy-setup-11':['HANDOFF.txt','REVIEW.txt','SYSTEM-SETUP.txt','test_policy.py'],
 'storage-propagation-repair-10':['SUCCESSOR.txt'], 'storage-live-09':['HANDOFF.txt'],
}.items():context.extend(H.parent/directory/name for name in names)
module=ast.parse((V/'private_workload.py').read_text())
for n in module.body:
 if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ('BINARIES','POLICY_INPUTS'):
  for entry in ast.literal_eval(n.value):assert pin(pathlib.Path(entry['path']))==entry;context.append(pathlib.Path(entry['path']))
(H/'reviewed-input-pins.json').write_text(json.dumps([pin(x) for x in context],indent=2)+'\n')
c=json.loads((V/'runtime-config.json').read_text())
state=V.parent/'storage-direct-v4/direct-state-v4.json';current=json.loads(state.read_text());old=json.loads((H.parent/'storage-live-14/final-state.json').read_text());assert current==old
r=current['phases']['F:live14-f-success-01']
assert r['stage']=='running' and 'inner_result' not in r and 'join' not in r
mem=int(next(x.split()[1] for x in pathlib.Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024
commands=[['systemctl','--user','list-units','--state=running,activating,deactivating','--plain','--no-legend','vkfworkers-*.service','vkfs0-*.service','*offload*.service']]
commands.extend(['systemctl','--user','show',u,'-p','ActiveState,SubState,UnitFileState'] for u in ('vkf-s0-synchronized-contexts.service','vkf-s0-synchronized-contexts.timer','vkf-s0-worker-done.path'))
observations=[]
for args in commands:
 p=subprocess.run(args,text=True,capture_output=True,timeout=10);observations.append(dict(argv=args,exit=p.returncode,stdout=p.stdout,stderr=p.stderr));assert p.returncode==0
assert not observations[0]['stdout'].strip()
assert all('ActiveState=inactive' in x['stdout'] for x in observations[1:])
mask=pathlib.Path('/run/user/1000/systemd/user/vkf-s0-synchronized-contexts.service')
assert mask.is_symlink() and str(mask.readlink())=='/dev/null'
cgroups={}
for lane,cg in c['lane_cgroups'].items():
 path=pathlib.Path('/sys/fs/cgroup')/cg.lstrip('/')
 cgroups[lane]={k:(path/k).read_text().strip() for k in ('cgroup.events','cgroup.procs','memory.max','memory.high','memory.swap.max','pids.max')}
 assert 'populated 0' in cgroups[lane]['cgroup.events'] and not cgroups[lane]['cgroup.procs']
seal=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),head=subprocess.check_output(['git','rev-parse','HEAD'],text=True,timeout=10).strip(),MemAvailable=mem,commands=observations,cgroups=cgroups,state_pin=pin(state),state_equals_live14=True,owner_pin=pin(pathlib.Path(c['owner_state'])),live14=dict(stage=r['stage'],ram_intent_retained=r['ram_bytes'],disk_charge_retained=r['phase_bytes'],normal_join=False,recovery_performed=False),installed_pins_unchanged=True,policy_and_binary_pins_unchanged=True,own_operational_jobs=0)
(H/'final-readonly-seal.json').write_text(json.dumps(seal,indent=2)+'\n')
print(json.dumps(seal,indent=2))
