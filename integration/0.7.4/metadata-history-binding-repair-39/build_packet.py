"""Own-output source preparation; never invokes native tools or operational APIs."""
import sys,resource,json,importlib.util,time
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/'generator'))
import prepare as p, payload
from authenticate import sha,pin,read,save
HEAD='0d6d2bea2eb8015ee56f95b1e0eaf78e3d3c3108'
NATIVE=Path('/mnt/development/CompilerOptimization/owner-01a14893-cb1e-7203-97dd-de3da44dcf31/A/direct-v2-20261017/compiler-native17-01')
SELECTIONS=('metadata',)
def main():
 resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,)*2);resource.setrlimit(resource.RLIMIT_CPU,(50,50));resource.setrlimit(resource.RLIMIT_CORE,(0,0))
 started=time.monotonic();assert p.current_head()==HEAD
 accepted=read(HERE.parent/'compiler-native-17/root-acceptance.json')
 receipt=read(NATIVE/'compiler/compiler-receipt.json');review=p.review(HERE.parent/'compiler-native-binding-08/corrected-review.json')
 assert accepted['accepted']=='native compiler build and core regression only'
 assert accepted['binary']==receipt['compiler'] and receipt['candidate_review']==review
 assert receipt['identity']=='340d32d743bfcd6da076840963974462ed590852314ae483bbde5b4cc20c2e74'
 assert receipt['native_build_passed'] and receipt['core_regression_passed']
 refs=[pin(NATIVE/'compiler/compiler-receipt.json'),accepted['native_evidence'],accepted['join'],receipt['compiler'],receipt['plan'],receipt['results']]
 for ref in refs:p.verify(ref)
 native_plan=read(receipt['plan']['path']);results=read(receipt['results']['path']);assert len(results)==len(native_plan['stages'])==8
 generated={str(Path(x['path']).resolve()):x['sha256'] for row in results for x in row.get('outputs',[])}
 for spec,row in zip(native_plan['stages'],results):
  assert spec['name']==row['name'] and spec['argv']==row['argv']
  j=row['join'];assert j['no_live_descendants'] and not any(j.get(k) for k in ('timed_out','guard_error','orphaned_descendant_on_exit','remaining_identities'))
  for ref in row.get('logs',[])+row.get('outputs',[])+row.get('actual_dependencies',[]):p.verify(ref)
  payload.check_result(spec,row['exit'],Path(row['logs'][0]['path']).read_text(),Path(row['logs'][1]['path']).read_text())
  if 'md' in spec:
   p.verify(row['depfile']);assert payload.validate_md(spec,generated)==row['actual_dependencies']
 with Path(receipt['compiler']['path']).open('rb') as f:
  assert f.read(4)==b'\x7fELF';f.seek(0);found=False;tail=b'';marker=receipt['identity'].encode()
  while chunk:=f.read(262144):found|=marker in tail+chunk;tail=chunk[-len(marker):]
  assert found
 save(HERE/'compiler-receipt.snapshot.json',receipt)
 save(HERE/'native-authentication.json',dict(accepted=pin(HERE.parent/'compiler-native-17/root-acceptance.json'),actual_inputs=refs,ELF_and_identity_verified=True,actual_MD_revalidated=True,eight_stage_oracles_and_joins_verified=True,native_execution=False,seconds=time.monotonic()-started))
 auth=read(p.HERE/'authentication.json');p.freeze_check(auth)
 recipe=read(p.CACHE/'Frontend/experiments/independent-worker-A/iteration347/recipe.json')
 extra=recipe['stdlib']+recipe['tools']
 # Explicit Valgrind launcher/script/interpreter and amd64 memcheck engine/preloads.
 for path in ['/usr/bin/valgrind','/usr/bin/valgrind.bin','/bin/sh','/usr/libexec/valgrind/memcheck-amd64-linux','/usr/libexec/valgrind/vgpreload_core-amd64-linux.so','/usr/libexec/valgrind/vgpreload_memcheck-amd64-linux.so','/usr/libexec/valgrind/default.supp']:
  extra.append(pin(path))
 origins=[pin(p.REPAIR/'regressions/metadata_actual_lengths.vkf')]
 counts=[]
 for selection in SELECTIONS:
  out=HERE/'staging'/selection
  plan=p.tests_plan(out,review,auth,receipt,selection)
  assert selection == 'metadata' and len(plan['cases']) == 1 and len(plan['stages']) == 3
  compile_stages = [stage for stage in plan['stages'] if stage['name'].endswith('-compile')]
  assert len(compile_stages) == 1 and not any(stage.get('valgrind') for stage in plan['stages'])
  # Actual native17 driver searches cwd/compiler/self_hosted/stdlib; VKF_HOME is insufficient.
  compile_stages[0]['cwd'] = str(out/'home')
  plan['directories']=[str(x) for x in sorted(out.rglob('*')) if x.is_dir() and not x.is_symlink()]
  plan['symlinks']=[dict(path=str(x),target=str(x.resolve()),sha256=sha(x)) for x in sorted(out.rglob('*')) if x.is_symlink()]
  merged={x['path']:x for x in plan['inputs']+extra+origins+plan['application_inputs']}
  plan['inputs']=list(merged.values());save(out/'plan.json',plan)
  counts.append(dict(selection=selection,cases=len(plan['cases']),stages=len(plan['stages']),modules=sum(len(c['modules']) for c in plan['cases']),source_bytes=sum(Path(x['path']).stat().st_size for x in plan['generated']),plan=pin(out/'plan.json')))
 save(HERE/'preparation.json',dict(source_commit=HEAD,phases=counts,seconds=time.monotonic()-started,native_execution=False,admitted=False))
 assert p.current_head()==HEAD
 print(json.dumps(counts))
if __name__=='__main__':main()
