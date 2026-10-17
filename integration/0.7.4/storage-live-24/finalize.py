"""Read-only evidence seal, success or first actual failure; no retry/recovery."""
import argparse,copy,hashlib,json,pathlib,time,os
from preflight import OUT,OLD,V2,STATE,OWNER,HEAD,save,pin,pinned,pinned_json,proc,Linux,run,mem
from storage_admission import Ledger
from storage_controller import Controller,parse_get_unit,parse_exec_start
from validate_trust import parse

def main():
 start=time.monotonic();cp=pin(V2/'runtime-config.json');c=pinned_json(cp)
 l=Ledger(STATE/'direct-state-v4.json',OLD/'capacity.lock',recovery_pin=c['recovery_authority']);data=l.snapshot();l.check(data)
 base=json.loads((OUT/'preflight-before-transitions.json').read_text())['initial_state'];transitions=json.loads((OUT/'owner-transitions.json').read_text())['transitions'];expected=copy.deepcopy(base)
 for w in 'FA':expected['lanes'][w]['transitions'].append(transitions[w])
 new={k:r for k,r in data['phases'].items() if k not in base['phases']};expected['phases'].update(new)
 assert expected==data and all(l.owner(data,w)==OWNER for w in 'FA')
 attempts=len(data['phases']);consumed=sum(x['phase_bytes'] for x in data['phases'].values())
 assert attempts==6+len(new)<=16 and consumed==25165824+4194304*len(new)<=67108864
 a=Linux();joins=[];diagnostics={};results=[];rawpins=[]
 for key,r in new.items():
  gp,mp=r['grant'],r['manifest'];g,m=pinned_json(gp),pinned_json(mp)
  assert r['owner']==OWNER
  ctrl=Controller(argparse.Namespace(config_sha256=cp['sha256'],grant=pathlib.Path(gp['path']),grant_sha256=gp['sha256'],manifest=pathlib.Path(mp['path']),manifest_sha256=mp['sha256']))
  record=dict(phase=key,stage=r['stage'],verified=False)
  try:
   assert r['stage']=='joined'
   t=time.monotonic();assert ctrl.verify_join(r,pinned_json(r['join']))
   ids=[r['custody']['identity'],r['service']['identity'],*r['inner_result']['tracked']]
   observations=[dict(saved=i,observed=proc(i['pid'])) for i in ids]
   assert all(x['observed'] is None or x['observed']['starttime']!=x['saved']['starttime'] for x in observations)
   unit=r['custody']['unit'];props=a.show(unit)
   obj=a.output(['busctl','--user','--json=short','call','org.freedesktop.systemd1','/org/freedesktop/systemd1','org.freedesktop.systemd1.Manager','GetUnit','s',unit])
   raw=a.output(['busctl','--user','--json=short','get-property','org.freedesktop.systemd1',parse_get_unit(obj),'org.freedesktop.systemd1.Service','ExecStart'])
   assert parse_exec_start(raw)[1]==r['custody']['service_argv'] and parse_exec_start(raw)[7]==r['service']['identity']['pid']
   assert props['ExecMainStatus']=='199' and props['InvocationID']==r['service']['invocation'] and props['MainPID']=='0'
   assert a.empty(r['custody']['cgroup'])
   record.update(verified=True,seconds=time.monotonic()-t,join=r['join'],properties=props,dbus_get_unit=obj,dbus_exec_start=raw,identities=observations,cgroup_empty=True)
  except Exception as exc:record.update(error=type(exc).__name__+': '+str(exc),reservation_retained=True)
  joins.append(record)
  receipts=pathlib.Path(m['receipts']);attempt=g['attempt'];streams={}
  if receipts.exists():
   for path in sorted(receipts.iterdir()):
    if path.is_file():
     pp=pin(path);pinned(pp);rawpins.append(pp)
     with (OUT/(attempt+'-raw-'+path.name)).open('xb') as f:f.write(path.read_bytes());f.flush();os.fsync(f.fileno())
     streams[path.name]=path.read_text()
  parsed={}
  for name in ['outer.stdout','stdout']:
   try:parsed[name]=dict(records=parse(streams.get(name,'')),parse_error=None)
   except Exception as exc:parsed[name]=dict(records=None,parse_error=repr(exc))
  diagnostics[key]=dict(streams=parsed,payload_exists=pathlib.Path(m['output_paths'][0]).exists(),inner_result=r.get('inner_result'))
  p=OUT/(attempt+'-result.json');results.append(json.loads(p.read_text()) if p.exists() else dict(passed=False,attempt=attempt,missing_result=True))
  for pp in [g['controller'],*g['helpers'],*g['inputs'],gp,mp]:pinned(pp)
 assert run(['git','-C',str(OUT.parents[2]),'rev-parse','HEAD'])['stdout'].strip()==HEAD
 for pp in json.loads((OUT/'preflight-before-transitions.json').read_text())['pins']:pinned(pp)
 for pp in json.loads((OUT/'dry-script-pins.json').read_text()):pinned(pp)
 plans=json.loads((OUT/'prepared.json').read_text())['records']
 for rec in plans:
  for pp in [rec['grant'],rec['manifest']]:pinned(pp)
  if rec['worker']+':'+rec['attempt'] not in new:assert not pathlib.Path(pinned_json(rec['manifest'])['attempt_root']).exists()
 save('final-state.json',data);save('final-owner-state.json',dict(pin=pin(pathlib.Path(c['owner_state'])),state=json.loads(pathlib.Path(c['owner_state']).read_text())))
 save('independent-terminal-joins.json',joins);save('security-trust-observations.json',diagnostics);save('raw-receipt-pins.json',rawpins)
 publications=[]
 for path in sorted(OUT.glob('publication-*-receipt.json')):
  receipt=json.loads(path.read_text());assert receipt['published'] is True
  for tag in ['before','after']:assert hashlib.sha256(bytes.fromhex(receipt[tag+'_hex'])).hexdigest()==receipt[tag+'_sha256']
  publications.append(pin(path))
 assert len(publications)==1+len(new)
 assert bytes.fromhex(receipt['after_hex'])==pathlib.Path(c['owner_state']).read_bytes()
 overlap=dict(worker=sorted(a.units('vkfworkers-*.service')),legacy=sorted(a.units('vkfs0-*.service')),lanes_empty={w:a.empty(c['lane_cgroups'][w]) for w in 'FA'})
 save('final-overlap.json',overlap)
 launches=[json.loads(p.read_text())['utc'] for p in OUT.glob('*-outer-start.json')]
 if launches:
  kernel=run(['sudo','-n','journalctl','-k','--since',min(launches),'--no-pager','-o','short-iso','-n','500'])
  save('kernel-journal-readonly.json',kernel)
 (OUT/'host-final-mountinfo.txt').write_text(pathlib.Path('/proc/self/mountinfo').read_text())
 import private_workload
 save('host-final-context.json',dict(context=private_workload.context(),observation=private_workload.trust_observation()))
 active=l.active_rows(data);passed=len(results)==6 and all(x['passed'] for x in results) and all(x['verified'] for x in joins) and not active and not (OUT/'STOP.json').exists()
 summary=dict(passed=passed,result='QUALIFIED tiny six-case storage' if passed else 'STOP / UNQUALIFIED',owner=OWNER,coordinator=c['coordinator'],source_commit=HEAD,installed_v9_unchanged=True,old_rows_policies_recovery_events_unchanged=True,owners_rotated=True,owner_publications=publications,attempts=attempts,consumed_bytes=consumed,max_attempts=16,total_bytes=67108864,remaining_attempts=16-attempts,remaining_bytes=67108864-consumed,active_ram_intent=sum(x['ram_bytes'] for x in active),qualified_phases=sum(x['passed'] for x in results),executed_cases=list(new),unrun_cases=[r['worker']+':'+r['mode'] for r in plans if r['worker']+':'+r['attempt'] not in new],normal_joins_verified=all(x['verified'] for x in joins),native_execution=False,retry=False,MemAvailable=mem(),overlap=overlap,finalization_seconds=time.monotonic()-start)
 save('qualification-result.json',summary);print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
