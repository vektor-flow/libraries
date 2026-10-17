"""Independent read-only delivered inventory, runtime closure and actual join audit."""
import ast, hashlib, json, os, stat, sys, time
from pathlib import Path
import adapter as a
OUT=Path(__file__).resolve().parent
H=OUT.parent/'metadata-repaired-binding-32'
R=OUT.parent/'metadata-entry-repair-31'
N=OUT.parent/'metadata-native-29'
seen={}; checks=[]
def check(value,label):
    assert value,label
    checks.append(label)
def verify(ref):
    p=Path(ref['path']);want=ref['sha256']
    if str(p) not in seen:
        with p.open('rb') as f: got=hashlib.file_digest(f,'sha256').hexdigest()
        seen[str(p)]=got
    check(seen[str(p)]==want,'sha256 '+str(p))
def read(path):
    verify(a.pin(path));return json.loads(Path(path).read_bytes())
start=time.monotonic()
delivery=read(H/'delivery.json')
for key in ('manifest','handoff','plan','recipe','result','source_contract'):verify(delivery[key])
artifacts=read(delivery['manifest']['path'])
check(len(artifacts)==delivery['artifacts']==119,'119 delivered artifact rows')
for row in artifacts:
    p=Path(row['path']);s=p.lstat()
    check(p.is_relative_to(H),'artifact within packet')
    if row['type']=='symlink':
        check(stat.S_ISLNK(s.st_mode) and os.readlink(p)==row['readlink'],'exact host staging symlink')
        verify(dict(path=str(p),sha256=row['target_sha256']))
    else:
        check(stat.S_ISREG(s.st_mode) and s.st_nlink==row['nlink']==1 and s.st_size==row['bytes'],'regular artifact size/link count')
        check(stat.S_IMODE(s.st_mode)==0o444,'read-only regular delivery')
        verify(row)
check(all(stat.S_IMODE(x.stat().st_mode)==0o555 for x in [H,*[p for p in H.rglob('*') if p.is_dir() and not p.is_symlink()]]),'read-only packet directories')
for ref in read(H/'input-pins.json'):verify(ref)
for ref in read(R/'input-pins.json'):verify(ref)
for ref in read(N/'attempt-artifact-pins.json'):verify(ref)
seal=read(H/'source-contract.json');plan=read(seal['control_plan']['path'])
check(a.current_head()==seal['source_commit']=='0d6d2bea2eb8015ee56f95b1e0eaf78e3d3c3108','exact current granted HEAD')
for ref in seal['pins']+plan['inputs']+plan['generated']:verify(ref)
check(len(seal['pins'])==262 and len(plan['inputs'])==732,'complete static/plan input inventories')
combined=a.unique(seal['pins']+a.controller_inputs(plan['inputs']))
check(len(combined)==924,'924 canonical runtime inputs')
a.check_plan(plan,seal['source_commit'],a.load_pin(seal['review']))
check((H/'adapter.py').read_bytes()==(OUT.parent/'metadata-control-preparation-27/adapter.py').read_bytes(),'entire adapter unchanged including lock/admission guards')
closure=read(H/'runtime-closure.json')
sys.path.insert(0,str(a.PACKAGE))
from authenticate import elf_needs
by_path={p['path']:p for p in combined}
for ref in closure['mapped']+closure['elf_pins']:verify(ref)
for module in closure['modules']:
    for key in ('source','cache'):
        if key in module:
            verify(module[key])
            if module['module']!='__main__':check(module[key] in combined,'runtime Python module/cache included')
actual_edges=[]
for source in sorted({edge['source'] for edge in closure['elf_edges']}):
    needs,interp,search=elf_needs(source)
    if interp:actual_edges.append((source,'PT_INTERP',str(Path(interp).resolve(strict=True))))
    for need in needs:
        dirs=[x.replace('${ORIGIN}',str(Path(source).parent)).replace('$ORIGIN',str(Path(source).parent)) for x in search]
        dirs+=['/usr/lib/x86_64-linux-gnu','/usr/lib','/lib/x86_64-linux-gnu']
        target=next((Path(d)/need).resolve(strict=True) for d in dirs if (Path(d)/need).is_file())
        actual_edges.append((source,need,str(target)))
check(sorted(actual_edges)==sorted((e['source'],e['needed'],e['target']) for e in closure['elf_edges']),'all 104 ELF loader edges recomputed from actual binary sections')
for source,need,target in actual_edges:
    check(source in by_path and target in by_path,'ELF edge endpoints in sealed combined inputs')
config=read(seal['v6_bundle']['config']['path'])
sys.path.insert(0,str(Path(seal['v6_bundle']['config']['path']).parent))
from storage_admission import Ledger
import private_workload
check(len(config['approved_policies'])==7,'seven approved policy pins')
for ref in config['approved_policies']:verify(ref)
policy=a.load_pin(seal['a_policy'])
view=private_workload.runtime_view(dict(inputs=combined,argv=[seal['python']['path']],attempt_root=policy['root']['path']+'/UNFULFILLED-next-metadata'))
check(view==closure['runtime_view_argv'],'exact runtime view constructor output')
# Constructor and pure readers only: never snapshot/transaction/Controller/live APIs.
ledger=Ledger(Path(seal['state_path']),Path(seal['lock_path']),recovery_pin=config['recovery_authority'])
state=read(seal['state_path'])
check(state==read(N/'final-state.json'),'unlocked current ledger equals retained metadata29 final state')
check(not ledger.active_rows(state),'unlocked active RAM intent zero using authenticated recovered rows')
key,row=max(((k,r) for k,r in state['phases'].items() if r['worker']=='A'),key=lambda x:x[1]['sequence'])
check(key=='A:metadata-native29-01' and row['sequence']==15 and row['stage']=='joined','latest USED metadata29 sequence15')
check(row['owner']==ledger.owner(state,'A')=='01a14a3a-d0d8-7a10-a188-717e31a22e31','exact authenticated owner chain')
owners=read(config['owner_state'])
check(owners['workers']['A']['thread']==row['owner'] and owners['workers']['A']['grant']==row['grant'],'actual published owner/grant agrees')
check(row['join']==read(N/'root-terminal-review.json')['join'] and row['join']['sha256']=='4a1ed5938463632747f40aba82b60beca7af7de4d676ed7e96ab9b01ea55f002','exact actual join pin')
verify(row['join']);join=read(row['join']['path'])
for field in ('grant','manifest','custody','service','inner_result'):
    check(join[field]==row[field],'actual join/ledger '+field+' equality')
