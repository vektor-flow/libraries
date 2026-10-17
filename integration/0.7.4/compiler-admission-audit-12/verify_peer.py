"""Read-only validation of peer11 draft, with no duplicate staging."""
import resource
resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,)*2)
resource.setrlimit(resource.RLIMIT_CPU,(50,50))
import ast, hashlib, importlib.util, json, os, sys, time
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
P=HERE.parent/'compiler-runtime-binding-11'
S=Path('/home/viktor/Projects/Vektor Flow/.coordination/s0-plan-20261012/synchronized-contexts/independent-workers/storage20gb')
t=time.monotonic()
spec=importlib.util.spec_from_file_location('peer_adapter',P/'adapter.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
s=a.static_contract()
assert s['source_commit']=='168085c78e1a91f413aa9f1cfadd9f40c97c1894'==a.current_head()
q=a.read(S/'compiler-qualified-v9-A-root-export-20261017.json')
assert s['v6_bundle']==q['v6_bundle']
plan=a.read(P/'staging/plan.json');a.check_plan(plan,s['source_commit'],a.load_pin(s['review']))
canonical=a.controller_inputs(plan['inputs'])
assert len(plan['inputs'])==727
constants={}
for n in ast.parse((S/'storage-direct-v9/private_workload.py').read_text()).body:
    if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ('BINARIES','POLICY_INPUTS'):
        constants[n.targets[0].id]=ast.literal_eval(n.value)
assert all(p in s['pins'] for p in constants['BINARIES']+constants['POLICY_INPUTS'])
runtime=a.read(HERE/'runtime-closure.json')
u={x['path']:x['sha256'] for x in s['pins']+canonical}
missing=[x for x in runtime['runtime_pins'] if 'compiler-admission-audit-12' not in x['path'] and x['path'] not in u]
assert not missing,missing
# Only imported trees are checked here; actual namespace access is qualified by live24.
paths=[x['path'] for x in s['pins']+canonical]+[s['state_path'],s['lock_path'],a.load_pin(s['v6_bundle']['config'])['owner_state']]
outside=[p for p in paths if not any(Path(p).resolve().is_relative_to(tree) for tree in ['/usr','/etc','/home','/mnt','/dev/shm'])]
assert not outside,outside
state=a.read(s['state_path']);owners=a.read(a.load_pin(s['v6_bundle']['config'])['owner_state'])
prior=state['phases']['A:live24-a-timeout-01']
assert prior['stage']=='joined' and prior['owner']==owners['workers']['A']['thread']
a.verify(prior['join'])
assert prior['join']['sha256']==a.pin(HERE.parent/'storage-live-24/live24-a-timeout-01-raw-service-join.json')['sha256']
result=dict(passed=True,seconds=time.monotonic()-t,maxrss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    peer_source_contract=a.pin(P/'source-contract.json'),peer_adapter=a.pin(P/'adapter.py'),peer_plan=a.pin(P/'staging/plan.json'),
    static_pins_verified=len(s['pins']),original_plan_inputs=len(plan['inputs']),canonical_plan_inputs=len(canonical),
    namespace_constants_present=True,observed_runtime_files_missing=[],runtime_paths_outside_view=[],
    stages=len(plan['stages']),exact_review_preserved=True,
    latest_A_phase='A:live24-a-timeout-01',latest_A_join=prior['join'],
    owner=owners['workers']['A'],required_succession='normal joined-owner transition; A is used',
    native_execution=False,materialization=False,root_admission=False,
    caveat='Peer draft snapshot, not final acceptance. Verify sealed peer handoff before adoption; no real final namespace compiler adapter run.')
(HERE/'peer-verification.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if not isinstance(v,(list,dict))}))
