"""Joined bounded verification. All writes stay inside this directory."""
import ast
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
HERE=Path(__file__).resolve().parent

def identity(pid):
    proc=Path('/proc')/str(pid)
    return dict(pid=pid,starttime=int((proc/'stat').read_text().rsplit(')',1)[1].split()[19]),
        boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip())

def pin(p):return dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
report=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),runner=identity(os.getpid()),children=[])
for p in HERE.rglob('*.py'):ast.parse(p.read_text(),filename=str(p))
for script,filename in [('test_recovery.py','test-results.txt'),('test_inherited_repair.py','inherited-test-results.txt'),('observe_readonly.py','readonly-observation.json')]:
    started=time.monotonic()
    with (HERE/filename).open('w') as output:
        child=subprocess.Popen([sys.executable,'-B',str(HERE/script)],stdout=output,stderr=subprocess.STDOUT,cwd=HERE)
        ident=identity(child.pid)
        try:code=child.wait(timeout=50)
        except BaseException:
            child.kill();child.wait();raise
    report['children'].append(dict(script=script,identity=ident,exit=code,seconds=time.monotonic()-started,
        joined=True,proc_absent=not Path('/proc',str(child.pid)).exists()))
    assert code==0,filename
with tempfile.TemporaryDirectory(dir=HERE,prefix='patch-') as temp:
    args=['git','apply','--unsafe-paths','--directory='+temp]
    patch=(HERE/'candidate-new-files.patch').read_bytes()
    for argv in ([*args,'--check'],args):
        result=subprocess.run(argv,input=patch,capture_output=True,timeout=10,cwd=HERE.parents[2])
        assert result.returncode==0,result.stderr.decode()
    for p in (HERE/'candidate/storage-direct-v4').glob('*.py'):
        assert p.read_bytes()==(Path(temp)/'storage-direct-v4'/p.name).read_bytes()
report['patch_applied_byte_identical']=True
inputs=json.loads((HERE/'input-pins.json').read_text())
report['input_recheck']=[dict(**p,unchanged=pin(Path(p['path']))['sha256']==p['sha256']) for p in inputs]
assert all(p['unchanged'] for p in report['input_recheck'])
report['test_children']=json.loads((HERE/'owned-test-joins.json').read_text())
assert all(x['joined'] and x['proc_absent'] for x in report['test_children'])
report['ended_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
(HERE/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(passed=True,inputs=len(inputs),children=report['children'],test_children=len(report['test_children'])),indent=2))
