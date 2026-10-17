"""Authorized normal joined-F succession then unused-A API revocation; no recovery."""
import argparse,copy,json,os,pathlib,time,traceback
from preflight import OUT,OLD,V2,STATE,OWNER,PREVIOUS,HEAD,save,pin,pinned,pinned_json,Linux,run
from storage_admission import Ledger,VERSION
from storage_controller import Controller
import terminal_recovery as recovery
SETUP=V2/'storage-live-19'
KEY='F:live17-f-success-01'
join_calls=0
def immutable(path,data):
    with path.open('x') as f:
        json.dump(data,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
    path.chmod(0o400)
    fd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY);os.fsync(fd);os.close(fd)
    return pin(path)
def verify_normal_join(row,receipt):
    global join_calls
    assert row['owner']==PREVIOUS and row['stage']=='joined' and row['inner_result']['exit']==-11
    assert pinned_json(row['grant'])['attempt']=='live17-f-success-01'
    cp=pin(V2/'runtime-config.json');gp,mp=row['grant'],row['manifest']
    ctrl=Controller(argparse.Namespace(config_sha256=cp['sha256'],grant=pathlib.Path(gp['path']),grant_sha256=gp['sha256'],manifest=pathlib.Path(mp['path']),manifest_sha256=mp['sha256']))
    result=ctrl.verify_join(row,receipt)
    assert result is True
    join_calls+=1
    return result

def validate_before():
    pre=json.loads((OUT/'preflight-before-transitions.json').read_text())
    for pp in pre['pins']:pinned(pp)
    assert run(['git','-C',str(OUT.parents[2]),'rev-parse','HEAD'])['stdout'].strip()==HEAD
    auth=pin(OLD/'storage-live-19-visible-chat-grant.json');authority=pinned_json(auth)
    assert authority['owner_thread']==OWNER and authority['coordinator']=='01a14893-cb1e-7203-97dd-de3da44dcf31'
    cp=pin(V2/'runtime-config.json');c=pinned_json(cp)
    recovery.live14_authority(c['recovery_authority'],recovery.LIVE14_STATE,recovery.LIVE14_LOCK)
    assert c['preserved_record_authorities'][-1]==json.loads((OUT.parent/'storage-exec-mapping-repair-18/preserved-v7-bundle.json').read_text())
    ledger=Ledger(STATE/'direct-state-v4.json',OLD/'capacity.lock',recovery_pin=c['recovery_authority'])
    before=ledger.snapshot();assert before==pre['initial_state'] and not ledger.active_rows(before)
    assert len(before['phases'])==5 and len(before['recovery_events'])==2 and sum(r['phase_bytes'] for r in before['phases'].values())==20971520
    assert all(ledger.owner(before,w)==PREVIOUS for w in 'FA')
    adapter=Linux();assert not adapter.units('vkfworkers-*.service') and not adapter.units('vkfs0-*.service'),'overlap'
    owner_bytes=pathlib.Path(c['owner_state']).read_bytes()
    receipt=json.loads((OUT.parent/'storage-live-17/final-owner-state.json').read_text())
    assert receipt['pin']==pin(pathlib.Path(c['owner_state'])) and json.loads(owner_bytes)==receipt['state']
    recovery.protected_pin(receipt['pin'])
    oldowners=json.loads(owner_bytes);oldauth=pinned_json(oldowners['authority'])
    assert oldauth['owner_thread']==PREVIOUS and oldauth['coordinator']==c['coordinator']
    for w in 'FA':
        e=oldowners['workers'][w];g=pinned_json(e['grant'])
        assert e['thread']==g['owner']==PREVIOUS and e['iteration']==g['iteration']==17
        assert g['owner_transition']==before['lanes'][w]['transitions'][-1] and g['authority']==oldowners['authority']
        for pp in [g['controller'],*g['helpers'],g['runtime_config'],*g['inputs']]:pinned(pp)
    assert not SETUP.exists() and not SETUP.is_symlink()
    ledger.check(before);verify_normal_join(before['phases'][KEY],pinned_json(before['phases'][KEY]['join']))
    return pre,auth,authority,cp,c,ledger,before,adapter,owner_bytes

