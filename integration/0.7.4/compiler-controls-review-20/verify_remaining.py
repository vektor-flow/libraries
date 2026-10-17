"""Bounded read-only remaining scope review; own TEMP FIFO and patch reconstruction only."""
import ast,hashlib,importlib.util,json,os,resource,subprocess,sys,tempfile,time
from pathlib import Path
resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,)*2);resource.setrlimit(resource.RLIMIT_CPU,(50,50));resource.setrlimit(resource.RLIMIT_CORE,(0,0))
sys.dont_write_bytecode=True
O=Path(__file__).resolve().parent;P=O.parent/'compiler-controls-preparation-18';start=time.monotonic()
spec=importlib.util.spec_from_file_location('frozen18',P/'adapter.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
s=a.static_contract();plan=a.load_pin(s['control_plan']);config=a.load_pin(s['v6_bundle']['config'])
sys.path.insert(0,str(Path(s['v6_bundle']['controller']['path']).parent));import storage_paths
pins=a.read(P/'artifact-pins.json')['pins']
for pin in pins:a.verify(pin)
inspected=a.unique(pins+s['pins']+[a.pin(P/n) for n in ('result.json','artifact-pins.json','source-contract.json','root_steps.py','seal_source.py','build_packet.py','test_controls.py','ROOT-RECIPE.txt')])
(O/'inspected-pins.json').write_text(json.dumps(dict(source_commit=s['source_commit'],pins=inspected),indent=2)+'\n')
# Native compiler provenance is direct real receipt equality, not a caller-authored boolean.
na=a.read(P/'native-authentication.json')
for pin in na['actual_inputs']+[na['accepted']]:a.verify(pin)
receipt=a.load_pin(s['compiler_receipt']);assert receipt==a.load_pin(na['actual_inputs'][0])
assert a.raw(s['compiler_receipt']['path'])==a.raw(na['actual_inputs'][0]['path'])
assert receipt==plan['compiler_receipt'] and receipt['native_build_passed'] is True and receipt['core_regression_passed'] is True
accept=a.load_pin(na['accepted']);assert accept['binary']==receipt['compiler']
sys.path.insert(0,str(a.PACKAGE));import payload
np=a.load_pin(receipt['plan']);nr=a.load_pin(receipt['results']);assert len(np['stages'])==len(nr)==8
produced={str(Path(p['path']).resolve()):p['sha256'] for row in nr for p in row.get('outputs',[])}
for stage,row in zip(np['stages'],nr):
 assert stage['name']==row['name'] and stage['argv']==row['argv']
 j=row['join'];assert j['no_live_descendants'] and not any(j.get(k) for k in ('timed_out','guard_error','orphaned_descendant_on_exit','remaining_identities'))
 for pin in row.get('logs',[])+row.get('outputs',[])+row.get('actual_dependencies',[]):a.verify(pin)
 payload.check_result(stage,row['exit'],Path(row['logs'][0]['path']).read_text(),Path(row['logs'][1]['path']).read_text())
 if 'md' in stage:
  a.verify(row['depfile']);assert payload.validate_md(stage,produced)==row['actual_dependencies']
compiler=receipt['compiler'];found=False;tail=b'';marker=receipt['identity'].encode()
with Path(compiler['path']).open('rb') as f:
 assert f.read(4)==b'\x7fELF';f.seek(0)
 while chunk:=f.read(262144):found|=marker in tail+chunk;tail=chunk[-len(marker):]
assert found
# Closure check invokes no inspected executable or dynamic loader.
inputs=a.unique(s['pins']+a.controller_inputs(plan['inputs']));by_path={x['path']:x['sha256'] for x in inputs}
closure=a.read(P/'runtime-closure.json')
for edge in closure['elf_edges']:assert str(Path(edge['target']).resolve()) in by_path
required=['/usr/bin/valgrind','/usr/bin/valgrind.bin','/bin/sh','/usr/libexec/valgrind/memcheck-amd64-linux','/usr/libexec/valgrind/vgpreload_core-amd64-linux.so','/usr/libexec/valgrind/vgpreload_memcheck-amd64-linux.so','/usr/libexec/valgrind/default.supp','/etc/ld.so.cache']
for path in required:
 pin=a.pin(Path(path).resolve());assert by_path[pin['path']]==pin['sha256']
# Receipt/plan/seal directed references: no self-hash or adapter-grant receipt cycle.
assert str(P/'source-contract.json') not in {p['path'] for p in s['pins']}
assert str(P/'source-contract.json') not in {p['path'] for p in plan['inputs']}
assert compiler not in s['pins'] and compiler in a.controller_inputs(plan['inputs'])
roots=[a.load_pin(p)['root']['path'] for p in config['approved_policies']]
a.protected([p['path'] for p in s['pins']],roots)
# Read only; no live lock/API state change. This is not a fresh admission/service qualification.
from storage_admission import Ledger
statepin=a.pin(s['state_path']);state=a.load_pin(statepin)
ledger=Ledger(s['state_path'],s['lock_path'],recovery_pin=config['recovery_authority'])
active=ledger.active_rows(state)
key,row=max(((k,r) for k,r in state['phases'].items() if r['worker']=='A'),key=lambda x:x[1]['sequence'])
assert key=='A:compiler-native17-01' and row['sequence']==13 and row['stage']=='joined'
assert ledger.owner(state,'A')==row['owner']=='01a14a07-a6c3-7941-b133-31fe3cbbee71'
a.verify(row['join']);assert row['join']==accept['join'];join=a.load_pin(row['join'])
assert join['main_pid']==0 and join['cgroup_empty'] and join['actual_service_joined'] and join['remaining_identities']==[]
assert join['grant']==row['grant'] and join['manifest']==row['manifest']
charges={w:state['lanes'][w]['policy']['historical_charge']+sum(r['phase_bytes'] for r in state['phases'].values() if r['worker']==w) for w in 'AF'}
assert charges==dict(A=20938285056,F=19821273088)
assert sum(r['ram_bytes'] for r in active)==0
a.verify(statepin)
# Optional vgdb IPC conflicts with exact installed regular-file-only allocator.
manual=Path('/usr/share/doc/valgrind/html/manual-core.html');advanced=manual.with_name('manual-core-adv.html')
mt=manual.read_text();at=advanced.read_text()
assert '--vgdb=&lt;no|yes|full&gt; [default: yes]' in mt
assert 'creates 3 files (2 named FIFOs and a mmap shared memory' in mt
assert 'by setting environment variable TMPDIR when running Valgrind' in at
assert all(not any(x.startswith('--vgdb') for x in stage['argv']) for stage in plan['stages'] if stage.get('valgrind'))
children=[]
with tempfile.TemporaryDirectory(prefix='TEST_ONLY_fifo_',dir=O) as tmp:
 path=Path(tmp);fifo=path/'vgdb-pipe-TEST_ONLY';os.mkfifo(fifo,0o600)
 try:storage_paths.allocated(path)
 except storage_paths.Rejected as e:assert str(e)=='symlink or special file';fifo_error=str(e)
 else:raise AssertionError('installed allocator accepted FIFO')
# Reconstruct both patches against frozen original sources in own scratch only.
patches=[]
with tempfile.TemporaryDirectory(prefix='TEST_ONLY_patch_',dir=O) as tmp:
 for original,proposed,diff in [('adapter.py','adapter.py','adapter-regular-stdlib.patch'),('build_packet.py','build_packet.py','build-packet-d288-cwd-vgdb.patch')]:
  dest=Path(tmp)/original
  command=['/usr/bin/patch','--batch','--output',str(dest),str(P/original),str(O/diff)]
  child=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
  try:stdout,stderr=child.communicate(timeout=5)
  except BaseException:
   child.kill();child.communicate();raise
  children.append(dict(pid=child.pid,exit=child.returncode,joined=True,absent=not Path('/proc',str(child.pid)).exists()))
  assert child.returncode==0,(stdout,stderr);assert dest.read_bytes()==(O/proposed).read_bytes()
  patches.append(dict(patch=a.pin(O/diff),reconstructed=a.pin(O/proposed),passed=True))
assert a.current_head()==s['source_commit']
report=dict(TEST_ONLY=True,passed=True,source_commit=s['source_commit'],artifact_pins_verified=len(pins),inspected_versions=a.pin(O/'inspected-pins.json'),compiler_snapshot_byte_identical_to_real_receipt=True,eight_actual_native17_stage_oracles_and_MD_reverified=True,compiler=compiler,identity=receipt['identity'],static_pins=len(s['pins']),combined_runtime_inputs=len(inputs),ELF_dependency_edges_checked=len(closure['elf_edges']),valgrind_pins=[a.pin(Path(x).resolve()) for x in required],vgdb_evidence=dict(manual=a.pin(manual),advanced=a.pin(advanced),installed_allocator=a.pin(storage_paths.__file__),default_vgdb_yes=True,default_IPC_FIFOs=2,original_no_override=True,TEMP_fifo_rejection=fifo_error,actual_native_IPC_not_run=True,proposed_vgdb_no_must_be_verified_in_actual_future_run=True),succession=dict(advisory_unlocked_read=True,state=statepin,key=key,sequence=row['sequence'],owner=row['owner'],stage=row['stage'],join=row['join'],active_ram_intent=sum(r['ram_bytes'] for r in active),charges=charges,fresh_locked_root_verification_still_required=True),source_receipt_cycle=False,prior_compiler_data_exception_not_authority=True,patches=patches,children=children,all_children_joined=True,all_TEMP_cleaned=not list(O.glob('TEST_ONLY_*')),seconds=time.monotonic()-start,native_execution=False,operational_mutations=0,memory=[x for x in Path('/proc/self/status').read_text().splitlines() if x.startswith(('VmPeak:','VmHWM:'))])
(O/'remaining-review-results.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ('passed','artifact_pins_verified','static_pins','combined_runtime_inputs','ELF_dependency_edges_checked','seconds','children','all_TEMP_cleaned')}))
