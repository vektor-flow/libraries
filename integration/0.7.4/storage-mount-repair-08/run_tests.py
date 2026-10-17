"""One bounded child, synchronous join; all test writes under this directory."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
HERE=Path(__file__).resolve().parent
start=time.monotonic()
argv=['/usr/bin/python3','-B','-m','unittest','-v','test_effective_storage','test_candidates']
with (HERE/'tests.stdout.txt').open('w') as out,(HERE/'tests.stderr.txt').open('w') as err:
    child=subprocess.Popen(argv,cwd=HERE,stdout=out,stderr=err,
        env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','TMPDIR':str(HERE)})
    pid=child.pid
    try:
        code=child.wait(timeout=60)
    except subprocess.TimeoutExpired:
        child.kill();child.wait();raise
result=dict(argv=argv,pid=pid,exit=code,owned_child_joined=child.poll() is not None,
    elapsed_seconds=time.monotonic()-start,live_sandbox=False,native_execution=False,
    operational_mutation=False)
(HERE/'tests-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
raise SystemExit(code)
