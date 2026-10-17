"""Review35 host-only replay. Original code read unchanged; all writes confined here.

No operational entry point is called. Audited suites use fake compiler/run stages.
Only test output sinks and TemporaryDirectory location are redirected. Popen is
restricted to ordinary git/patch/Python-normalizer/test-lock children and joined.
"""
import ast, importlib.util, json, os, resource, signal, subprocess, sys, tempfile, time, unittest
from pathlib import Path
sys.dont_write_bytecode = True
OUT = Path(__file__).resolve().parent
PACKET = OUT.parent/'metadata-repaired-binding-32'
REPAIR = OUT.parent/'metadata-entry-repair-31'
MODE = sys.argv[1]
resource.setrlimit(resource.RLIMIT_AS, (512*2**20,)*2)
resource.setrlimit(resource.RLIMIT_CPU, (50,50))
resource.setrlimit(resource.RLIMIT_CORE, (0,0))
signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('55s review limit')))
signal.alarm(55)
start = time.monotonic()
children = []
mutations = []

def writable(p):
    if isinstance(p, int): return
    q = Path(os.fsdecode(p)).absolute()
    assert q.is_relative_to(OUT) and q.resolve().is_relative_to(OUT), ('write outside review',str(q))
    mutations.append(str(q))

def audit(event, args):
    if event == 'open':
        p, mode, flags = args
        if flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND): writable(p)
    elif event in ('os.mkdir','os.remove','os.rmdir','os.chmod','os.truncate'):
        # shutil uses dir_fd-relative names during TemporaryDirectory cleanup.
        p=args[0]
        if not isinstance(p,int) and not Path(os.fsdecode(p)).is_absolute():
            fd = args[-1]
            if isinstance(fd,int) and fd >= 0: p=Path(os.readlink('/proc/self/fd/'+str(fd)))/os.fsdecode(p)
        writable(p)
    elif event in ('os.rename','os.link','os.symlink'):
        raise AssertionError(('unexpected mutation', event))
sys.addaudithook(audit)

OriginalPopen = subprocess.Popen
class HostPopen(OriginalPopen):
    def __init__(self, argv, *args, **kw):
        assert not kw.get('shell')
        name=Path(argv[0]).name
        allowed=name in ('git','patch')
        if name.startswith('python'):
            allowed=any(str(v).endswith('normalize_module_aliases.py') for v in argv)
            allowed |= '-c' in argv and 'fcntl.flock' in argv[argv.index('-c')+1] and str(OUT) in str(argv[-1])
        assert allowed, ('unapproved subprocess',argv)
        super().__init__(argv,*args,**kw)
        children.append(self)
subprocess.Popen = HostPopen
original_temp = tempfile.TemporaryDirectory
def own_temp(*args,**kwargs):
    kwargs['dir']=OUT
    return original_temp(*args,**kwargs)
tempfile.TemporaryDirectory=own_temp

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec);sys.modules[name]=mod
    spec.loader.exec_module(mod);return mod
def write(name,obj):
    with (OUT/name).open('x') as f: json.dump(obj,f,indent=2);f.write('\n')

sys.path.insert(0,str(PACKET))
import adapter as a
original_save=a.save
def own_save(path,obj):
    path=Path(path)
    if path.parent==PACKET: path=OUT/(MODE+'-'+path.name)
    original_save(path,obj)
a.save=own_save
passed=False
try:
    if MODE=='tests':
        mod=load('review_tests',PACKET/'test_controls.py')
        result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(mod.Tests))
        passed=result.wasSuccessful()
        write('tests-result.json',dict(passed=passed,tests=result.testsRun,failures=len(result.failures),errors=len(result.errors)))
    elif MODE in ('packet','independent'):
        name={'packet':'verify_packet.py','independent':'independent_verify.py'}[MODE]
        load('review_'+MODE,PACKET/name)
        passed=True
    elif MODE=='repair-proof':
        mod=load('investigate',REPAIR/'investigate.py')
        mod.save=lambda name,obj:write('repair-proof-'+name,obj)
        mod.main()
        final=load('repair_final',REPAIR/'final_verify.py')
        final.main();passed=True
    elif MODE=='native-provenance':
        # Execute only the read-only prefix of inspected build_packet.main.
        mod=load('review_build',PACKET/'build_packet.py')
        tree=ast.parse((PACKET/'build_packet.py').read_text())
        fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
        prefix=[]
        for n in fn.body:
            if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name) and n.value.func.id=='save': break
            prefix.append(n)
        ns=dict(mod.__dict__)
        exec(compile(ast.Module(body=prefix,type_ignores=[]),'read-only native17 provenance prefix','exec'),ns)
        write('native-provenance-result.json',dict(passed=True,actual_inputs=ns['refs'],stage_count=len(ns['results']),identity=ns['receipt']['identity'],native_execution=False))
        passed=True
    elif MODE=='audit':
        load('review_audit',OUT/'audit.py')
        passed=True
    else: raise ValueError(MODE)
finally:
    rows=[]
    for child in children:
        if child.poll() is None: child.kill()
        child.wait(timeout=3)
        rows.append(dict(pid=child.pid,argv=child.args,exit=child.returncode,joined=True,absent=not Path('/proc',str(child.pid)).exists()))
    assert all(r['joined'] and r['absent'] for r in rows)
    write(MODE+'-runner.json',dict(passed=passed,seconds=time.monotonic()-start,
        children=rows,all_children_joined=True,memory=[s for s in Path('/proc/self/status').read_text().splitlines() if s.startswith(('VmHWM:','VmPeak:'))],
        max_child_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
        AS_bytes=512*2**20,wall_limit_seconds=55,write_paths=sorted(set(mutations)),
        native_execution=False,operational_actions=False,live_locks=False,overlap_by_task=0))
sys.exit(0 if passed else 1)