check(join['actual_service_joined'] and join['cgroup_empty'] and join['main_pid']==0 and not join['remaining_identities'],'actual retained terminal join facts')
check(join['outer_exit']==199 and join['inner_result']['exit']==1,'retained outer/inner failed outcome')
owned=join['inner_result']['owned_join']
check(owned['no_live_descendants'] and not any(owned.get(k) for k in ('guard_error','timed_out','remaining_identities','orphaned_descendant_on_exit')),'retained owned descendant join and guards')
check(join['service']['identity']['argv']==join['custody']['service_argv'],'actual inner service argv/custody equality')
terminal=read(N/'independent-terminal-join.json')
check(terminal['join']==row['join'] and terminal['properties']['InvocationID']==join['service']['invocation'] and terminal['properties']['MainPID']=='0','actual invocation independently recorded')
verify(row['grant']);verify(row['manifest'])
grant=read(row['grant']['path']);manifest=read(row['manifest']['path'])
check(manifest['grant']==row['grant'] and grant['owner']==row['owner'] and grant['attempt']=='metadata-native29-01','actual grant/manifest/owner chain')
actual=read(N/'native-evidence.json');verify(actual['actual_plan']);oldplan=read(actual['actual_plan']['path'])
def relocate_fields(x):
    if isinstance(x,str):return x.replace(oldplan['out'],plan['out'])
    if isinstance(x,list):return [relocate_fields(v) for v in x]
    if isinstance(x,dict):return {k:relocate_fields(v) for k,v in x.items()}
    return x
check(relocate_fields(oldplan['stages'])==plan['stages'],'all three actual native29 stage fields exactly preserved after relocation')
check(plan['stages'][1]['cwd']==plan['out']+'/home','compile home cwd exact')
check(plan['stages'][-1]['stdout'].encode()==b'true\n' and 'stderr' not in plan['stages'][-1],'exact stdout oracle and original unspecified stderr')
last=actual['stages'][-1]
check(last['exit']==0 and all(Path(p['path']).read_bytes()==b'' for p in last['logs']),'actual native29 empty stdout/stderr failure retained')
charges={w:state['lanes'][w]['policy']['historical_charge']+sum(r['phase_bytes'] for r in state['phases'].values() if r['worker']==w) for w in 'AF'}
check(charges==dict(A=24159510528,F=19821273088) and row['phase_bytes']==2**30,'failed 1GiB charge and exact cumulative charges')
non_tiny={'A:compiler-native13-01','A:compiler-native17-01','A:d288-native24-01','A:metadata-native29-01'}
tiny=[r for k,r in state['phases'].items() if k not in non_tiny]
check(len(tiny)==12 and sum(r['phase_bytes'] for r in tiny)==50331648,'tiny 12 attempts/48MiB unchanged')
from root_steps import decision
try:decision(a.pin(H/'root-decisions.REQUIRED.json'))
except ValueError as e:check('genuine separate root' in str(e),'null root decision rejects before operational imports')
else:raise AssertionError('null root decision accepted')
check(not any((H/n).exists() for n in ('root-inputs.json','root-packet','grant.json','manifest.json')),'no operational packet issued')
# Exact source excerpts are independently compared to actual pinned providers.
proof=read(R/'source-proof.json')
for ex in proof['source_excerpts']:
    verify(ex['source'])
    check('\n'.join(Path(ex['source']['path']).read_text().splitlines()[ex['first_line']-1:ex['last_line']])==ex['text'],'source excerpt exact actual provider')
for ref in read(H/'initial-observation.json')['protected_pins']:verify(ref)
check(a.current_head()==seal['source_commit'],'HEAD still held at audit end')
report=dict(passed=True,source_commit=seal['source_commit'],packet_delivery=a.pin(H/'delivery.json'),artifact_manifest=delivery['manifest'],source_contract=delivery['source_contract'],plan=delivery['plan'],checks=checks,check_count=len(checks),unique_rehashed_paths=len(seen),current_ledger=a.pin(seal['state_path']),current_owners=a.pin(config['owner_state']),latest_A=dict(key=key,owner=row['owner'],sequence=row['sequence'],stage=row['stage'],join=row['join']),charges=charges,tiny_attempts=12,tiny_bytes=50331648,failed_native29_charge=2**30,runtime_edges=len(actual_edges),native_execution=False,operational_actions=False,live_join_reauthentication=False,live_lock=False,observation='read-only unlocked; root must reauthenticate live join and admission',seconds=time.monotonic()-start)
with (OUT/'audit-result.json').open('x') as f:json.dump(report,f,indent=2);f.write('\n')
with (OUT/'review-input-pins.json').open('x') as f:json.dump([dict(path=p,sha256=h) for p,h in sorted(seen.items())],f,indent=2);f.write('\n')
print(json.dumps({k:report[k] for k in ('passed','check_count','unique_rehashed_paths','runtime_edges','seconds')}))
