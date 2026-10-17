"""Bounded host-only proof: actual normalizer, fake compiler/run, exact installed allocator."""
import ast,copy,difflib,importlib.util,json,os,resource,stat,subprocess,sys,tempfile,time
from pathlib import Path
resource.setrlimit(resource.RLIMIT_AS,(512*2**20,)*2)
resource.setrlimit(resource.RLIMIT_CPU,(50,50));resource.setrlimit(resource.RLIMIT_CORE,(0,0))
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;sys.path.insert(0,str(H));import adapter as a
sys.path.insert(0,str(a.PACKAGE));import prepare as p,payload
start=time.monotonic();seal=a.static_contract();plan=a.load_pin(seal['control_plan']);oldH=H.parent/'metadata-control-preparation-27'
sys.path.insert(0,str(Path(seal['v6_bundle']['controller']['path']).parent));import storage_paths,private_workload
checks=[];children=[]
def check(ok,label):
 assert ok,label
 checks.append(label)
old=a.read(oldH/'staging/metadata/plan.json');moved,assets=a.relocate(old,plan['out'])
expected_generated=copy.deepcopy(moved['generated'])
for item in expected_generated:
 if item['path'].endswith('/metadata/raw/metadata.vkf'):item['sha256']=a.digest(Path(item['path']).read_bytes())
check(expected_generated==plan['generated'],'only repaired metadata raw generated pin differs after relocation')
check(moved['cases']==plan['cases'],'all original module and assertion counts retained')
expected=copy.deepcopy(moved['stages']);expected[1]['cwd']=str(Path(plan['out'])/'home')
check(expected==plan['stages'],'only compile cwd differs; all original stage argv/timeouts/oracles unchanged')
check(plan['compiler_receipt']==old['compiler_receipt'],'actual native17 receipt unchanged')
check((H/'compiler-receipt.snapshot.json').read_bytes()==Path(a.read(H/'native-authentication.json')['actual_inputs'][0]['path']).read_bytes(),'snapshot byte-identical to actual compiler receipt')
check(plan['application_inputs']==old['application_inputs'],'fresh current metadata closure unchanged by applied API/selection/package source')
check(plan['symlinks']==moved['symlinks'],'exact original stdlib membership and source pins retained')
root=p.REPAIR/'regressions/metadata_actual_lengths.vkf'
original=root.read_bytes();repaired=(Path(plan['out'])/'metadata/raw/metadata.vkf').read_bytes()
check(repaired==original[:-5]+b'::true\n','exact two-colon delta after all original fixture bytes')
assertions=[x for x in original.splitlines(keepends=True) if b'?!' in x]
check(len(assertions)==6 and assertions==[x for x in repaired.splitlines(keepends=True) if b'?!' in x],'six exact assertion lines and newline bytes in original order')
check(repaired.count(b'::true')==1 and repaired.endswith(b'\n::true\n') and repaired.rfind(b'?!')<repaired.rfind(b'::true'),'single explicit output strictly after original six assertions')
check(repaired==(H.parent/'metadata-entry-repair-31/metadata_actual_lengths.vkf').read_bytes(),'integrated repair31 exact fixture')
texts,pins=p.closure({'metadata':repaired.decode()})
check(sorted(texts)==plan['cases'][0]['modules'] and list(pins.values())==plan['application_inputs'],'fresh traversal of actual current application imports')
for name,text in texts.items():check((Path(plan['out'])/'metadata/raw'/(name+'.vkf')).read_text()==text,'current source exact '+name)
# Broader geometry/provenance/absence/ordered-tree/binary64 contracts are preserved,
# but this focused length regression is NOT a replacement or qualification for them.
paths=['examples/gpu-math/tests/document-text.test.mjs','examples/gpu-math/native-vkf/typed_packet_reference_harness_tests.vkf','examples/gpu-math/native-vkf/test_ordered_json.vkf','examples/gpu-math/native-vkf/scene_metadata_regression_tests.vkf','examples/gpu-math/native-vkf/scene_metadata_edit_regression_tests.vkf','examples/gpu-math/native-vkf/scene_metadata_export_regression_tests.vkf']
contract_pins=[]
for relative in paths:
 path=a.REPO/relative
 child=subprocess.Popen(['/usr/bin/git','-C',str(a.REPO),'show',old['application_head_at_preparation']+':'+relative],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 before,err=child.communicate(timeout=5);children.append(dict(pid=child.pid,exit=child.returncode,joined=True,absent=not Path('/proc',str(child.pid)).exists()))
 check(child.returncode==0 and path.read_bytes()==before,'original broader contract unchanged '+relative)
 contract_pins.append(a.pin(path))
check((a.REPO/'examples/gpu-math/native-vkf/test_ordered_json.vkf').read_bytes()==(H.parent/'serialization-boundary-04/candidate/test_ordered_json.vkf').read_bytes(),'independent ordered JSON/binary64 candidate preserved exactly')
# Authenticate the actual linked driver source, without executing the ELF.
profile=Path('/home/viktor/.cache/vkf-s0-runtimes-20261012/Integrator/independent-worker-F/iteration303-compose01/native-profile.json')
assert profile.stat().st_size<64*2**20
prof=json.loads(profile.read_bytes());driver=next(r for r in prof['drivers'] if r['label']=='driver-0')
source=next(r for r in driver['dependencies'] if r['effective'].endswith('/vkf_driver_artifact_smoke.cpp'))
sourcepin=dict(path=source['effective'],sha256=source['sha256']);a.verify(sourcepin);a.verify(driver['object']);a.verify(driver['actual_MD'])
check(driver['object'] in a.load_pin(plan['compiler_receipt']['results'])[2]['actual_dependencies'],'driver object is in actual native17 linker dependencies')
drivertext=Path(source['effective']).read_text()
for term in ['resolve_dot_module(', 'std::filesystem::absolute(importing_source).parent_path() / relative', 'directory / "compiler" / "self_hosted" / "stdlib" / relative', 'std::filesystem::current_path() /\n        "compiler" / "self_hosted" / "stdlib" / relative','const auto installed = bundled_stdlib_root / relative;', 'compiler.parent_path() / ".vkfbuild" / "stdlib-cache"']:
 check(term in drivertext,'driver branch '+term)
check('VKF_HOME' not in drivertext,'actual driver does not use VKF_HOME')
def resolve(source,module,cwd,compiler):
 relative=Path(*module.split('.')).with_suffix('.vkf');directory=source.absolute().parent
 candidates=[directory/relative]+[x/'compiler/self_hosted/stdlib'/relative for x in (directory,*directory.parents)]+[cwd/'compiler/self_hosted/stdlib'/relative,compiler.parent.parent/'compiler/self_hosted/stdlib'/relative]
 return next((x.resolve() for x in candidates if x.is_file()),None)
oldtree=ast.parse((oldH/'adapter.py').read_text());newtree=ast.parse((H/'adapter.py').read_text())
fn=lambda tree,name:next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name==name)
for name in ('acquire_runtime_lock','validate_runtime','run','protected_inputs','relocate'):
 check(ast.dump(fn(oldtree,name))==ast.dump(fn(newtree,name)),'accepted binding23 '+name+' AST unchanged')
