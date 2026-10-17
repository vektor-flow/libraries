"""Read-only failure seal; no launches, ledger writes, retries or policy changes."""
import argparse,copy,hashlib,json,pathlib,time,os
from preflight import OUT,OLD,V2,STATE,OWNER,HEAD,save,pin,pinned,pinned_json,proc,Linux,run,mem
from storage_admission import Ledger
from storage_controller import Controller,parse_get_unit,parse_exec_start
from validate_security import parse
assert (OUT/'STOP.json').is_file()
start=time.monotonic();cp=pin(V2/'runtime-config.json');c=pinned_json(cp)
l=Ledger(STATE/'direct-state-v4.json',OLD/'capacity.lock',recovery_pin=c['recovery_authority'])
data=l.snapshot();l.check(data)
base=json.loads((OUT/'initial-terminal-proof.json').read_text())['state']
transitions=json.loads((OUT/'owner-transitions.json').read_text())['transitions']
expected=copy.deepcopy(base)
for w in 'FA':expected['lanes'][w]['transitions'].append(transitions[w])
key='F:live17-f-success-01';r=data['phases'][key]
expected['phases'][key]=r
assert expected==data and r['stage']=='joined' and r['inner_result']['exit']==-11
assert len(data['phases'])==5 and sum(x['phase_bytes'] for x in data['phases'].values())==20971520
assert not l.active_rows(data) and all(l.owner(data,w)==OWNER for w in 'FA')
gp,mp=r['grant'],r['manifest'];g,m=pinned_json(gp),pinned_json(mp)
args=argparse.Namespace(config_sha256=cp['sha256'],grant=pathlib.Path(gp['path']),grant_sha256=gp['sha256'],manifest=pathlib.Path(mp['path']),manifest_sha256=mp['sha256'])
ctrl=Controller(args);a=Linux();t=time.monotonic();assert ctrl.verify_join(r,pinned_json(r['join']))
ids=[r['custody']['identity'],r['service']['identity'],*r['inner_result']['tracked']]
observations=[dict(saved=i,observed=proc(i['pid'])) for i in ids]
assert all(x['observed'] is None or x['observed']['starttime']!=x['saved']['starttime'] for x in observations)
unit=r['custody']['unit'];props=a.show(unit)
obj=a.output(['busctl','--user','--json=short','call','org.freedesktop.systemd1','/org/freedesktop/systemd1','org.freedesktop.systemd1.Manager','GetUnit','s',unit])
raw=a.output(['busctl','--user','--json=short','get-property','org.freedesktop.systemd1',parse_get_unit(obj),'org.freedesktop.systemd1.Service','ExecStart'])
assert parse_exec_start(raw)[1]==r['custody']['service_argv'] and parse_exec_start(raw)[7]==r['service']['identity']['pid']
assert props['ExecMainStatus']=='199' and props['InvocationID']==r['service']['invocation'] and props['MainPID']=='0'
assert a.empty(r['service']['identity']['cgroup']) and all(a.empty(c['lane_cgroups'][w]) for w in 'FA')
save('independent-terminal-join.json',dict(verified=True,seconds=time.monotonic()-t,join=r['join'],properties=props,dbus_get_unit=obj,dbus_exec_start=raw,identities=observations,cgroups_empty=True))
root=pathlib.Path(m['receipts']);rawpins=[]
for path in sorted(root.iterdir()):
 if path.is_file():
  pp=pin(path);pinned(pp);rawpins.append(pp)
  dest=OUT/('raw-'+path.name)
  with dest.open('xb') as f:f.write(path.read_bytes());f.flush();os.fsync(f.fileno())
