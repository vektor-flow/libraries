"""Compile and run VKF interpolation; Python is solely an independent test oracle.

Use --output with a NEW directory. This script does not acquire project-wide
execution locks; the caller owns any required scheduling lock for the full run.
"""
from pathlib import Path
from fractions import Fraction as F
import argparse
import ctypes
import hashlib
import json
import math
import os
import shutil
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]


def owned_process(command, log, timeout):
    """Retain output even on timeout; kill and join our isolated process group.

    main enables Linux child-subreaper mode so orphaned compiler helpers in this
    group become waitable here. The admission executor retains the shared lock.
    """
    stdout_path = log.with_suffix('.stdout.log')
    stderr_path = log.with_suffix('.stderr.log')
    process = None
    try:
        available = next(int(line.split()[1])*1024 for line in
                         Path('/proc/meminfo').read_text().splitlines()
                         if line.startswith('MemAvailable:'))
        if available < 4*1024**3:
            raise RuntimeError(f'host reserve below 4 GiB: {available}')
        if os.environ.get('INTERPOLATION_NATIVE_DEADLINE'):
            timeout = min(timeout, float(os.environ['INTERPOLATION_NATIVE_DEADLINE'])-time.time()-10)
            if timeout <= 0:
                raise TimeoutError('batch deadline closure reserve reached')
        with stdout_path.open('wb') as stdout, stderr_path.open('wb') as stderr:
            process = subprocess.Popen(command, stdout=stdout, stderr=stderr,
                                       start_new_session=True)
            try:
                process.wait(timeout=timeout)
            finally:
                # Also remove helpers left behind after a normal leader exit.
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait()
                while True:
                    try:
                        os.waitpid(-process.pid, 0)
                    except ChildProcessError:
                        break
        return subprocess.CompletedProcess(command, process.returncode,
                                           stdout_path.read_text(errors='replace'),
                                           stderr_path.read_text(errors='replace'))
    finally:
        log.write_bytes((stdout_path.read_bytes() if stdout_path.exists() else b'') +
                        (stderr_path.read_bytes() if stderr_path.exists() else b''))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def literal(values):
    return '[' + ','.join(format(float(x), '.17f') for x in values) + ']'


def polynomial(controls, t, derivative=0):
    """Independent exact Bernstein sum, not de Casteljau or native code."""
    rows = [list(map(F, row)) for row in controls]
    for _ in range(derivative):
        n = len(rows) - 1
        if n == 0:
            return [F(0)] * len(rows[0])
        rows = [[n * (b - a) for a, b in zip(rows[i], rows[i + 1])]
                for i in range(n)]
    n = len(rows) - 1
    return [sum(F(math.comb(n, i)) * (1-t)**(n-i) * t**i * rows[i][c]
                for i in range(n+1)) for c in range(len(rows[0]))]


def tensor(controls, u, v, du=0, dv=0):
    return polynomial([polynomial(row, u, du) for row in controls], v, dv)


