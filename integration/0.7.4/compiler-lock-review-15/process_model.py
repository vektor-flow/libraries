"""Review-only TEMP lock counterexamples, never an adapter implementation."""
import errno, fcntl, importlib.util, json, os, resource, subprocess, sys, tempfile, time
from pathlib import Path
sys.dont_write_bytecode=True
resource.setrlimit(resource.RLIMIT_AS,(256*2**20,256*2**20))
HERE=Path(__file__).resolve().parent
OWNED=Path('/home/viktor/Projects/Vektor Flow/.coordination/s0-plan-20261012/synchronized-contexts/independent-workers/storage20gb/owned-processes.py')
if len(sys.argv)>1:
    _,role,path,seconds=sys.argv
    with open(path,'rb') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX if role=='exclusive' else fcntl.LOCK_SH)
        print('held',flush=True)
        time.sleep(float(seconds))
    raise SystemExit(0)
results=[]; joins=[]
def holder(path,mode,seconds):
    p=subprocess.Popen([sys.executable,'-B',__file__,mode,str(path),str(seconds)],stdout=subprocess.PIPE,text=True,start_new_session=True)
    assert p.stdout.readline().strip()=='held'
    return p

def finish(p):
    try: code=p.wait(timeout=3)
    except subprocess.TimeoutExpired:
        p.kill();code=p.wait(timeout=3)
    p.stdout.close()
    joins.append(dict(pid=p.pid,exit=code,absent=not Path('/proc',str(p.pid)).exists()))
    assert joins[-1]['absent']

def bounded_model(fd,deadline):
    attempts=0
    while time.monotonic()<deadline:
        attempts+=1
        try: fcntl.flock(fd,fcntl.LOCK_SH|fcntl.LOCK_NB); return attempts
        except OSError as e:
            if e.errno not in (errno.EAGAIN,errno.EACCES): raise
        time.sleep(min(.01,max(0,deadline-time.monotonic())))
    raise TimeoutError('isolated model deadline')

started=time.monotonic()
with tempfile.TemporaryDirectory(prefix='isolated-lock-',dir=HERE) as temp:
    path=Path(temp)/'capacity.lock';path.touch()
    p=holder(path,'exclusive',.3)
    try:
        with path.open('rb') as fd:
            t=time.monotonic()
            try:fcntl.flock(fd,fcntl.LOCK_SH|fcntl.LOCK_NB)
            except BlockingIOError as e:assert e.errno==errno.EAGAIN
            else:raise AssertionError('expected EAGAIN')
            results.append(dict(case='original_one_shot_fails_during_legitimate_EX',passed=True,elapsed=time.monotonic()-t))
            tries=bounded_model(fd,time.monotonic()+1)
            results.append(dict(case='transient_EX_then_SH_acquires',passed=True,attempts=tries,elapsed=time.monotonic()-t))
    finally:finish(p)
    p=holder(path,'exclusive',.4)
    try:
        with path.open('rb') as fd:
            t=time.monotonic()
            try:bounded_model(fd,t+.1)
            except TimeoutError:pass
            else:raise AssertionError('expected bounded failure')
            elapsed=time.monotonic()-t;assert .09<=elapsed<.3
            results.append(dict(case='EX_outlasts_budget_bounded_failure',passed=True,elapsed=elapsed))
    finally:finish(p)
    # Use actual immutable owned wait loop; synchronous guard is intentionally blocked
    # by this TEMP shared holder. Demonstrates timeout check delayed, no live locks.
    spec=importlib.util.spec_from_file_location('review_owned',OWNED)
    owned=importlib.util.module_from_spec(spec);spec.loader.exec_module(owned)
    p=holder(path,'shared',.35)
    try:
        def guard():
            with path.open('rb') as fd:fcntl.flock(fd,fcntl.LOCK_EX)
        t=time.monotonic();code,joined=owned.wait_owned(p,.06,guard=guard)
        elapsed=time.monotonic()-t
        assert elapsed>.25 and joined['timed_out'] and code==124
        results.append(dict(case='actual_wait_owned_synchronous_EX_guard_delays_deadline',passed=True,requested_timeout=.06,elapsed=elapsed,code=code,joined=joined))
    finally:finish(p)
report=dict(kind='isolated model, not native validation or actual-holder attribution',cases=results,joins=joins,all_children_joined=all(x['absent'] for x in joins),elapsed=time.monotonic()-started,maxrss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,child_maxrss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,per_process_address_space_limit=256*2**20,simultaneous_processes_max=2)
(HERE/'process-model-results.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
