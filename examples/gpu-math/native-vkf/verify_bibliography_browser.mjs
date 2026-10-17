// Compare actual independent JS fixture outputs to a freshly emitted WASM core.
import {readFile, writeFile, mkdir} from 'node:fs/promises';
import {join, resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {compileBrowserKernel} from './compile_browser_kernel.mjs';

const [packageRoot, kernelSource, referenceDirectory, output] = process.argv.slice(2);
if (!output) throw Error('Arguments: packageRoot kernelSource nativeReferenceDirectory output');
await mkdir(output, {recursive: false});
const {createSymbolicKernel} = await import(pathToFileURL(join(resolve(packageRoot), 'vf-ui/vf-symbolic-kernel-runtime.mjs')));
const build = await compileBrowserKernel({packageRoot, source: kernelSource, output, entry: 'packet',
  entryCall: '::packet("{\\\"source\\\":\\\"\\\"}")'});
const caseBytes = await readFile(join(referenceDirectory, 'cases.json'));
const referenceBytes = await readFile(join(referenceDirectory, 'reference.json'));
const cases = JSON.parse(caseBytes);
const expected = JSON.parse(referenceBytes);
assert.equal(cases.length, expected.length);
const results = [];
const {instance} = await WebAssembly.instantiate(build.wasm);
const kernel = createSymbolicKernel({instance, manifest: build.manifest});
const report = {passed: false, backend: 'wasm', compiler: 'published canonical browser compiler',
  completeRendererPort: false, performanceValidated: false, cases: cases.length, verified: 0,
  caseSha256: createHash('sha256').update(caseBytes).digest('hex'),
  referenceSha256: createHash('sha256').update(referenceBytes).digest('hex')};
try {
  for (let index = 0; index < cases.length; index++) {
    const actual = JSON.parse(kernel.invokeValue('packet', [JSON.stringify(cases[index])]));
    const reference = expected[index];
    if (reference.error) {
      assert.ok(actual.error === reference.error || actual.diagnostics?.includes(reference.error), 'Expected error at ' + index);
    } else {
      delete actual.plain;
      assert.deepEqual(actual, reference, 'Reference case ' + index);
    }
    results.push(actual);
    report.verified++;
    await writeFile(join(output, 'progress.json'), JSON.stringify(report, null, 2) + '\n');
  }
  report.passed = true;
} finally {
  await writeFile(join(output, 'results.json'), JSON.stringify(results));
  await writeFile(join(output, 'verification.json'), JSON.stringify(report, null, 2) + '\n');
}
console.log(JSON.stringify(report));