# Materializer has only a diagnostic string phase rename.
before=ast.get_source_segment((oldH/'adapter.py').read_text(),fn(oldtree,'materialize')).replace('D288','metadata')
check(ast.dump(ast.parse(before).body[0])==ast.dump(fn(newtree,'materialize')),'accepted regular stdlib materializer unchanged')
allocation=[];resolver_rows=[]
with tempfile.TemporaryDirectory(prefix='TEST_ONLY_full_tree_',dir=H) as tmp:
 t=Path(tmp);q,assets=a.relocate(plan,t/'metadata');refs=[]
 for i,(target,data) in enumerate(assets):
  path=t/f'asset-{i}';path.write_bytes(data);refs.append(dict(source=a.pin(path),target=target))
 a.save(t/'plan.json',q);a.materialize(q,refs,a.pin(t/'plan.json'),Path(q['out']))
 def allocated(label):
  value=storage_paths.allocated(Path(q['out']));check(value<a.DISK,'entire installed allocated '+label)
  for x in Path(q['out']).rglob('*'):
   st=x.lstat();assert stat.S_ISREG(st.st_mode) or stat.S_ISDIR(st.st_mode)
   if stat.S_ISREG(st.st_mode):assert st.st_nlink==1
  allocation.append(dict(label=label,bytes=value));return value
 allocated('materialized')
 copies=[dict(path=x['path'],bytes=Path(x['path']).stat().st_size,allocated=Path(x['path']).stat().st_blocks*512) for x in q['symlinks']]
 seen=[]
 def fake(stage):
  seen.append(stage['name']);allocated('before '+stage['name'])
  if stage['name'].endswith('-normalize'):
   child=subprocess.Popen(stage['argv'],cwd=q['out'],env=payload.environment(Path(q['out']),q),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
   out,err=child.communicate(timeout=10);children.append(dict(pid=child.pid,exit=child.returncode,joined=True,absent=not Path('/proc',str(child.pid)).exists()))
   check(child.returncode==0,'exact original Python normalizer succeeds')
   normalized=Path(q['out'])/'metadata/normalized/source'
   for name in ('metadata.vkf','scene_metadata.vkf','text_chunks.vkf'):
    baseline=(H.parent/'metadata-entry-repair-31/host-original/metadata/normalized/source'/name).read_bytes()
    expected=baseline[:-5]+b'::true\n' if name=='metadata.vkf' else baseline
    check((normalized/name).read_bytes()==expected,'actual normalization exact repaired delta '+name)
   check([x for x in (normalized/'metadata.vkf').read_bytes().splitlines(keepends=True) if b'?!' in x]==assertions,'normalized six assertion bytes unchanged')
  else:out=stage.get('stdout','');err=''
  if stage['name'].endswith('-compile'):
   src=Path(stage['argv'][stage['argv'].index('-b')+1]);cwd=Path(stage['cwd']);check(src.is_file(),'real normalized compiler source exists')
   for module in ('io','errors'):
    target=cwd/'compiler/self_hosted/stdlib'/(module+'.vkf');actual=resolve(src,module,cwd,Path(stage['argv'][0]))
    check(actual==target and target.is_file() and not target.is_symlink(),'real driver lookup reaches regular '+module)
    row=next(x for x in q['symlinks'] if x['path']==str(target));a.verify(dict(path=str(target),sha256=row['sha256']))
    resolver_rows.append(dict(module=module,sha256=row['sha256'],target=str(target.relative_to(q['out']))))
  for output in stage['outputs']:Path(output).write_bytes(b'TEST_ONLY fake compiler output; not executable\n')
  allocated('after '+stage['name'])
  return 0,out,err,dict(no_live_descendants=True,remaining_identities=[])
 payload.execute(q,dict(timeout_seconds=20,disk_bytes=a.DISK),run_override=fake)
 check(seen==[s['name'] for s in q['stages']],'three original stages visited in order')
 check(a.read(Path(q['out'])/'execution-summary.json')['native_execution'] is False,'synthetic compiler/run evidence cannot be native')
 allocated('retained outputs/logs')
 for ref in q['generated']+q['inputs']:a.verify(ref)
 for key,value in payload.environment(Path(q['out']),q).items():
  if key in ('HOME','TMPDIR','TMP','TEMP','XDG_CACHE_HOME','CLANG_MODULE_CACHE_PATH','VKF_HOME'):check(Path(value).is_relative_to(q['out']),'charged environment '+key)
check(not list(H.glob('TEST_ONLY_*')),'temporary trees removed')
inputs=a.unique(seal['pins']+a.controller_inputs(plan['inputs']))
policy=a.load_pin(seal['a_policy']);target=policy['root']['path']+'/TEST_ONLY_NOT_CREATED'
argv=private_workload.command(dict(inputs=inputs,argv=[seal['python']['path']],attempt_root=target,cwd=target),{})
check([argv[i+1:i+3] for i,x in enumerate(argv) if x=='--bind']==[[target,target]],'only new attempt rw in real namespace constructor')
check(['/mnt','/mnt'] in [argv[i+1:i+3] for i,x in enumerate(argv) if x=='--ro-bind'],'previous compiler under read-only mnt')
for ref in inputs:storage_paths.pinned(ref)
check(all(x['joined'] and x['absent'] and x['exit']==0 for x in children),'all ordinary host children joined and absent')
check(a.current_head()==seal['source_commit'],'current HEAD held')
report=dict(passed=True,TEST_ONLY=True,checks=checks,seconds=time.monotonic()-start,children=children,all_children_joined=True,native_execution=False,actual_python_normalizer=True,compiler_and_run_synthetic=True,allocation=allocation,stdlib_copies=copies,resolver=resolver_rows,driver=dict(profile=a.pin(profile),source=sourcepin,object=driver['object'],MD=driver['actual_MD']),preserved_broader_contract_pins=contract_pins,broader_contracts_native_unqualified=True,runtime_inputs_verified=len(inputs),memory=[s for s in Path('/proc/self/status').read_text().splitlines() if s.startswith(('VmPeak:','VmHWM:'))])
a.save(H/'packet-verification.json',report)
print(json.dumps({k:v for k,v in report.items() if k not in ('checks','stdlib_copies','driver','preserved_broader_contract_pins','resolver')}))
