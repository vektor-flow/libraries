#!/usr/bin/env python3
"""Exact four primitive preparation and v4-controlled execution. No implicit admission."""
import argparse
import ctypes
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import stat
import subprocess
import sys
import time
from types import SimpleNamespace

PLAN_SHA = '1d2bf57861fdc0e9d8f5e1f4410ee6cb6ace99273cc706fc93090db43dcdd976'
ORDER = ('int64', 'extraction', 'unicode', 'native_named_syntax_dependency')
COORDINATOR = '01a14893-cb1e-7203-97dd-de3da44dcf31'
GIB = 2**30
HERE = Path(__file__).resolve()


def require(ok, reason):
    if not ok:
        raise RuntimeError(reason)


def encoded(obj):
    return (json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False)+'\n').encode()


def write(path, obj):
    with Path(path).open('xb') as f:
        f.write(encoded(obj)); f.flush(); os.fsync(f.fileno())


def pin(path):
    p = Path(path)
    return dict(path=str(p), sha256=hashlib.sha256(p.read_bytes()).hexdigest())


def verify(p):
    require(Path(p['path']).is_absolute(), 'pin must be absolute')
    require(pin(p['path'])['sha256'] == p['sha256'], 'changed input: '+p['path'])
    return Path(p['path'])


def read(p):
    return json.loads(verify(p).read_text())


def all_pins(obj):
    result = {}
    def visit(x):
        if isinstance(x, dict):
            if 'path' in x and 'sha256' in x:
                value = dict(path=x['path'], sha256=x['sha256'])
                require(x['path'] not in result or result[x['path']] == value, 'conflicting pin')
                result[x['path']] = value
            for v in x.values(): visit(v)
        elif isinstance(x, list):
            for v in x: visit(v)
    visit(obj)
    return [result[k] for k in sorted(result)]


def canonical_pins(values):
    # v4 O_NOFOLLOW pins require regular files, including the python3 symlink target.
    return all_pins([dict(path=str(verify(p).resolve()), sha256=p['sha256']) for p in all_pins(values)])


def load_plan(path):
    p = dict(path=str(Path(path)), sha256=PLAN_SHA)
    plan = read(p)
    require(tuple(e['id'] for e in plan['independent_order']) == ORDER, 'exact order')
    for q in all_pins(plan): verify(q)
    return p, plan


def absolute(path):
    p = Path(path)
    require(p.is_absolute() and '..' not in p.parts and str(p) == str(p.resolve()),
            'absolute canonical path required: '+str(p))
    return p


def spec_for(plan_path, entry, root):
    pp, plan = load_plan(plan_path)
    require(entry in ORDER, 'unknown entry')
    root = absolute(root)
    e = plan['independent_order'][ORDER.index(entry)]
    t = plan['toolchain']
    by_name = {Path(p['path']).name:p for p in t['tools']}
    work = root/'cwd'/'primitive'
    raw = work/'raw'; normalized = work/'normalized'
    source = [e['entry_source'], *e['source_closure']]
    destinations = [str(raw/Path(p['path']).name) for p in source]
    require(len(set(destinations)) == len(source), 'source name collision')
    env = dict(t['environment'], PATH='/home/viktor/.local/bin:/usr/bin:/bin',
               HOME=str(work/'home'), TMPDIR=str(root/'tmpdir'),
               TMP=str(root/'tmpdir'), TEMP=str(root/'tmpdir'),
               XDG_CACHE_HOME=str(root/'cache'), CCACHE_DIR=str(root/'ccache'))
    return dict(schema='native-primitive-spec-v1', plan=pp, entry=e, attempt_root=str(root),
        work=str(work), raw=str(raw), normalized=str(normalized),
        materialize=[dict(source=p, destination=d) for p,d in zip(source,destinations)],
        stdlib_copies=[dict(source=p, destination=str(work/Path(p['path']).relative_to(t['environment']['VKF_HOME']))) for p in t['stdlib']],
        environment=env, unset=t['unset'], stdin=str(work/'stdin'), binary=str(work/'case.exe'),
        argv=dict(normalize=[str(Path(by_name['python3']['path']).resolve()),'-B',by_name['normalize_module_aliases.py']['path'],
                            '--source-dir',str(raw),'--output-dir',str(normalized)],
                  compile=[str(Path(by_name['vkf-strict']['path']).resolve()),'-b',str(normalized/'source'/Path(e['entry_source']['path']).name),
                           '-o',str(work/'case.exe'),'--diagnostics'], run=[str(work/'case.exe')]),
        inputs=canonical_pins([pp, e['entry_source'], e['source_closure'], t]),
        original_input_pins=all_pins([pp, e['entry_source'], e['source_closure'], t]),
        estimate_provisional=True, inclusive_artifact_estimate_bytes=e['inclusive_artifact_estimate_bytes'],
        artifact_components_bytes=e['artifact_components_bytes'], native47_credit=0, original419_credit=0)


