"""One finite host/source test child, inherited limits for its git check children."""
import json,os,resource,signal,subprocess,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
def limits():
    resource.setrlimit(resource.RLIMIT_AS,(512*1024*1024,)*2)
    resource.setrlimit(resource.RLIMIT_CPU,(55,55))
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
start=time.monotonic()
with (HERE/'host-tests.stdout').open('xb') as out,(HERE/'host-tests.stderr').open('xb') as err:
    p=subprocess.Popen([sys.executable,'-B',str(HERE/'test_proposal.py')],cwd=HERE,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},stdout=out,stderr=err,start_new_session=True,preexec_fn=limits)
    timeout=False
    try:p.wait(timeout=60)
    except subprocess.TimeoutExpired:
        timeout=True;os.killpg(p.pid,signal.SIGKILL);p.wait()
result=dict(exit=p.returncode,seconds=time.monotonic()-start,pid=p.pid,joined=True,timed_out=timeout,child_maxrss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,address_space_limit_bytes=536870912,cpu_seconds_limit=55,wall_seconds_limit=60,native_execution=False,public_api_qualified=False)
(HERE/'host-results.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
sys.exit(0 if p.returncode==0 and not timeout else 1)
