"""TEST_ONLY ordinary processes and temporary files; no live locks or services."""
import ast
import copy
import errno
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import tempfile
import time
import types
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
V9=Path('/home/viktor/Projects/Vektor Flow/.coordination/s0-plan-20261012/synchronized-contexts/independent-workers/storage20gb/storage-direct-v9')
resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2))
resource.setrlimit(resource.RLIMIT_CPU,(40,40))
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
sys.dont_write_bytecode=True
sys.path.insert(0,str(HERE))
import adapter as a

# Reuse review10 fixtures in memory. Redirect ALL temporary files to own output;
# import exact installed v9 transaction/guard bodies, never construct a Controller.
src=BASE/'compiler-adapter-review-10/test_integration.py'
code=src.read_text().replace("HERE = Path(__file__).resolve().parent",'HERE = '+repr(str(HERE))+'; HERE = Path(HERE)')
code=code.replace("storage-direct-v6')","storage-direct-v9')")
legacy=types.ModuleType('TEST_ONLY_inherited10');legacy.__file__=str(src)
sys.modules[legacy.__name__]=legacy
exec(compile(code,str(src),'exec'),legacy.__dict__)
legacy.a=a
# Default arguments in inherited fixture methods retain their module object;
# that object is the same own proposal bytes and must receive the same patches.
a=legacy.Tests.runtime.__defaults__[1]
children=[]
observations=[]

