"""Fresh live17 grants and one-at-a-time qualification; no enrollment/recovery/reset."""
import argparse, dataclasses, datetime, json, os, pathlib, subprocess, sys, time, traceback
from preflight import OUT, OLD, V2, STATE, REPAIR, REPO, save, pin, pinned, pinned_json, proc, same, Linux, run, mem
from storage_admission import Ledger, GIB, VERSION
from storage_controller import Controller, parse_get_unit, parse_exec_start, HELPERS
import private_workload
from publication import owner_write
from check_loaded import check as check_loaded
from storage_paths import allocated
OWNER='01a1498d-0c53-74c0-96a2-899999a3fc97'
COORD='01a14893-cb1e-7203-97dd-de3da44dcf31'
HEAD='ec72b6b21d813994a6e02c77164b8c3baf074ba0'
SETUP=V2/'storage-live-17'
EXPECTED=[(w,m) for w in 'FA' for m in ['success','nonzero','timeout']]

def write(p,obj):
    with p.open('x') as f:
        json.dump(obj,f,indent=2); f.write('\n'); f.flush(); os.fsync(f.fileno())
    p.chmod(0o400)
    return pin(p)

def context():
    cp=pin(V2/'runtime-config.json'); c=pinned_json(cp)
    l=Ledger(STATE/'direct-state-v4.json',OLD/'capacity.lock',recovery_pin=c['recovery_authority'])
    return cp,c,l,l.snapshot()

def unchanged():
    assert run(['git','-C',str(REPO),'rev-parse','HEAD'])['stdout'].strip()==HEAD
    for p in json.loads((OUT/'preflight-before-transitions.json').read_text())['pins']: pinned(p)

def build_plan(data,transitions,owner_bytes,writer):
    cp=pin(V2/'runtime-config.json');a=pin(OLD/'storage-live-17-visible-chat-grant.json')
    python=pathlib.Path('/usr/bin/python3').resolve()
    import ctypes, _ctypes, ctypes._endian
    assert ctypes.CDLL(None).capset
    mapped={str(pathlib.Path(line.split()[-1]).resolve()) for line in pathlib.Path('/proc/self/maps').read_text().splitlines() if len(line.split())>=6 and line.split()[-1].startswith('/') and pathlib.Path(line.split()[-1]).is_file()}
    assert any('/libffi.so.' in p for p in mapped)
    inputs={str(python),str(REPAIR/'fixture.py'),str(REPAIR/'effective_storage.py')}
    for name in ['bwrap','systemd-run','systemctl','busctl','git']:inputs.add(str(pathlib.Path('/usr/bin',name).resolve()))
    for mod in list(sys.modules.values()):
        path=getattr(mod,'__file__',None)
        if path and str(path).startswith('/usr/lib/python3.14/') and pathlib.Path(path).is_file(): inputs.add(str(pathlib.Path(path).resolve()))
    inputs.update(mapped)
    inputs.add(pinned_json(cp)['recovery_authority']['path'])
    inputs.update(p['path'] for p in private_workload.BINARIES+private_workload.POLICY_INPUTS)
    inputs.update(str(V2/n) for n in ['storage_controller.py','runtime-config.json',*HELPERS])
    pins=[pin(p) for p in sorted(inputs)]
    records=[];owners=json.loads(owner_bytes);owners.update(coordinator=COORD,authority=a)
    for w,mode in EXPECTED:
        attempt='live17-'+w.lower()+'-'+mode+'-01'
        root=pathlib.Path(data['lanes'][w]['policy']['root']['path'])/attempt
        assert not root.exists()
        argv=[str(python),'-B',str(REPAIR/'fixture.py'),mode,str(root),str(REPAIR/'fixture.py'),os.readlink('/proc/self/ns/pid'),os.readlink('/proc/self/ns/net')]
        g=dict(storage_admission_version=VERSION,owner=OWNER,coordinator=COORD,worker=w,iteration=17,
            attempt=attempt,phase_scope='tiny real v7 storage '+mode+' and namespace qualification',phase_bytes=4194304,
            ram_peak_bytes=(8 if w=='A' else 3)*GIB,timeout_seconds=2 if mode=='timeout' else 10,
            source_commit=HEAD,inputs=pins,argv=argv,controller=pin(V2/'storage_controller.py'),
            helpers=[pin(V2/n) for n in HELPERS],
            owned_processes=pin(OLD/'owned-processes.py'),resource_ledger=pin(OLD/'resource-ledger21_9gb-20261015.json'),
            predecessor_controller=data['lanes'][w]['policy']['predecessor_controller'],storage_policy=data['lanes'][w]['pin'],
            runtime_config=cp,owner_transition=transitions[w],authority=a,
            qualification_limits=dict(max_attempts=16,consumed_before_live17=4,total_bytes=67108864,consumed_bytes_before_live17=16777216,max_phase_bytes=4194304))
        gp=writer(SETUP/(attempt+'-grant.json'),g)
        m={k:g[k] for k in ['owner','worker','iteration','attempt','phase_scope','phase_bytes','ram_peak_bytes','timeout_seconds','source_commit','inputs','argv','controller']}
        m.update(grant=gp,attempt_root=str(root),output_paths=[str(root/'cwd'/'payload.bin')])
        m.update({k:str(root/k) for k in ['cwd','tmpdir','cache','ccache','receipts']})
        mp=writer(SETUP/(attempt+'-manifest.json'),m)
        records.append(dict(worker=w,mode=mode,attempt=attempt,grant=gp,manifest=mp))
        if mode=='success': owners['workers'][w]=dict(thread=OWNER,iteration=17,grant=gp)
    return records,owners

