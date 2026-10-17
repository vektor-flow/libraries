"""Bounded host preparation only. No compiler, namespace, service or state writes."""
import importlib.util
import json
import resource
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import adapter as a

HEAD = '168085c78e1a91f413aa9f1cfadd9f40c97c1894'
S = Path('/home/viktor/Projects/Vektor Flow/.coordination/s0-plan-20261012/synchronized-contexts/independent-workers/storage20gb')
V9 = S/'storage-direct-v9'
QUAL = dict(path=str(S/'compiler-qualified-v9-A-root-export-20261017.json'),
            sha256='8cdeb6a0051fa2274a94ca6086e518388ceb46b26f629d95d2c1c9404f4695fa')

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

def main():
    start = time.monotonic()
    resource.setrlimit(resource.RLIMIT_AS, (512*1024**2,)*2)
    resource.setrlimit(resource.RLIMIT_CORE, (0,0))
    assert a.current_head() == HEAD
    assert a.pin(HERE/'adapter.py')['sha256'] == '7c167a22524f2c35057b2ea094b2488a57d64c0c0307f3fdbeed2421365498c2'
    qualified = a.load_pin(QUAL)
    bundle = qualified['v6_bundle']  # Historical key is a schema label, not v6 source.
    assert qualified['qualified'] is True and qualified['worker'] == 'A'
    assert qualified['cases'] == ['success','nonzero','timeout']
    assert qualified['boot'] == Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    installed_path = HERE.parent/'storage-combined-trust-review-23/root-v9-installed.json'
    installed = a.read(installed_path)
    for p in installed['installed_files'] + qualified['evidence']:
        a.verify(p)
    assert all(p in installed['installed_files'] for p in [bundle['controller'],bundle['config'],*bundle['helpers']])
    assert all(Path(p['path']).parent == V9 for p in [bundle['controller'],bundle['config'],*bundle['helpers']])
    config = a.load_pin(bundle['config'])
    ap = next(p for p in config['approved_policies'] if a.load_pin(p)['worker'] == 'A')
    policy = a.load_pin(ap)
    review = a.pin(HERE.parent/'compiler-native-binding-08/corrected-review.json')
    plan = a.read(HERE/'staging/plan.json')
    a.check_plan(plan, HEAD, a.load_pin(review))

    # Import the actual materialization/payload path in the isolated host interpreter.
    # This imports code only; execute()/run()/enable_subreaper() are never called.
    sys.path.insert(0, str(a.PACKAGE))
    import payload
    import authenticate
    owned = load_module('owned_inspection', S/'owned-processes.py')
    sys.path.insert(0, str(V9))
    import private_workload as private
    assert payload.__file__ == str(a.PACKAGE/'payload.py')
    assert private.__file__ == str(V9/'private_workload.py')
    module_rows = []
    for name, module in sorted(sys.modules.items()):
        path = getattr(module, '__file__', None)
        if path and Path(path).is_file():
            row = dict(module=name, source=a.pin(Path(path).resolve()))
            cached = getattr(module, '__cached__', None)
            if cached and Path(cached).is_file():
                row['cache'] = a.pin(Path(cached).resolve())
            module_rows.append(row)
    mapped = sorted({line.split()[-1] for line in Path('/proc/self/maps').read_text().splitlines()
                     if len(line.split()) >= 6 and line.split()[-1].startswith('/')
                     and Path(line.split()[-1]).is_file()})
    mapped_pins = [a.pin(Path(p).resolve()) for p in mapped]

    # Read ELF sections; never run ldd, compiler, linker or any inspected executable.
    # Seed ALL authenticated tools/runtime DSOs plus imported extension modules.
    known = {str(Path(p['path']).resolve()) for p in plan['inputs']}
    seeds = [p['path'] for p in plan['inputs'] if 'tool' in p['roles'] or 'tool/runtime ELF dependency' in p['roles']]
    seeds += [p['path'] for p in private.BINARIES] + mapped
    seeds += [r['source']['path'] for r in module_rows if r['source']['path'].endswith('.so')]
    seen, edges, elf_pins = set(), [], []
    pending = list(seeds)
    while pending:
        source = Path(pending.pop()).resolve(strict=True)
        if str(source) in seen: continue
        seen.add(str(source))
        needs, interp, search = authenticate.elf_needs(source)
        if not needs and not interp: continue
        elf_pins.append(a.pin(source))
        if interp:
            target = Path(interp).resolve(strict=True)
            edges.append(dict(source=str(source), needed='PT_INTERP', target=str(target)))
            pending.append(str(target))
        for need in needs:
            directories = [x.replace('${ORIGIN}',str(source.parent)).replace('$ORIGIN',str(source.parent)) for x in search]
            directories += ['/usr/lib/x86_64-linux-gnu','/usr/lib','/lib/x86_64-linux-gnu']
            matches = [Path(d)/need for d in directories if (Path(d)/need).is_file()]
            assert matches, ('unresolved ELF input',str(source),need)
            target = matches[0].resolve(strict=True)
            edges.append(dict(source=str(source), needed=need, target=str(target),
                              authenticated_plan_path=str(target) in known))
            pending.append(str(target))

    pins = installed['installed_files'] + private.BINARIES + private.POLICY_INPUTS
    pins += config['approved_policies'] + [config['recovery_authority'],policy['predecessor_controller'],policy['predecessor_ledger']]
    pins += [a.pin(S/'owned-processes.py'), a.pin(installed_path), QUAL, *qualified['evidence'], review]
    pins += [a.pin(a.PACKAGE/n) for n in ('authenticate.py','prepare.py','payload.py','authentication.json','SPEC.txt')]
    pins += [a.pin(HERE.parent/'compiler-controller-preparation-09'/n) for n in ('adapter.py','root-adoption.json')]
    pins += [a.pin(HERE.parent/'compiler-native-binding-08/root-acceptance.json')]
    pins += [a.pin(HERE/'adapter.py')] + mapped_pins + elf_pins
    # Dynamic loader selection and enabled site bootstrap are runtime inputs too.
    pins += [a.pin('/etc/ld.so.cache')]
    for directory in sys.path:
        if directory.startswith('/usr/') and Path(directory).is_dir():
            pins += [a.pin(p) for p in Path(directory).glob('*.pth')]
    for row in module_rows:
        # The sealer is preparation code, not part of the future runtime import path.
        if row['module'] != '__main__':
            pins += [row['source']]
            if 'cache' in row: pins += [row['cache']]
    pins = a.controller_inputs(pins)
    roots = [a.load_pin(p)['root']['path'] for p in config['approved_policies']]
    a.protected([p['path'] for p in pins], roots)
    for p in pins: a.verify(p)
    inputs = a.unique(pins+a.controller_inputs(plan['inputs']))
    # Calls only the existing pure argv constructor; no namespace or service run.
    view = private.runtime_view(dict(inputs=inputs,argv=['/usr/bin/python3.14'],
                                    attempt_root=policy['root']['path']+'/UNFULFILLED-next-compiler'))
    for p in inputs: private.pinned(p)
    # Also validate uncanonicalized compiler aliases against v9 visibility.
    private.runtime_view(dict(inputs=plan['inputs'],argv=['/usr/bin/python3.14'],
                              attempt_root=policy['root']['path']+'/UNFULFILLED-next-compiler'))
    result = dict(schema=1,source_commit=HEAD,v6_bundle=bundle,a_policy=ap,
                  owned_processes=a.pin(S/'owned-processes.py'),python=a.pin('/usr/bin/python3.14'),
                  review=review,state_path=str(S/'storage-direct-v4/direct-state-v4.json'),
                  lock_path=str(S/'capacity.lock'),pins=pins,
                  installed_version=9,qualification_review=QUAL,
                  scope='Source seal only; genuine root compiler ownership/admission/publication still required')
    a.save(HERE/'source-contract.json',result)
    a.save(HERE/'runtime-closure.json',dict(modules=module_rows,mapped=mapped_pins,elf_edges=edges,
           elf_pins=a.unique(elf_pins),runtime_view_argv=view,
           host_imports_only=True,native_execution=False,
           limitation='Static ELF/import closure and read-view compatibility; actual compiler MD/link results remain unexecuted.'))
    template = a.read(HERE.parent/'compiler-controller-preparation-09/root-inputs.REQUIRED.json')
    template.update(source_commit=HEAD,qualification_review=QUAL,boot=qualified['boot'])
    a.save(HERE/'root-inputs.REQUIRED.json',template)
    assert a.current_head() == HEAD
    a.save(HERE/'seal-result.json',dict(passed=True,source_commit=HEAD,static_pins=len(pins),
           combined_canonical_inputs=len(inputs),compiler_inputs=len(plan['inputs']),
           modules=len(module_rows),elf_edges=len(edges),native_execution=False,
           seconds=time.monotonic()-start,
           process_memory=[line for line in Path('/proc/self/status').read_text().splitlines() if line.startswith(('VmHWM:','VmPeak:'))]))
    print(json.dumps(a.read(HERE/'seal-result.json')))

if __name__ == '__main__': main()
