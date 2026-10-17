"""Independent binary64 roundtrip references for the portable VKF JSON writer.

The native test program and WASM kernel execute the same VKF formatter. Python
and Node only supply exact finite inputs and compare decoded IEEE-754 values.
"""
import argparse
import hashlib
import json
import math
import random
import shutil
import struct
import subprocess
import sys
from pathlib import Path

if sys.version_info[:2] != (3, 14):
    raise SystemExit('Reference checks require Python 3.14')
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--compiler', type=Path, required=True)
parser.add_argument('--wasm-compiler', type=Path, required=True)
parser.add_argument('--wasm-runtime', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=False)
root = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
report = {'componentOnly': True, 'completeRendererPort': False,
          'sourceSha256': sha(root/'json_numbers.vkf'), 'checks': []}


def run(command):
    result = subprocess.run(list(map(str, command)), text=True, capture_output=True, timeout=180)
    if result.returncode:
        report['failure'] = {'command': list(map(str, command)), 'exitCode': result.returncode,
                             'stdout': result.stdout, 'stderr': result.stderr}
        raise RuntimeError(result.stderr or result.stdout)
    return result.stdout


def expression(value):
    if value == 0:
        return 'num(0)'
    mantissa, exponent = math.frexp(abs(value))
    significand = int(mantissa*2**53)
    exponent -= 53
    while significand % 2 == 0:
        significand //= 2
        exponent += 1
    if value < 0:
        significand = -significand
    return f'num({significand})*2.0^({exponent})'


try:
    values = [0.0, -0.0, 1.0, -1.0, 0.1, 0.3, 1/3, 2/3,
              math.ulp(0.0), -math.ulp(0.0), sys.float_info.min,
              math.nextafter(sys.float_info.min, 0), 1e-300, 1e300]
    values.extend(n/255 for n in range(256))
    for exponent in [-300, -100, -20, -7, -1, 0, 7, 20, 100, 299]:
        value = 10.0**exponent
        values.extend([math.nextafter(value, 0), value, math.nextafter(value, math.inf)])
    generator = random.Random(1729)
    for _ in range(128):
        value = math.ldexp(generator.uniform(1, 2), generator.randint(-1074, 995))
        if value and math.isfinite(value) and abs(value) <= 1e300:
            values.extend([value, -value])
    (args.output/'values.json').write_text(json.dumps(values))
    for name in ['json_numbers.vkf', 'tex_text.vkf', 'text_chunks.vkf']:
        shutil.copyfile(root/name, args.output/name)
        assert sha(root/name) == sha(args.output/name)
    program = ('numbers: .json_numbers\n'
               'run()->int:\n    values:['+','.join(map(expression, values))+']\n'
               '    index:0\n    index<values.length()?>\n'
               '        ::numbers.roundtrip(values.(index))\n'
               '        .index:index+1\n    @:0\nrun()\n')
    source = args.output/'number_reference.vkf'
    source.write_text(program)
    executable = args.output/'number_reference'
    diagnostics = run([args.compiler, '-b', source, '-o', executable, '--diagnostics'])
    (args.output/'native-build.json').write_text(diagnostics)
    native_output = run([executable])
    (args.output/'native-output.txt').write_text(native_output)
    lines = native_output.splitlines()
    assert len(lines) == len(values)
    for index, (value, literal) in enumerate(zip(values, lines)):
        actual = json.loads(literal)
        assert type(actual) in (int, float), (index, literal)
        assert float(actual) == value, (index, value, literal, actual)
        if value:
            assert struct.pack('>d', float(actual)) == struct.pack('>d', value)
    report['checks'].append({'backend': 'native', 'values': len(values), 'binary64Exact': True})
    kernel = args.output/'number_kernel'
    diagnostics = run([args.compiler, '-b', root/'number_kernel.vkf', '-o', kernel, '--diagnostics'])
    (args.output/'kernel-build.json').write_text(diagnostics)
    wasm = args.output/'number_kernel.wasm'
    manifest = args.output/'kernel-wasm.json'
    run([args.wasm_compiler, '--typed-ir', json.loads(diagnostics)['typed_ir_path'],
         '--wasm', wasm, '--manifest', manifest, '--entry', 'json_number', '--prune-to-entry'])
    driver = args.output/'verify-wasm.mjs'
    driver.write_text('''import {readFile,writeFile} from 'node:fs/promises';
import {pathToFileURL} from 'node:url';
import assert from 'node:assert/strict';
const [runtime,manifestPath,wasmPath,inputsPath,nativePath,output]=process.argv.slice(2);
const {createSymbolicKernel}=await import(pathToFileURL(runtime));
const manifest=JSON.parse(await readFile(manifestPath));
const {instance}=await WebAssembly.instantiate(await readFile(wasmPath));
const kernel=createSymbolicKernel({instance,manifest});
const values=JSON.parse(await readFile(inputsPath));
const native=(await readFile(nativePath,'utf8')).trim().split('\\n');
for(let i=0;i<values.length;i++){
 const literal=kernel.invokeValue('json_number',[values[i]]);
 assert.equal(JSON.parse(literal),values[i]===0?0:values[i], 'binary64 value '+i);
 assert.equal(literal,native[i], 'native/WASM spelling '+i);
}
await writeFile(output,JSON.stringify({passed:true,values:values.length,binary64Exact:true})+'\\n');
console.log(JSON.stringify({passed:true,values:values.length}));
''')
    run(['node', driver, args.wasm_runtime, manifest, wasm, args.output/'values.json',
         args.output/'native-output.txt', args.output/'wasm.json'])
    report['checks'].append({'backend': 'WASM', 'values': len(values),
                             'binary64Exact': True, 'spellingMatchesNative': True})
    report['passed'] = True
finally:
    (args.output/'verification.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps({'passed': True, 'valuesPerBackend': len(values)}))