def materialize(spec):
    """Called inside the admitted attempt, or bounded tests; never modifies sources."""
    for p in spec['inputs']: verify(p)
    work = absolute(spec['work']); work.mkdir()  # exclusive, no replay
    Path(spec['raw']).mkdir(); (work/'home').mkdir()
    for item in spec['materialize']:
        data = verify(item['source']).read_bytes()
        require(hashlib.sha256(data).hexdigest() == item['source']['sha256'], 'copy race')
        with Path(item['destination']).open('xb') as f: f.write(data)
    for item in spec['stdlib_copies']:
        target = verify(item['source']); dest = Path(item['destination'])
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open('xb') as f: f.write(target.read_bytes())
        require(pin(dest)['sha256'] == item['source']['sha256'], 'stdlib copy race')
    with Path(spec['stdin']).open('xb') as f: f.write(spec['entry']['stdin'].encode())
    write(work/'materialization.json', dict(spec=spec, copied=[pin(x['destination']) for x in spec['materialize']]))


def identity(pid):
    try:
        s = (Path('/proc')/str(pid)/'stat').read_text().rsplit(')',1)[1].split()
        return dict(pid=int(pid), starttime=int(s[19]), ppid=int(s[1]), state=s[0])
    except (OSError, ValueError, IndexError): return None


def matches(saved):
    current = identity(saved['pid'])
    return current if current and current['starttime'] == saved['starttime'] else None


def owned_table(tracked):
    """Discover descendants AND subreaper-adopted children, including setsid orphans."""
    table = {}
    for p in Path('/proc').iterdir():
        if p.name.isdigit():
            v = identity(int(p.name))
            if v: table[v['pid']] = v
    parents = {os.getpid()} | {pid for pid,s in tracked.items() if matches(s)}
    while True:
        new = {pid for pid,v in table.items() if v['ppid'] in parents and pid not in parents}
        if not new: break
        for pid in new: tracked[pid] = table[pid]
        parents.update(new)


