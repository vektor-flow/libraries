"""TEST_ONLY host integration; NEVER authority, never enrolled roots/native/services.
All temporary fixtures are inside this review output. No operational state reads.
Historical input byte hashes are NOT rerun. Actual installed v6 source is imported
for its no-follow reader and attach method; no controller instance is constructed.
"""
import contextlib
import copy
import fcntl
import importlib.util
import json
from pathlib import Path
import resource
import sys
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
BASE = HERE.parent
V6 = Path('/home/viktor/Projects/Vektor Flow/.coordination/s0-plan-20261012/synchronized-contexts/independent-workers/storage20gb/storage-direct-v6')
resource.setrlimit(resource.RLIMIT_AS, (512*1024**2,512*1024**2))
resource.setrlimit(resource.RLIMIT_CPU, (30,30))
resource.setrlimit(resource.RLIMIT_CORE, (0,0))

def load(name, path):
    spec = importlib.util.spec_from_file_location(name,path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

original = load('TEST_ONLY_original_adapter', BASE/'compiler-controller-preparation-09/adapter.py')
a = load('TEST_ONLY_proposed_adapter', HERE/'adapter.py')
sys.path.insert(0,str(V6))
import storage_paths
import storage_admission
sys.path.insert(0,str(BASE/'compiler-build-preparation-03'))
import payload

JOINED_HOST_CHILDREN = []
REAL_PLAN = BASE/'compiler-native-binding-08/root-check01/compiler-preview/plan.json'

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='TEST_ONLY_',dir=HERE)
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root/'TEST_ONLY-NOT-AUTHORITY.txt').write_text('TEST_ONLY; NEVER operational authority; not enrolled.\n')

    def put(self,name,obj):
        p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True)
        p.write_bytes(a.encoded(dict(obj,TEST_ONLY=True)))
        return a.pin(p)

    def fixture(self, mod=a, real_inputs=False):
        # Each simulated authority path includes TEST_ONLY; source_contract is injected
        # only inside this Python test process, with no CLI acceptance bypass.
        source=self.root/'TEST_ONLY-staging';source.mkdir()
        (source/'sources').mkdir()
        candidate=source/'sources/TEST_ONLY.cpp';candidate.write_text('// TEST_ONLY no native compilation\n')
        regression=source/'sources/TEST_ONLY-regression.cpp';regression.write_text('// TEST_ONLY no native compilation\n')
        vfs=source/'TEST_ONLY-vfs.json';vfs.write_bytes(a.encoded({'TEST_ONLY':True,'path':str(candidate)}))
        runtime=self.root/'TEST_ONLY-runtime/libvkf-concurrent-runtime.so';runtime.parent.mkdir();runtime.write_text('TEST_ONLY not an ELF')
        review=dict(a.read(BASE/'compiler-native-binding-08/corrected-review.json'))
        review.update(candidate=a.pin(candidate),regression=a.pin(regression),TEST_ONLY=True)
        rp=self.put('TEST_ONLY-review.json',review)
        stages=[dict(name=n,timeout=t,argv=['TEST_ONLY_NEVER_EXECUTE'],outputs=[]) for n,t in zip(a.STAGES,[180]*5+[30,180,30])]
        stages[5].update(expected_exit='nonzero',stderr_contains='cross-ABI child was preserved')
        stages[7].update(expected_exit=0,stdout=review['candidate_success_stdout'])
        plan=dict(kind='compiler',out=str(source),candidate_review=dict(review,executable=True),
                  executable=True,application_head_at_preparation='TEST_ONLY_HEAD',identity='TEST_ONLY_identity',
                  stages=stages,inputs=[a.pin(runtime)],generated=[a.pin(p) for p in (candidate,regression,vfs)],TEST_ONLY=True)
        # The candidate/review stays outside target; sources get relocated only as generated.
        # Real corrected candidate path is also outside source staging in operational plan.
        for name in ('candidate','regression'):
            p=self.root/('TEST_ONLY-reviewed-'+name+'.cpp');p.write_bytes(Path(review[name]['path']).read_bytes());review[name]=a.pin(p)
        Path(rp['path']).write_bytes(a.encoded(review));rp=a.pin(rp['path']);plan['candidate_review']=dict(review,executable=True)
        dependency=self.root/'TEST_ONLY-dependency';dependency.write_text('TEST_ONLY dependency')
        alias=self.root/'TEST_ONLY-alias';alias.symlink_to(dependency)
        plan['inputs'].append(dict(path=str(alias),sha256=a.pin(dependency)['sha256']))
        if real_inputs:
            # Use the WHOLE real plan, not only its historical input list.
            plan=a.read(REAL_PLAN)
            rp=a.pin(BASE/'compiler-native-binding-08/corrected-review.json')
        pp=self.put('TEST_ONLY-plan.json',plan)
        root=self.root/'TEST_ONLY-unenrolled-root';root.mkdir()
        policy=self.put('TEST_ONLY-policy.json',dict(root=dict(path=str(root)),predecessor_controller=a.pin(__file__),predecessor_ledger=a.pin(__file__)))
        config=self.put('TEST_ONLY-config.json',dict(approved_policies=[policy],owner_state=str(self.root/'TEST_ONLY-owners.json')))
        bundle=dict(config=config,controller=a.pin(__file__),helpers=[a.pin(__file__)])
        transition=self.put('TEST_ONLY-transition.json',dict(worker='A',to_owner='TEST_ONLY-owner',coordinator=a.COORDINATOR))
        evidence=self.put('TEST_ONLY-evidence.json',dict(not_a_qualification=True))
        q=self.put('TEST_ONLY-qualification-review.json',dict(coordinator=a.COORDINATOR,qualified=True,worker='A',boot='TEST_ONLY_boot',v6_bundle=bundle,cases=['success','nonzero','timeout'],evidence=[evidence]))
        owner=self.put('TEST_ONLY-owner-receipt.json',dict(coordinator=a.COORDINATOR,worker='A',owner='TEST_ONLY-owner',iteration=10,transition=transition,rotation_completed=True))
        pubauth=self.put('TEST_ONLY-pubauth.json',dict(coordinator=a.COORDINATOR,owner_file_publication_authorized=True))
        request=dict(coordinator=a.COORDINATOR,native_execution=True,phase='compiler',worker='A',ram_bytes=8*a.GIB,disk_bytes=a.GIB,timeout_seconds=1200,source_commit=plan['application_head_at_preparation'],owner='TEST_ONLY-owner',iteration=10,attempt='TEST_ONLY_attempt',boot='TEST_ONLY_boot',owner_transition=transition,owner_receipt=owner,qualification_review=q,publication_authorization=pubauth,observed_only_toolchain_accepted=True,grant_path=str(self.root/'TEST_ONLY-grant.json'),manifest_path=str(self.root/'TEST_ONLY-manifest.json'),publication_receipt_path=str(self.root/'TEST_ONLY-publication.json'))
        req=self.put('TEST_ONLY-request.json',request)
        s=dict(source_commit=plan['application_head_at_preparation'],v6_bundle=bundle,a_policy=policy,owned_processes=a.pin(__file__),python=a.pin('/usr/bin/python3.14'),review=rp,pins=[a.pin(__file__)],state_path=str(self.root/'TEST_ONLY-state.json'),lock_path=str(self.root/'TEST_ONLY-capacity.lock'))
        (self.root/'source-contract.json').write_bytes(a.encoded(dict(s,TEST_ONLY=True)))
        return plan,pp,request,req,s

    def assemble(self,mod=a,real_inputs=False):
        plan,pp,r,req,s=self.fixture(mod,real_inputs)
        out=self.root/'TEST_ONLY-assembled'
        with patch.object(mod,'HERE',self.root),patch.object(mod,'static_contract',return_value=s),patch.object(mod,'current_head',return_value=s['source_commit']):
            mod.assemble(pp['path'],req['path'],str(out))
        return plan,r,s,out

    def test_01_original_real_plan_assemble_reproduces_noncanonical_input_failure(self):
        with self.assertRaisesRegex(ValueError,'absolute protected path'):
            self.assemble(original,real_inputs=True)
        self.assertTrue((self.root/'TEST_ONLY-assembled/contract.json').exists())
        self.assertFalse((self.root/'TEST_ONLY-unenrolled-root/TEST_ONLY_attempt').exists())

    def test_02_installed_v6_rejects_original_alias_then_accepts_canonical_pin(self):
        p=self.root/'TEST_ONLY-file';p.write_text('TEST_ONLY')
        alias=self.root/'TEST_ONLY-alias';alias.symlink_to(p)
        pin=a.pin(alias)
        with self.assertRaises(OSError): storage_paths.pinned(pin)
        canonical=a.controller_inputs([pin])[0]
        self.assertEqual(storage_paths.pinned(canonical),b'TEST_ONLY')
        self.assertEqual(pin['sha256'],canonical['sha256'])

    def test_03_real_plan_assembles_without_rehash_or_prefill(self):
        plan,r,s,out=self.assemble(real_inputs=True)
        g=a.read(out/'grant.candidate.json');m=a.read(out/'manifest.candidate.json');c=a.read(out/'contract.json')
        self.assertFalse(Path(c['attempt_root']).exists())
        self.assertEqual(m['inputs'],g['inputs'])
        self.assertEqual(m['grant']['sha256'],a.pin(out/'grant.candidate.json')['sha256'])
        for p in g['inputs']: self.assertEqual(str(Path(p['path']).resolve(strict=True)),p['path'])
        self.assertEqual(a.read(out/'plan.json')['inputs'],plan['inputs'])
        self.assertNotIn(r['grant_path'],[p['path'] for p in g['inputs']])
        self.assertNotIn(r['manifest_path'],[p['path'] for p in g['inputs']])
        self.assertNotIn(r['publication_receipt_path'],[p['path'] for p in g['inputs']])
        # No owner/state/publication pin cycle; state is observed only after charge.
        self.assertNotIn(s['state_path'],[p['path'] for p in g['inputs']])
        self.assertEqual(g['ram_peak_bytes'],8*a.GIB)
        self.assertEqual(g['phase_bytes'],a.GIB)
        self.assertEqual(g['timeout_seconds'],1200)

    def runtime(self,publication=True,mod=a):
        plan,r,s,out=self.assemble()
        for source,dest in [('grant.candidate.json',r['grant_path']),('manifest.candidate.json',r['manifest_path'])]: Path(dest).write_bytes((out/source).read_bytes())
        gp,mp=a.pin(r['grant_path']),a.pin(r['manifest_path']);g=a.read(gp['path']);c=a.read(out/'contract.json')
        owner=dict(grant=gp,thread=r['owner'],iteration=r['iteration'])
        owners=dict(workers=dict(A=owner),TEST_ONLY=True)
        config=a.load_pin(s['v6_bundle']['config']);Path(config['owner_state']).write_bytes(a.encoded(owners))
        cg=Path('/proc/self/cgroup').read_text().split('::')[-1].strip()
        # Use the real attach_service body to emit its exact schema; all storage
        # methods are replaced on this test-owned object, no real Ledger created.
        row=dict(stage='launch_claimed',grant=gp,manifest=mp,owner=r['owner'],worker='A',ram_bytes=8*a.GIB,phase_bytes=a.GIB,custody=dict(controller=g['controller'],config=g['runtime_config'],cgroup=cg),TEST_ONLY=True)
        state=dict(lanes=dict(A=dict(transitions=[r['owner_transition']],pin=g['storage_policy'])),phases={'A:'+g['attempt']:row},TEST_ONLY=True)
        ledger=storage_admission.Ledger.__new__(storage_admission.Ledger)
        @contextlib.contextmanager
        def transaction(): yield state
        ledger.transaction=transaction;ledger.require_active_target=lambda *x:None;ledger.check=lambda *x:None;ledger.save=lambda *x:None
        ledger.attach_service('A:'+g['attempt'],authenticate=lambda *x:dict(identity=dict(cgroup=cg,TEST_ONLY=True),invocation='TEST_ONLY_invocation'))
        Path(s['state_path']).write_bytes(a.encoded(state));Path(s['lock_path']).touch()
        pub=dict(coordinator=a.COORDINATOR,published=publication,under_capacity_lock=True,grant=gp,manifest=mp,owner_transition=r['owner_transition'],owner_entry=owner,TEST_ONLY=True)
        Path(r['publication_receipt_path']).write_bytes(a.encoded(pub))
        # Runtime's real boot check stays in place; bind TEST_ONLY request to this host
        # by changing the boot reader in this process, never actual evidence/authority.
        attempt=Path(c['attempt_root']);attempt.mkdir()
        for n in ('tmp','cache','ccache','receipts'): (attempt/n).mkdir()
        self.assertFalse((attempt/'compiler').exists())
        original_validate=mod.validate_runtime
        def validate(*args):
            return original_validate(*args[:-1],'TEST_ONLY_boot')
        executed=[]
        def execute(plan,binding):
            executed.append(True)
            # The adapter released its read-only shared lock before payload execution.
            with open(s['lock_path'],'rb+') as lock:
                fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            for p in plan['generated']: a.verify(p)
            self.assertEqual(binding['controller_receipt'],a.pin(s['state_path']))
            def fake(stage):
                self.assertEqual(stage['argv'],['TEST_ONLY_NEVER_EXECUTE'])
                if stage['name']=='link-compiler': (Path(plan['out'])/'vkf-strict').write_text('TEST_ONLY_identity')
                return (1,'','cross-ABI child was preserved',dict(no_live_descendants=True)) if stage['name']=='run-regression-baseline' else (0,stage.get('stdout') or '', '',dict(no_live_descendants=True))
            real_execute(plan,binding,run_override=fake)
        real_execute=payload.execute
        with patch.object(mod,'HERE',self.root),patch.object(mod,'static_contract',return_value=s),patch.object(mod,'current_head',return_value='TEST_ONLY_HEAD'),patch.object(mod,'validate_runtime',side_effect=validate),patch.object(payload,'current_head',return_value='TEST_ONLY_HEAD'),patch.object(payload,'execute',side_effect=execute):
            mod.run(str(out/'contract.json'),a.pin(out/'contract.json')['sha256'],r['grant_path'],r['manifest_path'])
        self.assertEqual(executed,[True])
        result=a.read(attempt/'compiler/execution-summary.json')
        self.assertEqual(result['completed'],8);self.assertFalse(result['native_execution'])
        self.assertFalse(a.read(attempt/'compiler/compiler-receipt.json')['native_build_passed'])
        return attempt

    def test_04_file_backed_assemble_run_real_payload_eight_fake_stages(self): self.runtime()

    def test_04b_original_runtime_rejects_canonical_grant_inputs(self):
        with self.assertRaisesRegex(ValueError,'plan inputs omitted'): self.runtime(mod=original)

    def test_05_missing_publication_fails_before_materialization(self):
        with self.assertRaisesRegex(ValueError,'publication receipt'): self.runtime(publication=False)
        self.assertFalse((self.root/'TEST_ONLY-unenrolled-root/TEST_ONLY_attempt/compiler').exists())

    def test_06_real_plan_all_materialization_parents_and_full_binding(self):
        p=a.read(REAL_PLAN);before=a.encoded(p);target=self.root/'TEST_ONLY-materialized'
        result,assets=a.relocate(p,str(target))
        target.mkdir()
        for n in ('tmp','cache','home','logs','objects','sources'): (target/n).mkdir()
        for dest,b in assets: Path(dest).write_bytes(b)
        for generated in result['generated']: a.verify(generated)
        for stage in result['stages']:
            for path in stage.get('outputs',[])+([stage['md']] if 'md' in stage else []): self.assertTrue(Path(path).parent.is_dir())
            for item in stage.get('expected',[]):
                path=item.get('effective',item.get('path'))
                if Path(path).is_relative_to(target) and item.get('sha256'): self.assertEqual(a.pin(path)['sha256'],item['sha256'])
        reverse=a.encoded(result).decode().replace(str(target),p['out'])
        for old,new in zip(p['generated'],result['generated']):reverse=reverse.replace(new['sha256'],old['sha256'])
        self.assertEqual(a.decode(reverse),p);self.assertEqual(a.encoded(p),before)
        a.check_plan(result,p['application_head_at_preparation'],a.read(BASE/'compiler-native-binding-08/corrected-review.json'))

    def test_07_readonly_shared_lock_conflicts_and_then_releases(self):
        p=self.root/'TEST_ONLY-capacity.lock';p.touch()
        with p.open('rb') as shared,p.open('r+b') as exclusive:
            fcntl.flock(shared,fcntl.LOCK_SH|fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError):fcntl.flock(exclusive,fcntl.LOCK_EX|fcntl.LOCK_NB)
            fcntl.flock(shared,fcntl.LOCK_UN)
            fcntl.flock(exclusive,fcntl.LOCK_EX|fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError):fcntl.flock(shared,fcntl.LOCK_SH|fcntl.LOCK_NB)

    def test_08_alias_digest_conflict_rejected(self):
        p=self.root/'TEST_ONLY-file';p.write_text('TEST_ONLY')
        alias=self.root/'TEST_ONLY-alias';alias.symlink_to(p)
        with self.assertRaisesRegex(ValueError,'conflicting'):
            a.controller_inputs([a.pin(p),dict(path=str(alias),sha256='TEST_ONLY_WRONG')])

    def test_08b_isolated_fresh_payload_imports_joined(self):
        code = "import sys;sys.path.insert(0," + repr(str(BASE/'compiler-build-preparation-03')) + ");import payload,prepare,authenticate;print(payload.__file__);print(prepare.__file__);print(authenticate.__file__)"
        child=subprocess.Popen(['/usr/bin/python3.14','-I','-B','-c',code],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        try:
            stdout,stderr=child.communicate(timeout=5)
        except BaseException:
            child.kill();child.communicate();raise
        record=dict(TEST_ONLY=True,pid=child.pid,exit=child.returncode,joined=True,seconds_bound=5,
                    purpose='isolated imports only; no native payload',stdout=stdout,stderr=stderr)
        JOINED_HOST_CHILDREN.append(record)
        self.assertEqual(child.returncode,0,stderr)
        self.assertEqual(stdout.splitlines(),[str(BASE/'compiler-build-preparation-03'/n) for n in ('payload.py','prepare.py','authenticate.py')])

    def test_09a_relative_input_rejected(self):
        with self.assertRaisesRegex(ValueError,'absolute compiler input'):
            a.controller_inputs([dict(path='TEST_ONLY-relative',sha256='TEST_ONLY')])

    def test_09b_nominal_alias_in_writable_root_rejected(self):
        p=self.root/'TEST_ONLY-external';p.write_text('TEST_ONLY')
        writable=self.root/'TEST_ONLY-writable';writable.mkdir()
        alias=writable/'TEST_ONLY-alias';alias.symlink_to(p)
        with self.assertRaisesRegex(ValueError,'authority in writable root'):
            a.protected([str(alias)],[str(writable)])

    def test_09c_actual_v6_rejects_actual_plan_noncanonical_samples_without_hashing(self):
        inputs=a.read(REAL_PLAN)['inputs']
        dot=next(p for p in inputs if '..' in Path(p['path']).parts)
        symlink=next(p for p in inputs if '..' not in Path(p['path']).parts and str(Path(p['path']).resolve())!=p['path'])
        with self.assertRaisesRegex(storage_paths.Rejected,'noncanonical'):
            storage_paths.pinned(dot)
        with self.assertRaises(OSError):storage_paths.pinned(symlink)

    def test_09d_temporal_ledger_pin_expires_after_replace(self):
        p=self.root/'TEST_ONLY-ledger.json';p.write_text('{"TEST_ONLY":true,"sequence":1}')
        old=a.pin(p);a.verify(old)
        new=self.root/'TEST_ONLY-next.json';new.write_text('{"TEST_ONLY":true,"sequence":2}')
        new.replace(p)
        with self.assertRaisesRegex(ValueError,'changed input'):a.verify(old)
        # This pin must not be installed as a permanent immutable grant input.

    def test_09_missing_nominal_dependency_rejected(self):
        with self.assertRaises(FileNotFoundError):a.controller_inputs([dict(path=str(self.root/'TEST_ONLY_MISSING'),sha256='TEST_ONLY')])

if __name__=='__main__':
    start=time.monotonic()
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    print(json.dumps(dict(TEST_ONLY=True,tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),seconds=time.monotonic()-start,maxrss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,native_children=0,test_children=len(JOINED_HOST_CHILDREN),joined_host_children=JOINED_HOST_CHILDREN)))
    raise SystemExit(not result.wasSuccessful())
