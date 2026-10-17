"""Bounded host-only audit; no native execution, materialization or operational writes."""
import resource
resource.setrlimit(resource.RLIMIT_AS, (512*1024**2,)*2)
resource.setrlimit(resource.RLIMIT_CPU, (50,50))
resource.setrlimit(resource.RLIMIT_CORE, (0,0))
import ast, hashlib, importlib.util, json, os, subprocess, sys, time
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
R=HERE.parent
S=Path('/home/viktor/Projects/Vektor Flow/.coordination/s0-plan-20261012/synchronized-contexts/independent-workers/storage20gb')
started=time.monotonic()
def read(p): return json.loads(Path(p).read_text())
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(262144),b''): h.update(b)
    return h.hexdigest()
def pin(p): return {'path':str(p),'sha256':sha(p)}
def save(n,d): (HERE/n).write_text(json.dumps(d,indent=2)+'\n')
def load(n,p):
    spec=importlib.util.spec_from_file_location(n,p)
    m=importlib.util.module_from_spec(spec);sys.modules[n]=m;spec.loader.exec_module(m);return m
auth=read(R/'compiler-build-preparation-03/authentication.json')
rows=auth['inputs']
actual=[]
for p in rows:
    actual.append(dict(path=p['path'],sha256=sha(p['path']),expected=p['sha256'],bytes=Path(p['path']).stat().st_size))
assert len(actual)==727 and all(p['sha256']==p['expected'] for p in actual)
classification=read(R/'compiler-package-review-06/observed-only-classification.json')
observed=[p for p in rows if p['classification']=='observed-only']
assert len(observed)==36 and {p['path'] for p in observed}=={p['path'] for p in classification['rows']}
assert sum(bool(p['recorded_aliases']) for p in classification['rows'])==1
save('provenance.json',dict(authentication=pin(R/'compiler-build-preparation-03/authentication.json'),
    classification=pin(R/'compiler-package-review-06/observed-only-classification.json'),
    count=len(actual),bytes=sum(p['bytes'] for p in actual),recorded_matches=691,
    observed_only=observed,alias_corroborated=1,without_selected_path_or_alias_authority=35,
    all_current_hashes_match=True,historical_provenance_established=False))
s=read(R/'compiler-controller-preparation-09/source-contract.json')
stale=[dict(p,actual=sha(p['path'])) for p in s['pins'] if sha(p['path'])!=p['sha256']]
installed=read(R/'storage-combined-trust-review-23/root-v9-installed.json')
assert all(sha(p['path'])==p['sha256'] for p in installed['installed_files'])
export=S/'compiler-qualified-v9-A-root-export-20261017.json'
assert sha(export)=='8cdeb6a0051fa2274a94ca6086e518388ceb46b26f629d95d2c1c9404f4695fa'
q=read(export)
assert q['qualified'] and q['worker']=='A' and q['cases']==['success','nonzero','timeout']
assert all(sha(p['path'])==p['sha256'] for p in q['evidence'])
assert q['v6_bundle']['controller']['path']==str(S/'storage-direct-v9/storage_controller.py')
save('contract-check.json',dict(historical_contract=pin(R/'compiler-controller-preparation-09/source-contract.json'),
    historical_head=s['source_commit'],stale_pins=stale,installed_v9=pin(R/'storage-combined-trust-review-23/root-v9-installed.json'),
    installed_files_verified=len(installed['installed_files']),genuine_qualified_A_export=pin(export),
    qualification_evidence_pins_verified=len(q['evidence']),legacy_v6_bundle_label_is_not_incompatibility=True))