def stage(argv, cwd, env, stdin, prefix, seconds):
    """Dedicated synchronous process owner; no other child may run concurrently."""
    require(0 < seconds <= 30, 'per-child deadline exceeds accepted plan')
    libc = ctypes.CDLL(None, use_errno=True)
    require(libc.prctl(36,1,0,0,0) == 0, 'subreaper unavailable')
    prefix = Path(prefix); tracked = {}; reaped = []; child = None
    start = time.monotonic(); timed_out = False; orphaned = False; error = None
    out = Path(str(prefix)+'.stdout'); err = Path(str(prefix)+'.stderr')
    try:
        with open(stdin,'rb') as inp, out.open('xb') as stdout, err.open('xb') as stderr:
            child = subprocess.Popen(argv, cwd=cwd, env=env, stdin=inp, stdout=stdout,
                                     stderr=stderr, start_new_session=True)
            first = identity(child.pid)
            if first: tracked[child.pid] = first
            while True:
                owned_table(tracked)
                code = child.poll()
                if code is not None: break
                if time.monotonic()-start >= seconds:
                    timed_out = True; break
                time.sleep(.01)
            owned_table(tracked)
            orphaned = any(pid != child.pid and matches(s) for pid,s in tracked.items())
    except BaseException as exc:
        error = type(exc).__name__+': '+str(exc)
    finally:
        # Always terminate/reap every remaining owned descendant, even after leader exit.
        end = time.monotonic()+5
        while child is not None:
            owned_table(tracked)
            for s in list(tracked.values()):
                v = matches(s)
                if v and v['state'] != 'Z':
                    try: os.kill(v['pid'], signal.SIGKILL)
                    except ProcessLookupError: pass
            child.poll()
            for pid,s in list(tracked.items()):
                if pid == child.pid: continue
                try:
                    got,status = os.waitpid(pid, os.WNOHANG)
                    if got: reaped.append(dict(pid=got, starttime=s['starttime'], wait_status=status))
                except ChildProcessError: pass
            if not any(matches(s) for s in tracked.values()): break
            if time.monotonic() >= end: break
            time.sleep(.01)
        if child is not None:
            try: child.wait(timeout=.1)
            except subprocess.TimeoutExpired: error = 'direct child did not join'
    remaining = [s for s in tracked.values() if matches(s)]
    record = dict(argv=argv, cwd=cwd, environment=env, stdin=pin(stdin),
        stdout=pin(out), stderr=pin(err), pid=child.pid if child else None,
        exit=child.returncode if child else None, timed_out=timed_out,
        deadline_seconds=seconds, elapsed_seconds=time.monotonic()-start,
        orphaned_descendant_on_exit=orphaned, tracked=list(tracked.values()), reaped=reaped,
        remaining_identities=remaining, children_joined=not remaining, error=error)
    record['ok'] = child is not None and record['exit'] == 0 and not any((timed_out,orphaned,remaining,error))
    write(str(prefix)+'.json', record)
    return record


def verify_normalized(spec):
    report = json.loads((Path(spec['normalized'])/'normalization.json').read_text())
    expected = {Path(x['destination']).name:x['source']['sha256'] for x in spec['materialize']}
    rows = report['files']
    require(len(rows) == len(expected) and {r['name'] for r in rows} == set(expected), 'normalized closure')
    require(report['baseline'] == spec['raw'] and report['ambiguousAliases'] == [], 'normalizer ambiguity')
    directory = Path(spec['normalized'])/'source'
    require({p.name for p in directory.iterdir()} == set(expected), 'unexpected normalized file')
    for row in rows:
        require(row['beforeSha256'] == expected[row['name']], 'normalizer input hash')
        require(pin(directory/row['name'])['sha256'] == row['afterSha256'], 'normalizer output hash')
    stdout = json.loads((Path(spec['work'])/'normalize.stdout').read_text())
    require(stdout == dict(changedFiles=report['changedFiles'], rewrittenCalls=report['rewrittenCalls'],
        ambiguousAliases=0, files=len(expected), source=str(directory)), 'unexpected normalizer stdout')
    require((Path(spec['work'])/'normalize.stderr').read_bytes() == b'', 'unexpected normalizer stderr')
    return [pin(directory/name) for name in sorted(expected)]


def execute(spec, *, stage_function=stage):
    """Internal payload engine. Production CLI obtains spec solely from pinned v4 inputs."""
    result = dict(entry=spec['entry']['id'], passed=False, native_credit=False, stages=[], error=None)
    work = Path(spec['work'])
    try:
        materialize(spec)
        for name in ('normalize','compile','run'):
            for p in spec['inputs']: verify(p)
            for item in spec['materialize']:
                require(pin(item['destination'])['sha256'] == item['source']['sha256'], 'raw input changed')
            if name == 'compile':
                result['normalized'] = verify_normalized(spec)
                require(not os.path.lexists(spec['binary']), 'executable exists before compile')
            if name == 'run':
                binary = Path(spec['binary'])
                require(binary.is_file() and not binary.is_symlink() and
                        stat.S_ISREG(binary.stat().st_mode) and os.access(binary,os.X_OK), 'missing fresh executable')
                result['binary'] = pin(binary)
            row = stage_function(spec['argv'][name], spec['work'], spec['environment'], spec['stdin'],
                                 work/name, spec['entry']['deadlines_seconds'][name])
            result['stages'].append(dict(name=name, **row))
            require(row['ok'], 'failed '+name)
            for p in spec['inputs']: verify(p)
            if name == 'run':
                require(pin(spec['binary']) == result['binary'], 'binary changed during run')
                require(Path(row['stdout']['path']).read_bytes() == spec['entry']['expected_stdout'].encode()
                    and Path(row['stderr']['path']).read_bytes() == spec['entry']['expected_stderr'].encode(),
                    'unexpected runtime output')
        for p in result['normalized']: verify(p)
        for item in spec['stdlib_copies']:
            require(pin(item['destination'])['sha256'] == item['source']['sha256'], 'stdlib posthash')
        for item in spec['materialize']:
            require(pin(item['destination'])['sha256'] == item['source']['sha256'], 'raw posthash')
        result['posthash_match'] = True
        result['passed'] = True
    except BaseException as exc:
        result['error'] = type(exc).__name__+': '+str(exc)
    if work.is_dir(): write(work/'result.json', result)
    return result


