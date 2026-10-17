"""One bounded test child, synchronously joined. No runtime launch."""
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time
HERE=Path(__file__).resolve().parent

def limits():
    resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,)*2)
    resource.setrlimit(resource.RLIMIT_CPU,(30,30))
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))

start=time.monotonic()
with (HERE/'tests.stdout').open('w') as out, (HERE/'tests.stderr').open('w') as err:
    env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=str(HERE/'proposed'))
    child=subprocess.Popen([sys.executable,'-B','-m','unittest','-v','test_runtime_view','test_effective_storage_regression'],cwd=HERE,env=env,stdout=out,stderr=err,preexec_fn=limits)
    timed_out=False
    try:code=child.wait(timeout=60)
    except subprocess.TimeoutExpired:
        timed_out=True;child.kill();code=child.wait()
record=dict(exit=code,pid=child.pid,joined=True,pid_absent=not Path('/proc',str(child.pid)).exists(),timed_out=timed_out,seconds=time.monotonic()-start,peak_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,bounds=dict(address_space_bytes=512*1024**2,cpu_seconds=30,wall_seconds=60),test_grandchildren=0,native_execution=False,namespace_execution=False)
(HERE/'tests-result.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record))
sys.exit(code)