def fixtures():
    lines = ['i:.Interpolation', 'tests()->bit:']
    comparisons = 0
    samples = 0

    def expect(expr, values, label):
        nonlocal comparisons, samples
        name = 's' + str(samples)
        samples += 1
        lines.append(f'    {name}:{expr}')
        for field, expected in values.items():
            for c, value in enumerate(expected):
                # Exact references, observed machine results checked with a
                # scoped relative/absolute tolerance, not a certified enclosure.
                tol = 3e-11 * (1 + abs(float(value)))
                lines.append(f'    (|{name}.{field}.({c})-({float(value):.17f})|<{tol:.17f})?! "{label} {field} {c}"')
                comparisons += 1

    qs = [F(0), F(1, 7), F(1, 3), F(1, 2), F(6, 7), F(1)]
    blend_start, blend_finish = [F(-2), F(4), F(1, 4)], [F(6), F(-3), F(5, 4)]
    for t in qs:
        name = 'blend' + str(samples)
        lines.append(f'    {name}:i.blend({literal(blend_start)},{literal(blend_finish)},{float(t):.17f})')
        lines.append(f'    ({name}.length()={len(blend_start)})?! "blend channel width {t}"')
        for c, (a, b) in enumerate(zip(blend_start, blend_finish)):
            target = (1-t)*a+t*b
            tol = 3e-11*(1+abs(float(target)))
            lines.append(f'    (|{name}.({c})-({float(target):.17f})|<{tol:.17f})?! "blend {t} {c}"')
            comparisons += 1
            scalar = f'{name}scalar{c}'
            lines.append(f'    {scalar}:i.lerp({float(a):.17f},{float(b):.17f},{float(t):.17f})')
            lines.append(f'    (|{scalar}-({float(target):.17f})|<{tol:.17f})?! "scalar lerp {t} {c}"')
            lines.append(f'    ({scalar}={name}.({c}))?! "scalar vector kernel agreement {t} {c}"')
            comparisons += 2
            if t in (0, 1):
                endpoint = a if t == 0 else b
                lines.append(f'    ({scalar}=({float(endpoint):.17f}))?! "exact scalar endpoint {t} {c}"')
                comparisons += 1
        if t in (0, 1):
            endpoint = blend_start if t == 0 else blend_finish
            for c, target in enumerate(endpoint):
                lines.append(f'    ({name}.({c})=({float(target):.17f}))?! "exact blend endpoint {t} {c}"')
        samples += 1
    cases = [
        [[F(3), F(-2), F(7, 4)]],
        [[F(0), F(2)], [F(3), F(-1)]],
        [[F(0), F(2), F(-1)], [F(2), F(-1), F(1, 2)],
         [F(-1), F(3), F(2)], [F(3), F(0), F(-2)]],
        [[F(3*i-2, 7), F((-1)**i*(i+1), 3)] for i in range(9)],
        [[F(2**30) + F(i, 4), F(-2**28)+F(i*i, 8)] for i in range(5)],
    ]
    for k, controls in enumerate(cases):
        flat = sum(controls, [])
        lines.append(f'    p{k}:i.prepare_bezier({literal(flat)},{len(controls[0])})')
        for t in qs:
            expect(f'i.sample_polynomial(p{k},{float(t):.17f})',
                   {field: polynomial(controls, t, d)
                    for field, d in [('value', 0), ('first', 1), ('second', 2)]},
                   f'Bezier {k} {t}')
        lines.append(f'    (p{k}.controls.length()={len(flat)})?! "prepared control storage width {k}"')
        for c, target in enumerate(flat):
            lines.append(f'    (p{k}.controls.({c})=({float(target):.17f}))?! "sampling must not mutate prepared controls {k} {c}"')
    p0, p1 = [F(1), F(-2)], [F(3), F(5)]
    v0, v1 = [F(2), F(0)], [F(-1), F(4)]
    controls = [p0, [x+v/F(3) for x,v in zip(p0,v0)],
                [x-v/F(3) for x,v in zip(p1,v1)], p1]
    lines.append(f'    h:i.prepare_hermite({literal(p0)},{literal(p1)},{literal(v0)},{literal(v1)})')
    for t in qs:
        expect(f'i.sample_polynomial(h,{float(t):.17f})',
               {field: polynomial(controls, t, d)
                for field, d in [('value', 0), ('first', 1), ('second', 2)]},
               f'Hermite {t}')
    # Genuinely bivariate graph: z=u^2 v+2uv^2-uv+u/4+3v/2.
    net = []
    for j in range(4):
        row = []
        for k in range(4):
            u, v = F(k, 3), F(j, 3)
            u2, v2 = F(k*(k-1), 6), F(j*(j-1), 6)
            row.append([u, v, u2*v+2*u*v2-u*v+u/F(4)+3*v/F(2)])
        net.append(row)
    nets = [net, [[[F(2), F(-1), F(7)]]],
            [[[F(k, 2), F(j, 4), F(k*j, 8)] for k in range(3)] for j in range(5)],
            [[[F(k), F(k*k-2), F((-1)**k, 2)] for k in range(4)]],
            [[[F(j), F(j*j-2), F((-1)**j, 2)]] for j in range(4)]]
    uv = [(F(0),F(0)), (F(1),F(1)), (F(0),F(1)), (F(1),F(0)), (F(1,4),F(3,4)),
          (F(1,2),F(1,2)), (F(1,2),F(0)), (F(1),F(1,3))]
    for k, controls in enumerate(nets):
        flat = [x for row in controls for point in row for x in point]
        lines.append(f'    n{k}:i.prepare_patch({literal(flat)},3,{len(controls[0])},{len(controls)})')
        for u,v in uv:
            expect(f'i.sample_patch(n{k},{float(u):.17f},{float(v):.17f})',
                   {field:tensor(controls,u,v,du,dv) for field,du,dv in
                    [('value',0,0),('du',1,0),('dv',0,1),('duu',2,0),('duv',1,1),('dvv',0,2)]},
                   f'Patch {k} {u},{v}')
        lines.append(f'    (n{k}.controls.length()={len(flat)})?! "prepared patch storage width {k}"')
        for c, target in enumerate(flat):
            lines.append(f'    (n{k}.controls.({c})=({float(target):.17f}))?! "patch samples must not mutate prepared net {k} {c}"')
    # Independent analytic mixed-derivative witness for the actual bicubic graph.
    expect('i.sample_patch(n0,0.25,0.75)',
           {'value':[F(1,4),F(3,4),F(85,64)],
            'du':[F(1),F(0),F(1)],
            'dv':[F(0),F(1),F(33,16)],
            'duu':[F(0),F(0),F(3,2)],
            'duv':[F(0),F(0),F(5,2)],
            'dvv':[F(0),F(0),F(1)]}, 'analytic coupled patch')
    lines += ['    @:true', '::tests()']
    return '\n'.join(lines)+'\n', comparisons, samples


