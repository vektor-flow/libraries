"""Fresh live07 grants and one-at-a-time qualification; no enrollment/recovery/reset."""
import argparse, datetime, json, os, pathlib, subprocess, sys, time, traceback
from preflight import OUT, OLD, V2, REPO, save, pin, pinned, pinned_json, proc, same, Linux, run, mem
from storage_admission import Ledger, GIB, VERSION
from storage_controller import Controller, parse_get_unit, parse_exec_start
from storage_paths import allocated
OWNER='01a14932-e9b3-7a33-bff0-0486c870eed7'
COORD='01a14893-cb1e-7203-97dd-de3da44dcf31'
HEAD='11c7b8ab0985575bda8e9554023c347e2430871e'
SETUP=V2/'storage-live-07'
EXPECTED=[(w,m) for w in 'FA' for m in ['success','nonzero','timeout']]

def write(p,obj):
    with p.open('x') as f:
        json.dump(obj,f,indent=2); f.write('\n'); f.flush(); os.fsync(f.fileno())
    p.chmod(0o600)
    return pin(p)

def context():
    cp=pin(V2/'runtime-config.json'); c=pinned_json(cp)
    l=Ledger(V2/'direct-state-v4.json',OLD/'capacity.lock',recovery_pin=c['recovery_authority'])
    return cp,c,l,l.snapshot()

def unchanged():
    assert run(['git','-C',str(REPO),'rev-parse','HEAD'])['stdout'].strip()==HEAD
    for p in json.loads((OUT/'preflight.json').read_text())['pins']: pinned(p)

def owner_write(c,state,tag):
    op=pathlib.Path(c['owner_state']);tmp=SETUP/(tag+'-owners.tmp')
    write(tmp,state);os.replace(tmp,op)
    fd=os.open(op.parent,os.O_RDONLY|os.O_DIRECTORY);os.fsync(fd);os.close(fd)

def prepare():
    assert not (OUT/'STOP.json').exists()
    unchanged();cp,c,l,data=context()
    assert len(data['phases'])==1 and not l.active_rows(data)
    a=pin(OLD/'storage-live-07-visible-chat-grant.json');authority=pinned_json(a)
    assert authority['owner_thread']==OWNER and authority['source_commit']==HEAD
    SETUP.mkdir(mode=0o700)
    python=pathlib.Path('/usr/bin/python3').resolve()
    inputs={str(python),str(OUT/'fixture.py')}
    for name in ['bwrap','systemd-run','systemctl','busctl','git']:inputs.add(str(pathlib.Path('/usr/bin',name).resolve()))
    for mod in list(sys.modules.values()):
        path=getattr(mod,'__file__',None)
        if path and str(path).startswith('/usr/lib/python3.14/') and pathlib.Path(path).is_file(): inputs.add(str(pathlib.Path(path).resolve()))
    pins=[pin(p) for p in sorted(inputs)]
    records=[];owners=dict(coordinator=COORD,authority=a,workers={})
    for w,mode in EXPECTED:
        attempt='live07-'+w.lower()+'-'+mode+'-01'
        root=pathlib.Path(data['lanes'][w]['policy']['root']['path'])/attempt
        assert not root.exists()
        argv=[str(python),'-B',str(OUT/'fixture.py'),mode,str(root),str(OUT/'fixture.py'),os.readlink('/proc/self/ns/pid'),os.readlink('/proc/self/ns/net')]
        g=dict(storage_admission_version=VERSION,owner=OWNER,coordinator=COORD,worker=w,iteration=7,
            attempt=attempt,phase_scope='tiny real v4 storage '+mode+' and namespace qualification',phase_bytes=4194304,
            ram_peak_bytes=(8 if w=='A' else 3)*GIB,timeout_seconds=2 if mode=='timeout' else 10,
            source_commit=HEAD,inputs=pins,argv=argv,controller=pin(V2/'storage_controller.py'),
            helpers=[pin(V2/n) for n in ['storage_admission.py','storage_paths.py','terminal_recovery.py']],
            owned_processes=pin(OLD/'owned-processes.py'),resource_ledger=pin(OLD/'resource-ledger21_9gb-20261015.json'),
            predecessor_controller=data['lanes'][w]['policy']['predecessor_controller'],storage_policy=data['lanes'][w]['pin'],
            runtime_config=cp,owner_transition=authority['owner_transitions'][w],authority=a,
            qualification_limits=dict(max_attempts=16,consumed_before_live07=1,total_bytes=67108864,consumed_bytes_before_live07=4194304,max_phase_bytes=4194304))
        gp=write(SETUP/(attempt+'-grant.json'),g)
        m={k:g[k] for k in ['owner','worker','iteration','attempt','phase_scope','phase_bytes','ram_peak_bytes','timeout_seconds','source_commit','inputs','argv','controller']}
        m.update(grant=gp,attempt_root=str(root),output_paths=[str(root/'cwd'/'payload.bin')])
        m.update({k:str(root/k) for k in ['cwd','tmpdir','cache','ccache','receipts']})
        mp=write(SETUP/(attempt+'-manifest.json'),m)
        records.append(dict(worker=w,mode=mode,attempt=attempt,grant=gp,manifest=mp))
        if w not in owners['workers']: owners['workers'][w]=dict(thread=OWNER,iteration=7,grant=gp)
    assert not pathlib.Path(c['owner_state']).exists()
    owner_write(c,owners,'initial')
    save('prepared.json',dict(records=records,config=cp,owners=owners,authority=a,source_commit=HEAD))
    print('Prepared six fresh pinned grants/manifests and owners-v4; no attempt launched')

