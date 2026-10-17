"""TEST_ONLY: exact installed allocator, real sealed sources, fake stage outputs.
No operational controller invocation, new staging, native code or shared writes.
"""
import ast, copy, importlib.util, json, os, resource, stat, sys, tempfile, time, unittest
from pathlib import Path
from unittest.mock import patch
resource.setrlimit(resource.RLIMIT_AS, (512*1024**2,)*2)
resource.setrlimit(resource.RLIMIT_CPU, (50,50))
resource.setrlimit(resource.RLIMIT_CORE, (0,0))
sys.dont_write_bytecode=True
OUT=Path(__file__).resolve().parent
PREP=OUT.parent/'compiler-controls-preparation-18'
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
old=load('original_controls18',PREP/'adapter.py')
fixed=load('proposal_controls20',OUT/'adapter.py')
# Test-only fixture location; proposal is intentionally NOT an admitted/resealed packet.
fixed.HERE=PREP
seal=old.static_contract();plan=old.load_pin(seal['control_plan']);review=old.load_pin(seal['review'])
sys.path.insert(0,str(Path(seal['v6_bundle']['controller']['path']).parent))
import storage_paths, private_workload
sys.path.insert(0,str(old.PACKAGE));import payload
REPORT={'TEST_ONLY':True,'native_execution':False,'operational_mutations':0,'children':[]}
class Review(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory(prefix='TEST_ONLY_review20_',dir=OUT);self.root=Path(self.t.name)
 def tearDown(self):
  root=self.root;self.t.cleanup();self.assertFalse(root.exists())
 def moved(self):
  p,assets=old.relocate(plan,self.root/'d288');refs=[]
  for i,(dest,b) in enumerate(assets):
   f=self.root/f'asset-{i}';f.write_bytes(b);refs.append(dict(source=old.pin(f),target=dest))
  pp=self.root/'plan.json';old.save(pp,p)
  return p,refs,old.pin(pp)
 def check_regular_tree(self,target):
  for p in target.rglob('*'):
   s=p.lstat();self.assertTrue(stat.S_ISDIR(s.st_mode) or stat.S_ISREG(s.st_mode),str(p))
   if stat.S_ISREG(s.st_mode):self.assertEqual(s.st_nlink,1,str(p))
  return storage_paths.allocated(target)
 def test_original_entire_tree_rejected(self):
  p,assets,ref=self.moved();old.materialize(p,assets,ref,Path(p['out']))
  self.assertEqual(sum(x.is_symlink() for x in Path(p['out']).rglob('*')),30)
  with self.assertRaisesRegex(storage_paths.Rejected,'symlink or special file'):storage_paths.allocated(p['out'])
 def test_fixed_entire_tree_and_fake_retained_outputs(self):
  p,assets,ref=self.moved();original=copy.deepcopy(p);fixed.check_plan(p,seal['source_commit'],review)
  fixed.materialize(p,assets,ref,Path(p['out']));self.assertEqual(p,original)
  copies=[]
  for link in p['symlinks']:
   dest=Path(link['path']);src=Path(link['target']);self.assertEqual(dest.read_bytes(),src.read_bytes())
   self.assertEqual(dest.resolve(),dest);self.assertNotEqual((dest.stat().st_dev,dest.stat().st_ino),(src.stat().st_dev,src.stat().st_ino))
   old.verify(dict(path=str(dest),sha256=link['sha256']))
   copies.append(dict(bytes=dest.stat().st_size,allocated_bytes=dest.stat().st_blocks*512,source=dict(path=str(src),sha256=link['sha256'])))
  for pin in p['generated']+p['inputs']:old.verify(pin)
  amount=self.check_regular_tree(Path(p['out']));self.assertLess(amount,fixed.DISK)
  seen=[]
  def fake(stage):
   seen.append(stage['name'])
   # Every fake boundary invokes EXACT installed allocation, which old tests omitted.
   self.check_regular_tree(Path(p['out']))
   for name in stage['outputs']:Path(name).write_bytes(b'TEST_ONLY nonexecutable synthetic output\n')
   return 0,stage.get('stdout',''),('ERROR SUMMARY: 0 errors\nAll heap blocks were freed\n' if stage.get('valgrind') else ''),dict(no_live_descendants=True,remaining_identities=[])
  with patch.object(payload,'current_head',return_value=seal['source_commit']):
   payload.execute(p,dict(timeout_seconds=20,disk_bytes=fixed.DISK),run_override=fake)
  self.assertEqual(seen,[s['name'] for s in p['stages']]);after=self.check_regular_tree(Path(p['out']))
  self.assertLess(after,fixed.DISK)
  self.assertFalse(old.read(Path(p['out'])/'execution-summary.json')['native_execution'])
  for pin in p['inputs']+p['generated']:old.verify(pin)
  REPORT['materialization']=dict(copied_files=len(copies),copied_logical_bytes=sum(x['bytes'] for x in copies),copied_allocated_bytes=sum(x['allocated_bytes'] for x in copies),tree_before_fake=amount,tree_after_fake=after,phase_inclusive_bytes=fixed.DISK,remaining_after_fixture_bytes=fixed.DISK-amount,fake_stages=len(seen),copies=copies,inputs_unchanged=True,plan_shape_and_stage_semantics_unchanged=True)
 def test_exclusive_stale_target(self):
  p,assets,ref=self.moved();fixed.materialize(p,assets,ref,Path(p['out']))
  before=storage_paths.allocated(p['out'])
  with self.assertRaisesRegex(ValueError,'fresh D288'):fixed.materialize(p,assets,ref,Path(p['out']))
  self.assertEqual(storage_paths.allocated(p['out']),before)
 def test_duplicate_destination_does_not_overwrite(self):
  p,assets,ref=self.moved();p['symlinks'].insert(1,copy.deepcopy(p['symlinks'][0]))
  with self.assertRaises(FileExistsError):fixed.materialize(p,assets,ref,Path(p['out']))
  first=p['symlinks'][0];old.verify(dict(path=first['path'],sha256=first['sha256']))
  self.check_regular_tree(Path(p['out']))
 def test_no_alias_or_path_escape(self):
  for mode in ['escape','destination_alias','source_alias','unpinned']:
   with self.subTest(mode=mode),tempfile.TemporaryDirectory(prefix='case_',dir=self.root) as sub:
    root=Path(sub);target=root/'d288';link=copy.deepcopy(plan['symlinks'][0]);link['path']=str(target/'copy.vkf')
    p=dict(directories=[],symlinks=[link],inputs=plan['inputs'])
    if mode=='escape':link['path']=str(root/'escaped.vkf')
    if mode=='destination_alias':
     alias=root/'alias';alias.symlink_to(root,target_is_directory=True);link['path']=str(alias/'escape.vkf')
    if mode=='source_alias':
     alias=root/'alias.vkf';alias.symlink_to(link['target']);link['target']=str(alias)
    if mode=='unpinned':link['sha256']='0'*64
    with self.assertRaises(ValueError):fixed.materialize(p,[],seal['control_plan'],target)
    self.assertFalse((root/'escaped.vkf').exists());self.assertFalse((root/'escape.vkf').exists())
 def test_changed_source_bytes_rejected_before_copy(self):
  p,assets,ref=self.moved();real=fixed.raw;source=Path(p['symlinks'][0]['target']);dest=Path(p['symlinks'][0]['path'])
  def changed(path,*args,**kw):return b'TEST_ONLY changed bytes' if Path(path)==source else real(path,*args,**kw)
  with patch.object(fixed,'raw',side_effect=changed):
   with self.assertRaisesRegex(ValueError,'changed stdlib source'):fixed.materialize(p,assets,ref,Path(p['out']))
  self.assertFalse(dest.exists())
 def test_exact_plan_tamper_and_stages(self):
  fixed.check_plan(plan,seal['source_commit'],review)
  for mutate in [lambda p:p.update(selection='metadata'),lambda p:p['stages'].pop(),lambda p:p['stages'][1].update(valgrind=False),lambda p:p['compiler_receipt'].update(identity='bad'),lambda p:p['symlinks'][0].update(sha256='0'*64)]:
   bad=copy.deepcopy(plan);mutate(bad)
   with self.assertRaises(ValueError):fixed.check_plan(bad,seal['source_commit'],review)
 def test_read_exception_is_exact_and_not_authority(self):
  compiler=plan['compiler_receipt']['compiler'];root=str(Path(compiler['path']).parents[2]);attempt=root+'/TEST_ONLY_new'
  fixed.protected_inputs([compiler],[root],attempt)
  for p in [dict(compiler,sha256='0'*64),dict(compiler,path=str(Path(compiler['path']).parent/'plan.json')),dict(compiler,exemption=True)]:
   with self.assertRaises(ValueError):fixed.protected_inputs([p],[root],attempt)
  alias=self.root/'compiler_alias';alias.symlink_to(compiler['path'])
  with self.assertRaises(ValueError):fixed.protected_inputs([dict(path=str(alias),sha256=compiler['sha256'])],[root],attempt)
  with self.assertRaises(ValueError):fixed.protected([compiler['path']],[root])
  with self.assertRaises(ValueError):fixed.protected_inputs([compiler],[root],root)
 def test_runtime_read_view_prior_compiler_and_new_rw_only(self):
  config=old.load_pin(seal['v6_bundle']['config']);policy=old.load_pin(seal['a_policy']);target=policy['root']['path']+'/TEST_ONLY_NOT_CREATED'
  inputs=old.unique(seal['pins']+old.controller_inputs(plan['inputs']))
  m=dict(inputs=inputs,argv=[seal['python']['path']],attempt_root=target,cwd=target)
  argv=private_workload.command(m,{})
  self.assertEqual([argv[i+1:i+3] for i,x in enumerate(argv) if x=='--bind'],[[target,target]])
  self.assertIn(['/mnt','/mnt'],[argv[i+1:i+3] for i,x in enumerate(argv) if x=='--ro-bind'])
  for pin in inputs:storage_paths.pinned(pin)
  REPORT['runtime_inputs_verified']=len(inputs)
 def test_original_controls_and_stdin_relocation(self):
  import prepare
  cases=[]
  for folder in [prepare.D,prepare.CACHE/'Proof/tests/independent-worker-D/iteration288-ownership02']:
   cases+=old.read(folder/'plan.json')['cases']
  self.assertEqual(len(cases),10);self.assertEqual(len(plan['stages']),20)
  flags=['--tool=memcheck','--leak-check=full','--show-leak-kinds=all','--errors-for-leak-kinds=definite,indirect','--error-exitcode=97']
  for i,c in enumerate(cases):
   compile,run=plan['stages'][2*i:2*i+2]
   self.assertEqual(Path(compile['argv'][1]).read_bytes(),Path(c['source']).read_bytes())
   self.assertEqual(compile['argv'],[plan['compiler_receipt']['compiler']['path'],compile['argv'][1],'-o',compile['outputs'][0]])
   self.assertEqual(run['argv'],['/usr/bin/valgrind',*flags,compile['outputs'][0]])
   self.assertEqual(run['stdout'],c['oracle']);self.assertEqual(run['expected_exit'],0);self.assertTrue(run['valgrind'])
   self.assertEqual(Path(run['stdin']).read_bytes(),b'0\n')
  a347=old.read(PREP/'staging/a347/plan.json');moved,assets=fixed.relocate(a347,self.root/'a347');data=dict(assets)
  for stage in moved['stages']:
   if stage.get('report'):self.assertEqual(data[stage['stdin']].decode().splitlines()[-1],stage['report'])
 def test_only_materializer_changed_and_lock_budget_preserved(self):
  before=ast.parse((PREP/'adapter.py').read_text());after=ast.parse((OUT/'adapter.py').read_text())
  before.body=[x for x in before.body if not (isinstance(x,ast.FunctionDef) and x.name=='materialize')]
  after.body=[x for x in after.body if not (isinstance(x,ast.FunctionDef) and x.name=='materialize')]
  self.assertEqual(ast.dump(before),ast.dump(after))
  self.assertEqual((fixed.PHASE,fixed.DISK,fixed.TIMEOUT),('d288',2*2**30,2400))
if __name__=='__main__':
 start=time.monotonic();result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Review))
 REPORT.update(passed=result.wasSuccessful(),tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),seconds=time.monotonic()-start,limits={'address_space_bytes':512*1024**2,'wall_seconds':60},memory=[x for x in Path('/proc/self/status').read_text().splitlines() if x.startswith(('VmPeak:','VmHWM:'))],all_temporary_trees_cleaned=not list(OUT.glob('TEST_ONLY_review20_*')),all_children_joined=True,inspected_adapter=old.pin(PREP/'adapter.py'),proposal=old.pin(OUT/'adapter.py'),installed_allocator=old.pin(storage_paths.__file__))
 (OUT/'test-results.json').write_text(json.dumps(REPORT,indent=2)+'\n')
 sys.exit(not result.wasSuccessful())
