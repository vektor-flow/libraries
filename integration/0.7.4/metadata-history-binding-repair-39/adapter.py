#!/usr/bin/env python3
"""Source-only proposal. assemble writes only this packet; run needs real root authority.
No controller/ledger mutations, receipt fabrication, subprocess launcher or retry.
"""
import argparse
import copy
import errno
import fcntl
import hashlib
import importlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
PACKAGE = HERE / 'generator'
COORDINATOR = '01a14893-cb1e-7203-97dd-de3da44dcf31'
GIB = 2**30
STAGES = ['compile-53', 'compile-90', 'link-compiler', 'compile-regression',
          'link-regression-baseline', 'run-regression-baseline',
          'link-regression-candidate', 'run-regression-candidate']
MATCH = ('owner', 'worker', 'iteration', 'attempt', 'phase_scope', 'phase_bytes',
         'ram_peak_bytes', 'timeout_seconds', 'source_commit', 'inputs', 'argv')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def raw(path, limit=16*1024*1024):
    p = Path(path)
    require(p.is_file() and p.stat().st_size <= limit, 'missing/oversized file: '+str(p))
    with p.open('rb') as f:
        b = f.read(limit+1)
    require(len(b) <= limit, 'file grew beyond bound')
    return b


def decode(b):
    def pairs(rows):
        out = {}
        for k, v in rows:
            require(k not in out, 'duplicate JSON key')
            out[k] = v
        return out
    return json.loads(b, object_pairs_hook=pairs)


def read(path):
    return decode(raw(path))


def encoded(obj):
    return (json.dumps(obj, sort_keys=True, indent=2)+'\n').encode()


def digest(b):
    return hashlib.sha256(b).hexdigest()


def pin(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(262144), b''):
            h.update(b)
    return dict(path=str(path), sha256=h.hexdigest())


def verify(p):
    require(pin(p['path']) == {k: p[k] for k in ('path', 'sha256')}, 'changed input: '+p['path'])
    return p


def load_pin(p):
    b = raw(p['path'])
    require(digest(b) == p['sha256'], 'changed JSON input')
    return decode(b)


def save(path, obj):
    with Path(path).open('xb') as f:
        f.write(encoded(obj))


def canonical(path):
    p = Path(path)
    require(p.is_absolute() and str(p) == str(path) and '..' not in p.parts,
            'noncanonical absolute path')
    require(p.resolve() == p, 'symlink authority/path')
    return p


def protected(paths, roots):
    for path in paths:
        p = Path(path)
        require(p.is_absolute() and '..' not in p.parts, 'absolute protected path')
        require(all(not p.is_relative_to(Path(root)) and not p.resolve().is_relative_to(Path(root).resolve()) for root in roots),
                'authority in writable root: '+str(p))


def unique(pins):
    result = {}
    for p in pins:
        q = {k: p[k] for k in ('path', 'sha256')}
        require(q['path'] not in result or result[q['path']] == q, 'conflicting input pin')
        result[q['path']] = q
    return [result[k] for k in sorted(result)]


def controller_inputs(pins):
    """Keep nominal compiler paths in the sealed plan; v6 pins canonical files.

    v6 opens all pin parents/files with O_NOFOLLOW and rejects '..'. Resolve each
    nominal input without changing its authorized digest. The immutable plan
    retains the aliases, roles, order and full original compiler argv/MD contract.
    """
    require(all(Path(p['path']).is_absolute() for p in pins), 'absolute compiler input')
    return unique([dict(path=str(Path(p['path']).resolve(strict=True)),
                        sha256=p['sha256']) for p in pins])


PHASE = 'metadata'
DISK = GIB
TIMEOUT = 300


