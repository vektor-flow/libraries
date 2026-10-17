"""Exact root-authorized succession through installed v6, real historical joins only."""
import argparse, copy, datetime, json, os, pathlib, time, traceback
from preflight import OUT, OLD, V2, STATE, OWNER, PREVIOUS, HEAD, save, pin, pinned, pinned_json, proc, Linux, run
from storage_admission import Ledger, VERSION
from storage_controller import Controller, parse_get_unit, parse_exec_start
SETUP=V2/'storage-live-14'

def immutable(path,data):
    with path.open('x') as f:
        json.dump(data,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
    path.chmod(0o400)
    fd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY);os.fsync(fd);os.close(fd)
    return pin(path)

def validate_before():
    pre=json.loads((OUT/'preflight-before-transitions.json').read_text())
    for pp in pre['pins']:pinned(pp)
    assert run(['git','-C',str(OUT.parents[2]),'rev-parse','HEAD'])['stdout'].strip()==HEAD
    auth=pin(OLD/'storage-live-14-visible-chat-grant.json');authority=pinned_json(auth)
    assert authority['owner_thread']==OWNER and authority['coordinator']=='01a14893-cb1e-7203-97dd-de3da44dcf31'
    cp=pin(V2/'runtime-config.json');c=pinned_json(cp)
    ledger=Ledger(STATE/'direct-state-v4.json',OLD/'capacity.lock',recovery_pin=c['recovery_authority'])
    before=ledger.snapshot();assert before==pre['initial_state'] and not ledger.active_rows(before)
    assert all(ledger.owner(before,w)==PREVIOUS for w in 'FA')
    adapter=Linux();assert not adapter.units('vkfworkers-*.service') and not adapter.units('vkfs0-*.service'),'overlap'
    owner_bytes=pathlib.Path(c['owner_state']).read_bytes()
    owner_receipt=json.loads((OUT.parent/'storage-live-12/final-owner-state.json').read_text())
    assert owner_receipt['pin']==pin(pathlib.Path(c['owner_state']))
    assert json.loads(owner_bytes)==owner_receipt['state']
    assert not SETUP.exists() and not SETUP.is_symlink()
    ledger.check(before)
    return pre,auth,authority,cp,c,ledger,before,adapter,owner_bytes


def transition(w,kind,data,c,auth,**fields):
    rec=data['lanes'][w]
    return dict(version=VERSION,worker=w,kind=kind,coordinator=c['coordinator'],policy=rec['pin'],previous=rec['transitions'][-1],from_owner=PREVIOUS,to_owner=OWNER,authority=auth,**fields)

def main():
    start=time.monotonic()
    assert not (OUT/'STOP.json').exists()
    pre,auth,authority,cp,c,ledger,before,adapter,owner_bytes=validate_before()
    SETUP.mkdir(mode=0o700)
    immutable(SETUP/'state-before-transitions.json',before)
    with (SETUP/'owners-before-transitions.raw').open('xb') as f:
        f.write(owner_bytes);f.flush();os.fsync(f.fileno())
    (SETUP/'owners-before-transitions.raw').chmod(0o400)
    immutable(SETUP/'owners-before-transitions.json',json.loads(owner_bytes))
    r=before['phases']['F:live09-f-success-01'];gp,mp=r['grant'],r['manifest']
    ctrl=Controller(argparse.Namespace(config_sha256=cp['sha256'],grant=pathlib.Path(gp['path']),grant_sha256=gp['sha256'],manifest=pathlib.Path(mp['path']),manifest_sha256=mp['sha256']))
    calls=[]
    def independent_join(row,receipt):
        t=time.monotonic()
        ok=ctrl.verify_join(row,receipt)
        unit=row['custody']['unit']
        obj=adapter.output(['busctl','--user','--json=short','call','org.freedesktop.systemd1','/org/freedesktop/systemd1','org.freedesktop.systemd1.Manager','GetUnit','s',unit])
        raw=adapter.output(['busctl','--user','--json=short','get-property','org.freedesktop.systemd1',parse_get_unit(obj),'org.freedesktop.systemd1.Service','ExecStart'])
        ids=[row['custody']['identity'],row['service']['identity'],*row['inner_result']['tracked']]
        observations=[dict(saved=i,observed=proc(i['pid'])) for i in ids]
        assert all(x['observed'] is None or x['observed']['starttime']!=x['saved']['starttime'] for x in observations)
        calls.append(dict(verified=ok,seconds=time.monotonic()-t,properties=adapter.show(unit),get_unit=obj,exec_start=raw,parsed=parse_exec_start(raw),identities=observations,join=row['join']))
        save('F-historical-independent-join.json',calls[-1])
        return ok
    fp=immutable(SETUP/'F-owner-transition.json',transition('F','joined',before,c,auth,prior_phase='F:live09-f-success-01',prior_join=r['join']))
    t=time.monotonic();ledger.rotate_owner(fp,verify_join=independent_join);fseconds=time.monotonic()-t
    after_f=ledger.snapshot();assert len(calls)==1 and ledger.owner(after_f,'F')==OWNER and ledger.owner(after_f,'A')==PREVIOUS
    expected=copy.deepcopy(before);expected['lanes']['F']['transitions'].append(fp);assert after_f==expected
    save('F-owner-transition-result.json',dict(authority=auth,transition=fp,verified_join=pin(OUT/'F-historical-independent-join.json'),seconds=fseconds,phases_and_charges_unchanged=True))
    with ledger.transaction() as locked:
        ledger.check(locked);assert locked==after_f and not ledger.active_rows(locked)
        snapshot=immutable(SETUP/'unused-A-state-after-F.json',locked)
    for lane in after_f['lanes'].values():assert not pathlib.Path(snapshot['path']).is_relative_to(pathlib.Path(lane['policy']['root']['path']))
    ap=immutable(SETUP/'A-owner-transition.json',transition('A','unused-owner-revocation',after_f,c,auth,unused_state=snapshot,phase_sequence=len(after_f['phases'])))
    t=time.monotonic();ledger.rotate_owner(ap,verify_join=independent_join);aseconds=time.monotonic()-t
    after_a=ledger.snapshot();expected['lanes']['A']['transitions'].append(ap);assert after_a==expected
    assert len(calls)==1 and all(ledger.owner(after_a,w)==OWNER for w in 'FA')
    save('A-owner-transition-result.json',dict(authority=auth,transition=ap,unused_state=snapshot,seconds=aseconds,phases_and_charges_unchanged=True,no_phase_or_join_created=True))
    final=immutable(SETUP/'state-after-transitions.json',after_a)
    save('owner-transitions.json',dict(authority=auth,transitions=dict(F=fp,A=ap),final_state=final,elapsed_seconds=time.monotonic()-start))
    print(json.dumps(dict(F='joined rotation verified',A='unused-owner-revocation verified',phase_count=len(after_a['phases']),consumed_bytes=sum(x['phase_bytes'] for x in after_a['phases'].values()),elapsed_seconds=time.monotonic()-start)))

if __name__=='__main__':
    os.umask(0o077)
    try:main()
    except BaseException as exc:
        if not (OUT/'STOP.json').exists():save('STOP.json',dict(stage='owner-transitions',error=repr(exc),traceback=traceback.format_exc()))
        raise
