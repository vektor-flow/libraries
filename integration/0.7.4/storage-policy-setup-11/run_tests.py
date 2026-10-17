"""Run only bounded Python source/mock tests; all writable fixtures below HERE."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time
import unittest
HERE=Path(__file__).resolve().parent

def child():
    resource.setrlimit(resource.RLIMIT_AS, (512*1024*1024,512*1024*1024))
    resource.setrlimit(resource.RLIMIT_CPU, (45,45))
    sys.path.insert(0,str(HERE))
    import test_successor
    import test_policy
    spec=importlib.util.spec_from_file_location('inherited_effective_tests',HERE.parent/'storage-mount-repair-08/test_effective_storage.py')
    inherited=importlib.util.module_from_spec(spec);spec.loader.exec_module(inherited)
    inherited.HERE=HERE
    suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromModule(test_successor),
                             unittest.defaultTestLoader.loadTestsFromModule(inherited),
                             unittest.defaultTestLoader.loadTestsFromModule(test_policy)])
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    (HERE/'test-counts.json').write_text(json.dumps(dict(tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped)))+'\n')
    return 0 if result.wasSuccessful() else 1

def parent():
    began=time.monotonic();argv=['/usr/bin/python3.14','-I','-B',str(Path(__file__).resolve()),'--child']
    with (HERE/'tests.stdout.txt').open('w') as out,(HERE/'tests.stderr.txt').open('w') as err:
        p=subprocess.Popen(argv,stdout=out,stderr=err,cwd=HERE,env={**os.environ,'TMPDIR':str(HERE),'PYTHONDONTWRITEBYTECODE':'1'})
        raw=Path('/proc',str(p.pid),'stat').read_text().rsplit(')',1)[1].split()
        identity=dict(pid=p.pid,starttime=int(raw[19]))
        try:code=p.wait(timeout=60)
        except subprocess.TimeoutExpired:
            p.kill();code=p.wait(timeout=5)
    absent=not Path('/proc',str(p.pid)).exists()
    record=dict(argv=argv,identity=identity,exit=code,joined=True,absent_after=absent,
                seconds=time.monotonic()-began,maxrss_KiB=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
                test_children=0,services=0,namespaces=0,native_or_compiler_runs=0)
    (HERE/'ownedjoins.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(record));print((HERE/'test-counts.json').read_text() if (HERE/'test-counts.json').exists() else 'counts unavailable')
    return code
if __name__=='__main__':sys.exit(child() if sys.argv[1:]==['--child'] else parent())