def check_plan(plan, head, review):
    require(plan['kind'] == 'vkf' and plan.get('selection') == PHASE, 'metadata phase only')
    require(plan['application_head_at_preparation'] == head, 'stale plan HEAD')
    require(plan['candidate_review'] == dict(review, executable=True), 'complete corrected review')
    require(plan['executable'] is True, 'held plan')
    seal = read(HERE/'source-contract.json')
    expected = load_pin(seal['control_plan'])
    expected, _ = relocate(expected, plan['out'])
    require(plan == expected, 'complete sealed metadata plan mismatch')
    require(plan['compiler_receipt'] == load_pin(seal['compiler_receipt']), 'actual native17 receipt')
    require(len(plan['cases']) == 1 and len(plan['stages']) == 3, 'original metadata case and three stages')


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
    require(not target.exists(), 'fresh metadata subdirectory')
    target.mkdir()
    for path in plan['directories']:
        dest = canonical(path)
        require(dest.is_relative_to(target), 'directory materialization escape')
        dest.mkdir(parents=True, exist_ok=True)
    for link in plan['symlinks']:
        dest = canonical(link['path']); source = canonical(link['target'])
        require(dest.is_relative_to(target), 'symlink materialization escape')
        require(dict(path=str(source), sha256=link['sha256']) in controller_inputs(plan['inputs']), 'unpinned stdlib link')
        # The sealed legacy 'symlinks' rows bind original stdlib sources.
        # Installed accounting requires regular files in the charged attempt.
        # Retain those canonical input pins and copy their exact bytes; do not
        # link/hardlink an external file into the writable attempt.
        data = raw(source)
        require(digest(data) == link['sha256'], 'changed stdlib source')
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open('xb') as f: f.write(data)
        verify(dict(path=str(dest), sha256=link['sha256']))
    for item in assets:
        dest = canonical(item['target'])
        require(dest.is_relative_to(target), 'materialization escape')
        verify(item['source'])
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open('xb') as f: f.write(raw(item['source']['path']))
    with (target/'plan.json').open('xb') as f: f.write(raw(plan_pin['path']))


def relocate(plan, target):
    """Only relocate output-root strings and generated JSON; C++ bytes unchanged.
    Caller seals returned assets/plan outside writable roots. No materialization here.
    """
    old, new = str(canonical(plan['out'])), str(canonical(target))
    def move(x):
        if isinstance(x, str):
            # Some compiler arguments embed an absolute dependency path after '='.
            return x.replace(old+'/', new+'/') if old+'/' in x else new if x == old else x
        if isinstance(x, list): return [move(v) for v in x]
        if isinstance(x, dict): return {move(k): move(v) for k,v in x.items()}
        return x
    result, assets, hashes = move(plan), [], {}
    for p in plan['generated']:
        source = canonical(p['path'])
        require(source.is_relative_to(Path(old)), 'generated path outside source staging')
        b = raw(source)
        require(digest(b) == p['sha256'], 'changed generated source')
        if source.suffix == '.json': b = encoded(move(decode(b)))
        elif source.suffix == '.stdin': b = move(b.decode('utf-8')).encode('utf-8')
        dest = move(str(source))
        hashes[dest] = digest(b)
        assets.append((dest, b))
    def update(x):
        if isinstance(x, dict):
            for v in x.values(): update(v)
            path = x.get('effective', x.get('path'))
            if path in hashes and 'sha256' in x: x['sha256'] = hashes[path]
        elif isinstance(x, list):
            for v in x: update(v)
    update(result)
    require(result['stages'] == move(plan['stages']), 'oracle transformation')
    return result, assets


def current_head():
    child = subprocess.run(['/usr/bin/git','-C',str(REPO),'rev-parse','HEAD'],
                           check=True,capture_output=True,text=True,timeout=5)
    return child.stdout.strip()


def static_contract():
    s = read(HERE/'source-contract.json')
    for p in s['pins']: verify(p)
    require(pin(HERE/'adapter.py') in s['pins'], 'adapter source not sealed')
    return s


def evidence(request, s):
    # These are root review exports of REAL receipts, never substitutes for them.
    require(request['coordinator'] == COORDINATOR and request['native_execution'] is True,
            'actual root execution decision required')
    require(request['phase'] == PHASE and request['worker'] == 'A' and
            request['ram_bytes'] == 8*GIB and request['disk_bytes'] == DISK and
            request['timeout_seconds'] == TIMEOUT, 'root must admit metadata A8GiB/1GiB/300s explicitly')
    require(request['source_commit'] == s['source_commit'], 'source transition needs resealed packet')
    q = load_pin(request['qualification_review'])
    require(q['coordinator'] == COORDINATOR and q['qualified'] is True and q['worker'] == 'A'
            and q['boot'] == request['boot'] and q['v6_bundle'] == s['v6_bundle'],
            'actual A namespace qualification required')
    require(q['cases'] == ['success','nonzero','timeout'] and q['evidence'], 'complete qualification/joins required')
    for p in q['evidence']: verify(p)
    o = load_pin(request['owner_receipt'])
    require(o['coordinator'] == COORDINATOR and o['worker'] == 'A' and o['owner'] == request['owner']
            and o['iteration'] == request['iteration'] and o['transition'] == request['owner_transition']
            and o['rotation_completed'] is True, 'genuine owner rotation receipt required')
    transition = load_pin(request['owner_transition'])
    require(transition['worker'] == 'A' and transition['to_owner'] == request['owner']
            and transition['coordinator'] == COORDINATOR, 'transition owner')
    publication_auth = load_pin(request['publication_authorization'])
    require(publication_auth['coordinator'] == COORDINATOR and
            publication_auth['owner_file_publication_authorized'] is True,
            'separate root publication authorization required')
    require(request['observed_only_toolchain_accepted'] is True, 'root toolchain provenance decision required')
    return unique([request[k] for k in ('qualification_review','owner_receipt','owner_transition',
                                      'publication_authorization')] + q['evidence'])


