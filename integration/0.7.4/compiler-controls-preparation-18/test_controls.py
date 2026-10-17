"""Bounded TEST_ONLY host verification. Never acquires live lock or launches native."""
import ast,copy,errno,fcntl,importlib.util,json,os,resource,subprocess,sys,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;sys.path.insert(0,str(H))
import adapter as a
sys.path.insert(0,str(a.PACKAGE));import payload
resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,)*2);resource.setrlimit(resource.RLIMIT_CPU,(45,45));resource.setrlimit(resource.RLIMIT_CORE,(0,0))
CHILDREN=[]
class Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.seal=a.static_contract();cls.plan=a.load_pin(cls.seal['control_plan']);cls.review=a.load_pin(cls.seal['review'])
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(prefix='TEST_ONLY_',dir=H);self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
 def moved(self):
  p,assets=a.relocate(self.plan,self.root/'d288');refs=[]
  for i,(dest,b) in enumerate(assets):
   f=self.root/f'asset-{i}';f.write_bytes(b);refs.append(dict(source=a.pin(f),target=dest))
  a.save(self.root/'plan.json',p);return p,refs,a.pin(self.root/'plan.json')
 def test_exact_plan_and_relocation(self):
  a.check_plan(self.plan,a.current_head(),self.review)
  p,assets,ref=self.moved();a.check_plan(p,a.current_head(),self.review)
  a.materialize(p,assets,ref,Path(p['out']))
  for item in p['generated']:a.verify(item)
  for link in p['symlinks']:self.assertEqual(Path(link['path']).resolve(),Path(link['target']))
  back,_=a.relocate(p,self.plan['out']);self.assertEqual(back,self.plan)
  self.assertTrue(all(not Path(s['outputs'][0]).exists() for s in p['stages'] if s['outputs']))
 def test_all_phase_assets_and_A347_report_relocation(self):
  for phase in ('metadata','a345','f364','a347','full-app'):
   original=a.read(H/'staging'/phase/'plan.json');p,assets=a.relocate(original,self.root/phase)
   data=dict(assets)
   for stage in p['stages']:
    if stage.get('report'):
     self.assertEqual(data[stage['stdin']].decode().splitlines()[-1],stage['report'])
   self.assertEqual(len(p['stages']),len(original['stages']))
   for item in p['generated']:self.assertEqual(a.digest(data[item['path']]),item['sha256'])
   with self.assertRaisesRegex(ValueError,'D288 phase only'):a.check_plan(p,a.current_head(),self.review)
 def test_full_plan_tampering_rejected(self):
  mutations=[lambda x:x.update(selection='metadata'),lambda x:x.update(kind='compiler'),lambda x:x['stages'].pop(),lambda x:x['stages'][1].update(stdout='false\n'),lambda x:x['stages'][1].update(valgrind=False),lambda x:x['stages'][0]['argv'].append('--relax'),lambda x:x['compiler_receipt'].update(identity='bad'),lambda x:x['generated'].pop(),lambda x:x['symlinks'].pop(),lambda x:x.update(application_head_at_preparation='stale')]
  for mutation in mutations:
   p=copy.deepcopy(self.plan);mutation(p)
   with self.assertRaises(ValueError):a.check_plan(p,a.current_head(),self.review)
 def test_null_authority_cannot_assemble(self):
  dest=H/'TEST_ONLY_no_packet'
  with self.assertRaisesRegex(ValueError,'actual root execution decision'):a.assemble(self.seal['control_plan']['path'],H/'root-inputs.REQUIRED.json',dest)
  self.assertFalse(dest.exists())
 def test_phase_budget_request_rejection_before_receipt_reads(self):
  r=dict(coordinator=a.COORDINATOR,native_execution=True,worker='A',phase='compiler',ram_bytes=8*a.GIB,disk_bytes=a.DISK,timeout_seconds=a.TIMEOUT)
  with self.assertRaisesRegex(ValueError,'D288'):a.evidence(r,self.seal)
  r.update(phase='d288',disk_bytes=a.GIB)
  with self.assertRaisesRegex(ValueError,'D288'):a.evidence(r,self.seal)
 def test_previous_ELF_only_read_exception(self):
  compiler=self.plan['compiler_receipt']['compiler'];oldroot=str(Path(compiler['path']).parents[2]);target=oldroot+'/TEST_ONLY_future'
  a.protected_inputs([compiler],[oldroot],target)
  for p in [dict(compiler,sha256='0'*64),dict(compiler,path=str(Path(compiler['path']).parent/'plan.json'))]:
   with self.assertRaises(ValueError):a.protected_inputs([p],[oldroot],target)
  with self.assertRaises(ValueError):a.protected_inputs([compiler],[oldroot],oldroot)
  with self.assertRaises(ValueError):a.protected([compiler['path']],[oldroot])
 def test_no_materialization_path_escape_or_stale_target(self):
  p,assets,ref=self.moved();p['directories'].append(str(self.root/'escape'))
  with self.assertRaises(ValueError):a.materialize(p,assets,ref,Path(p['out']))
  self.assertFalse((self.root/'escape').exists())
  with self.assertRaises(ValueError):a.materialize(p,assets,ref,Path(p['out']))
 def test_all_twenty_fake_stages_join_and_original_oracles(self):
  p,assets,ref=self.moved();a.materialize(p,assets,ref,Path(p['out']));seen=[]
  def fake(s):
   seen.append(s['name'])
   for path in s['outputs']:Path(path).write_text('TEST_ONLY synthetic output; not executable')
   return 0,s.get('stdout',''),'ERROR SUMMARY: 0 errors\nAll heap blocks were freed\n' if s.get('valgrind') else '',dict(no_live_descendants=True,remaining_identities=[])
  payload.execute(p,dict(timeout_seconds=20,disk_bytes=100*2**20),run_override=fake)
  self.assertEqual(seen,[s['name'] for s in p['stages']]);self.assertFalse(a.read(Path(p['out'])/'execution-summary.json')['native_execution'])
  self.assertFalse((Path(p['out'])/'compiler-receipt.json').exists())
 def test_first_failure_stops_and_retains_join(self):
  p,assets,ref=self.moved();a.materialize(p,assets,ref,Path(p['out']));seen=[]
  def fake(s):
   seen.append(s['name'])
   for path in s['outputs']:Path(path).write_text('TEST_ONLY')
   return (0,'wrong\n','',dict(no_live_descendants=True,remaining_identities=[]))
  with self.assertRaises(ValueError):payload.execute(p,dict(timeout_seconds=20,disk_bytes=100*2**20),run_override=fake)
  self.assertEqual(len(seen),2);self.assertTrue(a.read(Path(p['out'])/'results.json')[-1]['join']['no_live_descendants'])
 def test_original_valgrind_and_payload_phase_checks(self):
  s=self.plan['stages'][1]
  for code,out,err in [(97,'true\n',''),(0,'true\n','ERROR SUMMARY: 1 errors\nAll heap blocks were freed'),(0,'true\n','ERROR SUMMARY: 0 errors'),(0,'false\n','ERROR SUMMARY: 0 errors\nAll heap blocks were freed')]:
   with self.assertRaises(ValueError):payload.check_result(s,code,out,err)
  # Pure validation rejects phase before requiring any authority files.
  admission=dict(coordinator=a.COORDINATOR,plan=self.seal['control_plan'],charged_attempt=self.plan['out'],native_execution=True,environment_qualified=True,phase='compiler')
  with self.assertRaisesRegex(ValueError,'wrong phase'):payload.validate_admission(self.plan,admission,self.seal['control_plan'])
 def test_repaired_lock_exact_AST_and_locked_validation_preserved(self):
  old=ast.parse((H.parent/'compiler-runtime-binding-16/adapter.py').read_text());new=ast.parse((H/'adapter.py').read_text())
  fn=lambda t,n:next(x for x in t.body if isinstance(x,ast.FunctionDef) and x.name==n)
  self.assertEqual(ast.dump(fn(old,'acquire_runtime_lock')),ast.dump(fn(new,'acquire_runtime_lock')))
  # Only phase budget constants change in pure runtime validation.
  original=ast.get_source_segment((H.parent/'compiler-runtime-binding-16/adapter.py').read_text(),fn(old,'validate_runtime'))
  expected=original.replace("g['phase_bytes'] == GIB","g['phase_bytes'] == DISK").replace("g['timeout_seconds'] == 1200 and g['phase_scope'] == 'compiler'","g['timeout_seconds'] == TIMEOUT and g['phase_scope'] == PHASE").replace("row['phase_bytes'] == GIB","row['phase_bytes'] == DISK")
  self.assertEqual(ast.dump(ast.parse(expected).body[0]),ast.dump(fn(new,'validate_runtime')))
  run=fn(new,'run');lock=next(x for x in ast.walk(run) if isinstance(x,ast.With))
  calls=[x.func.attr if isinstance(x.func,ast.Attribute) else x.func.id for x in ast.walk(lock) if isinstance(x,ast.Call) and isinstance(x.func,(ast.Name,ast.Attribute))]
  self.assertIn('validate_runtime',calls);self.assertIn('validate_admission',calls);self.assertNotIn('materialize',calls);self.assertNotIn('execute',calls)
  text=ast.unparse(run);self.assertIn('deadline = time.monotonic() + TIMEOUT',text);self.assertIn('remaining = deadline - time.monotonic()',text);self.assertIn('timeout_seconds=remaining',text)
 def test_bounded_lock_contention_and_release(self):
  f=self.root/'TEST_ONLY_capacity.lock';f.touch()
  child=subprocess.Popen([sys.executable,'-I','-B','-c','import fcntl,sys,time; f=open(sys.argv[1],"rb"); fcntl.flock(f,fcntl.LOCK_EX); print("held",flush=True); time.sleep(.3)',str(f)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
  try:
   self.assertEqual(child.stdout.readline().strip(),'held')
   with f.open('rb') as fd:
    with self.assertRaises(TimeoutError):a.acquire_runtime_lock(fd,time.monotonic()+.05)
   with f.open('rb') as fd:a.acquire_runtime_lock(fd,time.monotonic()+1)
  finally:
   out,err=child.communicate(timeout=3);CHILDREN.append(dict(pid=child.pid,exit=child.returncode,joined=True,absent=not Path('/proc',str(child.pid)).exists()))
  self.assertEqual(child.returncode,0)
  with f.open('rb') as fd:
   with patch.object(a.fcntl,'flock',side_effect=OSError(errno.EIO,'TEST_ONLY')):
    with self.assertRaises(OSError):a.acquire_runtime_lock(fd,time.monotonic()+1)
 def test_successor_exact_native17_only(self):
  s=(H/'root_steps.py').read_text();self.assertIn("key=='A:compiler-native17-01' and row['sequence']==13",s);self.assertIn("d['iteration']>26",s);self.assertIn('59a64d4dd9c467d71de4264ddf2c3f6fe8d62763ef9809c16f5ec56aef95b150',s);self.assertNotIn('compiler-native13-01',s)
if __name__=='__main__':
 start=time.monotonic();result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
 (H/'test-results.json').write_bytes(a.encoded(dict(TEST_ONLY=True,passed=result.wasSuccessful(),tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),seconds=time.monotonic()-start,children=CHILDREN,native_execution=False,operational_mutations=0,memory=[x for x in Path('/proc/self/status').read_text().splitlines() if x.startswith(('VmHWM:','VmPeak:'))])))
 sys.exit(not result.wasSuccessful())
