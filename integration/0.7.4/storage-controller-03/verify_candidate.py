"""Bounded local checks. Writes only beside this file; no live controller calls."""
import ast
import datetime
import difflib
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def stamp(): return datetime.datetime.now(datetime.timezone.utc).isoformat()

def main():
    start=time.monotonic();result={'started_utc':stamp(),'python':sys.version,'checks':[]}
    files=['storage_controller.py','storage_admission.py','storage_paths.py','test_core_regression.py','test_lifecycle.py']
    for name in files:ast.parse((HERE/name).read_text(),filename=name)
    result['ast_files']=files
    launch=time.monotonic()
    with (HERE/'test-results.txt').open('w') as log:
        p=subprocess.Popen([sys.executable,'-B','-m','unittest','-v','test_core_regression','test_lifecycle'],
                           cwd=HERE,stdout=log,stderr=subprocess.STDOUT)
        stat=Path('/proc')/str(p.pid)/'stat'
        ident={'pid':p.pid,'starttime':int(stat.read_text().rsplit(')',1)[1].split()[19]),
               'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip()}
        try:code=p.wait(timeout=30)
        except BaseException:
            p.kill();p.wait(timeout=5);raise
    result['tests']={'exit':code,'wall_seconds':time.monotonic()-launch,'runner':dict(ident,joined=True,returncode=code)}
    (HERE/'test-runner-join.json').write_text(json.dumps(result['tests'],indent=2)+'\n')
    if code:raise RuntimeError('tests failed; inspect test-results.txt')
    installed={name:name for name in files};installed['README.txt']='INTEGRATION.txt'
    patch=''.join(''.join(difflib.unified_diff([], (HERE/src).read_text().splitlines(keepends=True),
                      fromfile='/dev/null',tofile='b/storage-direct-v2/'+name)) for name,src in installed.items())
    patchfile=HERE/'candidate-integration.patch';patchfile.write_text(patch)
    with tempfile.TemporaryDirectory(prefix='patch-check-',dir=HERE) as tmp:
        # Keep this disposable check outside the enclosing Git worktree context.
        env=dict(os.environ,GIT_CEILING_DIRECTORIES=str(HERE))
        for mode in (['--check'],[]):
            run=subprocess.run(['git','apply',*mode,str(patchfile)],cwd=tmp,env=env,
                               text=True,capture_output=True,timeout=10)
            result['checks'].append(dict(command=['git','apply',*mode,'candidate-integration.patch'],exit=run.returncode,
                                         stdout=run.stdout,stderr=run.stderr))
            if run.returncode:raise RuntimeError(run.stderr)
        for name,src in installed.items():
            actual=Path(tmp)/'storage-direct-v2'/name
            assert actual.read_bytes()==(HERE/src).read_bytes(),name
    result['patch']={'path':str(patchfile),'sha256':sha(patchfile),'files':list(installed),'installed_bytes_match':True}
    result['race_children']=json.loads((HERE/'owned-job-joins.json').read_text())
    assert all(x['exitcode']==0 and not x['alive'] for x in result['race_children'])
    result['wall_seconds']=time.monotonic()-start;result['ended_utc']=stamp()
    (HERE/'check-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
