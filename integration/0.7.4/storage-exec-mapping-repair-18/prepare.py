from pathlib import Path
import ast,difflib,gzip,hashlib,json,os,subprocess
H=Path(__file__).resolve().parent;R=H.parents[2];ROOT=Path('/home/viktor/Projects/Vektor Flow')
BASE=ROOT/'.coordination/s0-plan-20261012/synchronized-contexts/independent-workers/storage20gb';V=BASE/'storage-direct-v7'
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def pin(p):return dict(path=str(p),sha256=digest(p))
def save(n,d):(H/n).write_text(json.dumps(d,indent=2)+'\n')
old=(V/'private_workload.py').read_text();assert digest(V/'private_workload.py')=='d9c460205d3512f0ec17c08c4150ed539648753a3c942306987c5cd00958ccc0'
constants={}
for n in ast.parse(old).body:
 if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name):
  try:constants[n.targets[0].id]=ast.literal_eval(n.value)
  except (ValueError,TypeError):pass
pins=[]
for p in constants['BINARIES']+constants['POLICY_INPUTS']:
 assert digest(p['path'])==p['sha256'],p;pins.append(p)
for p in constants['ABSENT_INCLUDES']:assert not os.path.lexists(p),p
for p in [*V.glob('*.py'),V/'runtime-config.json',V/'recovery-authority-live14.json',BASE/'storage-direct-v4/direct-state-v4.json',BASE/'storage-direct-v4/owners-v4.json',BASE/'storage-exec-mapping-repair-18-visible-chat-grant.json',Path('/usr/bin/unshare'),Path('/usr/sbin/apparmor_parser'),Path('/usr/bin/python3.14'),Path('/etc/apparmor/parser.conf')]:pins.append(pin(p))
for p in [H.parent/'storage-live-17'/n for n in ['HANDOFF.txt','kernel-journal-readonly.json','security-observations.json','final-state.json','final-owner-state.json','initial-loaded-policy.json']]:pins.append(pin(p))
for p in [H.parent/'storage-policy-setup-11/HANDOFF.txt',H.parent/'storage-capability-repair-15/HANDOFF.txt',H.parent/'storage-capability-repair-15/proposed/private_workload.py',H.parent/'storage-propagation-repair-10/sources/ubuntu-unshare.c',H.parent/'storage-propagation-repair-10/sources/ubuntu-bubblewrap.c',H.parent/'storage-propagation-repair-10/sources/ubuntu-bind-mount.c']:pins.append(pin(p))
save('input-pins.json',pins);save('absent-includes.json',constants['ABSENT_INCLUDES'])
(H/'proposed').mkdir();(H/'system-setup').mkdir();(H/'baseline').mkdir();(H/'evidence').mkdir()
for p in V.glob('*.py'):(H/'baseline'/p.name).write_bytes(p.read_bytes())
policy=Path('/etc/apparmor.d/vkf-storage-private-v1').read_text();(H/'baseline/vkf-storage-private-v1').write_text(policy)
newpolicy=policy.replace('vkf-storage-private-v1','vkf-storage-private-v2').replace('vkf-storage-pre-v1','vkf-storage-pre-v2')
newpolicy=newpolicy.replace('  /usr/bin/python3.14 Px -> vkf-storage-pre-v2,','  /usr/bin/python3.14 m,\n  /usr/bin/python3.14 Px -> vkf-storage-pre-v2,')
newpolicy=newpolicy.replace('  /usr/bin/bwrap Px -> bwrap,','  /usr/bin/python3.14 m,\n  /usr/bin/bwrap m,\n  /usr/bin/bwrap Px -> bwrap,')
(H/'system-setup/vkf-storage-private-v2').write_text(newpolicy);psha=digest(H/'system-setup/vkf-storage-private-v2')
new=old.replace('vkf-storage-private-v1','vkf-storage-private-v2').replace('vkf-storage-pre-v1','vkf-storage-pre-v2').replace('a6a82dd0c9f50c296e88933645e8a8487b947dd4de6ff6e66acee2541e1a17a4',psha)
(H/'proposed/private_workload.py').write_text(new)
(H/'private-workload-v7-to-v8.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/private_workload.py',tofile='b/private_workload.py')))
(H/'policy-v1-to-v2.diff').write_text(''.join(difflib.unified_diff(policy.splitlines(True),newpolicy.splitlines(True),fromfile='installed-readonly/vkf-storage-private-v1',tofile='proposed-only/vkf-storage-private-v2')))
for n in ['apparmor.d.5','apparmor_parser.8']:
 p=Path('/usr/share/man/man'+n[-1])/(n+'.gz');(H/'sources'/n).write_bytes(gzip.decompress(p.read_bytes()));pins.append(pin(p))
# Hash all installed program metadata without executing the programs.
elf=[]
for p in ['/usr/local/libexec/vkf-storage-private-v1/unshare','/usr/bin/python3.14','/usr/bin/bwrap']:
 r=subprocess.run(['/usr/bin/readelf','-l','-d',p],capture_output=True,text=True,check=True,timeout=10)
 elf.append(dict(input=pin(p),argv=r.args,stdout=r.stdout,stderr=r.stderr))
save('evidence/elf-static.json',elf)
sc=ast.parse((V/'storage_controller.py').read_text());helpers=next(ast.literal_eval(n.value) for n in sc.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='HELPERS')
bundle=dict(controller=pin(V/'storage_controller.py'),helpers=[pin(V/n) for n in helpers],config=pin(V/'runtime-config.json'))
save('preserved-v7-bundle.json',bundle)
contract=dict(old_private_workload=pin(V/'private_workload.py'),new_private_workload=pin(H/'proposed/private_workload.py'),new_policy_source=pin(H/'system-setup/vkf-storage-private-v2'),new_policy_destination='/etc/apparmor.d/vkf-storage-private-v2',new_binary_destination='/usr/local/libexec/vkf-storage-private-v2/unshare',binary_source=pin('/usr/bin/unshare'),old_policy=pin('/etc/apparmor.d/vkf-storage-private-v1'),minimum_changes=['BINARIES[0].path','UNSHARE','POLICY_INPUTS[0].path','POLICY_INPUTS[0].sha256','policy_gate pre exact label'],preserved_v7_bundle=bundle,unchanged_helpers=[pin(V/n) for n in helpers if n!='private_workload.py'],unchanged_controller=pin(V/'storage_controller.py'),unchanged_recovery=pin(V/'recover_live14.py'),unchanged_authority=pin(V/'recovery-authority-live14.json'))
save('successor-contract.json',contract);save('input-pins.json',pins)
print(json.dumps({k:contract[k] for k in ['new_private_workload','new_policy_source','old_private_workload']}))