def transition(w,kind,data,c,auth,**fields):
    rec=data['lanes'][w]
    return dict(version=VERSION,worker=w,kind=kind,coordinator=c['coordinator'],policy=rec['pin'],previous=rec['transitions'][-1],from_owner=PREVIOUS,to_owner=OWNER,authority=auth,**fields)
def ftransition(data,c,auth):
    return transition('F','joined',data,c,auth,prior_phase=KEY,prior_join=data['phases'][KEY]['join'])
def forbidden_join(*args):raise AssertionError('No join permitted for unused A')
def main():
    start=time.monotonic();assert not (OUT/'STOP.json').exists()
    pre,auth,authority,cp,c,ledger,before,adapter,owner_bytes=validate_before()
    assert json.loads((OUT/'dry-validation.json').read_text())['passed']
    assert json.loads((OUT/'publication-tests.json').read_text())['success']
    for pp in json.loads((OUT/'dry-script-pins.json').read_text()):pinned(pp)
    SETUP.mkdir(mode=0o700)
    immutable(SETUP/'state-before-transitions.json',before)
    with (SETUP/'owners-before-transitions.raw').open('xb') as f:
        f.write(owner_bytes);f.flush();os.fsync(f.fileno())
    (SETUP/'owners-before-transitions.raw').chmod(0o400)
    immutable(SETUP/'owners-before-transitions.json',json.loads(owner_bytes))
    fp=immutable(SETUP/'F-owner-transition.json',ftransition(before,c,auth))
    save('F-rotation-intent.json',dict(api='Ledger.rotate_owner',transition=fp,kind='joined',prior_phase=KEY,prior_join=before['phases'][KEY]['join']))
    t=time.monotonic();ledger.rotate_owner(fp,verify_join=verify_normal_join);seconds=time.monotonic()-t
    after_f=ledger.snapshot();expected=copy.deepcopy(before);expected['lanes']['F']['transitions'].append(fp)
    assert after_f==expected and ledger.owner(after_f,'F')==OWNER and ledger.owner(after_f,'A')==PREVIOUS
    save('F-owner-transition-result.json',dict(transition=fp,seconds=seconds,normal_join_verified=True,join_calls=join_calls,owner_publication=False))
    with ledger.transaction() as locked:
        ledger.check(locked);assert locked==after_f and not ledger.active_rows(locked)
        snapshot=immutable(SETUP/'unused-A-state-after-F.json',locked)
    ap=immutable(SETUP/'A-owner-transition.json',transition('A','unused-owner-revocation',after_f,c,auth,unused_state=snapshot,phase_sequence=5))
    t=time.monotonic();ledger.rotate_owner(ap,verify_join=forbidden_join);aseconds=time.monotonic()-t
    after_a=ledger.snapshot();expected['lanes']['A']['transitions'].append(ap);assert after_a==expected
    assert all(ledger.owner(after_a,w)==OWNER for w in 'FA')
    save('A-owner-transition-result.json',dict(authority=auth,transition=ap,unused_state=snapshot,seconds=aseconds,phases_and_charges_unchanged=True,no_phase_or_join_created=True))
    final=immutable(SETUP/'state-after-transitions.json',after_a)
    save('owner-transitions.json',dict(authority=auth,transitions=dict(F=fp,A=ap),final_state=final,elapsed_seconds=time.monotonic()-start))
    print(json.dumps(dict(F='normal joined succession verified',A='unused revocation verified',phase_count=5,consumed_bytes=20971520,seconds=time.monotonic()-start)))
if __name__=='__main__':
    os.umask(0o077)
    try:main()
    except BaseException as exc:
        if not (OUT/'STOP.json').exists():save('STOP.json',dict(stage='owner-transitions',error=repr(exc),traceback=traceback.format_exc()))
        raise
