"""Bounded source/provenance/forecast report. No operational authority is generated."""
import sys,resource,json,time
from pathlib import Path
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;sys.path.insert(0,str(H));import adapter as a
sys.path.insert(0,str(a.PACKAGE));import prepare as p
resource.setrlimit(resource.RLIMIT_AS,(512*2**20,)*2);resource.setrlimit(resource.RLIMIT_CORE,(0,0))
def main():
 old=a.read(p.HERE/'current-application-inputs.json')['selections'];rows={}
 for phase in ('d288','metadata','a345','f364','a347','full-app'):
  plan=a.read(H/'staging'/phase/'plan.json');before={x['path']:x['sha256'] for x in old[phase]['inputs']};after={x['path']:x['sha256'] for x in plan['application_inputs']}
  origins=[];origins_verified=[]
  if phase=='d288':
   for folder in (p.D,p.CACHE/'Proof/tests/independent-worker-D/iteration288-ownership02'):
    originals=a.read(folder/'plan.json')['cases'];origins.extend([a.pin(folder/'plan.json'),a.pin(folder/'run.py')])
    for case in originals:
     path=H/'staging'/phase/case['name']/'raw'/(case['name']+'.vkf');assert path.read_bytes()==Path(case['source']).read_bytes();origins.append(a.pin(case['source']));origins_verified.append(str(path))
  elif phase in ('metadata','a345','a347'):
   source=p.REPAIR/'regressions/metadata_actual_lengths.vkf' if phase=='metadata' else next((p.REPAIR/'regressions').glob('*small*' if phase=='a345' else '*real*'))
   name={'metadata':'metadata','a345':'A345','a347':'A347'}[phase];path=H/'staging'/phase/name/'raw'/(name+'.vkf');assert path.read_bytes()==source.read_bytes();origins=[a.pin(source)];origins_verified=[str(path)]
  elif phase=='f364':
   f=p.CACHE/'Integrator/independent-worker-F/iteration364-scene-ten01';history=a.read(f/'execution-plan.json')['suites'][0]
   origins=[a.pin(f/'execution-plan.json'),a.pin(f/'prepare_group.py'),history['derivative']]
   for run in history['runs']:origins.append(a.pin(run['stdin']))
   assert len([s for s in plan['stages'] if 'stdin' in s])==11
  else:
   source=a.REPO/'examples/gpu-math/native-vkf/native_document_cli.vkf';origins=[a.pin(source)];assert (H/'staging/full-app/full-app/raw/native_document_cli.vkf').read_bytes()==source.read_bytes()
  for ref in origins:a.verify(ref)
  rows[phase]=dict(plan=a.pin(H/'staging'/phase/'plan.json'),historical_origins=origins,byte_identical_roots_verified=origins_verified,current_source_inputs=plan['application_inputs'],current_modules_including_roots=sum(len(x['modules']) for x in plan['cases']),changed_sources=[dict(path=x,before=before[x],after=after[x]) for x in sorted(before.keys()&after.keys()) if before[x]!=after[x]],added_sources=[dict(path=x,sha256=after[x]) for x in sorted(after.keys()-before.keys())],removed_sources=sorted(before.keys()-after.keys()),cases=plan['cases'],stages=[{k:s[k] for k in ('name','argv','timeout','expected_exit','stdout','stderr','valgrind','stdin','report') if k in s} for s in plan['stages']],runs=[dict(name=s['name'],stdin=Path(s['stdin']).read_text()) for s in plan['stages'] if 'stdin' in s])
 oldseal=a.read(H.parent/'compiler-runtime-binding-16/source-contract.json');seal=a.read(H/'source-contract.json');before={x['path']:x['sha256'] for x in oldseal['pins']};after={x['path']:x['sha256'] for x in seal['pins']}
 a.save(H/'provenance-delta.json',dict(source_commit=seal['source_commit'],compiler_source_commit='5b6d933546020702c20d57d1bb1821c1b79266bd',native_compiler=a.read(H/'compiler-receipt.snapshot.json')['compiler'],compiler_not_rebuilt=True,old_closure_head=old['metadata']['head'],phases=rows,static_pin_delta=dict(added=[dict(path=x,sha256=after[x]) for x in sorted(after.keys()-before.keys())],changed=[dict(path=x,before=before[x],after=after[x]) for x in sorted(before.keys()&after.keys()) if before[x]!=after[x]],removed=sorted(before.keys()-after.keys()))))
 estimate=a.read(p.HERE/'estimates.json');forecasts=[x for x in estimate['phases'] if x['name']!='compiler']
 for forecast in forecasts:
  phase=forecast['name'];plan=a.read(H/'staging'/phase/'plan.json');forecast.update(native_control_measurements_available=False,phase_stage_timeout_sum_seconds=sum(s['timeout'] for s in plan['stages']),plan=a.pin(H/'staging'/phase/'plan.json'),run_stage_count=sum('stdin' in s for s in plan['stages']),admitted=False)
 a.save(H/'phase-forecasts.json',dict(estimates_not_admission=True,source= a.pin(p.HERE/'estimates.json'),phases=forecasts,cumulative_retained_disk_upper_bytes=sum(x['inclusive_new_attempt_disk_bytes'] for x in forecasts),proposed_first_phase=dict(phase='d288',worker='A',disk_bytes=a.DISK,timeout_seconds=a.TIMEOUT,admission_ram_bytes=8*a.GIB,forecast_ram_bytes=4*a.GIB,reason='Installed preserved A policy requires existing8GiB profile;4GiB is only an uncalibrated forecast',native_execution=False),all_failed_artifacts_retained=True,root_selects_each_separate_grant=True,full_app_compile_only=True))
 # Genuine future decision template, deliberately null where only root may authorize.
 required=a.read(H.parent/'compiler-runtime-binding-11/root-decisions.REQUIRED.json')
 required.update(source_contract=a.pin(H/'source-contract.json'),source_commit=seal['source_commit'],phase='d288',ram_bytes=8*a.GIB,disk_bytes=a.DISK,timeout_seconds=a.TIMEOUT,boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip())
 a.save(H/'root-decisions.REQUIRED.json',required)
 print(json.dumps(dict(phases={k:dict(modules=v['current_modules_including_roots'],changed=len(v['changed_sources']),added=len(v['added_sources']),removed=len(v['removed_sources'])) for k,v in rows.items()},forecasts_not_admission=True)))
if __name__=='__main__':main()
