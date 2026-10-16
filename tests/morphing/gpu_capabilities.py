"""Qualify Morphing's compiler GPU route offline; never execute a GPU program.

This is a capability gate, not a performance benchmark or browser qualification.
Failures stay failures: successful CPU/WASM builds cannot satisfy this gate.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess


PROBES = {
    'circle_control': ('math:.math\n',
                       '0.6-math.sqrt((x+q)*(x+q)+y*y)'),
    'bilinear_control': ('', '(1-x)*(1-y)*q+x*(1-y)*0.5+(1-x)*y*0.75+x*y'),
    'segment_value': ('s:.morphing.segment\n', 's.value(x,y,0.2,-0.4,2,q)'),
    'segment_first': ('s:.morphing.segment\n', 's.first(x,y,0.2,-0.4,2,q)'),
    'segment_second': ('s:.morphing.segment\n', 's.second(x,y,q)'),
    'biological_union': ('b:.morphing.biological\n', 'b.union(x,y,q)'),
    'state_sample': ('m:.Morphing\n', '\n'
                     '    plan:m.prepare([0,1],[x,y],1,0,false,false)\n'
                     '    @:m.sample(plan,q).value.(0)'),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--library', type=Path, required=True)
    parser.add_argument('--compiler', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    source = out / 'source'
    source.mkdir()
    shutil.copy2(args.library / 'Morphing.vkf', source / 'Morphing.vkf')
    shutil.copytree(args.library / 'morphing', source / 'morphing')
    compiler = args.compiler.resolve()
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    report = {
        'hardwareExecuted': False, 'browserQualified': False,
        'performanceMeasured': False, 'passed': False,
        'compiler': str(compiler), 'compilerSha256': sha(compiler),
        'librarySources': {str(p.relative_to(source)): sha(p)
                           for p in sorted(source.rglob('*.vkf'))},
        'probes': {},
    }

    def run(command, name):
        command = [str(part) for part in command]
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=180)
            code, stdout, stderr = result.returncode, result.stdout, result.stderr
        except (OSError, subprocess.TimeoutExpired) as error:
            code, stdout, stderr = None, '', str(error)
        (out / (name + '.stdout')).write_text(stdout)
        (out / (name + '.stderr')).write_text(stderr)
        return {'command': command, 'exit': code, 'stderr': stderr}

    try:
        for name, (imports, expression) in PROBES.items():
            path = source / (name + '.vkf')
            path.write_text(imports + 'point(x:num,y:num,q:num)->num:' + expression + '\n'
                            'run(q:num):\n'
                            '    X_i:[-1,0,1]_i\n'
                            '    Y_j:[-1,0,1]_j\n'
                            '    ::point(X,Y,q)\n'
                            '    0\n'
                            'run(0.25)\n')
            shader = out / (name + '.comp')
            probe = {'sourceSha256': sha(path), 'passed': False}
            report['probes'][name] = probe
            probe['compile'] = run([
                compiler, '-b', path, '-o', out / (name + '.native'),
                '--diagnostics', '--optimizer-policy', 'scalar',
                '--emit-vulkan-field', shader, '--vulkan-field-entry', 'run',
                '--vulkan-field-runtime-inputs',
            ], name + '.compile')
            if probe['compile']['exit'] != 0:
                continue
            # A shader specialized to the example q is not an interpolation kernel.
            manifest = json.loads(Path(str(shader) + '.json').read_text())
            abi = manifest.get('runtime_input_abi', {})
            probe['runtimeCoordinate'] = (
                manifest.get('input_binding_mode') == 'runtime-f64-snapshot'
                and abi.get('storage') == 'readonly-std430-f64'
                and any(p.get('name') == 'q' and p.get('component_count') == 1
                        for p in abi.get('parameters', []))
            )
            if not probe['runtimeCoordinate']:
                continue
            binary = out / (name + '.spv')
            probe['spirv'] = run(['glslangValidator', '-V', '-S', 'comp', shader,
                                  '-o', binary], name + '.spirv')
            if probe['spirv']['exit'] != 0:
                continue
            probe['validate'] = run(['spirv-val', binary], name + '.validate')
            probe['passed'] = probe['validate']['exit'] == 0
            if probe['passed']:
                probe['shaderSha256'] = sha(shader)
                probe['spirvSha256'] = sha(binary)
        report['passed'] = all(p['passed'] for p in report['probes'].values())
    finally:
        (out / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({key: report[key] for key in
                      ['passed', 'hardwareExecuted', 'browserQualified', 'performanceMeasured']}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