def prepare():
    assert not (OUT/'STOP.json').exists()
    unchanged();cp,c,l,data=context()
    assert len(data['phases'])==4 and not l.active_rows(data)
    a=pin(OLD/'storage-live-17-visible-chat-grant.json');authority=pinned_json(a)
    assert authority['owner_thread']==OWNER and authority['source_commit']==HEAD
    assert SETUP.is_dir()
    transitions=json.loads((OUT/'owner-transitions.json').read_text())['transitions']
    assert all(l.owner(data,w)==OWNER and data['lanes'][w]['transitions'][-1]==transitions[w] for w in 'FA')
    records,owners=build_plan(data,transitions,(SETUP/'owners-before-transitions.raw').read_bytes(),write)
    assert json.loads(pathlib.Path(c['owner_state']).read_text())==json.loads((SETUP/'owners-before-transitions.json').read_text())
    owner_write(c,owners,'initial',records)
    save('prepared.json',dict(records=records,config=cp,owners=owners,authority=a,source_commit=HEAD))
    print('Prepared six fresh pinned grants/manifests and owners-v4; no attempt launched')

def qualify(index):
    start=time.monotonic();assert not (OUT/'STOP.json').exists()
    assert index in range(len(EXPECTED))
    unchanged(); cp,c,l,data=context();adapter=Linux()
    assert not l.active_rows(data)
    assert not adapter.units('vkfworkers-*.service') and not adapter.units('vkfs0-*.service'), 'overlap'
    for prior in range(index):assert json.loads((OUT/('live17-'+EXPECTED[prior][0].lower()+'-'+EXPECTED[prior][1]+'-01-result.json')).read_text())['passed']
    assert len(data['phases'])==4+index and len(data['phases'])<16
    assert sum(r['phase_bytes'] for r in data['phases'].values())+4194304<=67108864
    rec=json.loads((OUT/'prepared.json').read_text())['records'][index]
    gp,mp=rec['grant'],rec['manifest'];g,m=pinned_json(gp),pinned_json(mp)
    w,mode,attempt=rec['worker'],rec['mode'],rec['attempt'];key=w+':'+attempt
    assert mem()>=g['ram_peak_bytes']+2*GIB,'memory admission floor'
    root=pathlib.Path(m['attempt_root']);assert not root.exists()
    owners=json.loads(pathlib.Path(c['owner_state']).read_text());owners['workers'][w]=dict(thread=OWNER,iteration=17,grant=gp)
    owner_write(c,owners,attempt,[rec])
    root.mkdir(mode=0o700)
    check_loaded(attempt)
    args=argparse.Namespace(config_sha256=cp['sha256'],grant=pathlib.Path(gp['path']),grant_sha256=gp['sha256'],manifest=pathlib.Path(mp['path']),manifest_sha256=mp['sha256'])
    controller=Controller(args)
    controller.current();l.check(data)
    host=controller.host(data)
    assert host[1]==0 and host[0]>=g['ram_peak_bytes']+2*GIB, 'memory/overlap floor'
    holds={}
    for u in ['vkf-s0-synchronized-contexts.service','vkf-s0-synchronized-contexts.timer','vkf-s0-worker-done.path']:
        holds[u]=run(['systemctl','--user','show',u,'-p','ActiveState','-p','MainPID'])
        assert holds[u]['exit']==0 and 'ActiveState=inactive' in holds[u]['stdout']
    assert os.readlink('/run/user/1000/systemd/user/vkf-s0-synchronized-contexts.service')=='/dev/null'
    save(attempt+'-prelaunch.json',dict(host=host,holds=holds,granted_bytes=g['phase_bytes'],consumed_attempts=len(data['phases']),consumed_bytes=sum(x['phase_bytes'] for x in data['phases'].values())))
    high=None
    if w=='A':
        cg=pathlib.Path('/sys/fs/cgroup')/c['lane_cgroups']['A'].lstrip('/')
        assert (cg/'memory.max').read_text().strip()==str(8*GIB) and (cg.parent/'memory.max').read_text().strip()==str(21*GIB)
        assert (cg/'memory.high').read_text().strip()==str(3*GIB)
        high=run(['systemctl','--user','set-property','--runtime','vkfworkers-a.slice','MemoryHigh=7G']);assert high['exit']==0
        assert (cg/'memory.high').read_text().strip()==str(7*GIB)
    command=['/usr/bin/python3','-B',str(V2/'storage_controller.py'),'--config-sha256',cp['sha256'],
        '--grant',gp['path'],'--grant-sha256',gp['sha256'],'--manifest',mp['path'],'--manifest-sha256',mp['sha256']]
    launch=time.monotonic()
    p=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,
        env={**os.environ,'PATH':'/home/viktor/.local/bin:'+os.environ['PATH'],'PYTHONDONTWRITEBYTECODE':'1'})
    ident=proc(p.pid)
    save(attempt+'-outer-start.json',dict(identity=ident,argv=command,grant=gp,manifest=mp,high_activation=high,utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    stdout,stderr=p.communicate(timeout=85);wall=time.monotonic()-launch
    assert proc(p.pid) is None or proc(p.pid)['starttime']!=ident['starttime']
    data=l.snapshot();r=data['phases'].get(key);unit='vkfworkers-'+w.lower()+'-'+attempt+'.service'
    props=adapter.show(unit);cg=c['lane_cgroups'][w]+'/'+unit
    checks=dict(outer_joined=True,outer_identity=ident,outer_exit=p.returncode,unit=unit,properties=props,
        cgroup_empty=adapter.empty(cg),phase=r,stdout=stdout,stderr=stderr,elapsed_seconds=time.monotonic()-start,
        controller_wall_seconds=wall,attempt_allocated_bytes=allocated(root),passed=False)
    if props['LoadState']=='loaded':
        objraw=adapter.output(['busctl','--user','--json=short','call','org.freedesktop.systemd1','/org/freedesktop/systemd1','org.freedesktop.systemd1.Manager','GetUnit','s',unit])
        raw=adapter.output(['busctl','--user','--json=short','get-property','org.freedesktop.systemd1',parse_get_unit(objraw),'org.freedesktop.systemd1.Service','ExecStart'])
        checks['dbus_execstart']=dict(get_unit=objraw,raw=raw,parsed=parse_exec_start(raw))
    if r and 'inner_result' in r:
        checks['owned_descendants']=[dict(saved=x,observed=proc(x['pid'])) for x in r['inner_result']['tracked']]
        checks['payload_stdout']=(root/'receipts'/'stdout').read_text();checks['payload_stderr']=(root/'receipts'/'stderr').read_text()
    for name in ['outer.stdout','outer.stderr','stdout','stderr','controller-failure.json','admission.json','service-join.json']:
        path=root/'receipts'/name
        if path.is_file():checks.setdefault('raw_receipts',{})[name]=dict(pin=pin(path),text=path.read_text())
    # Seal raw evidence before independently evaluating it.
    save(attempt+'-observation.json',checks)
    records=[json.loads(line) for line in checks.get('payload_stdout','').splitlines() if line.strip()]
    private_snaps=[x for x in records if 'private_workload_snapshot' in x]
    for no,snapshot in enumerate(private_snaps):
        rawpath=OUT/(attempt+'-private-'+str(no)+'-'+snapshot['private_workload_snapshot']+'-mountinfo.txt')
        with rawpath.open('x') as f:f.write(snapshot['mountinfo']);f.flush();os.fsync(f.fileno())
    checks['private_snapshots']=private_snaps
    snapshots=[x for x in records if x.get('stage')=='mount-snapshot']
    if snapshots:
        assert len(snapshots)==1
        with (OUT/(attempt+'-mountinfo.txt')).open('x') as f:
            f.write(snapshots[0]['mountinfo']);f.flush();os.fsync(f.fileno())
        checks['raw_mount_snapshot']=pin(OUT/(attempt+'-mountinfo.txt'))
    try:
        assert r and r['stage']=='joined'
        assert props['ExecMainStatus']=='199' and checks['cgroup_empty'] and props['MainPID']=='0'
        assert checks['dbus_execstart']['parsed'][1]==r['custody']['service_argv']
        assert checks['dbus_execstart']['parsed'][7]==r['service']['identity']['pid']
        assert props['InvocationID']==r['service']['invocation']
        assert r['service']['identity']['argv']==r['custody']['service_argv'] and r['service']['identity']['cgroup']==cg
        assert r['custody']['identity']==ident
        args=argparse.Namespace(config_sha256=cp['sha256'],grant=pathlib.Path(gp['path']),grant_sha256=gp['sha256'],manifest=pathlib.Path(mp['path']),manifest_sha256=mp['sha256'])
        controller=Controller(args)
        t=time.monotonic()
        assert controller.verify_join(r,pinned_json(r['join']))
        checks['independent_join']=dict(verified=True,seconds=time.monotonic()-t,join=r['join'])
        checks['all_identities']=[dict(saved=x,observed=proc(x['pid'])) for x in [r['custody']['identity'],r['service']['identity'],*r['inner_result']['tracked']]]
        assert all(x['observed'] is None or x['observed']['starttime']!=x['saved']['starttime'] for x in checks['all_identities'])
        checks['metrics']=run(['systemctl','--user','show',unit,'-p','MemoryPeak','-p','MemorySwapPeak','-p','CPUUsageNSec','-p','ExecMainStartTimestampMonotonic','-p','ExecMainExitTimestampMonotonic'])
        checks['A_memory_high_after_join']=(pathlib.Path('/sys/fs/cgroup')/c['lane_cgroups']['A'].lstrip('/')/'memory.high').read_text().strip()
        assert checks['A_memory_high_after_join']==str(3*GIB)
        assert props['MemoryMax']==str(g['ram_peak_bytes']) and props['MemorySwapMax']=='0' and props['TasksMax']=='128'
        assert not l.active_rows(l.snapshot()) and not adapter.units('vkfworkers-*.service')
        assert p.returncode==r['inner_result']['exit']=={'success':0,'nonzero':23,'timeout':124}[mode], 'unexpected payload exit: '+str(p.returncode)
        from validate_snapshots import validate
        checks['v7_snapshots_validated']=validate(records,r,g,m)
        from validate_security import validate_security
        checks['security_diagnostics']=validate_security(checks['raw_receipts']['outer.stdout']['text'],records)
        reports=[x for x in records if 'effective_storage' in x]
        assert len(snapshots)==len(reports)==1
        report=reports[0]
        assert report['mode']==mode and report['outside_readonly'] is True
        import hashlib
        proof=report['effective_storage']
        assert proof['mountinfo_sha256']==hashlib.sha256(snapshots[0]['mountinfo'].encode('utf-8','surrogateescape')).hexdigest()
        allowed=[row for row in proof['rows'] if row['result']=='charged-attempt']
        assert len(allowed)==1 and allowed[0]['path']==str(root) and allowed[0]['id']==proof['attempt_mount_id']
        assert report['pid_ns']!=g['argv'][-2] and report['net_ns']!=g['argv'][-1]
        assert checks['attempt_allocated_bytes']<=4194304
        assert not r['inner_result']['owned_join'].get('guard_error')
        if mode=='timeout':assert r['inner_result']['owned_join']['timed_out'] and len(r['inner_result']['tracked'])>=3
        else:assert not r['inner_result']['owned_join']['timed_out']
        if w=='A':
            checks['restored_memory_high']=(pathlib.Path('/sys/fs/cgroup')/c['lane_cgroups']['A'].lstrip('/')/'memory.high').read_text().strip()
            assert checks['restored_memory_high']==str(3*GIB)
        unchanged();assert not l.active_rows(l.snapshot());assert not adapter.units('vkfworkers-*.service')
        checks['passed']=True
    except BaseException as exc:
        checks['verification_error']=repr(exc);checks['traceback']=traceback.format_exc()
    save(attempt+'-result.json',checks)
    if not checks['passed']:raise RuntimeError('Unexpected live result; see '+attempt+'-result.json')
    print(json.dumps(dict(attempt=attempt,passed=True,exit=p.returncode,controller_wall_seconds=wall,allocated=checks['attempt_allocated_bytes'])))

if __name__=='__main__':
    os.umask(0o077)
    try:
        if sys.argv[1]=='prepare':prepare()
        else:qualify(int(sys.argv[1]))
    except BaseException as exc:
        if not (OUT/'STOP.json').exists():save('STOP.json',dict(reason=repr(exc),traceback=traceback.format_exc(),command=sys.argv))
        raise
