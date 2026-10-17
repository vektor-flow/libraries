"""ROOT-ONLY FUTURE RECIPE. Not executed by preparation11.

Requires an independently issued, pinned real root decision. Each step is one-shot.
No launch function: the installed controller remains the only execution path.
"""
import argparse
import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import uuid

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import adapter as a

def decision(ref):
    d=a.load_pin(ref);s=a.static_contract()
    a.require(d['coordinator']==a.COORDINATOR and d['native_execution'] is True
              and d['owner_rotation_authorized'] is True
              and d['owner_file_publication_authorized'] is True,
              'genuine separate root execution/rotation/publication authorization required')
    a.require(d['source_contract']==a.pin(HERE/'source-contract.json')
              and d['source_commit']==s['source_commit']==a.current_head(), 'root seal/HEAD decision')
    a.require(d['worker']=='A' and d['ram_bytes']==8*a.GIB and d['disk_bytes']==a.GIB
              and d['timeout_seconds']==1200 and d['observed_only_toolchain_accepted'] is True,
              'root resource/toolchain decision required')
    a.require(isinstance(d['owner'],str) and d['owner'] and type(d['iteration']) is int
              and d['iteration']>24, 'fresh root execution owner/iteration required')
    a.require(d['boot']==Path('/proc/sys/kernel/random/boot_id').read_text().strip(), 'boot changed')
    q=a.load_pin(s['qualification_review'])
    a.require(d['boot']==q['boot'] and q['v6_bundle']==s['v6_bundle'], 'qualified installed bundle')
    for p in q['evidence']:a.verify(p)
    config=a.load_pin(s['v6_bundle']['config'])
    root=a.canonical(d['protected_directory'])
    a.protected([str(root),ref['path']], [a.load_pin(p)['root']['path'] for p in config['approved_policies']])
    a.require(root.is_relative_to(Path(config['owner_state']).parent.parent/'storage-direct-v9'),
              'explicit protected v9 authority directory required')
    a.require(a.re.fullmatch(r'[A-Za-z0-9_.-]+',d['attempt']) and d['attempt'] not in ('.','..'),'fresh attempt component')
    return d,s,config,root