def assemble(plan_path, request_path, out):
    """No owner/state reads, no native/service calls; requires completed root inputs."""
    out = canonical(out)
    require(out.is_relative_to(HERE) and not out.exists(), 'fresh output inside own packet only')
    s, r = static_contract(), read(request_path)
    ep = evidence(r, s)  # Fail before any output if actual root inputs are absent.
    require(current_head() == r['source_commit'], 'stale current HEAD before assembly')
    plan = read(plan_path)
    review = load_pin(s['review'])
    check_plan(plan, r['source_commit'], review)
    config = load_pin(s['v6_bundle']['config'])
    policies = [load_pin(p) for p in config['approved_policies']]
    roots = [p['root']['path'] for p in policies]
    policy_pin = s['a_policy']
    policy = load_pin(policy_pin)
    require(re.fullmatch(r'[A-Za-z0-9_.-]+', r['attempt']) and r['attempt'] not in ('.','..'), 'attempt name')
    attempt = str(Path(policy['root']['path'])/r['attempt'])
    target = str(Path(attempt)/PHASE)
    authority_paths = [str(out), r['grant_path'], r['manifest_path'], r['publication_receipt_path'],
                       config['owner_state'], s['state_path'], s['lock_path'], str(plan_path), str(request_path)]
    for path in authority_paths: canonical(path)
    protected(authority_paths+[p['path'] for p in s['pins']+ep], roots)
    # Nominal aliases must also stay outside every job-writable root.
    protected_inputs(plan['inputs'], roots, attempt)
    result, assets = relocate(plan, target)
    check_plan(result, r['source_commit'], review)
    out.mkdir()
    sources = []
    for i,(dest,b) in enumerate(assets):
        f = out/('asset-'+str(i))
        with f.open('xb') as stream: stream.write(b)
        sources.append(dict(source=pin(f), target=dest))
    save(out/'plan.json', result)
    c = dict(schema=1, request=r, source_contract=pin(HERE/'source-contract.json'),
             plan=pin(out/'plan.json'), assets=sources, attempt_root=attempt,
             roots=roots, candidate_review=s['review'])
    save(out/'contract.json', c)
    cp = pin(out/'contract.json')
    argv = [s['python']['path'], '-I', '-B', str(HERE/'adapter.py'), 'run',
            '--contract', cp['path'], '--contract-sha256', cp['sha256'],
            '--grant', r['grant_path'], '--manifest', r['manifest_path']]
    inputs = unique(s['pins']+ep+controller_inputs(plan['inputs'])+[pin(HERE/'source-contract.json'), cp, c['plan']]
                    +[x['source'] for x in sources])
    protected_inputs(inputs, roots, attempt)
    g = dict(storage_admission_version='direct-directory-v2', coordinator=COORDINATOR,
             worker='A', owner=r['owner'], iteration=r['iteration'], attempt=r['attempt'],
             phase_scope=PHASE, phase_bytes=DISK, ram_peak_bytes=8*GIB, timeout_seconds=TIMEOUT,
             source_commit=r['source_commit'], owner_transition=r['owner_transition'],
             runtime_config=s['v6_bundle']['config'], controller=s['v6_bundle']['controller'],
             helpers=s['v6_bundle']['helpers'], storage_policy=policy_pin,
             predecessor_controller=policy['predecessor_controller'], resource_ledger=policy['predecessor_ledger'],
             owned_processes=s['owned_processes'], inputs=inputs, argv=argv)
    # The manifest pins the final bytes of the grant, at its FUTURE protected path.
    gp = dict(path=r['grant_path'], sha256=digest(encoded(g)))
    m = {k:copy.deepcopy(g[k]) for k in MATCH}
    m.update(grant=gp, controller=g['controller'], attempt_root=attempt, cwd=attempt,
             tmpdir=attempt+'/tmp', cache=attempt+'/cache', ccache=attempt+'/ccache',
             receipts=attempt+'/receipts', output_paths=[target, attempt+'/receipts', attempt+'/tmp',
                                                        attempt+'/cache', attempt+'/ccache'])
    save(out/'grant.candidate.json', g)
    save(out/'manifest.candidate.json', m)
    require(current_head() == r['source_commit'], 'HEAD advanced during assembly; discard candidate')
    save(out/'PREPARATION-ONLY.json', dict(native_executed=False, admitted=False,
         grant=gp, manifest=dict(path=r['manifest_path'], sha256=digest(encoded(m))),
         forecast=dict(ram_bytes=4*GIB,disk_bytes=DISK,timeout_seconds=TIMEOUT),
         authority_publication='ROOT ONLY; exact bytes; owner file separate after rotation'))


