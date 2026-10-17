"""Strict parse of new v7 security diagnostics; never suppress JSON or observation errors."""
import json,os

def parse(text):
    return [json.loads(line) for line in text.splitlines() if line.strip()]

def validate_security(service_stdout,payload_records):
    origin=parse(service_stdout)
    diagnostics=[x for x in origin+payload_records if 'private_workload_security' in x]
    assert len(diagnostics)==5
    assert [d['private_workload_security'] for d in diagnostics]==['origin-capability-drop-before','origin-capability-drop-after','policy-gate','policy-gate','policy-gate']
    before,after,*gates=diagnostics
    assert [d['stage'] for d in gates]==['origin','pre','post']
    assert after['passed'] is True and after['error'] is None
    for d in diagnostics:
        assert d['observation_errors']==[] and d['status']['Uid']==[str(os.getuid())]*4 and d['status']['Gid']==[str(os.getgid())]*4
        for k in ['CapInh','CapPrm','CapEff','CapAmb','CapBnd']:
            v=d['status'][k];assert len(v)==1 and len(v[0])==16 and all(c in '0123456789abcdef' for c in v[0])
        for k in ['CapPrm','CapEff','CapAmb']:assert int(d['status'][k][0],16)==0
        if d is not before:assert int(d['status']['CapInh'][0],16)==0
    for k in ['Uid','Gid','Groups','Threads','CapBnd','NoNewPrivs']:assert after['status'][k]==before['status'][k]
    assert before['status']['Threads']==['1'] and before['label']==after['label']=='unconfined'
    for d in [before,after,*gates[:2]]:assert d['status']['NoNewPrivs']==['0']
    assert gates[0]['label']=='unconfined' and gates[1]['label']=='vkf-storage-pre-v1 (enforce)'
    assert gates[2]['status']['NoNewPrivs']==['1'] and int(gates[2]['status']['CapBnd'][0],16)==0
    assert gates[2]['label'].endswith(' (enforce)') and sorted(gates[2]['label'][:-10].split('//&'))==['bwrap','unpriv_bwrap']
    return diagnostics