def main():
    # Linux PR_SET_CHILD_SUBREAPER: reap our orphaned compiler/helper children.
    if ctypes.CDLL(None, use_errno=True).prctl(36, 1, 0, 0, 0) != 0:
        raise OSError(ctypes.get_errno(), 'cannot enable owned-helper reaping')

    def interrupted(signum, frame):
        raise InterruptedError(f'executor interrupted by signal {signum}')

    signal.signal(signal.SIGTERM, interrupted)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compiler', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--only', choices=['compatibility','oracles','all'], default='all')
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    compiler = args.compiler.resolve()
    report = {'passed':False, 'compiler':str(compiler), 'compiler_sha256':sha(compiler),
              'scope':'Native CPU source development checks; not release/GPU/UI qualification',
              'cases':[], 'sources':{}, 'test_runner_sha256':sha(Path(__file__)),
              'qualification':{'native_cpu':False,'wasm':False,'gpu':False,'renderer':False},
              'planned_native_programs':16 if args.only=='all' else 1,
              'nonfinite_runtime_injection':'not tested; no additional runtime injection program in the fixed 16-program batch',
              'oracle_error_contract':'observed float agreement to independent exact rational targets; no continuum enclosure'}
    try:
        project = out/'project'
        project.mkdir()
        for name in ['Morphing.vkf','Interpolation.vkf']:
            shutil.copy2(ROOT/name, project/name)
        for name in ['morphing','interpolation']:
            if (ROOT/name).is_dir():
                shutil.copytree(ROOT/name, project/name)
        report['sources'] = {str(p.relative_to(project)):sha(p) for p in project.rglob('*.vkf')}

        def run(name, text, expected_success=True):
            source = project/(name+'.vkf')
            source.write_text(text)
            binary = out/name
            start = time.monotonic()
            case = {'name':name,'expected_success':expected_success,'stage':'build',
                    'source_sha256':sha(source)}
            report['cases'].append(case)
            (out/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
            try:
                build = owned_process([str(compiler),'-b',str(source),'-o',str(binary)],
                                      out/(name+'-build.log'),120)
                case['build_returncode'] = build.returncode
                if build.returncode:
                    raise RuntimeError(f'{name} compilation failed; see {name}-build.log')
                case['stage'] = 'run'
                result = owned_process([str(binary)],out/(name+'-run.log'),60)
                case['returncode'] = result.returncode
                if (result.returncode==0) != expected_success:
                    raise RuntimeError(f'{name} unexpected return code {result.returncode}')
                case['stage'] = 'complete'
                return result.stdout
            except BaseException as exc:
                case['error'] = repr(exc)
                raise
            finally:
                case['seconds'] = time.monotonic()-start
                case['owned_process_group_joined'] = True
                (out/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
        if args.only!='oracles':
            run('compatibility', (ROOT/'tests/interpolation/compatibility.vkf').read_text())
        if args.only=='all':
            run('existing-core-via-interpolation',
                (ROOT/'tests/morphing/core.vkf').read_text().replace('m:.Morphing','m:.Interpolation',1))
        if args.only in ('all','oracles'):
            source, count, samples = fixtures()
            report.update(scalar_oracle_comparisons=count,oracle_samples=samples)
            run('polynomial-patch-oracles',source)
        if args.only=='all':
            example = run('basics',(ROOT/'examples/interpolation-basics.vkf').read_text())
            if [float(x) for x in example.splitlines() if x.strip()] != [1,3,.5,9]:
                raise RuntimeError('example output differs from documented four lines')
            run('surface',(ROOT/'tests/interpolation/surface.vkf').read_text())
            for name,expr in {
                'bezier-width':'i.prepare_bezier([0,1],0)',
                'bezier-layout':'i.prepare_bezier([0,1,2],2)',
                'bezier-empty':'i.prepare_bezier([],1)',
                'bezier-magnitude':'i.prepare_bezier([10^101],1)',
                'bezier-query':'i.sample_polynomial(i.prepare_bezier([0,1],1),1.1)',
                'hermite-layout':'i.prepare_hermite([0],[1,2],[1],[1])',
                'patch-layout':'i.prepare_patch([0,1,2],1,2,2)',
                'patch-count':'i.prepare_patch([0],1,0,1)',
                'patch-query':'i.sample_patch(i.prepare_patch([0,1,2,3],1,2,2),0.5,-0.1)',
                'blend-query':'i.blend([0],[1],-0.1)',
                'blend-width':'i.blend([0],[1,2],0.5)',
            }.items():
                run(name,'i:.Interpolation\n::'+expr+'\n',False)
        report['passed']=True
        report['qualification']['native_cpu']=True
    except Exception as exc:
        report['error']=str(exc)
        raise
    finally:
        (out/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
