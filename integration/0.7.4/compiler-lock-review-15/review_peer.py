"""Independent focused tests of pinned peer helper; ordinary TEMP locks only."""
import ast, errno, fcntl, hashlib, json, os, resource, subprocess, sys, tempfile, time
from pathlib import Path
from unittest.mock import patch
sys.dont_write_bytecode=True
resource.setrlimit(resource.RLIMIT_AS,(256*2**20,256*2**20))
HERE=Path(__file__).resolve().parent
source=(HERE/'inspected-peer14-adapter.py').read_text()
module=ast.parse(source)
functions=[n for n in module.body if isinstance(n,ast.FunctionDef) and n.name in ['require','canonical','acquire_runtime_lock']]
ns=dict(time=time,fcntl=fcntl,errno=errno,os=os,Path=Path)
exec(compile(ast.Module(body=functions,type_ignores=[]),'<pinned-peer14-helper>','exec'),ns)
acquire=ns['acquire_runtime_lock'];results=[];joins=[]
def expect(kind,fn):
    try:fn()
    except kind:return
    raise AssertionError('expected '+kind.__name__)

def real_case(lockpath,hold,budget,want_success):
    child=subprocess.Popen([sys.executable,'-B',str(HERE/'process_model.py'),'exclusive',str(lockpath),str(hold)],stdout=subprocess.PIPE,text=True,start_new_session=True)
    try:
        assert child.stdout.readline().strip()=='held'
        t=time.monotonic()
        with lockpath.open('rb') as fd:
            if want_success:acquire(fd,t+budget)
            else:expect(TimeoutError,lambda:acquire(fd,t+budget))
        assert fd.closed
        elapsed=time.monotonic()-t
        assert elapsed<budget+.25
        results.append(dict(case='peer_real_transient' if want_success else 'peer_real_timeout',passed=True,elapsed=elapsed,fd_closed=True))
    finally:
        try:code=child.wait(timeout=3)
        except subprocess.TimeoutExpired:child.kill();code=child.wait(timeout=3)
        child.stdout.close();assert not Path('/proc',str(child.pid)).exists()
        joins.append(dict(pid=child.pid,exit=code,absent=True))
started=time.monotonic()
with tempfile.TemporaryDirectory(prefix='peer-review-',dir=HERE) as d:
    p=Path(d)/'lock';p.touch()
    real_case(p,.15,.8,True);real_case(p,.25,.05,False)
    with p.open('rb') as fd,patch.object(fcntl,'flock',side_effect=OSError(errno.EIO,'injected')) as op,patch.object(time,'sleep') as sleep:
        expect(OSError,lambda:acquire(fd,time.monotonic()+1));assert op.call_count==1 and sleep.call_count==0
    assert fd.closed;results.append(dict(case='unexpected_errno_immediate_propagation_cleanup',passed=True))
    with p.open('rb') as fd,patch.object(fcntl,'flock') as op:
        expect(TimeoutError,lambda:acquire(fd,time.monotonic()-1));assert not op.called
    results.append(dict(case='expired_budget_no_flock',passed=True))
    with p.open('rb') as fd:
        p.unlink();p.touch();expect(ValueError,lambda:acquire(fd,time.monotonic()+1))
    assert fd.closed;results.append(dict(case='replaced_lock_inode_rejected_cleanup',passed=True))
    with p.open('rb') as fd,patch.object(time,'monotonic',side_effect=[0,0,2]):
        expect(ValueError,lambda:acquire(fd,1))
    assert fd.closed;results.append(dict(case='deadline_crossed_during_successful_flock_rejected_cleanup',passed=True))
# Compare original validation body structurally; acquire statement only substitution.
base=Path('/home/viktor/Projects/Vektor Flow/.worktrees/gpu-math-20261014-libraries/integration/0.7.4/compiler-runtime-binding-11/adapter.py').read_text()
def runnode(text):return next(n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef) and n.name=='run')
def locknode(text):return next(n for n in runnode(text).body if isinstance(n,ast.With))
a,b=locknode(base),locknode(source)
assert ast.dump(ast.Module(body=a.body[1:],type_ignores=[]))==ast.dump(ast.Module(body=b.body[1:],type_ignores=[]))
assert not any(isinstance(n,(ast.For,ast.While)) for s in b.body[1:] for n in ast.walk(s))
results.append(dict(case='entire_retained_locked_validation_AST_identical',passed=True))
report=dict(inspected_sha256=hashlib.sha256(source.encode()).hexdigest(),cases=results,joins=joins,all_children_joined=True,elapsed=time.monotonic()-started,maxrss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,child_maxrss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,per_process_address_space_limit=256*2**20,simultaneous_processes_max=2)
(HERE/'peer-review-results.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
