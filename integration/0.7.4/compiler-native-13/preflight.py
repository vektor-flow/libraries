import argparse, importlib.util, json, os, pathlib, stat, subprocess, sys, time
OUT=pathlib.Path(__file__).resolve().parent
REPO=OUT.parents[2]; PACKET=OUT.parent/'compiler-runtime-binding-11'
STORAGE=pathlib.Path('/home/viktor/Projects/Vektor Flow/.coordination/s0-plan-20261012/synchronized-contexts/independent-workers/storage20gb')
sys.path.insert(0,str(PACKET));import adapter as a
sys.path.insert(0,str(STORAGE/'storage-direct-v9'))
from storage_admission import Ledger,physical
from storage_controller import Controller,Linux,mem,proc,same
from storage_paths import pinned,pinned_json,identity,allocated
import private_workload

def save(name,data):
 with (OUT/name).open('x') as f:json.dump(data,f,indent=2);f.write('\n')
def controller(s,row):
 gp,mp=row['grant'],row['manifest']
 return Controller(argparse.Namespace(config_sha256=s['v6_bundle']['config']['sha256'],grant=pathlib.Path(gp['path']),grant_sha256=gp['sha256'],manifest=pathlib.Path(mp['path']),manifest_sha256=mp['sha256']))
def main():
 start=time.monotonic();tag=sys.argv[1]
 grant=a.read(STORAGE/'compiler-native-13-visible-chat-grant.json');a.verify(grant['root_decision'])
 sys.path.insert(0,str(PACKET));import root_steps
 d,s,c,protected=root_steps.decision(grant['root_decision'])
 for k in ('artifact_pins','recipe','audit'):a.verify(d['root_review'][k])
 artifacts=a.load_pin(d['root_review']['artifact_pins'])['files']
 for p in artifacts:a.verify(p)
 provenance=a.load_pin(d['provenance_decision'])
 for k in ('provenance','authentication','classification','corrected_review'):a.verify(provenance[k])
 assert len(artifacts)==42 and len(s['pins'])==229
 private_workload.verify_dependencies()
 install=a.read(OUT.parent/'storage-combined-trust-review-23/root-v9-installed.json')
 for p in install['installed_files']:
  pinned(p);st=pathlib.Path(p['path']).lstat();assert stat.S_ISREG(st.st_mode) and st.st_nlink==1 and st.st_uid==os.getuid() and stat.S_IMODE(st.st_mode)==0o400
 for bundle in c['preserved_record_authorities']:
  for p in [bundle['controller'],*bundle['helpers'],bundle['config']]:pinned(p)
 ledger=Ledger(pathlib.Path(s['state_path']),pathlib.Path(s['lock_path']),recovery_pin=c['recovery_authority'])
 data=ledger.snapshot();ledger.check(data);assert not ledger.active_rows(data)
 initial=a.read(OUT.parent/'storage-live-24/final-state.json')
 assert data['phases']==initial['phases'] and data['recovery_events']==initial['recovery_events']
 assert len(data['phases'])==12 and sum(r['phase_bytes'] for r in data['phases'].values())==50331648
 osapi=Linux();assert not osapi.units('vkfworkers-*.service') and not osapi.units('vkfs0-*.service')
 joins={};lanes={}
 for w in 'AF':
  p=data['lanes'][w]['policy']; row=max((r for r in data['phases'].values() if r['worker']==w),key=lambda r:r['sequence'])
  ctrl=controller(s,row);assert ctrl.verify_join(row,pinned_json(row['join']))
  assert not same(row['custody']['identity'])
  joins[w]=dict(join=row['join'],verified=True,controller_absent=True,service=osapi.show(row['custody']['unit']))
  cg=pathlib.Path('/sys/fs/cgroup')/c['lane_cgroups'][w].lstrip('/')
  props={n:(cg/n).read_text().strip() for n in ('memory.max','memory.high','memory.swap.max','pids.max','cgroup.events','cgroup.procs')}
  assert props['memory.max']==str((8 if w=='A' else 3)*2**30) and props['memory.swap.max']=='0' and props['pids.max']=='160'
  assert osapi.empty(c['lane_cgroups'][w]) and (cg.parent/'memory.max').read_text().strip()==str(21*2**30) and (cg.parent/'memory.swap.max').read_text().strip()=='0'
  if w=='A':assert props['memory.high']==str(3*2**30)
  charge=p['historical_charge']+sum(r['phase_bytes'] for r in data['phases'].values() if r['worker']==w)
  assert charge==({'A':18790801408,'F':19821273088}[w])
  lanes[w]=dict(owner=ledger.owner(data,w),charge=charge,properties=props,old_volume=physical(p['old_volume']['path']),root_allocated=allocated(p['root']['path']),root_identity=identity(p['root']['path']))
 available,offload=ctrl.host(data);assert offload==0 and available>=10*2**30
 holds={}
 for u in ('vkf-s0-synchronized-contexts.service','vkf-s0-synchronized-contexts.timer','vkf-s0-worker-done.path'):
  p=subprocess.run(['systemctl','--user','show',u,'-p','ActiveState','-p','MainPID'],capture_output=True,text=True,timeout=15)
  assert p.returncode==0 and 'ActiveState=inactive' in p.stdout;holds[u]=p.stdout
 assert os.readlink('/run/user/1000/systemd/user/vkf-s0-synchronized-contexts.service')=='/dev/null'
 assert physical('/mnt/vkf-storage-2tb')['free']>=250000000000+10*2**30
 sys.path.insert(0,str(OUT.parent/'storage-live-24'));import check_loaded
 check_loaded.save=save;assert check_loaded.check(tag)
 e=dict(passed=True,boot=d['boot'],head=a.current_head(),available=available,active_ram=0,offload=offload,lanes=lanes,joins=joins,holds=holds,physical={p:physical(p) for p in ('/','/mnt/development','/mnt/vkf-storage-2tb')},state_pin=a.pin(s['state_path']),owner_pin=a.pin(c['owner_state']),artifact_count=len(artifacts),static_pins=len(s['pins']),elapsed_seconds=time.monotonic()-start)
 save(tag+'-resources.json',e);save(tag+'-state.json',data)
 print(json.dumps(e))
if __name__=='__main__':main()
