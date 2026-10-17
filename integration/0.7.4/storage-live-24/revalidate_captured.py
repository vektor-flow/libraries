"""Resolve a local schema-only wrapper error from retained bytes; never launch."""
import argparse,copy,hashlib,json,os,pathlib,time
from preflight import OUT,OLD,V2,STATE,OWNER,HEAD,save,pin,pinned,pinned_json,proc,Linux,run
from storage_admission import Ledger,GIB
from storage_controller import Controller,parse_exec_start
from validate_trust import parse,validate_trust
from validate_snapshots import validate
from validate_security import validate_security
from validate_fixture import validate_fixture
start=time.monotonic();cp=pin(V2/'runtime-config.json');c=pinned_json(cp);l=Ledger(STATE/'direct-state-v4.json',OLD/'capacity.lock',recovery_pin=c['recovery_authority'])
before=l.snapshot();statepin=pin(l.state);ownerpin=pin(pathlib.Path(c['owner_state']));a=Linux();proofs=[]
assert not l.active_rows(before) and len(before['phases'])==9 and sum(r['phase_bytes'] for r in before['phases'].values())==37748736
assert json.loads((OUT/'fixture-parser-tests.json').read_text())['passed']
for mode in ['success','nonzero','timeout']:
 attempt='live24-f-'+mode+'-01';result=json.loads((OUT/(attempt+'-result.json')).read_text());row=result['phase'];r=before['phases']['F:'+attempt]
 assert row==r and r['stage']=='joined' and r['owner']==OWNER
 gp,mp=r['grant'],r['manifest'];g,m=pinned_json(gp),pinned_json(mp);root=pathlib.Path(m['attempt_root'])
 ctrl=Controller(argparse.Namespace(config_sha256=cp['sha256'],grant=pathlib.Path(gp['path']),grant_sha256=gp['sha256'],manifest=pathlib.Path(mp['path']),manifest_sha256=mp['sha256']))
 assert ctrl.verify_join(r,pinned_json(r['join']))
 assert result['outer_exit']==r['inner_result']['exit']==dict(success=0,nonzero=23,timeout=124)[mode]
 assert result['outer_joined'] and r['custody']['identity']==result['outer_identity']
 props=a.show(r['custody']['unit']);assert props['MainPID']=='0' and props['ExecMainStatus']=='199' and props['InvocationID']==r['service']['invocation']
 assert a.argv(r['custody']['unit'])==r['custody']['service_argv']==r['service']['identity']['argv']
 assert parse_exec_start(result['dbus_execstart']['raw'])[7]==r['service']['identity']['pid']
 assert props['MemoryMax']==str(3*GIB) and props['MemorySwapMax']=='0' and props['TasksMax']=='128'
 identities=[r['custody']['identity'],r['service']['identity'],*r['inner_result']['tracked']]
 observed=[dict(saved=x,observed=proc(x['pid'])) for x in identities]
 assert all(x['observed'] is None or x['observed']['starttime']!=x['saved']['starttime'] for x in observed)
 assert a.empty(r['custody']['cgroup']) and all(a.empty(c['lane_cgroups'][w]) for w in 'FA')
 for name,record in result['raw_receipts'].items():
  pinned(record['pin']);assert pathlib.Path(record['pin']['path']).read_text()==record['text']
 payload=(root/'receipts/stdout').read_text();outer=(root/'receipts/outer.stdout').read_text()
 assert payload==result['payload_stdout'] and (root/'receipts/stderr').read_text()==result['payload_stderr']==''
 records=parse(payload);assert validate(records,r,g,m);trust=validate_trust(outer,records,r,g,m);security=validate_security(outer,records)
 fixture=validate_fixture(records,mode,m,pathlib.Path(m['output_paths'][0]).read_bytes())
 assert result['attempt_allocated_bytes']<=4194304
 owned=r['inner_result']['owned_join'];assert owned['guard_error'] is None and owned['timed_out']==(mode=='timeout') and owned['remaining_identities']==[]
 if mode=='timeout':assert len(r['inner_result']['tracked'])>=4
 assert (pathlib.Path('/sys/fs/cgroup')/c['lane_cgroups']['A'].lstrip('/')/'memory.high').read_text().strip()==str(3*GIB)
 proofs.append(dict(attempt=attempt,exit=r['inner_result']['exit'],join=r['join'],normal_join_verified=True,identities=observed,fixture=fixture,trust_stages=trust['ordered_stages'],security_records=len(security),all_runtime_checks_passed=True))
 if mode=='timeout':
  assert result['verification_error']=="AssertionError('unexpected fixture/helper record count')" and len(records)==12
  corrected=copy.deepcopy(result);corrected.update(passed=True,strict_fixture_validated=fixture,wrapper_correction=dict(kind='local record schema only',reason='fixture prints in both parent and child after fork',original_result=pin(OUT/(attempt+'-result.json')),revalidation='revalidation-receipt.json',new_attempt=False))
  corrected.pop('verification_error');corrected.pop('traceback')
assert run(['git','-C',str(OUT.parents[2]),'rev-parse','HEAD'])['stdout'].strip()==HEAD
for pp in json.loads((OUT/'preflight-before-transitions.json').read_text())['pins']:pinned(pp)
assert l.snapshot()==before and pin(l.state)==statepin and pin(pathlib.Path(c['owner_state']))==ownerpin
assert not a.units('vkfworkers-*.service') and not a.units('vkfs0-*.service')
oldpins=json.loads((OUT/'dry-script-pins.json').read_text());changed=[]
for pp in oldpins:
 if pin(pp['path'])!=pp:changed.append(pp['path'])
assert changed==[str(OUT/'qualify.py')]
assert (OUT/'local-wrapper-correction-01/qualify.py').read_bytes() and pin(OUT/'local-wrapper-correction-01/qualify.py')['sha256']==next(p['sha256'] for p in oldpins if p['path']==str(OUT/'qualify.py'))
for path in OUT.glob('*.py'):compile(path.read_text(),str(path),'exec')
save('revalidation-receipt.json',dict(passed=True,scope='schema-only correction; no new attempt, service, publication, rotation or ledger write',before_state=statepin,after_state=pin(l.state),before_owners=ownerpin,after_owners=pin(pathlib.Path(c['owner_state'])),proofs=proofs,changed_operational_wrappers=changed,source_trace=dict(fixture=pin(OUT.parent/'storage-mount-repair-08/fixture.py'),fork_then_unconditional_print=True,expected_fork_records=2),seconds=time.monotonic()-start))
# Preserve original failed own reports at distinct archival names before publishing corrected review.
archive=OUT/'local-wrapper-correction-01'
(OUT/'live24-f-timeout-01-result.json').rename(archive/'original-result-from-live-run.json')
corrected['wrapper_correction']['original_result']=pin(archive/'original-result-from-live-run.json')
save('live24-f-timeout-01-result.json',corrected)
(OUT/'STOP.json').rename(archive/'original-stop-from-live-run.json')
(OUT/'dry-script-pins.json').rename(archive/'original-script-pins-from-dry-run.json')
save('dry-script-pins.json',[pin(path) for path in OUT.glob('*.py')])
print('PASS: captured F0/F23/F124 all revalidated, independent joins and state pins unchanged; local count error archived, no actual replay')
