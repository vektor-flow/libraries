"""Bounded host-only proof of the exact generator delta and resolver path wiring."""
import ast,copy,importlib.util,json,resource,sys,tempfile,time
from unittest.mock import patch
from pathlib import Path
resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,)*2);resource.setrlimit(resource.RLIMIT_CORE,(0,0))
sys.dont_write_bytecode=True
OUT=Path(__file__).resolve().parent;PREP=OUT.parent/'compiler-controls-preparation-18'
spec=importlib.util.spec_from_file_location('review20_materializer',OUT/'adapter.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a);a.HERE=PREP
seal=a.static_contract();before=a.load_pin(seal['control_plan']);start=time.monotonic()
sys.path.insert(0,str(Path(seal['v6_bundle']['controller']['path']).parent));import storage_paths
# Execute ONLY the exact added conditional from the proposed generator, never main().
old=ast.parse((PREP/'build_packet.py').read_text());new=ast.parse((OUT/'build_packet.py').read_text())
main=lambda t:next(x for x in t.body if isinstance(x,ast.FunctionDef) and x.name=='main')
loop=lambda t:next(x for x in main(t).body if isinstance(x,ast.For) and isinstance(x.target,ast.Name) and x.target.id=='selection')
conditional=next(x for x in loop(new).body if isinstance(x,ast.If))
code=compile(ast.fix_missing_locations(ast.Module(body=[conditional],type_ignores=[])),'TEST_ONLY_exact_generator_delta','exec')
loop(new).body.remove(conditional);assert ast.dump(old)==ast.dump(new),'unexpected generator change'
def transform(plan,selection):
 result=copy.deepcopy(plan);exec(code,dict(plan=result,selection=selection,out=Path(result['out'])));return result

def differences(x,y,path=()):
 if isinstance(x,dict) and isinstance(y,dict):
  assert x.keys()==y.keys();return sum((differences(x[k],y[k],path+(k,)) for k in x),[])
 if isinstance(x,list) and isinstance(y,list):
  if path[-1:] == ('argv',) and len(y)==len(x)+1:
   assert y[0]==x[0]=='/usr/bin/valgrind' and y[1]=='--vgdb=no' and y[2:]==x[1:]
   return [dict(path=list(path),before=x,after=y)]
  assert len(x)==len(y);return sum((differences(u,v,path+(i,)) for i,(u,v) in enumerate(zip(x,y))),[])
 return [] if x==y else [dict(path=list(path),before=x,after=y)]
after=transform(before,'d288');diff=differences(before,after)
assert len(diff)==20
assert {tuple(x['path']) for x in diff}=={('stages',i,'cwd') for i in range(0,20,2)}|{('stages',i,'argv') for i in range(1,20,2)}
for item in diff:
 if item['path'][-1]=='cwd':assert item['after']==str(Path(before['out'])/'home')
for phase in ('metadata','a345','f364','a347','full-app'):
 p=a.read(PREP/'staging'/phase/'plan.json');assert transform(p,phase)==p
# Old seal MUST reject changed cwd; next packet needs a newly generated sealed plan.
try:a.check_plan(after,seal['source_commit'],a.load_pin(seal['review']))
except ValueError as e:assert 'complete sealed D288 plan mismatch' in str(e)
else:raise AssertionError('old seal unexpectedly accepted changed plan')
profile=Path('/home/viktor/.cache/vkf-s0-runtimes-20261012/Integrator/independent-worker-F/iteration303-compose01/native-profile.json')
assert profile.stat().st_size < 64*1024**2
prof=json.loads(profile.read_bytes());driver=next(r for r in prof['drivers'] if r['label']=='driver-0')
source=next(p for p in driver['dependencies'] if p['effective'].endswith('/vkf_driver_artifact_smoke.cpp'))
sourcepin=dict(path=source['effective'],sha256=source['sha256']);a.verify(sourcepin);a.verify(driver['object']);a.verify(driver['actual_MD'])
native=a.load_pin(before['compiler_receipt']['results']);assert driver['object'] in native[2]['actual_dependencies']
text=Path(source['effective']).read_text();assert 'VKF_HOME' not in text
for term in ['resolve_dot_module(', 'std::filesystem::absolute(importing_source).parent_path() / relative',
 'directory / "compiler" / "self_hosted" / "stdlib" / relative',
 'std::filesystem::current_path() /\n        "compiler" / "self_hosted" / "stdlib" / relative',
 'const auto installed = bundled_stdlib_root / relative;',
 'stdlib.filename() != "stdlib"', 'compiler.parent_path() / ".vkfbuild" / "stdlib-cache"',
 'std::filesystem::absolute(source).lexically_normal().parent_path() /',
 'const auto requested_output = std::filesystem::absolute(args.output);']:
 assert term in text,term
# Model the four explicit path branches in pinned driver lines2282-2322.
def resolver(importing,module,cwd,compiler):
 relative=Path(*module.split('.')).with_suffix('.vkf');directory=Path(importing).absolute().parent
 paths=[directory/relative]
 for ancestor in (directory,*directory.parents):paths.append(ancestor/'compiler/self_hosted/stdlib'/relative)
 paths.append(Path(cwd)/'compiler/self_hosted/stdlib'/relative)
 paths.append(Path(compiler).parent.parent/'compiler/self_hosted/stdlib'/relative)
 return next((p.resolve() for p in paths if p.is_file()),None)
rows=[]
with tempfile.TemporaryDirectory(prefix='TEST_ONLY_cwd_',dir=OUT) as tmp:
 root=Path(tmp);p,assets=a.relocate(after,root/'d288');refs=[]
 for i,(dest,b) in enumerate(assets):
  f=root/f'asset-{i}';f.write_bytes(b);refs.append(dict(source=a.pin(f),target=dest))
 pp=root/'plan.json';a.save(pp,p);a.materialize(p,refs,a.pin(pp),Path(p['out']))
 bytes_used=storage_paths.allocated(p['out']);assert bytes_used<a.DISK
 for stage in p['stages'][::2]:
  assert stage['cwd']==str(Path(p['out'])/'home')
  sourcepath=Path(stage['argv'][1]);assert sourcepath.is_absolute()
  output=Path(stage['argv'][stage['argv'].index('-o')+1]);assert output.is_absolute() and output.is_relative_to(Path(p['out']))
  for module in ('io','errors'):
   original=resolver(sourcepath,module,sourcepath.parent.parent,stage['argv'][0]);assert original is None
   actual=resolver(sourcepath,module,stage['cwd'],stage['argv'][0]);expected=Path(stage['cwd'])/'compiler/self_hosted/stdlib'/(module+'.vkf')
   assert actual==expected and actual.is_file() and not actual.is_symlink()
   link=next(x for x in p['symlinks'] if x['path']==str(expected));a.verify(dict(path=str(actual),sha256=link['sha256']))
   rows.append(dict(stage=stage['name'],module=module,relative_to_attempt=str(actual.relative_to(p['out'])),sha256=link['sha256'],old_search_result=None))
  # Source-scoped build dirs, output and new stdlib cache all stay charged.
  build=sourcepath.parent/'.vkfbuild'/sourcepath.stem;assert build.is_relative_to(Path(p['out']))
 assert (Path(p['out'])/'home/.vkfbuild/stdlib-cache').is_relative_to(Path(p['out']))
 env_module_path=OUT.parent/'compiler-build-preparation-03';sys.path.insert(0,str(env_module_path));import payload
 env=payload.environment(Path(p['out']),p)
 for key in ('HOME','TMPDIR','TMP','TEMP','XDG_CACHE_HOME','CLANG_MODULE_CACHE_PATH','VKF_HOME'):assert Path(env[key]).is_relative_to(Path(p['out']))
 assert storage_paths.allocated(p['out'])==bytes_used
 seen=[]
 def fake(stage):
  assert storage_paths.allocated(p['out'])<a.DISK
  if stage.get('valgrind'):assert stage['argv'][1]=='--vgdb=no'
  for output in stage['outputs']:Path(output).write_bytes(b'TEST_ONLY not executable\n')
  seen.append(stage['name'])
  return 0,stage.get('stdout',''),('ERROR SUMMARY: 0 errors\nAll heap blocks were freed\n' if stage.get('valgrind') else ''),dict(no_live_descendants=True,remaining_identities=[])
 with patch.object(payload,'current_head',return_value=seal['source_commit']):
  payload.execute(p,dict(timeout_seconds=20,disk_bytes=a.DISK),run_override=fake)
 assert len(seen)==20
 retained_bytes=storage_paths.allocated(p['out']);assert retained_bytes<a.DISK
 for pin in p['inputs']+p['generated']:a.verify(pin)
 assert not any(x.is_symlink() for x in Path(p['out']).rglob('*'))
# Capture exact immutable proof; no transformed operational plan is written.
report=dict(TEST_ONLY=True,passed=True,allowed_differences=diff,only_ten_compile_cwd_and_ten_vgdb_insertions=True,original_memcheck_options_and_oracles_unchanged=True,other_five_phase_plans_unchanged=True,old_seal_rejects_delta=True,new_source_seal_required=True,plan_schema_unchanged=True,source_plan=seal['control_plan'],generator_before=a.pin(PREP/'build_packet.py'),generator_proposal=a.pin(OUT/'build_packet.py'),driver_profile=a.pin(profile),driver_object=driver['object'],driver_MD=driver['actual_MD'],driver_source=sourcepin,resolver_model='Pinned C++ source branch order; no C++ or native execution',resolver_matches=rows,regular_materialized_allocated_bytes=bytes_used,regular_retained_fake_output_bytes=retained_bytes,fake_stages=20,actual_fifo_absence_requires_native_qualification=True,all_temp_cleaned=not list(OUT.glob('TEST_ONLY_cwd_*')),native_execution=False,operational_mutations=0,children=[],all_children_joined=True,seconds=time.monotonic()-start,memory=[x for x in Path('/proc/self/status').read_text().splitlines() if x.startswith(('VmHWM:','VmPeak:'))])
(OUT/'cwd-delta-results.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ('allowed_differences','resolver_matches')}))