def prepare(request_path, output):
    """Pure preparation: review files only; no owner/ledger/config/service operations."""
    request_pin = pin(absolute(request_path)); req = read(request_pin)
    require(req['coordinator'] == COORDINATOR, 'coordinator')
    require(req['entry'] in ORDER and req['owner'] and req['worker'] in ('A','F'), 'fresh owner/lane')
    qual = read(req['live_qualification_review'])
    require(qual['coordinator'] == COORDINATOR and qual['storage_v4_qualified'] is True
            and qual['native_primitives_authorized'] is True, 'root live qualification/admission review required')
    root = absolute(req['attempt_root']); require(not root.exists(), 'attempt exists')
    require(root.name == req['attempt'] and req['attempt'] not in ('.','..'), 'attempt name')
    spec = spec_for(req['plan'], req['entry'], root)
    require(req['phase_bytes'] >= spec['inclusive_artifact_estimate_bytes'], 'inclusive provisional estimate')
    require(req['ram_peak_bytes'] in (3*GIB,8*GIB) and (req['ram_peak_bytes'] != 8*GIB or req['worker']=='A'), 'RAM profile')
    require(120 <= req['timeout_seconds'] <= 180, 'outer deadline must allow three 30s children and joins')
    out = absolute(output)
    require(not out.is_relative_to(root), 'authority inside writable attempt')
    out.mkdir()  # final immutable review location: root must not relocate emitted files
    spec_path = out/'spec.json'; write(spec_path,spec)
    spec_pin = pin(spec_path)
    argv = [str(Path('/usr/bin/python3').resolve()),'-B',str(HERE),'payload','--spec',str(spec_path),'--sha256',spec_pin['sha256'],
            '--request',str(request_path),'--request-sha256',request_pin['sha256']]
    keys = ('owner','worker','iteration','attempt','phase_bytes','ram_peak_bytes','timeout_seconds','source_commit',
            'controller','helpers','owned_processes','resource_ledger','predecessor_controller','storage_policy',
            'runtime_config','owner_transition')
    g = {k:req[k] for k in keys}
    g.update(storage_admission_version='direct-directory-v2',coordinator=COORDINATOR,
        phase_scope='exact independent primitive '+req['entry'], argv=argv,
        inputs=canonical_pins([spec['inputs'],spec_pin,request_pin,pin(HERE),req['extra_inputs'],req['live_qualification_review']]))
    for p in all_pins(g): verify(p)
    write(out/'grant.json',g)
    manifest = {k:g[k] for k in ('owner','worker','iteration','attempt','phase_scope','phase_bytes','ram_peak_bytes',
        'timeout_seconds','source_commit','inputs','argv','controller')}
    manifest.update(grant=pin(out/'grant.json'),attempt_root=str(root),
        **{k:str(root/k) for k in ('cwd','tmpdir','cache','ccache','receipts')},
        output_paths=[spec['work'],str(root/'tmpdir'),str(root/'cache'),str(root/'ccache'),str(root/'receipts')])
    write(out/'manifest.json', manifest)
    bundle = dict(entry=req['entry'], spec=spec_pin, request=request_pin, grant=pin(out/'grant.json'),
                  manifest=pin(out/'manifest.json'), previous=req['previous'], preparation_only=True)
    write(out/'bundle.json',bundle)
    return bundle