def validate_runtime(c, s, g, m, gp, mp, state, owners, publication, cgroup, boot):
    """Pure validation seam: no mutations; tests use in-memory marked data only."""
    r = c['request']
    require(boot == r['boot'], 'stale boot/qualification')
    require(g['worker'] == 'A' and g['owner'] == r['owner'] and g['iteration'] == r['iteration']
            and g['owner_transition'] == r['owner_transition'], 'stale owner')
    require(g['ram_peak_bytes'] == 8*GIB and g['phase_bytes'] == DISK and
            g['timeout_seconds'] == TIMEOUT and g['phase_scope'] == PHASE, 'admission budget/scope')
    require(g['coordinator'] == COORDINATOR and g['storage_admission_version'] == 'direct-directory-v2', 'authority')
    require(g['controller'] == s['v6_bundle']['controller'] and g['helpers'] == s['v6_bundle']['helpers']
            and g['runtime_config'] == s['v6_bundle']['config'], 'complete installed v6 bundle')
    require(g['source_commit'] == r['source_commit'], 'source HEAD')
    require(all(m[k] == g[k] for k in MATCH) and m['grant'] == gp and
            m['controller'] == g['controller'] and m['attempt_root'] == c['attempt_root'], 'manifest binding')
    require(all(p in g['inputs'] for p in s['pins']), 'helper/bin/policy/package omission')
    require(owners['workers']['A'] == dict(grant=gp, thread=r['owner'], iteration=r['iteration']), 'owner publication mismatch')
    lane = state['lanes']['A']
    require(lane['transitions'][-1] == r['owner_transition'] and lane['pin'] == g['storage_policy'], 'stale ledger owner/policy')
    require(publication['coordinator'] == COORDINATOR and publication['published'] is True and
            publication['under_capacity_lock'] is True and publication['grant'] == gp and
            publication['manifest'] == mp and publication['owner_transition'] == r['owner_transition'] and
            publication['owner_entry'] == owners['workers']['A'], 'real separately authorized publication receipt required')
    row = state['phases']['A:'+g['attempt']]
    require(row['stage'] == 'running' and 'join' not in row and row['grant'] == gp and row['manifest'] == mp
            and row['owner'] == r['owner'] and row['worker'] == 'A' and
            row['ram_bytes'] == 8*GIB and row['phase_bytes'] == DISK, 'actual running controller admission required')
    require(row['custody']['controller'] == g['controller'] and row['custody']['config'] == g['runtime_config']
            and row['custody']['cgroup'] == cgroup and row['service']['identity']['cgroup'] == cgroup
            and row['service']['invocation'], 'controller service custody')
    return row


def acquire_runtime_lock(lock, deadline):
    """Retry only contention, on the same read-only FD, within an absolute budget.

    The caller owns the FD context and closes it on every outcome. No snapshot
    reads occur until this returns; the controller's outer timer keeps running.
    """
    started = time.monotonic()
    attempts = 0
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError('capacity shared-lock deadline expired: path=%s '
                               'waited=%.3fs attempts=%d; no snapshot/materialization; '
                               'inspect controller guards/lock holders before a new grant'
                               % (lock.name, time.monotonic()-started, attempts))
        attempts += 1
        try:
            fcntl.flock(lock, fcntl.LOCK_SH | fcntl.LOCK_NB)
        except OSError as error:
            if error.errno not in (errno.EAGAIN, errno.EWOULDBLOCK):
                raise
            time.sleep(min(0.05, max(0.0, deadline-time.monotonic())))
        else:
            require(time.monotonic() < deadline, 'shared lock acquired after deadline')
            opened, current = os.fstat(lock.fileno()), os.stat(canonical(lock.name))
            require((opened.st_dev, opened.st_ino) == (current.st_dev, current.st_ino),
                    'capacity lock replaced during acquisition')
            return


