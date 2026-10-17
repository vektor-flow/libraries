"""Host-only cross-packet consistency, restoration patch and mutable-input inventory."""
import ast, collections, hashlib, json, os, stat, subprocess, sys, tempfile, time
from pathlib import Path
H=Path(__file__).resolve().parent;sys.path.insert(0,str(H))
import adapter as a
sys.path.insert(0,str(a.PACKAGE))
import prepare,payload,authenticate
start=time.monotonic();checks=[]
def check(ok,label):
 assert ok,label
 checks.append(label)
seal=a.static_contract();plan=a.load_pin(seal['control_plan'])
old=H.parent/'compiler-build-preparation-03';binding=H.parent/'metadata-repaired-binding-32'
for m in (prepare,payload,authenticate):check(Path(m.__file__).parent==H/'generator','actual imported module relocated: '+m.__name__)
check(a.pin(H/'generator/prepare.py')['sha256']=='400a56b07d9cb67c7d4d9331a787d13af43fd60dfba56a09481e88b9f66de169','repaired generator byte identity retained')
check(a.pin(H/'historical-prepare.py')['sha256']=='fd49773772924b2ccf59b4a9386dc5e22a1062cc8176391c6a0ed5058713ffda','authentic historical Git bytes retained')
check((old/'prepare.py').read_bytes()==(H/'generator/prepare.py').read_bytes(),'shared generator not restored or temporarily swapped by worker')
check(prepare.REPO==a.REPO and prepare.REPAIR==H.parent/'compiler-renderer-repair-02' and prepare.HERE==a.PACKAGE,'generator context resolves actual repository and original fixture')
check((H/'generator/payload.py').read_bytes()==(old/'payload.py').read_bytes(),'payload unchanged byte for byte')
check((H/'generator/authentication.json').read_bytes()==(old/'authentication.json').read_bytes(),'authentication inventory unchanged byte for byte')
check((H/'generator/authenticate.py').read_text().replace('REPO=HERE.parents[3]','REPO=HERE.parents[2]').replace("REPAIR=HERE.parents[1]/'compiler-renderer-repair-02'","REPAIR=HERE.parent/'compiler-renderer-repair-02'")==(old/'authenticate.py').read_text(),'authentication implementation only two location constants changed')
check((H/'adapter.py').read_text().replace("PACKAGE = HERE / 'generator'","PACKAGE = HERE.parent / 'compiler-build-preparation-03'")==(binding/'adapter.py').read_text(),'adapter only PACKAGE location changed')
check((H/'build_packet.py').read_text().replace("HERE/'generator'","HERE.parent/'compiler-build-preparation-03'")==(binding/'build_packet.py').read_text(),'build only generator import location changed')
check((H/'seal_source.py').read_bytes()==(binding/'seal_source.py').read_bytes(),'sealer unchanged and follows adapter package binding')
check((H/'root_steps.py').read_text().replace('source-only history repair39','source-only repaired binding32')==(binding/'root_steps.py').read_text(),'root recipe predicates and operations unchanged')
inputs=a.unique(seal['pins']+a.controller_inputs(plan['inputs']))
check(not any(Path(p['path']).is_relative_to(old) for p in inputs),'successor direct input closure has no historical package path')
for name in ('prepare.py','payload.py','authenticate.py','authentication.json','SPEC.txt'):
 check(a.pin(a.PACKAGE/name) in inputs,'successor seals exact relocated '+name)
closure=a.read(H/'runtime-closure.json')
for name in ('prepare','payload','authenticate'):
 check(next(r['source'] for r in closure['modules'] if r['module']==name)==a.pin(a.PACKAGE/(name+'.py')),'actual sealer import source pinned '+name)
check(len(closure['elf_edges'])==104,'full ELF edge closure retained')
with tempfile.TemporaryDirectory(prefix='TEST_ONLY_restore_',dir=H) as tmp:
 target=Path(tmp)/'prepare.py';target.write_bytes((old/'prepare.py').read_bytes())
 proc=subprocess.run(['/usr/bin/patch','--batch',str(target),str(H/'ROOT-restore-historical.patch')],capture_output=True,timeout=5)
 check(proc.returncode==0 and target.read_bytes()==(H/'historical-prepare.py').read_bytes(),'root restoration patch reconstructs exact authentic bytes in own temporary file')
check((old/'prepare.py').read_bytes()==(H/'generator/prepare.py').read_bytes(),'original path remained unchanged after patch reconstruction')
audit=a.read(H/'history-audit.json');inventory=[];groups=collections.Counter()
for entry in audit['inputs']:
 p=Path(entry['pin']['path']);st=p.stat();parent=p.parent.stat()
 group=('repository' if p.is_relative_to(a.REPO) else 'coordination' if '/.coordination/' in str(p) else 'historical-cache' if '/.cache/vkf-' in str(p) else 'prior-native-artifact' if str(p).startswith('/mnt/development/') else 'host-runtime-or-policy')
 groups[group]+=1
 inventory.append(dict(pin=entry['pin'],group=group,mode=oct(stat.S_IMODE(st.st_mode)),uid=st.st_uid,owned_by_worker=st.st_uid==os.getuid(),currently_writable=os.access(p,os.W_OK),parent_currently_writable=os.access(p.parent,os.W_OK),matching=entry['verified']))
check(sum(groups.values())==915 and sum(not x['matching'] for x in inventory)==1,'full metadata29 manifest inventoried; exactly one incompatible pin')
state=Path(seal['state_path']);check(state.read_bytes()==(H.parent/'metadata-native-29/final-state.json').read_bytes(),'full current state equals native29 terminal state')
config=a.load_pin(seal['v6_bundle']['config']);check(Path(config['owner_state']).read_bytes()==(H.parent/'metadata-native-29/final-owners.json').read_bytes(),'published owners unchanged')
data=a.read(state)
charges={w:data['lanes'][w]['policy']['historical_charge']+sum(r['phase_bytes'] for r in data['phases'].values() if r['worker']==w) for w in 'AF'}
check(charges==dict(A=24159510528,F=19821273088),'all cumulative charges retained')
check(os.readlink('/run/user/1000/systemd/user/vkf-s0-synchronized-contexts.service')=='/dev/null','dispatcher runtime mask retained')
check(not subprocess.check_output(['/usr/bin/git','-C',str(a.REPO),'diff','HEAD','--']),'no tracked shared mutations')
result=dict(passed=True,checks=checks,check_count=len(checks),seconds=time.monotonic()-start,source_commit=a.current_head(),native_execution=False,operational_mutations=0,manifest_groups=dict(groups),worker_writable_inputs=sum(r['currently_writable'] for r in inventory),worker_replaceable_parents=sum(r['parent_currently_writable'] for r in inventory),charges=charges,inputs=inventory,limitation='No filesystem immutability guarantee: writable files or directories and privileged host updates remain capable of invalidating pins. Final root HEAD/path reseal required.')
a.save(H/'relocation-verification.json',result)
print(json.dumps({k:v for k,v in result.items() if k not in ('inputs','checks')}))