def validate_bundle(bundle):
    req = read(bundle['request']); spec = read(bundle['spec'])
    require(spec == spec_for(req['plan'],bundle['entry'],req['attempt_root']), 'spec drift')
    require(req['entry'] == bundle['entry'] and req['previous'] == bundle['previous'], 'bundle/request drift')
    qualification = read(req['live_qualification_review'])
    require(qualification['coordinator'] == COORDINATOR and qualification['storage_v4_qualified'] is True
            and qualification['native_primitives_authorized'] is True, 'unqualified root authority')
    g = read(bundle['grant']); m = read(bundle['manifest'])
    expected_argv = [str(Path('/usr/bin/python3').resolve()),'-B',str(HERE),'payload',
        '--spec',bundle['spec']['path'],'--sha256',bundle['spec']['sha256'],
        '--request',bundle['request']['path'],'--request-sha256',bundle['request']['sha256']]
    require(g['argv'] == m['argv'] == expected_argv, 'payload binding')
    expected_inputs = canonical_pins([spec['inputs'],bundle['spec'],bundle['request'],pin(HERE),
                                     req['extra_inputs'],req['live_qualification_review']])
    require(g['inputs'] == m['inputs'] == expected_inputs, 'exact granted inputs')
    require(m['grant'] == bundle['grant'] and m['controller'] == g['controller'], 'grant/manifest binding')
    for k in ('owner','worker','iteration','attempt','phase_bytes','ram_peak_bytes','timeout_seconds','source_commit'):
        require(g[k] == m[k] == req[k], 'request/grant mismatch '+k)
    require(g['phase_bytes'] >= GIB and 120 <= g['timeout_seconds'] <= 180, 'phase envelope')
    require(g['coordinator'] == req['coordinator'] == COORDINATOR, 'coordinator')
    for k in ('controller','helpers','owned_processes','resource_ledger','predecessor_controller',
              'storage_policy','runtime_config','owner_transition'):
        require(g[k] == req[k], 'authority binding '+k)
    require(m['attempt_root'] == spec['attempt_root'], 'attempt binding')
    for k in ('cwd','tmpdir','cache','ccache','receipts'):
        require(m[k] == str(Path(spec['attempt_root'])/k), 'charged output binding '+k)
    require(m['output_paths'] == [spec['work'],m['tmpdir'],m['cache'],m['ccache'],m['receipts']], 'exact output paths')
    return req,spec,g,m


def controller_for(bundle):
    g = read(bundle['grant']); m = read(bundle['manifest'])
    for p in [g['controller'],*g['helpers']]: verify(p)
    sys.path.insert(0,str(Path(g['controller']['path']).parent))
    module_spec = importlib.util.spec_from_file_location('primitive_v4',g['controller']['path'])
    module = importlib.util.module_from_spec(module_spec); module_spec.loader.exec_module(module)
    args = SimpleNamespace(config_sha256=g['runtime_config']['sha256'],grant=Path(bundle['grant']['path']),
        grant_sha256=bundle['grant']['sha256'], manifest=Path(bundle['manifest']['path']),
        manifest_sha256=bundle['manifest']['sha256'])
    return module.Controller(args), g, m


def authenticate_completed(bundle):
    req,spec,g,m = validate_bundle(bundle)
    controller,g,m = controller_for(bundle)
    r = controller.ledger.snapshot()['phases'][g['worker']+':'+g['attempt']]
    require(r['stage']=='joined' and r['grant']==bundle['grant'] and r['manifest']==bundle['manifest'], 'phase not joined')
    receipt = read(r['join'])
    controller.verify_join(r,receipt)
    require(r['inner_result']['exit']==0, 'payload failed')
    spec = read(bundle['spec']); result = json.loads((Path(spec['work'])/'result.json').read_text())
    require(result['passed'] is True and result['entry']==bundle['entry'] and result['posthash_match'] is True, 'primitive failed')
    require([s['name'] for s in result['stages']] == ['normalize','compile','run'], 'missing stages')
    for s in result['stages']:
        require(s['ok'] and s['exit']==0 and not s['timed_out'] and not s['remaining_identities']
                and s['children_joined'] and s['deadline_seconds']==30, 'stage failure/join')
        name = s['name']
        require(s['argv'] == spec['argv'][name] and s['cwd'] == spec['work']
                and s['environment'] == spec['environment'] and s['error'] is None
                and not s['orphaned_descendant_on_exit'], 'actual stage contract')
        require(s['stdin'] == pin(spec['stdin']) and s['stdin']['sha256'] == spec['entry']['stdin_sha256'], 'actual stdin')
        for channel in ('stdout','stderr'):
            require(s[channel]['path'] == str(Path(spec['work'])/(name+'.'+channel)), 'actual output path')
            verify(s[channel])
    require(result['binary']['path'] == spec['binary'], 'actual binary path')
    verify(result['binary'])
    require(result['normalized'] == verify_normalized(spec), 'normalized snapshot evidence')
    for item in spec['materialize']+spec['stdlib_copies']:
        require(pin(item['destination'])['sha256'] == item['source']['sha256'], 'materialized posthash')
    for p in spec['inputs']+result['normalized']: verify(p)
    run = result['stages'][-1]
    require(verify(run['stdout']).read_bytes()==b'' and verify(run['stderr']).read_bytes()==b'', 'runtime output')
    return dict(bundle=bundle, service_join=r['join'], result=pin(Path(spec['work'])/'result.json'))


