import datetime, hashlib, json, os, pathlib, subprocess, sys, time, traceback

OUT = pathlib.Path(__file__).resolve().parent
REPO = OUT.parents[2]
PROJECT = pathlib.Path('/home/viktor/Projects/Vektor Flow')
OLD = PROJECT/'.coordination/s0-plan-20261012/synchronized-contexts/independent-workers/storage20gb'
V2 = OLD/'storage-direct-v8'
STATE = OLD/'storage-direct-v4'
OWNER = '01a149a4-a1db-77a3-8094-f450e46d1ee8'
PREVIOUS = '01a1498d-0c53-74c0-96a2-899999a3fc97'
HEAD = '1b76a245c632e0b6b1b63eda740b14a49fc2f60d'
REPAIR = OUT.parent/'storage-mount-repair-08'
sys.path.insert(0, str(V2))
from storage_controller import Linux, pin, proc, mem, same
from storage_paths import identity, pinned, pinned_json
from storage_admission import physical

def save(name, data):
    p = OUT/name
    with p.open('x') as f:
        json.dump(data, f, indent=2); f.write('\n'); f.flush(); os.fsync(f.fileno())
    p.chmod(0o600)

def run(argv):
    p = subprocess.run(argv, text=True, capture_output=True, timeout=15)
    return dict(argv=argv, exit=p.returncode, stdout=p.stdout, stderr=p.stderr)