def run(contract, contract_sha256, grant_path, manifest_path):
    # Consume preflight/lock/materialization time from the exact metadata phase budget.
    deadline = time.monotonic() + TIMEOUT
    # Only ROOT may arrange this invocation inside v6's already qualified namespace.
    cp = dict(path=contract, sha256=contract_sha256)
    c = load_pin(cp)
    verify(c['source_contract'])
    require(c['source_contract']['path'] == str(HERE/'source-contract.json'), 'source contract path')
    s = static_contract()
    r = c['request']
    ep = evidence(r, s)
    require(grant_path == r['grant_path'] and manifest_path == r['manifest_path'], 'authority path')
    gp, mp = pin(grant_path), pin(manifest_path)
    g, m = load_pin(gp), load_pin(mp)
    config = load_pin(s['v6_bundle']['config'])
    require(c['roots'] == [load_pin(p)['root']['path'] for p in config['approved_policies']],
            'all enrolled writable roots required')
    for path in (grant_path,manifest_path,r['publication_receipt_path'],s['state_path'],config['owner_state']): canonical(path)
    protected([grant_path,manifest_path,r['publication_receipt_path'],
               s['state_path'],s['lock_path'],config['owner_state']], c['roots'])
    protected_inputs(g['inputs'], c['roots'], c['attempt_root'])
    expected_argv = [s['python']['path'], '-I', '-B', str(HERE/'adapter.py'), 'run', '--contract',
                     contract, '--contract-sha256', contract_sha256, '--grant', grant_path, '--manifest', manifest_path]
    require(g['argv'] == expected_argv, 'exact adapter argv')
    for p in unique(s['pins']+ep+[cp,c['source_contract'],c['plan']]+[x['source'] for x in c['assets']]):
        require(p in g['inputs'], 'binding/materialization input omitted'); verify(p)
    plan = load_pin(c['plan'])
    check_plan(plan, r['source_commit'], load_pin(c['candidate_review']))
    protected_inputs(plan['inputs'], c['roots'], c['attempt_root'])
    require(all(p in g['inputs'] for p in controller_inputs(plan['inputs'])), 'plan inputs omitted')
    # Use pinned package, isolated Python invocation and no editable cwd imports.
    sys.path.insert(0, str(PACKAGE))
    payload = importlib.import_module('payload')
    require(current_head() == r['source_commit'], 'stale current HEAD')
    # Existing lock opened read-only; shared lock, no creation/save/owner API call.
    with open(canonical(s['lock_path']), 'rb') as lock:
        acquire_runtime_lock(lock, min(deadline, time.monotonic()+10.0))
        state_pin = pin(s['state_path'])
        state = load_pin(state_pin)
        owners = read(config['owner_state'])
        publication_pin = pin(r['publication_receipt_path'])
        publication = load_pin(publication_pin)
        cgroup = Path('/proc/self/cgroup').read_text().split('::')[-1].strip()
        validate_runtime(c,s,g,m,gp,mp,state,owners,publication,cgroup,
                         Path('/proc/sys/kernel/random/boot_id').read_text().strip())
        binding = dict(coordinator=COORDINATOR, plan=c['plan'], charged_attempt=plan['out'],
                       phase=PHASE, native_execution=True, environment_qualified=True,
                       ram_bytes=g['ram_peak_bytes'], disk_bytes=g['phase_bytes'],
                       timeout_seconds=g['timeout_seconds'], grant=gp, controller_receipt=state_pin,
                       environment_qualification=r['qualification_review'], candidate_review=c['candidate_review'])
        # controller_receipt is the genuine protected live ledger snapshot, validated under lock.
        # Never use attempt/receipts/admission.json as writable authority. No disk binding receipt.
        payload.validate_admission(plan,binding,c['plan'])
    for p in g['inputs']: verify(p)
    require(current_head() == r['source_commit'], 'HEAD changed before materialization')
    target = canonical(plan['out'])
    require(target == Path(c['attempt_root'])/PHASE and not target.exists(), 'fresh compiler subdirectory')
    require(time.monotonic() < deadline, 'phase deadline before materialization')
    materialize(plan, c['assets'], c['plan'], target)
    # v6 guards/accounting and its independently joined service remain authoritative.
    remaining = deadline - time.monotonic()
    require(remaining > 0, 'phase deadline before payload')
    payload.execute(plan,dict(binding, timeout_seconds=remaining))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='mode',required=True)
    a = sub.add_parser('assemble')
    a.add_argument('--plan',required=True); a.add_argument('--root-inputs',required=True); a.add_argument('--out',required=True)
    a = sub.add_parser('run')
    a.add_argument('--contract',required=True); a.add_argument('--contract-sha256',required=True)
    a.add_argument('--grant',required=True); a.add_argument('--manifest',required=True)
    args = parser.parse_args()
    if args.mode == 'assemble': assemble(args.plan,args.root_inputs,args.out)
    else: run(args.contract,args.contract_sha256,args.grant,args.manifest)

if __name__ == '__main__':
    main()