def drive(bundle_path, sha):
    """One sequential step. Root binds each next grant in owner-state between calls."""
    bundle = read(dict(path=str(absolute(bundle_path)),sha256=sha))
    index = ORDER.index(bundle['entry'])
    require(len(bundle['previous'])==index, 'missing predecessor evidence')
    for name,p in zip(ORDER[:index],bundle['previous']):
        prior = read(p); require(prior['entry']==name, 'predecessor order')
        authenticate_completed(prior)
    req,spec,g,m = validate_bundle(bundle)
    controller,g,m = controller_for(bundle)
    root = absolute(m['attempt_root'])
    require(not root.exists(), 'no retry/existing attempt')
    policy = read(g['storage_policy'])
    require(root == Path(policy['root']['path'])/g['attempt'], 'policy attempt root')
    # v4 requires an existing EMPTY attempt before reserve; metadata is in the full phase estimate.
    # This is reached only by explicit drive, never preparation. Any failure consumes this path.
    root.mkdir(mode=0o700)
    controller.current()  # fresh owner/config/source checks before reserve/service launch
    # outer() is the installed v4 sequential guarded launcher, including terminal verification.
    code = controller.outer()
    require(code==0, 'controller/payload failed; stop, no retry')
    return authenticate_completed(bundle)


def payload(spec_path, sha, request_path, request_sha):
    spec = read(dict(path=str(absolute(spec_path)),sha256=sha))
    req = read(dict(path=str(absolute(request_path)),sha256=request_sha))
    require(spec == spec_for(req['plan'],req['entry'],req['attempt_root']), 'spec drift')
    # Runtime accident guard, not a substitute for v4's actual custody authentication.
    for name in ('pid','net'):
        require(os.readlink('/proc/self/ns/'+name) != req['host_namespaces'][name], 'requires v4 sandbox namespace')
    require(str(Path.cwd()) == str(Path(req['attempt_root'])/'cwd'), 'v4 cwd required')
    return 0 if execute(spec)['passed'] else 1


def main():
    p = argparse.ArgumentParser(description=__doc__); sub = p.add_subparsers(dest='action',required=True)
    q = sub.add_parser('prepare'); q.add_argument('--request',required=True); q.add_argument('--output',required=True)
    q = sub.add_parser('drive'); q.add_argument('--bundle',required=True); q.add_argument('--sha256',required=True)
    q = sub.add_parser('payload'); q.add_argument('--spec',required=True); q.add_argument('--sha256',required=True)
    q.add_argument('--request',required=True); q.add_argument('--request-sha256',required=True)
    a = p.parse_args()
    if a.action=='prepare': print(json.dumps(prepare(a.request,a.output))); return 0
    if a.action=='drive': print(json.dumps(drive(a.bundle,a.sha256))); return 0
    return payload(a.spec,a.sha256,a.request,a.request_sha256)


if __name__=='__main__':
    try: sys.exit(main())
    except Exception as exc:
        print('STOP: '+type(exc).__name__+': '+str(exc),file=sys.stderr); sys.exit(1)
