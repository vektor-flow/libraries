"""Coordinator-authorized owner-file compare-and-publish; no ledger writes."""
import copy,hashlib,json,os,pathlib,stat,uuid
from preflight import OUT,OLD,V2,STATE,OWNER,HEAD,save,pin,pinned,pinned_json,Linux,run,REPO
from storage_admission import Ledger
from storage_paths import directory
from storage_controller import HELPERS
import private_workload
COORD='01a14893-cb1e-7203-97dd-de3da44dcf31'
SETUP=V2/'storage-live-17'
def owner_write(config,desired,tag,records):
    assert not (OUT/'STOP.json').exists()
    authority=pin(OLD/'storage-live-17-visible-chat-grant.json');auth=pinned_json(authority)
    assert auth['owner_thread']==OWNER and auth['coordinator']==COORD and auth['source_commit']==HEAD
    assert auth['owner_publication_authorized'] is True
    op=pathlib.Path(config['owner_state']);assert str(op)==auth['owner_publication_path']
    transitions=json.loads((OUT/'owner-transitions.json').read_text())['transitions']
    previous_receipts=sorted(OUT.glob('publication-*-receipt.json'))
    expected=(bytes.fromhex(json.loads(previous_receipts[-1].read_text())['after_hex']) if previous_receipts else (SETUP/'owners-before-transitions.raw').read_bytes())
    serial=len(previous_receipts);prefix=f'publication-{serial:02d}-{tag}'
    ledger=Ledger(STATE/'direct-state-v4.json',OLD/'capacity.lock',recovery_pin=config['recovery_authority'])
    with ledger.transaction() as data:
        ledger.check(data);assert not ledger.active_rows(data)
        assert all(ledger.owner(data,w)==OWNER and data['lanes'][w]['transitions'][-1]==transitions[w] for w in 'FA')
        assert config['coordinator']==COORD and run(['git','-C',str(REPO),'rev-parse','HEAD'])['stdout'].strip()==HEAD
        adapter=Linux();assert not adapter.units('vkfworkers-*.service') and not adapter.units('vkfs0-*.service')
        assert all(adapter.empty(config['lane_cgroups'][w]) for w in 'FA')
        for pp in transitions.values():pinned(pp);assert pinned_json(pp)['authority']==authority
        assert desired['authority']==authority and desired['coordinator']==COORD
        validate_selection(data,config,desired,tag,records,expected,transitions,authority)
        changed={'F','A'} if tag=='initial' else {records[0]['worker']}
        def before(actual,new):
            evidence=dict(before_hex=actual.hex(),after_hex=new.hex(),before_sha256=hashlib.sha256(actual).hexdigest(),after_sha256=hashlib.sha256(new).hexdigest(),ledger_snapshot=data,ledger_pin=pin(ledger.state),transitions=transitions,authority=authority,changed_workers=sorted(changed))
            save(prefix+'-intent.json',evidence)
            return evidence
        evidence=atomic_publish(op,expected,desired,before)
        save(prefix+'-receipt.json',dict(evidence,published=True))

def validate_selection(data,config,desired,tag,records,expected,transitions,authority,loader=pinned_json,verify=pinned):
    changed={'F','A'} if tag=='initial' else {records[0]['worker']}
    old=json.loads(expected)
    assert old['coordinator']==COORD and loader(old['authority'])['coordinator']==COORD
    for w,entry in old['workers'].items():
        if w not in changed:assert desired['workers'][w]==entry
    assert set(desired)==set(old) and set(desired['workers'])==set(old['workers'])
    assert all(desired[k]==old[k] for k in old if k not in ('coordinator','authority','workers'))
    for w in changed:
        entry=desired['workers'][w];assert set(entry)==set(old['workers'][w])=={'thread','iteration','grant'}
        rec=next(r for r in records if r['worker']==w and r['grant']==entry['grant'])
        g=loader(rec['grant']);m=loader(rec['manifest'])
        assert entry==dict(thread=OWNER,iteration=17,grant=rec['grant'])
        assert g['owner']==OWNER and g['worker']==w and g['iteration']==17 and g['attempt'].startswith('live17-')
        assert w+':'+g['attempt'] not in data['phases']
        assert g['authority']==authority and g['coordinator']==COORD and g['source_commit']==HEAD
        assert g['owner_transition']==transitions[w] and g['runtime_config']==pin(V2/'runtime-config.json')
        assert m['grant']==rec['grant'] and m['inputs']==g['inputs']
        assert g['controller']==pin(V2/'storage_controller.py') and g['helpers']==[pin(V2/n) for n in HELPERS]
        for pp in [g['controller'],*g['helpers'],*g['inputs'],rec['grant'],rec['manifest'],authority]:
            verify(pp)
            assert all(not pathlib.Path(pp['path']).is_relative_to(lane['policy']['root']['path']) for lane in data['lanes'].values())
        assert all(pp in g['inputs'] and pp in m['inputs'] for pp in private_workload.BINARIES+private_workload.POLICY_INPUTS+[config['recovery_authority']])

def atomic_publish(op,expected,desired,before):
    """Caller holds capacity.lock and has authenticated all authority/selection gates."""
    with directory(op.parent) as parent:
        ds=os.fstat(parent);assert ds.st_uid==os.getuid()!=0 and not ds.st_mode&0o022
        fd=os.open(op.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent)
        with os.fdopen(fd,'rb') as f:
            st=os.fstat(f.fileno());actual=f.read()
        assert stat.S_ISREG(st.st_mode) and st.st_nlink==1 and st.st_uid==os.getuid() and not st.st_mode&0o022
        assert actual==expected and hashlib.sha256(actual).digest()==hashlib.sha256(expected).digest()
        new=(json.dumps(desired,indent=2)+'\n').encode()
        evidence=before(actual,new)
        name='.owners-live17-'+uuid.uuid4().hex+'.tmp'
        fd=os.open(name,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o400,dir_fd=parent)
        with os.fdopen(fd,'wb') as f:
            assert stat.S_ISREG(os.fstat(f.fileno()).st_mode) and os.fstat(f.fileno()).st_uid==os.getuid()
            f.write(new);f.flush();os.fsync(f.fileno())
        os.replace(name,op.name,src_dir_fd=parent,dst_dir_fd=parent);os.fsync(parent)
        assert pin(op)['sha256']==hashlib.sha256(new).hexdigest()
        return evidence
