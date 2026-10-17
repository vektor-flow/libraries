"""Reproduce final bounded fixtures and isolated patch application; no shared-source writes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
out=a.output.resolve();out.mkdir()
candidate=HERE/'candidate';target=candidate/'integration/0.7.4/native-primitive-runner'
records=[]
def proc(pid):
    try:
        f=(Path('/proc')/str(pid)/'stat').read_text().rsplit(')',1)[1].split()
        return dict(pid=pid,starttime=int(f[19]))
    except FileNotFoundError:return None

def run(argv,cwd,seconds,label):
    with (out/(label+'.stdout')).open('xb') as stdout,(out/(label+'.stderr')).open('xb') as stderr:
        start=time.monotonic()
        child=subprocess.Popen(argv,cwd=cwd,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','GIT_CEILING_DIRECTORIES':str(out)},stdout=stdout,stderr=stderr)
        ident=proc(child.pid)
        try:code=child.wait(timeout=seconds)
        except subprocess.TimeoutExpired:
            child.kill();child.wait();raise
        rec=dict(argv=argv,cwd=str(cwd),identity=ident,exit=code,seconds=time.monotonic()-start,joined=True,identity_absent=proc(child.pid)!=ident)
        records.append(rec)
        (out/'child-joins.json').write_text(json.dumps(records,indent=2)+'\n')
        assert code==0 and rec['identity_absent'],rec

def pin(f):return dict(path=str(f),sha256=hashlib.sha256(f.read_bytes()).hexdigest())
run(['/usr/bin/python3','-B',str(target/'test_runner.py'),'--repo',str(REPO),'--artifacts',str(out/'fixtures')],REPO,45,'tests')
# Apply only inside a new owned disposable directory, never the shared repository.
apply=out/'patch-application';apply.mkdir()
run(['git','apply','--check',str(HERE/'candidate-new-files.patch')],apply,10,'patch-check')
run(['git','apply',str(HERE/'candidate-new-files.patch')],apply,10,'patch-apply')
files=sorted(p for p in target.iterdir() if p.is_file())
for f in files:
    assert (apply/f.relative_to(candidate)).read_bytes()==f.read_bytes()
report=dict(children=records,patch_files=[pin(f) for f in files],patch=pin(HERE/'candidate-new-files.patch'),
            tests=pin(out/'fixtures/verification.json'),native_executed=False,operational_writes=False)
(out/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(tests=json.loads((out/'fixtures/verification.json').read_text())['tests'],children_joined=len(records),patch_files=len(files))))
