import datetime, json, os, pathlib, sys, time
from preflight import OUT, OLD, V2, REPO, save, pin, pinned, pinned_json, identity, physical, Linux, run
from storage_admission import Ledger, GIB, VERSION

OWNER='01a1490c-d736-79d2-b96f-8195d7406ff3'
COORD='01a14893-cb1e-7203-97dd-de3da44dcf31'

def write(path, obj):
    with path.open('x') as f:
        json.dump(obj,f,indent=2); f.write('\n'); f.flush(); os.fsync(f.fileno())
    path.chmod(0o600)
    return pin(path)

def main():
    start=time.monotonic(); os.umask(0o077)
    pf=json.loads((OUT/'preflight.json').read_text()); assert not pf['failures']
    authority=pin(OLD/'storage-live-04-visible-chat-grant.json'); a=pinned_json(authority)
    assert a['owner_thread']==OWNER and a['coordinator']==COORD
    assert run(['git','-C',str(REPO),'rev-parse','HEAD'])['stdout'].strip()==a['source_commit']
    assert not (V2/'direct-state-v2.json').exists() and not (V2/'runtime-config.json').exists()
    V2.chmod(0o700)
    setup=V2/'storage-live-04'; setup.mkdir(mode=0o700)
    held={}
    for unit in ['vkf-s0-synchronized-contexts.service','vkf-s0-synchronized-contexts.timer','vkf-s0-worker-done.path']:
        r=run(['systemctl','--user','show',unit,'-p','ActiveState','-p','MainPID'])
        assert r['exit']==0 and 'ActiveState=inactive' in r['stdout'];held[unit]=r
    mask=pathlib.Path('/run/user/1000/systemd/user/vkf-s0-synchronized-contexts.service')
    assert mask.is_symlink() and os.readlink(mask)=='/dev/null'
    held['runtime_mask']=str(mask)
    assert not Linux().units('vkfworkers-*.service') and not Linux().units('vkfs0-*.service')
    # Preserve the actual registry byte-for-byte; do not invent missing terminal records.
    registry_pin=next(p for p in pf['pins'] if p['path']==str(OLD/'live-capacity.json'))
    raw=pinned(registry_pin)
    (setup/'legacy-registry.json').write_bytes(raw)
    registry=pin(setup/'legacy-registry.json')
    legacy_joins={w:pf['lanes'][w]['terminal']['receipt'] for w in 'AF'}
    off=pinned_json(next(p for p in pf['pins'] if p['path']==str(OLD/'adopted-offload.json')))
    off.update(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),offload_job_live=False,
               offload_job_joined=True,actual_cgroup_processes=[],refresh_evidence=pin(OUT/'preflight.json'))
    off_pin=write(setup/'adopted-offload-terminal.json',off)
    policies=[];roots={}; lane_cgroups={}
    for w in 'FA':
        prior=pf['lanes'][w]
        for key, ident in prior['identities'].items(): assert identity(ident['path'])==ident
        used=physical(prior['identities']['old_volume']['path'])['used']
        carried=prior['carried_evidence'];pinned(carried['pin'])
        history=dict(worker=w,old_used=used,carried_charge=carried['value'],
                     carried_evidence=carried,preflight=pin(OUT/'preflight.json'),authority=authority)
        hp=write(setup/(w+'-history.json'),history)
        root=pathlib.Path('/mnt/development/CompilerOptimization')/('owner-'+COORD)/w/'direct-v2-20261017'
        assert not root.exists()
        root.mkdir(parents=True,mode=0o700); assert not any(root.iterdir())
        ri=identity(root);assert ri['uuid']=='d189b76f-1138-40a0-abdf-da48d249b679'
        roots[w]=str(root)
        inc_id='storage-live-04-additional64GiB-'+w
        inc=write(setup/(w+'-increment.json'),dict(worker=w,owner=OWNER,coordinator=COORD,id=inc_id,
            additional_bytes=a['additional_bytes_by_lane'][w],authority=authority))
        predecessor=OLD/('run-worker-latex074-build8gb-20261017.py' if w=='A' else 'run-worker-capacity21_9gb-20261015.py')
        policy=dict(version='direct-directory-v1',worker=w,owner=OWNER,coordinator=COORD,
            predecessor_ledger=pin(OLD/'resource-ledger21_9gb-20261015.json'),predecessor_controller=pin(predecessor),
            historical_evidence=hp,historical_charge=max(used,carried['value']),root=ri,
            **prior['identities'],increments=[dict(id=inc_id,bytes=a['additional_bytes_by_lane'][w],authority=inc)])
        policies.append(write(setup/(w+'-policy.json'),policy))
        lane_cgroups[w]=dict(x.split('=',1) for x in prior['lane_properties']['stdout'].splitlines())['ControlGroup']
    owner_state=setup/'owner-state.json'
    write(owner_state,dict(coordinator=COORD,authority=authority,workers={}))
    config=dict(version=VERSION,coordinator=COORD,legacy_launchers_held=True,hold_evidence=held,
        owner_state=str(owner_state),source_repository=str(REPO),approved_policies=policies,
        development_uuid='d189b76f-1138-40a0-abdf-da48d249b679',development_root='/mnt/development/CompilerOptimization',
        lane_cgroups=lane_cgroups,deployed_volumes=pin(OLD/'deployed-volumes.json'),legacy_registry=registry,
        legacy_registry_source=registry_pin,adopted_offload=off_pin,legacy_joins=legacy_joins,
        legacy_cgroups={w:pf['lanes'][w]['terminal']['expected_cgroup'] for w in 'AF'},authority=authority)
    cp=write(V2/'runtime-config.json',config)
    ledger=Ledger(V2/'direct-state-v2.json',OLD/'capacity.lock');ledger.initialize()
    for p in policies:ledger.enroll(p)
    save('enrollment.json',dict(config=cp,policies=policies,authority=authority,roots=roots,
         state=ledger.snapshot(),elapsed_seconds=time.monotonic()-start,held=held))
    print(json.dumps(dict(enrolled=list(ledger.snapshot()['lanes']),config=cp,elapsed=time.monotonic()-start)))

if __name__=='__main__': main()
