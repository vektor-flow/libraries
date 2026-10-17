from pathlib import Path
import ast,datetime,hashlib,json,os,subprocess
H=Path(__file__).resolve().parent
BASE=Path('/home/viktor/Projects/Vektor Flow/.coordination/s0-plan-20261012/synchronized-contexts/independent-workers/storage20gb')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def pin(p):return dict(path=str(p),sha256=sha(p))
pins=json.loads((H/'input-pins.json').read_text())
for p in pins:assert sha(p['path'])==p['sha256'],p
for p in json.loads((H/'absent-includes.json').read_text()):assert not os.path.lexists(p),p
state=json.loads((BASE/'storage-direct-v4/direct-state-v4.json').read_text())
prior=json.loads((H.parent/'storage-live-17/final-state.json').read_text())
assert state==prior,'live17 state drift'
owners=json.loads((BASE/'storage-direct-v4/owners-v4.json').read_text())
previous=json.loads((H.parent/'storage-live-17/final-owner-state.json').read_text())
assert owners==previous['state'] and sha(previous['pin']['path'])==previous['pin']['sha256'],'live17 owners drift'
resources={}
for lane in 'af':
 p=Path('/sys/fs/cgroup/user.slice/user-1000.slice/user@1000.service/vkfworkers.slice')/('vkfworkers-'+lane+'.slice')
 resources[lane]={n:(p/n).read_text().strip() for n in ['cgroup.events','cgroup.procs','memory.max','memory.high','memory.swap.max','pids.max']}
 assert 'populated 0' in resources[lane]['cgroup.events'].splitlines() and resources[lane]['cgroup.procs']==''
argv=['/usr/bin/systemctl','--user','list-units','--state=activating,active,deactivating','--no-legend','--no-pager','vkfworkers-*.service','vkfs0-*.service']
p=subprocess.run(argv,capture_output=True,text=True,timeout=15);assert p.returncode==0 and not p.stdout.strip()
held=subprocess.run(['/usr/bin/systemctl','--user','show','vkf-s0-synchronized-contexts.service','vkf-s0-synchronized-contexts.timer','vkf-s0-worker-done.path','-p','Id','-p','ActiveState'],capture_output=True,text=True,timeout=15)
assert held.returncode==0 and held.stdout.count('ActiveState=inactive')==3
assert os.readlink('/run/user/1000/systemd/user/vkf-s0-synchronized-contexts.service')=='/dev/null'
mem=int(next(s.split()[1] for s in Path('/proc/meminfo').read_text().splitlines() if s.startswith('MemAvailable:')))*1024
joins=[]
for n in ['initial-test-results.json','before-lock-test-results.json','test-results.json']:
 r=json.loads((H/n).read_text());assert r['exit']==0 and not Path('/proc/'+str(r['pid'])).exists();joins.append(r)
for r in json.loads((H/'compile-results.json').read_text()):assert r['returncode']==0 and not Path('/proc/'+str(r['pid'])).exists();joins.append(r)
(H/'all-owned-test-parser-joins.json').write_text(json.dumps(joins,indent=2)+'\n')
additional=[Path('/home/viktor/Projects/AGENTS.md'),H.parent/'HANDOVER.txt',H.parent/'COORDINATOR-STATUS.txt',BASE.parents[1]/'controller.py',Path('/home/viktor/Projects/Vektor Flow/.worktrees/integration-0133/bootstrap/scripts/worker_supervisor_0136.py')]
(H/'additional-input-pins.json').write_text(json.dumps([pin(x) for x in additional],indent=2)+'\n')
checks=[]
for name in ('install','rollback'):
 a=['/usr/bin/bash','-n',str(H/'system-setup'/(name+'-reviewed.sh'))];r=subprocess.run(a,capture_output=True,text=True,timeout=10);assert r.returncode==0;checks.append(dict(argv=a,exit=r.returncode,stderr=r.stderr))
for p in H.glob('*.py'):ast.parse(p.read_text())
ast.parse((H/'system-setup/system_setup.py').read_text())
result=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_inputs_unchanged=len(pins),state_equal_live17=True,owners_equal_live17=True,retained_attempts=5,retained_charged_bytes=20*1024**2,active_ram_intent=0,accounting_basis='byte-equivalent live17 final state and normal-join evidence; no operational mutation',new_attempts=0,worker='01a14996-21e5-7d01-8d80-eced8f40d032',MemAvailable=mem,active_worker_legacy_services='',lanes=resources,dispatcher=held.stdout,dispatcher_mask='/dev/null',syntax_checks=checks,HEAD=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),test_parser_children_joined=len(joins),owned_output_bytes=sum(p.stat().st_size for p in H.rglob('*') if p.is_file()),all_output_ordinary_owned=all(p.lstat().st_uid==os.getuid() for p in H.rglob('*')))
assert result['all_output_ordinary_owned']
(H/'final-readonly-seal.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
