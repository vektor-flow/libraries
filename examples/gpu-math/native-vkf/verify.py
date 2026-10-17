"""Python 3.14 build/reference driver; all renderer assertions live in VKF."""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

if sys.version_info[:2] != (3, 14):
    raise SystemExit('Reference checks require Python 3.14')

root = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--compiler', type=Path, required=True)
parser.add_argument('--wasm-compiler', type=Path)
parser.add_argument('--wasm-runtime', type=Path)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--suite', action='append', help='Run only this VKF suite stem (repeatable)')
parser.add_argument('--build-timeout', type=int, default=120, help='Native compilation timeout in seconds')
args = parser.parse_args()
sources = sorted(root.glob('*_tests.vkf'))
if args.suite:
    unknown = set(args.suite)-{source.stem for source in sources}
    if unknown:
        parser.error('Unknown suites: '+', '.join(sorted(unknown)))
    sources = [source for source in sources if source.stem in args.suite]
args.output.mkdir(parents=True, exist_ok=False)
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
report = {'python': sys.version, 'compiler': str(args.compiler),
          'compilerSha256': sha(args.compiler), 'suites': [],
          'sources': {p.name: sha(p) for p in root.glob('*.vkf')},
          'completeRendererPort': False, 'fullRenderPerformanceMeasured': False}
report.update(selectedSuites=[source.stem for source in sources], fullSuite=not args.suite)
if args.wasm_compiler:
    if not args.wasm_runtime:
        parser.error('--wasm-runtime is required with --wasm-compiler')
    report.update(wasmCompilerSha256=sha(args.wasm_compiler),
                  wasmRuntimeSha256=sha(args.wasm_runtime))
    wasm_driver = args.output/'run-wasm.mjs'
    wasm_driver.write_text('''import {readFile} from 'node:fs/promises';
import {pathToFileURL} from 'node:url';
const {createSymbolicKernel}=await import(pathToFileURL(process.argv[2]));
const manifest=JSON.parse(await readFile(process.argv[3]));
const {instance}=await WebAssembly.instantiate(await readFile(process.argv[4]));
const kernel=createSymbolicKernel({instance,manifest});
for(let i=0;i<3;i++)if(kernel.invokeValue('renderer_tests')!==true)throw Error('VKF assertions failed');
console.log(JSON.stringify({passed:true,invocations:3}));
''')

def checked(command, timeout):
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        report['failure'] = {'command': command, 'timeoutSeconds': timeout}
        raise
    if result.returncode:
        report['failure'] = {'command': command, 'exitCode': result.returncode,
                             'stdout': result.stdout, 'stderr': result.stderr}
        raise RuntimeError(result.stderr or result.stdout or 'Verification failed')
    return result


try:
    for source in sources:
        output = args.output/source.stem
        command = [str(args.compiler), '-b', str(source), '-o', str(output), '--diagnostics']
        compiled = checked(command, args.build_timeout)
        diagnostics = json.loads(compiled.stdout)
        (args.output/(source.stem+'-build.json')).write_text(compiled.stdout)
        run = checked([str(output)], 60)
        suite = {'name': source.stem, 'native': True, 'nativeSha256': sha(output),
                 'buildCommand': command, 'stdout': run.stdout, 'stderr': run.stderr}
        report['suites'].append(suite)
        if args.wasm_compiler:
            wasm = args.output/(source.stem+'.wasm')
            manifest = args.output/(source.stem+'-wasm.json')
            command = [str(args.wasm_compiler), '--typed-ir', diagnostics['typed_ir_path'],
                       '--wasm', str(wasm), '--manifest', str(manifest),
                       '--entry', 'renderer_tests', '--prune-to-entry']
            checked(command, 120)
            run = checked(['node', str(wasm_driver), str(args.wasm_runtime),
                           str(manifest), str(wasm)], 120)
            suite.update(wasm=True, wasmSha256=sha(wasm), wasmBuildCommand=command,
                         wasmChecks=json.loads(run.stdout))
    report['passed'] = True
finally:
    (args.output/'verification.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps({'passed': True, 'suites': len(report['suites']), 'python': sys.version.split()[0]}))