def qualify(index):
    start=time.monotonic();assert not (OUT/'STOP.json').exists()
    unchanged(); cp,c,l,data=context();adapter=Linux()
    assert not l.active_rows(data)
    assert not adapter.units('vkfworkers-*.service') and not adapter.units('vkfs0-*.service'), 'overlap'
    for prior in range(index):assert json.loads((OUT/('live07-'+EXPECTED[prior][0].lower()+'-'+EXPECTED[prior][1]+'-01-result.json')).read_text())['passed']
    assert len(data['phases'])==1+index and len(data['phases'])<16
    assert sum(r['phase_bytes'] for r in data['phases'].values())+4194304<=67108864
    rec=json.loads((OUT/'prepared.json').read_text())['records'][index]
    gp,mp=rec['grant'],rec['manifest'];g,m=pinned_json(gp),pinned_json(mp)
    w,mode,attempt=rec['worker'],rec['mode'],rec['attempt'];key=w+':'+attempt
    assert mem()>=g['ram_peak_bytes']+2*GIB,'memory admission floor'
    root=pathlib.Path(m['attempt_root']);assert not root.exists();root.mkdir(mode=0o700)
    owners=json.loads(pathlib.Path(c['owner_state']).read_text());owners['workers'][w]=dict(thread=OWNER,iteration=7,grant=gp)
    owner_write(c,owners,attempt)
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
    # Seal raw evidence before independently evaluating it.
    save(attempt+'-observation.json',checks)
    try:
        assert r and r['stage']=='joined' and p.returncode=={'success':0,'nonzero':23,'timeout':124}[mode]
        assert props['ExecMainStatus']=='199' and checks['cgroup_empty'] and props['MainPID']=='0'
        assert checks['dbus_execstart']['parsed'][1]==r['custody']['service_argv']
        assert checks['dbus_execstart']['parsed'][7]==r['service']['identity']['pid']
        assert props['InvocationID']==r['service']['invocation']
        assert r['service']['identity']['argv']==r['custody']['service_argv'] and r['service']['identity']['cgroup']==cg
        assert r['custody']['identity']==ident
        args=argparse.Namespace(config_sha256=cp['sha256'],grant=pathlib.Path(gp['path']),grant_sha256=gp['sha256'],manifest=pathlib.Path(mp['path']),manifest_sha256=mp['sha256'])
        controller=Controller(args)
        assert controller.verify_join(r,pinned_json(r['join']))
        report=json.loads(checks['payload_stdout'].splitlines()[0])
        assert report['mode']==mode and report['outside_write_errno']==30 and report['writable_storage_mounts']==[str(root)]
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
