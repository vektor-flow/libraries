import json,os,pathlib,subprocess,sys,time
OUT=pathlib.Path(__file__).resolve().parent;P=OUT.parent/'metadata-control-preparation-27'
sys.path.insert(0,str(OUT));from preflight import a,STORAGE,controller,save
assert not (OUT/'STOP.json').exists()
s=a.static_contract();r=a.read(P/'root-inputs.json');v=a.read(P/'root-packet/PREPARATION-ONLY.json');m=a.load_pin(v['manifest']);g=a.load_pin(v['grant']);config=a.load_pin(s['v6_bundle']['config'])
ctrl=controller(s,dict(grant=v['grant'],manifest=v['manifest']))
publication=a.read(r['publication_receipt_path']);owners=a.read(config['owner_state'])
assert publication['coordinator']==r['coordinator'] and publication['published'] is True and publication['under_capacity_lock'] is True
assert publication['grant']==v['grant'] and publication['manifest']==v['manifest'] and publication['owner_transition']==r['owner_transition'] and publication['owner_entry']==owners['workers']['A']
assert a.read(OUT/'prelaunch-resources.json')['passed'] is True
root=pathlib.Path(m['attempt_root']);assert not root.exists() and not root.is_symlink()
cmd=['/usr/bin/python3','-B',s['v6_bundle']['controller']['path'],'--config-sha256',s['v6_bundle']['config']['sha256'],'--grant',r['grant_path'],'--grant-sha256',v['grant']['sha256'],'--manifest',r['manifest_path'],'--manifest-sha256',v['manifest']['sha256']]
save('launch-intent.json',dict(argv=cmd,attempt=str(root),prelaunch=a.pin(OUT/'prelaunch-resources.json'),publication=a.pin(r['publication_receipt_path'])))
root.mkdir(mode=0o700);assert not list(root.iterdir())
assert ctrl.current()==dict(grant=v['grant'],thread=r['owner'],iteration=r['iteration'])
high=subprocess.run(['/usr/bin/systemctl','--user','set-property','--runtime','vkfworkers-a.slice','MemoryHigh=7G'],capture_output=True,text=True)
save('set-high-result.json',dict(exit=high.returncode,stdout=high.stdout,stderr=high.stderr))
if high.returncode:
 save('STOP.json',dict(stage='set-high',exit=high.returncode));raise SystemExit(high.returncode)
cg=pathlib.Path('/sys/fs/cgroup')/config['lane_cgroups']['A'].lstrip('/')
assert (cg/'memory.high').read_text().strip()==str(7*2**30) and not list(root.iterdir())
start=time.monotonic()
with (OUT/'controller.stdout').open('xb') as stdout,(OUT/'controller.stderr').open('xb') as stderr:
 result=subprocess.run(cmd,stdout=stdout,stderr=stderr)
rec=dict(exit=result.returncode,seconds=time.monotonic()-start,controller_subprocess_joined=True,argv=cmd)
save('controller-result.json',rec)
if result.returncode:save('STOP.json',dict(stage='controller',**rec))
print(json.dumps(rec));raise SystemExit(result.returncode)