sys.path.insert(0,str(R/'compiler-build-preparation-03'))
adapter=load('audit_adapter',R/'compiler-controller-preparation-09/adapter.py')
import payload, prepare, authenticate
load('audit_owned',S/'owned-processes.py')  # import only; never enable_subreaper or wait_owned
module_paths={str(Path(m.__file__).resolve()) for m in list(sys.modules.values()) if getattr(m,'__file__',None) and Path(m.__file__).is_file()}
mapped={line.split(None,5)[5].strip() for line in Path('/proc/self/maps').read_text().splitlines() if len(line.split(None,5))==6 and line.split(None,5)[5].startswith('/')}
old_pins={str(Path(p['path']).resolve()):p['sha256'] for p in s['pins']+rows}
constants={}
for n in ast.parse((S/'storage-direct-v9/private_workload.py').read_text()).body:
    if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ('BINARIES','POLICY_INPUTS'):
        constants[n.targets[0].id]=ast.literal_eval(n.value)
namespace_missing=[p for p in constants['BINARIES']+constants['POLICY_INPUTS'] if str(Path(p['path']).resolve()) not in old_pins or old_pins[str(Path(p['path']).resolve())]!=p['sha256']]
runtime_paths=sorted(module_paths|mapped|{str(Path('/usr/bin/git').resolve())})
runtime_pins=[pin(p) for p in runtime_paths]
missing=[p for p in runtime_pins if p['path'] not in old_pins]
# Read ELF metadata only, using the already authenticated parser; do not execute ldd/tools.
elf=[]
for p in runtime_paths:
    needs,interp,search=authenticate.elf_needs(p)
    if needs or interp: elf.append(dict(path=p,needs=needs,interpreter=interp,search=search))
save('runtime-closure.json',dict(scope='isolated host imports and mapped DSOs; not final-namespace execution',
    imports_successful=True,native_children=0,runtime_pins=runtime_pins,missing_from_historical_compiler_union=missing,
    installed_v9_constants_missing_from_historical_union=namespace_missing,elf_metadata=elf,
    limitation='Loaded .pyc files may appear for stdlib. Root must seal exact loaded files and source; Git dependencies need explicit closure too.'))
state_path=S/'storage-direct-v4/direct-state-v4.json'
state=read(state_path)
budgets={}
for lane,rec in state['lanes'].items():
    policy=rec['policy'];budget=21900000000+sum(i['bytes'] for i in policy['increments'])
    charge=policy['historical_charge']+sum(p['phase_bytes'] for p in state['phases'].values() if p['worker']==lane)
    budgets[lane]=dict(budget=budget,charge=charge,remaining=budget-charge)
budgets['A'].update(first_compiler_charge=1073741824,after_first=budgets['A']['charge']+1073741824,
    remaining_after_first=budgets['A']['remaining']-1073741824,
    remaining_after_all_seven_forecasts=budgets['A']['remaining']-21474836480)
space={}
for path in ['/', '/mnt/development', '/mnt/vkf-worker-disks/worker-A', '/mnt/vkf-worker-disks/worker-F']:
    v=os.statvfs(path);space[path]=dict(free=v.f_bavail*v.f_frsize,used=(v.f_blocks-v.f_bfree)*v.f_frsize)
save('resource-fit.json',dict(state_observation=pin(state_path),not_immutable_authority=True,budgets=budgets,
    physical_snapshot=space,backing_floor=250000000000+10*1024**3+2*64*1024**3,
    tiny_qualification=read(R/'storage-live-24/final-charge-check.json'),
    compiler_forecast=dict(ram=4*1024**3,actual_adapter_A_profile=8*1024**3,disk=1024**3,seconds=1200,
    native_measurements_available=False,stage_timeout_sum=1140,overhead_slack_seconds=60,
    subphase_disk_sum=134217728+33554432+268435456+402653184,disk_slack=1024**3-(134217728+33554432+268435456+402653184))))
save('audit-execution.json',dict(passed=True,seconds=time.monotonic()-started,maxrss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    limits=dict(address_space_bytes=512*1024**2,cpu_seconds=50,external_wall_seconds=60),native_execution=False))
print(json.dumps(dict(passed=True,seconds=time.monotonic()-started,hashes=len(actual),stale_pins=len(stale),runtime_missing=len(missing),namespace_missing=len(namespace_missing),budgets=budgets)))