class LockTests(legacy.Tests):
    # Do not collect inherited whole historical suite; select relevant checks below.
    def holder(self,path,seconds):
        code='import fcntl,sys,time; f=open(sys.argv[1],"r+b"); fcntl.flock(f,fcntl.LOCK_EX); print("held",flush=True); time.sleep(float(sys.argv[2]))'
        child=subprocess.Popen([sys.executable,'-I','-B','-c',code,str(path),str(seconds)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True)
        self.addCleanup(self.join_child,child)
        self.assertEqual(child.stdout.readline().strip(),'held')
        return child

    def join_child(self,child):
        if child.poll() is None: child.terminate()
        stdout,stderr=child.communicate(timeout=4)
        children.append(dict(pid=child.pid,returncode=child.returncode,joined=True,stderr=stderr))
        self.assertFalse(Path('/proc',str(child.pid)).exists())

    def test_transient_full_run(self):
        original=a.acquire_runtime_lock; captured=[]; elapsed=[]
        def acquire(lock,deadline):
            captured.append(lock);self.holder(lock.name,.25)
            with self.assertRaises(BlockingIOError):fcntl.flock(lock,fcntl.LOCK_SH|fcntl.LOCK_NB)
            start=time.monotonic();original(lock,deadline);elapsed.append(time.monotonic()-start)
        with patch.object(a,'acquire_runtime_lock',side_effect=acquire):
            self.runtime()
        self.assertTrue(captured[0].closed)
        self.assertGreaterEqual(elapsed[0],.20)
        observations.append(dict(case='real EX transient full adapter + eight TEST_ONLY stages',wait_seconds=elapsed[0]))

    def test_persistent_no_snapshot_no_materialization(self):
        original=a.acquire_runtime_lock; captured=[]; pins=[]; pin=a.pin
        def record(path):
            pins.append(str(path));return pin(path)
        def acquire(lock,deadline):
            captured.append(lock);self.holder(lock.name,2)
            original(lock,min(deadline,time.monotonic()+.12))
        start=time.monotonic()
        with patch.object(a,'acquire_runtime_lock',side_effect=acquire),patch.object(a,'pin',side_effect=record):
            with self.assertRaisesRegex(TimeoutError,'no snapshot/materialization'):
                self.runtime()
        self.assertLess(time.monotonic()-start,1.5)
        self.assertTrue(captured[0].closed)
        self.assertNotIn(str(self.root/'TEST_ONLY-state.json'),pins)
        self.assertFalse((self.root/'TEST_ONLY-unenrolled-root/TEST_ONLY_attempt/compiler').exists())
        observations.append(dict(case='persistent contention bounded failure',seconds=time.monotonic()-start))

    def test_unexpected_errno_propagates_closes_no_materialization(self):
        original=a.acquire_runtime_lock; captured=[]
        error=OSError(errno.EIO,'TEST_ONLY unexpected IO')
        def acquire(lock,deadline):
            captured.append(lock)
            with patch.object(a.fcntl,'flock',side_effect=error):original(lock,deadline)
        with patch.object(a,'acquire_runtime_lock',side_effect=acquire):
            with self.assertRaises(OSError) as got:self.runtime()
        self.assertIs(got.exception,error);self.assertTrue(captured[0].closed)
        self.assertFalse((self.root/'TEST_ONLY-unenrolled-root/TEST_ONLY_attempt/compiler').exists())

    def test_successful_flock_after_deadline_rejected_and_closed(self):
        p=self.root/'TEST_ONLY-lock';p.touch()
        with p.open('rb') as lock:
            with patch.object(a.time,'monotonic',side_effect=[0,0,2]):
                with self.assertRaisesRegex(ValueError,'after deadline'):a.acquire_runtime_lock(lock,1)
        self.assertTrue(lock.closed)
        with p.open('r+b') as fd:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)

    def test_precheck_and_materialization_time_deducted(self):
        offset=[0.0];real_clock=time.monotonic;real_load=a.load_pin;real_raw=a.raw
        def load(pin):
            result=real_load(pin)
            if Path(pin['path']).name=='contract.json':offset[0]+=25
            return result
        def raw(path,*args):
            result=real_raw(path,*args)
            if Path(path).name.startswith('asset-'):offset[0]+=5
            return result
        real_execute=legacy.payload.execute
        def execute(plan,binding,run_override=None):
            self.assertLess(binding['timeout_seconds'],1170)
            self.assertGreater(binding['timeout_seconds'],1100)
            observations.append(dict(case='precheck and materialization budget deduction',seconds=binding['timeout_seconds'],injected_elapsed=offset[0]))
            return real_execute(plan,binding,run_override=run_override)
        with patch.object(a.time,'monotonic',side_effect=lambda:real_clock()+offset[0]),patch.object(a,'load_pin',side_effect=load),patch.object(a,'raw',side_effect=raw),patch.object(legacy.payload,'execute',side_effect=execute):
            self.runtime()

    def test_exhausted_precheck_no_materialization(self):
        offset=[0.0];real_clock=time.monotonic;real_load=a.load_pin
        def load(pin):
            result=real_load(pin)
            if Path(pin['path']).name=='contract.json':offset[0]+=1201
            return result
        with patch.object(a.time,'monotonic',side_effect=lambda:real_clock()+offset[0]),patch.object(a,'load_pin',side_effect=load):
            with self.assertRaises(TimeoutError):self.runtime()
        self.assertFalse((self.root/'TEST_ONLY-unenrolled-root/TEST_ONLY_attempt/compiler').exists())

    def test_exhausted_materialization_no_payload(self):
        offset=[0.0];real_clock=time.monotonic;real_raw=a.raw
        def raw(path,*args):
            result=real_raw(path,*args)
            if Path(path).name.startswith('asset-'):offset[0]=1201
            return result
        with patch.object(a.time,'monotonic',side_effect=lambda:real_clock()+offset[0]),patch.object(a,'raw',side_effect=raw):
            with self.assertRaisesRegex(ValueError,'deadline before payload'):self.runtime()
        self.assertFalse((self.root/'TEST_ONLY-unenrolled-root/TEST_ONLY_attempt/compiler/execution-started.json').exists())

    def test_replaced_lock_rejected(self):
        p=self.root/'TEST_ONLY-lock';p.touch()
        with p.open('rb') as lock:
            p.unlink();p.touch()
            with self.assertRaisesRegex(ValueError,'lock replaced'):a.acquire_runtime_lock(lock,time.monotonic()+1)
        self.assertTrue(lock.closed)

    def test_expired_deadline_never_flocks(self):
        p=self.root/'TEST_ONLY-lock';p.touch()
        with p.open('rb') as lock,patch.object(a.fcntl,'flock') as flock:
            with self.assertRaises(TimeoutError):a.acquire_runtime_lock(lock,time.monotonic()-1)
            flock.assert_not_called()

    def test_protected_checks_hold_SH_release_before_payload_reduced_budget(self):
        real=a.validate_runtime; checks=[];captured=[]
        real_acquire=a.acquire_runtime_lock
        def acquire(lock,deadline):
            captured.append(lock);self.holder(lock.name,.20);real_acquire(lock,deadline)
        def validate(*args):
            p=Path(args[1]['lock_path'])
            with p.open('r+b') as fd:
                with self.assertRaises(BlockingIOError):fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            checks.append(True);return real(*args)
        real_execute=legacy.payload.execute
        def execute(plan,binding,run_override=None):
            self.assertTrue(captured[0].closed)
            self.assertGreater(binding['timeout_seconds'],0)
            self.assertLess(binding['timeout_seconds'],1199.85)
            observations.append(dict(case='remaining payload budget',seconds=binding['timeout_seconds']))
            return real_execute(plan,binding,run_override=run_override)
        with patch.object(a,'acquire_runtime_lock',side_effect=acquire),patch.object(a,'validate_runtime',side_effect=validate),patch.object(legacy.payload,'execute',side_effect=execute):
            self.runtime()
        self.assertEqual(checks,[True])

    def test_validation_failure_releases_SH_no_materialization(self):
        captured=[];real=a.acquire_runtime_lock
        def acquire(lock,deadline):captured.append(lock);real(lock,deadline)
        with patch.object(a,'acquire_runtime_lock',side_effect=acquire):
            with self.assertRaisesRegex(ValueError,'publication receipt'):self.runtime(publication=False)
        self.assertTrue(captured[0].closed)
        self.assertFalse((self.root/'TEST_ONLY-unenrolled-root/TEST_ONLY_attempt/compiler').exists())
        with open(captured[0].name,'r+b') as fd:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)

    def test_actual_guard_transaction_wait_owned_TEMP_only(self):
        # Production lock + guard + owned-wait bodies; synthetic state/callbacks
        # avoid all live state, accounting, host/service probes and authority.
        adm=legacy.storage_admission
        self.assertEqual(Path(adm.__file__).parent,V9)
        p=self.root/'TEST_ONLY-lock';p.touch();state=self.root/'TEST_ONLY-state'
        state.write_text(json.dumps(dict(TEST_ONLY=True,lanes={},phases={'TEST_ONLY':{'stage':'running'}})))
        ledger=adm.Ledger(state,p,recovery_pin={'TEST_ONLY':True})
        ledger.released=lambda data:None
        ledger.require_active_target=lambda data,key:None
        ledger.check=lambda data:None
        owned=legacy.load('TEST_ONLY_owned',V9.parent/'owned-processes.py')
        gate=self.root/'TEST_ONLY-ready'
        child_code='''import sys,time,fcntl
from pathlib import Path
sys.path.insert(0,sys.argv[1]);import adapter
p,gate=map(Path,sys.argv[2:4])
while not gate.exists():time.sleep(.005)
t=time.monotonic()
with p.open('rb') as f:
 adapter.acquire_runtime_lock(f,time.monotonic()+1)
 print(time.monotonic()-t,flush=True)
 time.sleep(.04)
'''
        child=subprocess.Popen([sys.executable,'-I','-B','-c',child_code,str(HERE),str(p),str(gate)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True)
        self.addCleanup(self.join_child,child)
        calls=[]
        def authenticate(data,row):
            calls.append(time.monotonic())
            if len(calls)==1:gate.touch();time.sleep(.25)
        def guard():ledger.guard_service('TEST_ONLY',authenticate=authenticate,host=lambda data:(2*adm.GIB,0))
        started=time.monotonic();code,result=owned.wait_owned(child,2,guard=guard)
        stdout,stderr=child.communicate(timeout=3)
        self.assertEqual(code,0,stderr);self.assertFalse(result['timed_out'])
        self.assertTrue(result['no_live_descendants']);self.assertEqual(result['remaining_identities'],[])
        self.assertGreater(float(stdout.strip()),.10)
        observations.append(dict(case='actual v9 guard_service/transaction + owned wait, TEMP synthetic callbacks',seconds=time.monotonic()-started,acquire_seconds=float(stdout.strip()),join=result))

    def test_preserved_code_and_all_state_rejections(self):
        old=ast.parse((BASE/'compiler-runtime-binding-11/adapter.py').read_text());new=ast.parse((HERE/'adapter.py').read_text())
        of={n.name:n for n in old.body if isinstance(n,ast.FunctionDef)};nf={n.name:n for n in new.body if isinstance(n,ast.FunctionDef)}
        for name,node in of.items():
            if name!='run':self.assertEqual(ast.dump(node),ast.dump(nf[name]),name)
        ow=next(n for n in ast.walk(of['run']) if isinstance(n,ast.With))
        nw=next(n for n in ast.walk(nf['run']) if isinstance(n,ast.With))
        self.assertEqual([ast.dump(n) for n in ow.body[1:]],[ast.dump(n) for n in nw.body[1:]])
        sys.modules['adapter']=a
        model=legacy.load('TEST_ONLY_runtime09',BASE/'compiler-controller-preparation-09/test_adapter.py')
        suite=unittest.defaultTestLoader.loadTestsFromTestCase(model.RuntimeContractTests)
        result=unittest.TestResult();suite.run(result)
        self.assertTrue(result.wasSuccessful(),str(result.errors)+str(result.failures))
        observations.append(dict(case='inherited unchanged runtime validation negatives',tests=result.testsRun))

if __name__=='__main__':
    start=time.monotonic()
    names=[n for n in LockTests.__dict__ if n.startswith('test_')]
    # Relevant inherited alias/full plan/oracle and materialization checks.
    names += ['test_02_installed_v6_rejects_original_alias_then_accepts_canonical_pin','test_06_real_plan_all_materialization_parents_and_full_binding','test_08_alias_digest_conflict_rejected']
    result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(LockTests(n) for n in names))
    report=dict(TEST_ONLY=True,successful=result.wasSuccessful(),tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),seconds=time.monotonic()-start,maxrss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,joined_children=children,observations=observations,live_lock_acquisitions=0,native_execution=False)
    (HERE/'test-results.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('observations','joined_children')}))
    raise SystemExit(not result.wasSuccessful())
