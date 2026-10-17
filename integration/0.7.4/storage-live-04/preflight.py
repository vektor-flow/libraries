import datetime, hashlib, json, os, pathlib, subprocess, sys, time, traceback

OUT = pathlib.Path(__file__).resolve().parent
REPO = OUT.parents[2]
PROJECT = pathlib.Path('/home/viktor/Projects/Vektor Flow')
OLD = PROJECT/'.coordination/s0-plan-20261012/synchronized-contexts/independent-workers/storage20gb'
V2 = OLD/'storage-direct-v2'
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
    start = time.monotonic()
    evidence = dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), pins=[], checks={}, failures=[])
    paths = [OLD/'storage-live-04-visible-chat-grant.json', OLD/'storage-direct-v2-installed-20261017.json',
             OLD/'resource-ledger21_9gb-20261015.json', OLD/'run-worker-capacity21_9gb-20261015.py',
             OLD/'run-worker-latex074-build8gb-20261017.py', OLD/'owned-processes.py',
             OLD/'live-capacity.json', OLD/'adopted-offload.json', OLD/'deployed-volumes.json',
             OLD.parent/'state.json', OLD/'user-consolidation-hold-20261017.json']
    paths += [pathlib.Path(p['path']) for p in json.loads((OLD/'storage-direct-v2-installed-20261017.json').read_text())['files']]
    for p in paths: evidence['pins'].append(pin(p))
    for p in json.loads((OLD/'storage-direct-v2-installed-20261017.json').read_text())['files']: pinned(p)
    evidence['checks']['HEAD'] = run(['git','-C',str(REPO),'rev-parse','HEAD'])
    assert evidence['checks']['HEAD']['stdout'].strip() == '5747ff8008ccd580b1b45ebc26560ffb0cda33fa'
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
    evidence['elapsed_seconds'] = time.monotonic()-start
    save('preflight.json',evidence)
    print(json.dumps(dict(failures=evidence['failures'], lanes={k:dict(H=v['historical_charge'],old_used=v['old_used']) for k,v in evidence['lanes'].items()},elapsed=evidence['elapsed_seconds'],checks=evidence['checks']['system_dispatch']),indent=2))

if __name__ == '__main__': main()
