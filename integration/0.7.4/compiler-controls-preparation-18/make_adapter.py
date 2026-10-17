"""Produce a reviewable D288-only derivative; historical adapter stays untouched."""
from pathlib import Path
import difflib
H=Path(__file__).resolve().parent
old=(H.parent/'compiler-runtime-binding-16/adapter.py').read_text();s=old
start=s.index('def check_plan(');end=s.index('\ndef relocate(',start)
s=s[:start]+'''PHASE = 'd288'
DISK = 2*GIB
TIMEOUT = 2400


def check_plan(plan, head, review):
    require(plan['kind'] == 'vkf' and plan.get('selection') == PHASE, 'D288 phase only')
    require(plan['application_head_at_preparation'] == head, 'stale plan HEAD')
    require(plan['candidate_review'] == dict(review, executable=True), 'complete corrected review')
    require(plan['executable'] is True, 'held plan')
    seal = read(HERE/'source-contract.json')
    expected = load_pin(seal['control_plan'])
    expected, _ = relocate(expected, plan['out'])
    require(plan == expected, 'complete sealed D288 plan mismatch')
    require(plan['compiler_receipt'] == load_pin(seal['compiler_receipt']), 'actual native17 receipt')
    require(len(plan['cases']) == 10 and len(plan['stages']) == 20, 'all ten original D288 cases')


def protected_inputs(pins, roots, target):
    # Only the exact accepted prior ELF may be in an enrolled job root. The
    # installed namespace ro-binds /mnt and rebinds ONLY this fresh attempt rw.
    # No receipt, config, source seal, ledger or owner authority gets an exception.
    receipt = load_pin(read(HERE/'source-contract.json')['compiler_receipt'])
    compiler = receipt['compiler']
    for p in pins:
        canonical(p['path']) if p == compiler else None
        if p == compiler:
            require(not Path(p['path']).is_relative_to(Path(target)), 'compiler overlaps new attempt')
            verify(p)
        else:
            protected([os.path.abspath(p['path'])], roots)


def materialize(plan, assets, plan_pin, target):
    require(not target.exists(), 'fresh D288 subdirectory')
    target.mkdir()
    for path in plan['directories']:
        dest = canonical(path)
        require(dest.is_relative_to(target), 'directory materialization escape')
        dest.mkdir(parents=True, exist_ok=True)
    for link in plan['symlinks']:
        dest = canonical(link['path']); source = canonical(link['target'])
        require(dest.is_relative_to(target), 'symlink materialization escape')
        require(dict(path=str(source), sha256=link['sha256']) in controller_inputs(plan['inputs']), 'unpinned stdlib link')
        verify(dict(path=str(source), sha256=link['sha256']))
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.symlink_to(source)
    for item in assets:
        dest = canonical(item['target'])
        require(dest.is_relative_to(target), 'materialization escape')
        verify(item['source'])
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open('xb') as f: f.write(raw(item['source']['path']))
    with (target/'plan.json').open('xb') as f: f.write(raw(plan_pin['path']))

''' +s[end:]
s=s.replace("        if source.suffix == '.json': b = encoded(move(decode(b)))", "        if source.suffix == '.json': b = encoded(move(decode(b)))\n        elif source.suffix == '.stdin': b = move(b.decode('utf-8')).encode('utf-8')")
s=s.replace("require(result['stages'][5] == move(plan['stages'][5]) and\n            result['stages'][7] == move(plan['stages'][7]), 'oracle transformation')","require(result['stages'] == move(plan['stages']), 'oracle transformation')")
s=s.replace("request['phase'] == 'compiler'", "request['phase'] == PHASE")
s=s.replace("request['disk_bytes'] == GIB", "request['disk_bytes'] == DISK").replace("request['timeout_seconds'] == 1200", "request['timeout_seconds'] == TIMEOUT")
s=s.replace("root must admit A8GiB/1GiB/1200s explicitly", "root must admit D288 A8GiB/2GiB/2400s explicitly")
s=s.replace("Path(attempt)/'compiler'", "Path(attempt)/PHASE")
s=s.replace("protected([os.path.abspath(p['path']) for p in plan['inputs']], roots)","protected_inputs(plan['inputs'], roots, attempt)")
s=s.replace("protected([p['path'] for p in inputs], roots)","protected_inputs(inputs, roots, attempt)")
s=s.replace("phase_scope='compiler', phase_bytes=GIB, ram_peak_bytes=8*GIB, timeout_seconds=1200", "phase_scope=PHASE, phase_bytes=DISK, ram_peak_bytes=8*GIB, timeout_seconds=TIMEOUT")
s=s.replace("forecast=dict(ram_bytes=4*GIB,disk_bytes=GIB,timeout_seconds=1200)","forecast=dict(ram_bytes=4*GIB,disk_bytes=DISK,timeout_seconds=TIMEOUT)")
s=s.replace("g['phase_bytes'] == GIB", "g['phase_bytes'] == DISK").replace("g['timeout_seconds'] == 1200 and g['phase_scope'] == 'compiler'", "g['timeout_seconds'] == TIMEOUT and g['phase_scope'] == PHASE")
s=s.replace("row['phase_bytes'] == GIB", "row['phase_bytes'] == DISK")
s=s.replace("deadline = time.monotonic() + 1200", "deadline = time.monotonic() + TIMEOUT")
s=s.replace("# Consume preflight/lock/materialization time from the existing 1200s budget.","# Consume preflight/lock/materialization time from the exact D288 phase budget.")
s=s.replace("protected([p['path'] for p in g['inputs']]+[grant_path,manifest_path,r['publication_receipt_path'],", "protected([grant_path,manifest_path,r['publication_receipt_path'],")
s=s.replace("s['state_path'],s['lock_path'],config['owner_state']], c['roots'])", "s['state_path'],s['lock_path'],config['owner_state']], c['roots'])\n    protected_inputs(g['inputs'], c['roots'], c['attempt_root'])")
s=s.replace("protected([os.path.abspath(p['path']) for p in plan['inputs']], c['roots'])", "protected_inputs(plan['inputs'], c['roots'], c['attempt_root'])")
s=s.replace("phase='compiler', native_execution=True", "phase=PHASE, native_execution=True")
s=s.replace("Path(c['attempt_root'])/'compiler'", "Path(c['attempt_root'])/PHASE")
start=s.index('    target.mkdir()\n',s.index('def run('));end=s.index('    # v6 guards/accounting',start)
s=s[:start]+"    materialize(plan, c['assets'], c['plan'], target)\n"+s[end:]
(H/'adapter.py').write_text(s)
(H/'adapter.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile='compiler-runtime-binding-16/adapter.py',tofile='compiler-controls-preparation-18/adapter.py')))
# Root-only recipe derivative: all operations remain pending genuine fresh authorization.
old=(H.parent/'compiler-runtime-binding-16/root_steps.py').read_text();s=old
s=s.replace("d['disk_bytes']==a.GIB", "d['disk_bytes']==a.DISK").replace("d['timeout_seconds']==1200", "d['timeout_seconds']==a.TIMEOUT")
s=s.replace("d['iteration']>25", "d['iteration']>26")
s=s.replace("A:compiler-native13-01", "A:compiler-native17-01").replace("row['sequence']==12", "row['sequence']==13")
s=s.replace('01a149f1-6e6c-7683-8d76-43acab856af5','01a14a07-a6c3-7941-b133-31fe3cbbee71')
s=s.replace('compiler-native13-01/receipts/service-join.json','compiler-native17-01/receipts/service-join.json').replace('d256ac9107872673b7751c4d7c2490b607ff23e6ec8c16b80257bd6ed63c2492','59a64d4dd9c467d71de4264ddf2c3f6fe8d62763ef9809c16f5ec56aef95b150')
s=s.replace("request.update(phase='compiler'", "request.update(phase=a.PHASE")
s=s.replace("g['phase_scope']=='compiler'", "g['phase_scope']==a.PHASE")
s=s.replace("==(8*a.GIB,a.GIB,1200)", "==(8*a.GIB,a.DISK,a.TIMEOUT)")
s=s.replace("d['worker']=='A' and", "d['phase']==a.PHASE and d['worker']=='A' and")
(H/'root_steps.py').write_text(s)
(H/'root_steps.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile='compiler-runtime-binding-16/root_steps.py',tofile='compiler-controls-preparation-18/root_steps.py')))
