"""Read loaded raw bytes only; never invokes a compiler or loads policy."""
import hashlib,json,subprocess
from pathlib import Path
from preflight import OUT,save,pin,pinned
ROOT=OUT.parent/'storage-policy-setup-11'
def check(tag):
    program="""from pathlib import Path
import json
root=Path('/sys/kernel/security/apparmor/policy/profiles')
print(json.dumps([dict(path=str(p),name=(p/'name').read_text().strip(),mode=(p/'mode').read_text().strip(),raw=(p/'raw_data').read_bytes().hex()) for p in root.iterdir() if p.name.startswith(('bwrap.','unpriv_bwrap.','unprivileged_userns.','vkf-storage-'))]))
"""
    p=subprocess.run(['sudo','-n','/usr/bin/python3','-I','-B','-c',program],capture_output=True,text=True,timeout=15)
    assert p.returncode==0,p.stderr
    records=json.loads(p.stdout);byname={x['name']:x for x in records}
    assert len(records)==len(byname)==7
    existing=json.loads((ROOT/'root-loaded-uncompressed-comparison.json').read_text())
    new=json.loads((ROOT/'root-loaded-new-policy-check.json').read_text())
    for name,ref in [('bwrap',existing[0]),('unpriv_bwrap',existing[0]),('unprivileged_userns',existing[1])]:
        raw=bytes.fromhex(byname[name]['raw']);assert hashlib.sha256(raw).hexdigest()==ref['loaded_sha256'] and len(raw)==ref['loaded_bytes']
    combined=bytearray(new['compiled_bytes'])
    for ref in new['profiles']:
        r=next(x for x in records if Path(x['path']).name==ref['name']);raw=bytes.fromhex(r['raw'])
        assert hashlib.sha256(raw).hexdigest()==ref['sha256'] and len(raw)==ref['bytes']
        off=ref['exact_offset_in_compiled'];combined[off:off+len(raw)]=raw
    assert hashlib.sha256(combined).hexdigest()==new['compiled_sha256']
    v2=json.loads((OUT.parent/'storage-exec-mapping-repair-18/compiled-profile-contract.json').read_text())
    combined2=bytearray(v2['combined_bytes'])
    for ref in v2['profiles']:
        raw=bytes.fromhex(byname[ref['name']]['raw'])
        assert hashlib.sha256(raw).hexdigest()==ref['sha256'] and len(raw)==ref['bytes']
        combined2[ref['offset']:ref['offset']+len(raw)]=raw
    assert hashlib.sha256(combined2).hexdigest()==v2['combined_sha256']
    assert set(byname)=={'bwrap','unpriv_bwrap','unprivileged_userns','vkf-storage-pre-v1','vkf-storage-private-v1','vkf-storage-pre-v2','vkf-storage-private-v2'}
    assert all(x['mode']=='enforce' for x in records)
    save(tag+'-loaded-policy.json',dict(records=records,receipts=[pin(ROOT/n) for n in ['root-installed.json','root-loaded-uncompressed-comparison.json','root-loaded-new-policy-check.json']],exact=True))
    return True
if __name__=='__main__':check('initial')
