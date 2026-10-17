"""Seal own deliverables; read-only external pin checks, no operational changes."""
import sys,resource,json,re,hashlib,subprocess,time
from pathlib import Path
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;sys.path.insert(0,str(H));import adapter as a
resource.setrlimit(resource.RLIMIT_AS,(512*2**20,)*2);resource.setrlimit(resource.RLIMIT_CPU,(45,45));resource.setrlimit(resource.RLIMIT_CORE,(0,0))
def reconstruct(source,patch):
 old=source.splitlines(True);out=[];position=0;lines=patch.splitlines(True);i=0
 while i<len(lines):
  line=lines[i]
  if not line.startswith('@@ '):i+=1;continue
  match=re.match(r'@@ -(\d+)(?:,\d+)? \+\d+(?:,\d+)? @@',line);assert match
  start=int(match[1])-1;out.extend(old[position:start]);position=start;i+=1
  while i<len(lines) and not lines[i].startswith('@@ '):
   line=lines[i];kind=line[:1];body=line[1:]
   if kind in (' ','-'):assert old[position]==body;position+=1
   if kind in (' ','+'):out.append(body)
   i+=1
 out.extend(old[position:]);return ''.join(out)
def main():
 started=time.monotonic();s=a.static_contract();assert a.current_head()==s['source_commit']
 for name in ('adapter','root_steps'):
  assert reconstruct((H.parent/'compiler-runtime-binding-16'/(name+'.py')).read_text(),(H/(name+'.patch')).read_text())==(H/(name+'.py')).read_text()
 count=0
 for phase in a.read(H/'preparation.json')['phases']:
  a.verify(phase['plan']);p=a.load_pin(phase['plan'])
  for ref in p['inputs']+p['generated']+p['application_inputs']:a.verify(ref);count+=1
  for ref in a.read(a.PACKAGE/'authentication.json')['inputs']:
   assert any(x['path']==ref['path'] and x['sha256']==ref['sha256'] for x in p['inputs'])
 observation=a.read(H/'succession-observation.json')
 if 'active_rows' in observation:
  observation['nonjoined_historical_rows_not_an_active_RAM_measurement']=observation.pop('active_rows')
  (H/'succession-observation.json').write_bytes(a.encoded(observation))
 tests=a.read(H/'test-results.json');assert tests['passed'] and tests['tests']==13 and all(c['joined'] and c['absent'] for c in tests['children'])
 result=dict(result='D288_SOURCE_PACKET_READY_FOR_ROOT_REVIEW',owner='01a14a0d-d6f5-75a0-8371-5374dc4f7784',coordinator=a.COORDINATOR,source_commit=s['source_commit'],native_execution=False,operational_mutations=0,agents=0,commits=0,root_acceptance_pending=True,first_phase='d288',later_phases_staged=['metadata','a345','f364','a347','full-app'],test_results=a.pin(H/'test-results.json'),source_contract=a.pin(H/'source-contract.json'),adapter=a.pin(H/'adapter.py'),adapter_patch=a.pin(H/'adapter.patch'),root_steps=a.pin(H/'root_steps.py'),root_steps_patch=a.pin(H/'root_steps.patch'),native_authentication=a.pin(H/'native-authentication.json'),runtime_closure=a.pin(H/'runtime-closure.json'),provenance_delta=a.pin(H/'provenance-delta.json'),phase_forecasts=a.pin(H/'phase-forecasts.json'),handoff=a.pin(H/'HANDOFF.txt'),recipe=a.pin(H/'ROOT-RECIPE.txt'),patch_reconstruction_passed=True,final_plan_input_rechecks=count,seconds=time.monotonic()-started,all_own_children_joined=True,native47_or_original419_credit_added=0,renderer_PDF_acceptance=False,full_app_compile_only=True,memory=[line for line in Path('/proc/self/status').read_text().splitlines() if line.startswith(('VmHWM:','VmPeak:'))])
 a.save(H/'result.json',result)
 refs=[a.pin(path) for path in sorted(H.rglob('*')) if path.is_file() and not path.is_symlink() and path.name not in ('artifact-pins.json','finalize.stdout','finalize.stderr')]
 a.save(H/'artifact-pins.json',dict(pins=refs,scope='Own immutable delivery before final notification; generated .stdin roots included; external stdlib symlink targets pinned in plans'))
 print(json.dumps(result))
if __name__=='__main__':main()
