"""Read-only final authority/source check, and own-output patch reconstruction."""
import json,resource,subprocess,sys,time
from pathlib import Path
resource.setrlimit(resource.RLIMIT_AS,(512*2**20,)*2);resource.setrlimit(resource.RLIMIT_CPU,(50,50));resource.setrlimit(resource.RLIMIT_CORE,(0,0));sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;sys.path.insert(0,str(H));import adapter as a
start=time.monotonic();seal=a.static_contract();plan=a.load_pin(seal['control_plan']);config=a.load_pin(seal['v6_bundle']['config'])
for pin in seal['pins']+plan['inputs']+plan['generated']:a.verify(pin)
a.check_plan(plan,a.current_head(),a.load_pin(seal['review']))
from root_steps import decision
try:decision(a.pin(H/'root-decisions.REQUIRED.json'))
except ValueError as e:assert 'genuine separate root' in str(e)
else:raise AssertionError('null decision accepted')
sys.path.insert(0,str(Path(seal['v6_bundle']['config']['path']).parent));from storage_admission import Ledger
ledger=Ledger(Path(seal['state_path']),Path(seal['lock_path']),recovery_pin=config['recovery_authority'])
# No snapshot/transaction/lock: authenticate released rows and inspect read-only bytes.
state=a.read(seal['state_path']);active=ledger.active_rows(state);assert not active
key,row=max(((k,r) for k,r in state['phases'].items() if r['worker']=='A'),key=lambda x:x[1]['sequence'])
assert key=='A:metadata-native29-01' and row['sequence']==15 and row['stage']=='joined'
assert row['owner']==ledger.owner(state,'A')=='01a14a3a-d0d8-7a10-a188-717e31a22e31'
accept=a.read(H.parent/'metadata-native-29/root-terminal-review.json');assert row['join']==accept['join'];a.verify(row['join'])
charges={w:state['lanes'][w]['policy']['historical_charge']+sum(r['phase_bytes'] for r in state['phases'].values() if r['worker']==w) for w in 'AF'}
assert charges==dict(A=24159510528,F=19821273088)
non_tiny={'A:compiler-native13-01','A:compiler-native17-01','A:d288-native24-01','A:metadata-native29-01'}
tiny=[r for k,r in state['phases'].items() if k not in non_tiny]
assert len(tiny)==12 and sum(r['phase_bytes'] for r in tiny)==50331648
assert row['phase_bytes']==1073741824
historical=a.read(H.parent/'metadata-native-29/final-state.json')
assert state==historical, 'ledger changed since retained native29 terminal state; fresh root review required'
terminal=a.read(H.parent/'metadata-native-29/independent-terminal-join.json')
assert terminal['verified'] and terminal['join']==row['join'] and terminal['cgroup_empty']
assert terminal['outer_controller_joined'] and terminal['owned_descendants_joined']
retained=a.read(H.parent/'metadata-native-29/attempt-artifact-pins.json')
for ref in retained:a.verify(ref)
actual=a.read(H.parent/'metadata-native-29/native-evidence.json')
assert not actual['passed'] and actual['all_recorded_children_joined']
actual_plan=a.load_pin(actual['actual_plan'])
assert actual_plan['stages'][-1]['stdout']=='true\n'
run=actual['stages'][-1]
assert run['exit']==0 and len(run['logs'])==2
assert Path(run['logs'][0]['path']).read_bytes()==b'' and Path(run['logs'][1]['path']).read_bytes()==b''
for ref in a.read(H/'initial-observation.json')['protected_pins']:a.verify(ref)
assert (H/'adapter.py').read_bytes()==(H.parent/'metadata-control-preparation-27/adapter.py').read_bytes()

proof=[];children=[];out=H/'patch-reconstruction';out.mkdir(exist_ok=False)
for name in ('build_packet.py','seal_source.py','root_steps.py'):
 source=H.parent/'metadata-control-preparation-27'/name
 child=subprocess.Popen(['/usr/bin/patch','--batch','--output',str(out/name),str(source),str(H/(name+'.patch'))],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
 stdout,stderr=child.communicate(timeout=5)
 children.append(dict(pid=child.pid,exit=child.returncode,joined=True,absent=not Path('/proc',str(child.pid)).exists()))
 assert child.returncode==0 and (out/name).read_bytes()==(H/name).read_bytes(),(stdout,stderr)
 proof.append(dict(original=a.pin(source),patch=a.pin(H/(name+'.patch')),reconstructed=a.pin(out/name),candidate=a.pin(H/name)))
for report in ('test-results.json','packet-verification.json','independent-verification.json'):
 d=a.read(H/report);assert d['passed']
 for child in d['children']:assert child['joined'] and child['absent'] and not Path('/proc',str(child['pid'])).exists()
assert all(c['joined'] and c['absent'] for c in children)
assert a.current_head()==seal['source_commit']
# Tracked repository source must remain unchanged; preexisting untracked work is unrelated.
child=subprocess.Popen(['/usr/bin/git','-C',str(a.REPO),'diff','--exit-code','HEAD','--'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
stdout,stderr=child.communicate(timeout=5);assert child.returncode==0 and not stdout
children.append(dict(pid=child.pid,exit=child.returncode,joined=True,absent=not Path('/proc',str(child.pid)).exists()))
report=dict(passed=True,source_commit=seal['source_commit'],source_contract=a.pin(H/'source-contract.json'),all_sealed_pins_verified=True,null_decision_rejected=True,latest_A=dict(key=key,sequence=row['sequence'],owner=row['owner'],join=row['join']),charges=charges,tiny_attempts=len(tiny),tiny_bytes=sum(r['phase_bytes'] for r in tiny),failed_native29_charge_retained=row['phase_bytes'],native29_actual_artifacts_reauthenticated=len(retained),native29_empty_stdout_failure_retained=True,active_ram_intent=sum(r['ram_bytes'] for r in active),unlocked_observation_not_admission=True,patch_reconstruction=proof,children=children,all_children_joined=True,tracked_shared_source_unchanged=True,native_execution=False,operational_mutations=0,seconds=time.monotonic()-start,memory=[s for s in Path('/proc/self/status').read_text().splitlines() if s.startswith(('VmHWM:','VmPeak:'))])
a.save(H/'final-verification.json',report);print(json.dumps({k:v for k,v in report.items() if k!='patch_reconstruction'}))