def immutable(path,data):
    with path.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
    path.chmod(0o400)
    fd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)
    return a.pin(path)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('step',choices=['rotate','export','publish'])
    p.add_argument('--decision',required=True);p.add_argument('--decision-sha256',required=True)
    args=p.parse_args();ref=dict(path=args.decision,sha256=args.decision_sha256)
    d,s,config,root=decision(ref)  # NULL template stops before operational imports/writes.
    v9=Path(s['v6_bundle']['config']['path']).parent
    sys.path.insert(0,str(v9))
    from storage_admission import Ledger,VERSION
    from storage_controller import Controller,Linux
    from storage_paths import pinned_json,pinned,directory
    import private_workload
    ledger=Ledger(Path(s['state_path']),Path(s['lock_path']),recovery_pin=config['recovery_authority'])
    linux=Linux()
    def quiescent(data):
        ledger.check(data)
        assert not ledger.active_rows(data)
        assert not linux.units('vkfworkers-*.service') and not linux.units('vkfs0-*.service')
        assert all(linux.empty(config['lane_cgroups'][w]) for w in 'AF')
    def verify_join(row,receipt):
        gp,mp=row['grant'],row['manifest']
        c=Controller(argparse.Namespace(config_sha256=s['v6_bundle']['config']['sha256'],
             grant=Path(gp['path']),grant_sha256=gp['sha256'],
             manifest=Path(mp['path']),manifest_sha256=mp['sha256']))
        return c.verify_join(row,receipt)

    if args.step=='rotate':
        assert not root.exists(),'fresh authority directory only'
        before=ledger.snapshot();quiescent(before)
        phases=[(k,r) for k,r in before['phases'].items() if r['worker']=='A']
        key,row=max(phases,key=lambda x:x[1]['sequence'])
        assert key=='A:live24-a-timeout-01' and row['stage']=='joined'
        assert ledger.owner(before,'A')=='01a149d1-1ba6-77f0-904a-23fc7490075b'
        assert row['owner']==ledger.owner(before,'A') and verify_join(row,pinned_json(row['join'])) is True
        root.mkdir(mode=0o700)
        immutable(root/'state-before.json',a.encoded(before))
        immutable(root/'owners-before.raw',Path(config['owner_state']).read_bytes())
        transition=dict(version=VERSION,worker='A',kind='joined',coordinator=a.COORDINATOR,
            policy=before['lanes']['A']['pin'],previous=before['lanes']['A']['transitions'][-1],
            from_owner=row['owner'],to_owner=d['owner'],authority=ref,prior_phase=key,prior_join=row['join'])
        tp=immutable(root/'A-owner-transition.json',a.encoded(transition))
        # Installed API independently verifies latest join again under capacity.lock.
        ledger.rotate_owner(tp,verify_join=verify_join)
        after=ledger.snapshot();expected=copy.deepcopy(before)
        expected['lanes']['A']['transitions'].append(tp)
        assert after==expected and ledger.owner(after,'A')==d['owner']
        immutable(root/'state-after.json',a.encoded(after))
        immutable(root/'A-owner-receipt.json',a.encoded(dict(coordinator=a.COORDINATOR,worker='A',
            owner=d['owner'],iteration=d['iteration'],transition=tp,rotation_completed=True,
            before=a.pin(root/'state-before.json'),after=a.pin(root/'state-after.json'),authority=ref)))

    elif args.step=='export':
        tp=a.pin(root/'A-owner-transition.json');op=a.pin(root/'A-owner-receipt.json')
        data=ledger.snapshot();quiescent(data)
        assert data['lanes']['A']['transitions'][-1]==tp and ledger.owner(data,'A')==d['owner']
        request={k:d[k] for k in ('coordinator','native_execution','worker','ram_bytes','disk_bytes',
            'timeout_seconds','source_commit','owner','iteration','attempt','boot','observed_only_toolchain_accepted')}
        request.update(phase='compiler',qualification_review=s['qualification_review'],owner_receipt=op,
            owner_transition=tp,publication_authorization=ref,publication_receipt_path=str(root/'publication.json'),
            grant_path=str(root/'grant.json'),manifest_path=str(root/'manifest.json'))
        a.evidence(request,s)
        a.save(HERE/'root-inputs.json',request)

    elif args.step=='publish':
        packet=HERE/'root-packet'
        c=a.read(packet/'contract.json');r=c['request']
        assert r==a.read(HERE/'root-inputs.json') and r['publication_authorization']==ref
        a.evidence(r,s)
        gp0=a.pin(packet/'grant.candidate.json');mp0=a.pin(packet/'manifest.candidate.json')
        g=a.load_pin(gp0);m=a.load_pin(mp0)
        gp=dict(path=r['grant_path'],sha256=gp0['sha256']);mp=dict(path=r['manifest_path'],sha256=mp0['sha256'])
        assert m['grant']==gp and all(m[k]==g[k] for k in a.MATCH)
        assert g['owner']==d['owner'] and g['iteration']==d['iteration'] and g['attempt']==d['attempt']
        assert g['controller']==s['v6_bundle']['controller'] and g['runtime_config']==s['v6_bundle']['config']
        assert g['helpers']==s['v6_bundle']['helpers'] and g['phase_scope']=='compiler'
        assert (g['ram_peak_bytes'],g['phase_bytes'],g['timeout_seconds'])==(8*a.GIB,a.GIB,1200)
        assert g['source_commit']==d['source_commit'] and all(x in g['inputs'] for x in s['pins'])
        private_workload.runtime_view(m)
        for pp in g['inputs']:pinned(pp)
        assert immutable(Path(gp['path']),Path(gp0['path']).read_bytes())==gp
        assert immutable(Path(mp['path']),Path(mp0['path']).read_bytes())==mp
        expected=(root/'owners-before.raw').read_bytes()
        # Reuse the exact reviewed live24 atomic primitive, not its tiny-case wrapper.
        source=HERE.parent/'storage-live-24/publication.py'
        tree=ast.parse(source.read_text())
        function=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='atomic_publish')
        namespace=dict(os=os,stat=stat,uuid=uuid,json=json,hashlib=hashlib,directory=directory,pin=a.pin)
        exec(compile(ast.Module(body=[function],type_ignores=[]),str(source),'exec'),namespace)
        with ledger.transaction() as data:
            quiescent(data)
            assert data['lanes']['A']['transitions'][-1]==r['owner_transition'] and ledger.owner(data,'A')==r['owner']
            assert 'A:'+g['attempt'] not in data['phases'] and a.current_head()==d['source_commit']
            old=json.loads(expected);desired=copy.deepcopy(old)
            desired['authority']=ref
            desired['workers']['A']=dict(grant=gp,thread=r['owner'],iteration=r['iteration'])
            assert desired['workers']['F']==old['workers']['F']
            def before(actual,new):
                evidence=dict(before_sha256=hashlib.sha256(actual).hexdigest(),after_sha256=hashlib.sha256(new).hexdigest(),
                              before_hex=actual.hex(),after_hex=new.hex(),ledger_pin=a.pin(s['state_path']))
                immutable(root/'publication-intent.json',a.encoded(evidence));return evidence
            actual=namespace['atomic_publish'](Path(config['owner_state']),expected,desired,before)
            immutable(root/'publication.json',a.encoded(dict(actual,coordinator=a.COORDINATOR,published=True,
                under_capacity_lock=True,grant=gp,manifest=mp,owner_transition=r['owner_transition'],
                owner_entry=desired['workers']['A'],authorization=ref)))
    print(json.dumps(dict(step=args.step,completed=True,launch_performed=False)))

if __name__=='__main__':main()