save('raw-receipt-pins.json',rawpins)
origin=parse((root/'outer.stdout').read_text());payload=parse((root/'stdout').read_text())
assert payload==[] and (root/'stderr').read_bytes()==b''
assert len(origin)==3
before,after,gate=origin
assert [x['private_workload_security'] for x in origin]==['origin-capability-drop-before','origin-capability-drop-after','policy-gate']
assert gate['stage']=='origin' and after['passed'] is True and after['error'] is None
for x in origin:
 assert x['observation_errors']==[] and x['label']=='unconfined'
 s=x['status'];assert s['Uid']==[str(os.getuid())]*4 and s['Gid']==[str(os.getgid())]*4
 assert s['Threads']==['1'] and s['NoNewPrivs']==['0']
 for n in ['CapInh','CapPrm','CapEff','CapAmb','CapBnd']:
  assert len(s[n])==1 and len(s[n][0])==16 and all(c in '0123456789abcdef' for c in s[n][0])
 for n in ['CapPrm','CapEff','CapAmb']:assert s[n]==['0000000000000000']
for k in ['Uid','Gid','Groups','Threads','CapBnd','NoNewPrivs']:assert before['status'][k]==after['status'][k]==gate['status'][k]
assert before['status']['CapInh']==['0000000800000000']
assert after['status']['CapInh']==gate['status']['CapInh']==['0000000000000000']
save('security-observations.json',dict(diagnostics=origin,origin_drop_verified=True,origin_gate_observed=True,pre_policy_observations=[],post_policy_observations=[],pre_mount_observations=[],post_mount_observations=[],fixture_output=[],environment_qualified=False))
assert run(['git','-C',str(OUT.parents[2]),'rev-parse','HEAD'])['stdout'].strip()==HEAD
for pp in json.loads((OUT/'preflight-before-transitions.json').read_text())['pins']:pinned(pp)
for pp in [g['controller'],*g['helpers'],*g['inputs'],gp,mp]:pinned(pp)
for rec in json.loads((OUT/'prepared.json').read_text())['records']:
 for pp in [rec['grant'],rec['manifest']]:pinned(pp)
 if rec['attempt']!='live17-f-success-01':assert not pathlib.Path(pinned_json(rec['manifest'])['attempt_root']).exists()
assert all(pin(pathlib.Path(pp['path']))==pp for pp in json.loads((OUT/'dry-script-pins.json').read_text()))
save('final-state.json',data)
save('final-owner-state.json',dict(pin=pin(pathlib.Path(c['owner_state'])),state=json.loads(pathlib.Path(c['owner_state']).read_text())))
publications=[]
for path in sorted(OUT.glob('publication-*-receipt.json')):
 receipt=json.loads(path.read_text());assert receipt['published'] is True
 for tag in ['before','after']:assert hashlib.sha256(bytes.fromhex(receipt[tag+'_hex'])).hexdigest()==receipt[tag+'_sha256']
 publications.append(pin(path))
assert len(publications)==2
assert bytes.fromhex(json.loads(path.read_text())['after_hex'])==pathlib.Path(c['owner_state']).read_bytes()
assert not a.units('vkfworkers-*.service') and not a.units('vkfs0-*.service')
summary=dict(passed=False,result='STOP: first F success case sandbox child SIGSEGV; exact AppArmor file_mmap denial recorded',owner=OWNER,coordinator=c['coordinator'],source_commit=HEAD,installed_v7_unchanged=True,old_rows_policies_recovery_events_unchanged=True,owners_rotated=True,owner_publications=publications,attempts=5,consumed_bytes=20971520,max_attempts=16,total_bytes=67108864,remaining_attempts=11,remaining_bytes=46137344,active_ram_intent=0,qualified_phases=0,executed_cases=['F:success'],unrun_cases=['F:nonzero','F:timeout','A:success','A:nonzero','A:timeout'],outer_exit=245,sandbox_exit=-11,service_exit=199,normal_join_verified=True,native_execution=False,retry=False,MemAvailable=mem(),finalization_seconds=time.monotonic()-start)
save('qualification-result.json',summary)
print(json.dumps(summary,indent=2))
