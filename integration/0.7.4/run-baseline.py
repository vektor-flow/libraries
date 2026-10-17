"""One consolidated baseline; failures remain failures, dependent gates are blocked."""
import argparse, hashlib, json, os, pathlib, signal, subprocess, time

p = argparse.ArgumentParser()
p.add_argument('--artifacts', required=True, type=pathlib.Path)
p.add_argument('--python', required=True)
p.add_argument('--vitest', required=True)
p.add_argument('--recipe', required=True, type=pathlib.Path)
a = p.parse_args()
repo = pathlib.Path(__file__).resolve().parents[2]
out = a.artifacts.resolve()
out.mkdir(parents=True, exist_ok=False)
results = {'stages': [], 'release_qualified': False}
def save():
    (out/'results.json').write_text(json.dumps(results, indent=2)+'\n')
def run(name, argv, timeout, cwd=repo, env=None):
    start = time.monotonic()
    with (out/(name+'.stdout')).open('wb') as stdout, (out/(name+'.stderr')).open('wb') as stderr:
        child = subprocess.Popen(argv, cwd=cwd, env=env, stdout=stdout, stderr=stderr, start_new_session=True)
        try:
            code = child.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGTERM)
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()
            code = 124
    results['stages'].append({'name':name,'argv':argv,'exit':code,'seconds':time.monotonic()-start,'status':'pass' if code==0 else 'fail'})
    save()
    print(name, code, flush=True)
    return code
sources = {}
for base in ['browser-ui','examples/gpu-math','tests','vendor']:
    for f in sorted((repo/base).rglob('*')):
        if f.is_file() and '.vkfbuild' not in f.parts and '__pycache__' not in f.parts:
            sources[str(f.relative_to(repo))] = hashlib.sha256(f.read_bytes()).hexdigest()
(out/'source-pins.json').write_text(json.dumps(sources, indent=2)+'\n')
results['source_commit'] = subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()
node_tests = sorted({str(f) for root in [repo/'tests',repo/'examples/gpu-math/tests'] for f in root.rglob('*.test.mjs')})
run('node-tests', ['node','--test','--test-concurrency=1',*node_tests], 300)
vitest_tests = sorted(str(f) for f in (repo/'tests/browser-ui').glob('*.test.js'))
run('browser-ui-unit-tests', ['node',a.vitest,'run','--root',str(repo),'--maxWorkers=1','--no-file-parallelism',*vitest_tests], 180)
run('analytic-curves', ['node','tests/browser-ui/analytic-curves.check.mjs'], 30)
run('python-tests', [a.python,'-m','unittest','discover','-s','examples/gpu-math/tests','-p','test_*.py'], 180)
recipe = json.loads(a.recipe.read_text())
build = out/'native';build.mkdir()
env = dict(os.environ);env.update(recipe['environment'])
for key in recipe['unset']:
    env.pop(key, None)
for pin in recipe['stdlib']:
    target = pathlib.Path(pin['path'])
    assert hashlib.sha256(target.read_bytes()).hexdigest()==pin['sha256']
    dest = build/target.relative_to(pathlib.Path(recipe['environment']['VKF_HOME']))
    dest.parent.mkdir(parents=True,exist_ok=True);dest.symlink_to(target)
compiler = recipe['tools'][0]
assert hashlib.sha256(pathlib.Path(compiler['path']).read_bytes()).hexdigest()==compiler['sha256']
native = repo/'examples/gpu-math/native-vkf'
if run('native-normalize',[a.python,str(native/'normalize_module_aliases.py'),'--source-dir',str(native),'--output-dir',str(build/'normalized')],30,build,env)==0:
    code = run('native-full-build',[compiler['path'],'-b',str(build/'normalized/source/native_document_cli.vkf'),'-o',str(build/'native-document-cli'),'--diagnostics'],180,build,env)
    results['native_binary_produced'] = code==0 and (build/'native-document-cli').exists()
    if results['native_binary_produced']:
        results['native_binary_sha256'] = hashlib.sha256((build/'native-document-cli').read_bytes()).hexdigest()
results['blocked_gates'] = ['40-page save/correctness/timing requires successful native full build and dedicated renderer harness', 'full WASM remains an outstanding historical bad_alloc blocker; not rerun as a passing gate', 'Adobe/Edge interactive PDF selection and TeX editing remain unimplemented/unqualified', 'physical GPU qualification excluded by existing stop policy']
results['source_posthash_match'] = all(hashlib.sha256((repo/name).read_bytes()).hexdigest()==digest for name,digest in sources.items())
results['canonical_original419'] = '293/419 unchanged; original compiler suite not rerun by this application baseline'
save()