def main():
    # Fresh read-only preflight; no mutation or launch path.
    assert not (OUT/'STOP.json').exists()
    after = sys.argv[2]=='after'
    label=sys.argv[1]
    start = time.monotonic()
    evidence = dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), pins=[], checks={}, failures=[])
    paths = [OLD/'storage-live-19-visible-chat-grant.json', OLD/'storage-direct-v2-installed-20261017.json',
             OLD/'resource-ledger21_9gb-20261015.json', OLD/'run-worker-capacity21_9gb-20261015.py',
             OLD/'run-worker-latex074-build8gb-20261017.py', OLD/'owned-processes.py',
             OLD/'live-capacity.json', OLD/'adopted-offload.json', OLD/'deployed-volumes.json',
             OLD.parent/'state.json', OLD/'user-consolidation-hold-20261017.json']
    paths += [pathlib.Path(p['path']) for p in json.loads((OLD/'storage-direct-v2-installed-20261017.json').read_text())['files']]
    for p in paths: evidence['pins'].append(pin(p))
    for p in json.loads((OLD/'storage-direct-v2-installed-20261017.json').read_text())['files']: pinned(p)
    evidence['checks']['HEAD'] = run(['git','-C',str(REPO),'rev-parse','HEAD'])
    assert evidence['checks']['HEAD']['stdout'].strip() == HEAD
    evidence['checks']['git_status'] = run(['git','-C',str(REPO),'status','--short'])
    adapter = Linux()
    evidence['checks']['active_worker_services'] = sorted(adapter.units('vkfworkers-*.service'))
    evidence['checks']['active_legacy_services'] = sorted(adapter.units('vkfs0-*.service'))
    evidence['checks']['MemAvailable'] = mem()
    evidence['checks']['mount'] = run(['findmnt','-T','/mnt/development','-o','TARGET,SOURCE,FSTYPE,UUID'])
    evidence['checks']['system_dispatch'] = run(['systemctl','list-units','--all','--plain','--no-legend','*dispatch*'])
    evidence['checks']['user_timers'] = run(['systemctl','--user','list-timers','--all','--no-legend'])
    evidence['checks']['system_timers'] = run(['systemctl','list-timers','--all','--no-legend'])
    evidence['legacy_registry'] = json.loads((OLD/'live-capacity.json').read_text())
    evidence['lanes'] = {}
    state = json.loads((OLD.parent/'state.json').read_text())
    for lane in 'AF':
        root = pathlib.Path(state['workers'][lane]['profile']['writable_root'])
        volume = pathlib.Path(state['workers'][lane]['profile']['volume'])
        d = dict(old_used=physical(volume), identities={}, terminal={})
        for key,p in [('old_volume',volume),('old_workspace',volume/'workspace'),('old_workspace_alias',root)]:
            try: d['identities'][key] = identity(p)
            except Exception as exc: evidence['failures'].append(dict(lane=lane, check=key, error=repr(exc)))
        receipt = max((root/'receipts20gb').glob('*service-join.json'), key=lambda p:p.stat().st_mtime)
        rp = pin(receipt); r = pinned_json(rp)
        for p in (rp,r['grant'],r['manifest']): pinned(p); evidence['pins'].append(p)
        g = pinned_json(r['grant']); pinned(g['controller']); evidence['pins'].append(g['controller'])
        assert pinned_json(r['manifest'])['grant'] == r['grant']
        assert r['actual_service_joined'] is True and not same(r['identity'])
        props = adapter.show(r['unit'])
        lane_props = run(['systemctl','--user','show','vkfworkers-'+lane.lower()+'.slice','-p','ControlGroup','-p','MemoryMax','-p','MemoryHigh','-p','MemorySwapMax','-p','TasksMax'])
        d['lane_properties'] = lane_props
        parent = dict(x.split('=',1) for x in lane_props['stdout'].splitlines())['ControlGroup']
        cg = parent+'/'+r['unit']
        assert props['MainPID']=='0' and props['ActiveState'] in ('inactive','failed') and adapter.empty(cg)
        d['terminal'] = dict(receipt=rp, observed_properties=props, expected_cgroup=cg, cgroup_empty=True,
                             prior_identity=r['identity'], observed_prior_pid=proc(r['identity']['pid']))
        if props['LoadState']=='loaded': assert adapter.argv(r['unit'])==r['service_argv']
        carried_file = root/('iteration349/verification.json' if lane=='A' else 'iteration365-python-tokens01/reviewed-results.json')
        carried = json.loads(carried_file.read_text())
        field = 'lane_used_bytes' if lane=='A' else 'volume_used_bytes_before_summary'
        d['carried_evidence'] = dict(pin=pin(carried_file),field=field,value=carried[field])
        evidence['pins'].append(pin(carried_file))
        d['historical_charge'] = max(d['old_used']['used'],carried[field])
        evidence['lanes'][lane] = d
    off = json.loads((OLD/'adopted-offload.json').read_text())
    pinned(off['continuation_manifest']); evidence['pins'].append(off['continuation_manifest'])
    phase = pinned_json(off['continuation_manifest'])
    script = dict(path=str(pathlib.Path(off['continuation_manifest']['path']).parent/'offload.py'),sha256=phase['script_sha256'])
    pinned(script); evidence['pins'].append(script)
    props = adapter.show(off['service'])
    progress_path = pathlib.Path(off['progress_path']); progress = json.loads(progress_path.read_text())
    evidence['pins'].append(pin(progress_path))
    evidence['offload'] = dict(properties=props, previous_main_identity=off['main_identity'],
        observed_prior_pid=proc(off['main_identity']['pid']), cgroup=off['service_properties']['ControlGroup'],
        cgroup_empty=adapter.empty(off['service_properties']['ControlGroup']),progress_pin=pin(progress_path),
        progress_status=progress.get('status'), owned_children_joined=progress.get('owned_children_joined'))
    assert props['MainPID']=='0' and props['ActiveState'] in ('inactive','failed') and evidence['offload']['cgroup_empty']
    assert not same(off['main_identity']) and progress['owned_children_joined'] is True
    for p in ['/','/mnt/development','/mnt/vkf-storage-2tb']: evidence['checks']['physical:'+p]=physical(p)
    for lane in 'af':
        cg = pathlib.Path('/sys/fs/cgroup/user.slice/user-1000.slice/user@1000.service/vkfworkers.slice/vkfworkers-'+lane+'.slice')
        evidence['checks']['cgroup:'+lane] = {n:(cg/n).read_text().strip() for n in ['memory.max','memory.high','memory.swap.max','pids.max','cgroup.events','cgroup.procs']}
    evidence['checks']['development_identity'] = identity('/mnt/development')
    assert evidence['checks']['development_identity']['uuid']=='d189b76f-1138-40a0-abdf-da48d249b679'
    assert not evidence['checks']['active_worker_services'] and not evidence['checks']['active_legacy_services'], 'overlap'
    assert mem() >= 10*1024**3, 'memory admission floor'
    for unit in ['vkf-s0-synchronized-contexts.service','vkf-s0-synchronized-contexts.timer','vkf-s0-worker-done.path']:
        obs=run(['systemctl','--user','show',unit,'-p','ActiveState','-p','MainPID'])
        evidence['checks'][unit]=obs
        assert obs['exit']==0 and 'ActiveState=inactive' in obs['stdout']
    assert os.readlink('/run/user/1000/systemd/user/vkf-s0-synchronized-contexts.service')=='/dev/null'
    from storage_admission import Ledger
    authority=pinned_json(pin(OLD/'storage-live-19-visible-chat-grant.json'))
    cp=pin(V2/'runtime-config.json'); config=pinned_json(cp)
    ledger=Ledger(STATE/'direct-state-v4.json', OLD/'capacity.lock', recovery_pin=config['recovery_authority'])
    data=ledger.snapshot(); ledger.check(data)
    assert {'F:live04-f-success-01','F:live07-f-success-01','F:live09-f-success-01','F:live14-f-success-01','F:live17-f-success-01'} <= set(data['phases'])
    assert len(data['phases'])<=16
    assert 20971520<=sum(r['phase_bytes'] for r in data['phases'].values())<=67108864
    assert not ledger.active_rows(data)
    baseline=json.loads((OUT.parent/'storage-live-17/final-state.json').read_text())
    assert all(data['phases'][k]==v for k,v in baseline['phases'].items()) and data['recovery_events']==baseline['recovery_events']
    assert authority['owner_thread']==OWNER and authority['source_commit']==HEAD
    for w in 'FA':
        assert ledger.owner(data,w)==(OWNER if after else PREVIOUS)
        assert data['lanes'][w]['policy']==baseline['lanes'][w]['policy']
        assert data['lanes'][w]['transitions'][:len(baseline['lanes'][w]['transitions'])]==baseline['lanes'][w]['transitions']
        if after: assert data['lanes'][w]['transitions'][-1]==json.loads((OUT/'owner-transitions.json').read_text())['transitions'][w]
        for pp in data['lanes'][w]['transitions']: pinned(pp)
        cg=pathlib.Path('/sys/fs/cgroup')/config['lane_cgroups'][w].lstrip('/')
        assert (cg/'memory.max').read_text().strip()==str((8 if w=='A' else 3)*1024**3)
        assert (cg/'memory.swap.max').read_text().strip()=='0'
        assert adapter.empty(config['lane_cgroups'][w]), 'overlap: populated lane'
        assert (cg.parent/'memory.max').read_text().strip()==str(21*1024**3)
        assert (cg.parent/'memory.swap.max').read_text().strip()=='0'
        if w=='A': assert (cg/'memory.high').read_text().strip()==str(3*1024**3)
        evidence['lanes'][w]['direct_root_identity']=identity(data['lanes'][w]['policy']['root']['path'])
        evidence['lanes'][w]['direct_root_physical']=physical(data['lanes'][w]['policy']['root']['path'])
    assert pin(OLD/'live-capacity.json')==config['legacy_registry_source']
    from storage_controller import Controller
    import argparse
    r=data['phases']['F:live17-f-success-01'];gp,mp=r['grant'],r['manifest']
    ctrl=Controller(argparse.Namespace(config_sha256=cp['sha256'],grant=pathlib.Path(gp['path']),grant_sha256=gp['sha256'],manifest=pathlib.Path(mp['path']),manifest_sha256=mp['sha256']))
    jt=time.monotonic()
    verified=ctrl.verify_join(r,pinned_json(r['join']))
    assert verified and r['stage']=='joined' and r['inner_result']['exit']==-11
    ids=[r['custody']['identity'],r['service']['identity'],*r['inner_result']['tracked']]
    observed=[dict(saved=i,observed=proc(i['pid'])) for i in ids]
    assert all(x['observed'] is None or x['observed']['starttime']!=x['saved']['starttime'] for x in observed)
    evidence['fresh_independent_join']=dict(verified=verified,seconds=time.monotonic()-jt,join=r['join'],identities=observed,properties=adapter.show(r['custody']['unit']))
    evidence['combined_host_observation']=ctrl.host(data)
    assert evidence['combined_host_observation'][1]==0
    for p in json.loads((OUT.parent/'storage-exec-mapping-repair-18/root-v8-installed.json').read_text())['installed_files']:
        pinned(p); evidence['pins'].append(p)
    for bundle in config['preserved_record_authorities']:
        for p in [bundle['controller'],*bundle['helpers'],bundle['config']]:
            pinned(p); evidence['pins'].append(p)
    assert config['preserved_record_authorities'][-1]==json.loads((OUT.parent/'storage-exec-mapping-repair-18/preserved-v7-bundle.json').read_text())
    assert len(data['recovery_events'])==2
    artifact_pins=json.loads((REPAIR/'artifact-pins.json').read_text())
    if isinstance(artifact_pins,dict): raise RuntimeError('unexpected repair pin schema')
    for name in ['fixture.py','effective_storage.py']:
        pp=next(p for p in artifact_pins if p['path']==str(REPAIR/name))
        pinned(pp);evidence['pins'].append(pp)
    for p in [config['recovery_authority'],config['legacy_registry_source'],config['legacy_registry'],config['adopted_offload'],data['recovery_events'][0]['original_state']]:
        pinned(p);evidence['pins'].append(p)
    assert not evidence['failures'], 'legacy identity failures'
    import private_workload
    private_workload.verify_dependencies()
    evidence['dependency_checks']=dict(verified=True,binaries=private_workload.BINARIES,policy_inputs=private_workload.POLICY_INPUTS,absent=private_workload.ABSENT_INCLUDES)
    evidence['pins'] += private_workload.BINARIES + private_workload.POLICY_INPUTS
    evidence['initial_state']=data
    evidence['initial_state_pin']=pin(STATE/'direct-state-v4.json')
    evidence['elapsed_seconds'] = time.monotonic()-start
    save(label+'-resources.json',evidence)
    print(json.dumps(dict(failures=evidence['failures'], lanes={k:dict(H=v['historical_charge'],old_used=v['old_used']) for k,v in evidence['lanes'].items()},elapsed=evidence['elapsed_seconds'],checks=evidence['checks']['system_dispatch']),indent=2))

if __name__ == '__main__':
    try: main()
    except BaseException as exc:
        save('STOP.json',dict(reason=str(exc),traceback=traceback.format_exc(),stage='read-only-evidence-seal'))
        raise
