import argparse, ctypes, datetime, errno, hashlib, json, os, pathlib, signal, subprocess, sys, time
from preflight import OUT, OLD, V2, REPO, save, pin, pinned, pinned_json, proc, same, Linux, run
from prepare import OWNER, COORD, write
from storage_admission import Ledger, GIB, VERSION

def main():
    parser=argparse.ArgumentParser();parser.add_argument('lane',choices=['F','A']);parser.add_argument('mode',choices=['success','nonzero','timeout']);a=parser.parse_args()
    os.umask(0o077);start=time.monotonic();utc=datetime.datetime.now(datetime.timezone.utc).isoformat()
    assert not (OUT/'STOP.json').exists(),'Prior failure; fresh repair chat required'
    cp=pin(V2/'runtime-config.json');config=pinned_json(cp)
    ledger=Ledger(V2/'direct-state-v2.json',OLD/'capacity.lock');data=ledger.snapshot()
    assert all('join' in r for r in data['phases'].values()),'Outstanding reservation'
    expected=[('F','success'),('F','nonzero'),('F','timeout'),('A','success'),('A','nonzero'),('A','timeout')]
    n=len(data['phases']);assert n<6 and (a.lane,a.mode)==expected[n]
    assert sum(r['phase_bytes'] for r in data['phases'].values())+4*1024**2<=64*1024**2
    setup=V2/'storage-live-04';attempt='live04-'+a.lane.lower()+'-'+a.mode+'-01'
    policy=data['lanes'][a.lane]['pin'];root=pathlib.Path(data['lanes'][a.lane]['policy']['root']['path'])/attempt
    assert not root.exists();root.mkdir(mode=0o700)
    assert run(['git','-C',str(REPO),'rev-parse','HEAD'])['stdout'].strip()=='5747ff8008ccd580b1b45ebc26560ffb0cda33fa'
    for p in json.loads((OLD/'storage-direct-v2-installed-20261017.json').read_text())['files']:pinned(p)
    python=pathlib.Path('/usr/bin/python3').resolve()
    inputs={str(python),str(OUT/'fixture.py')}
    for name in ['bwrap','systemd-run','systemctl','busctl','git']:inputs.add(str(pathlib.Path('/usr/bin',name).resolve()))
    for m in list(sys.modules.values()):
        p=getattr(m,'__file__',None)
        if p and str(p).startswith('/usr/lib/python3.14/') and pathlib.Path(p).is_file():inputs.add(str(pathlib.Path(p).resolve()))
    input_pins=[pin(pathlib.Path(p)) for p in sorted(inputs)]
    for p in input_pins:pinned(p)
    argv=[str(python),'-B',str(OUT/'fixture.py'),a.mode,str(root),str(OUT/'fixture.py'),os.readlink('/proc/self/ns/pid'),os.readlink('/proc/self/ns/net')]
    g=dict(storage_admission_version=VERSION,owner=OWNER,coordinator=COORD,worker=a.lane,iteration=4,
           attempt=attempt,phase_scope='tiny storage-only '+a.mode+' and namespace qualification',phase_bytes=4194304,
           ram_peak_bytes=(8 if a.lane=='A' else 3)*GIB,timeout_seconds=2 if a.mode=='timeout' else 10,
           source_commit='5747ff8008ccd580b1b45ebc26560ffb0cda33fa',inputs=input_pins,argv=argv,
           controller=pin(V2/'storage_controller.py'),helpers=[pin(V2/n) for n in ['storage_admission.py','storage_paths.py']],
           owned_processes=pin(OLD/'owned-processes.py'),resource_ledger=pin(OLD/'resource-ledger21_9gb-20261015.json'),
           predecessor_controller=data['lanes'][a.lane]['policy']['predecessor_controller'],storage_policy=policy,
           runtime_config=cp,owner_transition=None,authority=pin(OLD/'storage-live-04-visible-chat-grant.json'))
    gp=write(setup/(attempt+'-grant.json'),g)
    m={k:g[k] for k in ['owner','worker','iteration','attempt','phase_scope','phase_bytes','ram_peak_bytes','timeout_seconds','source_commit','inputs','argv','controller']}
    m.update(grant=gp,attempt_root=str(root),output_paths=[str(root/'cwd'/'payload.bin')])
    m.update({k:str(root/k) for k in ['cwd','tmpdir','cache','ccache','receipts']})
    mp=write(setup/(attempt+'-manifest.json'),m)
    op=pathlib.Path(config['owner_state']);state=json.loads(op.read_text());state['workers'][a.lane]=dict(thread=OWNER,iteration=4,grant=gp)
    tmp=op.with_name(attempt+'-owner-state.tmp');write(tmp,state);os.replace(tmp,op)
    fd=os.open(op.parent,os.O_RDONLY|os.O_DIRECTORY);os.fsync(fd);os.close(fd)
    high=None
    if a.lane=='A':
        cg=pathlib.Path('/sys/fs/cgroup')/config['lane_cgroups']['A'].lstrip('/')
        assert (cg/'memory.max').read_text().strip()==str(8*GIB) and (cg.parent/'memory.max').read_text().strip()==str(21*GIB)
        assert (cg/'memory.high').read_text().strip()==str(3*GIB)
        high=run(['systemctl','--user','set-property','--runtime','vkfworkers-a.slice','MemoryHigh=7G']);assert high['exit']==0
        assert (cg/'memory.high').read_text().strip()==str(7*GIB)
    command=['/usr/bin/python3','-B',str(V2/'storage_controller.py'),'--config-sha256',cp['sha256'],
             '--grant',gp['path'],'--grant-sha256',gp['sha256'],'--manifest',mp['path'],'--manifest-sha256',mp['sha256']]
    p=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,
        env={**os.environ,'PATH':'/home/viktor/.local/bin:'+os.environ['PATH'],'PYTHONDONTWRITEBYTECODE':'1'})
    ident=proc(p.pid)
    save(attempt+'-outer-start.json',dict(utc=utc,identity=ident,argv=command,grant=gp,manifest=mp,high_activation=high))
    stdout,stderr=p.communicate(timeout=90)
    observed=proc(p.pid);assert observed is None or observed['starttime']!=ident['starttime']
    data=ledger.snapshot();key=a.lane+':'+attempt;r=data['phases'].get(key)
    adapter=Linux();unit='vkfworkers-'+a.lane.lower()+'-'+attempt+'.service'
    props=adapter.show(unit);cg=config['lane_cgroups'][a.lane]+'/'+unit
    checks=dict(outer_joined=True,outer_identity=ident,outer_exit=p.returncode,unit=unit,properties=props,
                cgroup_empty=adapter.empty(cg),phase=r,stdout=stdout,stderr=stderr,elapsed_seconds=time.monotonic()-start,
                utc=utc,inputs_unchanged=all(pinned(x) is not None for x in input_pins))
    intended={'success':0,'nonzero':23,'timeout':124}[a.mode]
    checks['passed']=bool(r and r['stage']=='joined' and p.returncode==intended and props['ExecMainStatus']=='199' and checks['cgroup_empty'])
    if r and 'inner_result' in r:
        checks['owned_descendants']=[dict(saved=x,observed=proc(x['pid'])) for x in r['inner_result']['tracked']]
        checks['payload_stdout']=(root/'receipts'/'stdout').read_text()
        checks['payload_stderr']=(root/'receipts'/'stderr').read_text()
        if a.mode=='timeout':checks['passed']=checks['passed'] and r['inner_result']['owned_join']['timed_out'] and len(r['inner_result']['tracked'])>=3
    if a.lane=='A':
        checks['restored_memory_high']=(pathlib.Path('/sys/fs/cgroup')/config['lane_cgroups']['A'].lstrip('/')/'memory.high').read_text().strip()
        checks['passed']=checks['passed'] and checks['restored_memory_high']==str(3*GIB)
    save(attempt+'-result.json',checks)
    if not checks['passed']:save('STOP.json',dict(reason='Actual integration failed; no retry or source repair authorized',result=pin(OUT/(attempt+'-result.json')),phase=key))
    print(json.dumps({k:checks[k] for k in ['passed','outer_exit','elapsed_seconds','properties','stderr']},indent=2))
    return 0 if checks['passed'] else 1

if __name__=='__main__':sys.exit(main())
