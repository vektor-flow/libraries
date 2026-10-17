// ABI/reference driver only. Parsing, project resolution and expansion are VKF.
import assert from 'node:assert/strict';
import {readFile, writeFile} from 'node:fs/promises';
import {pathToFileURL} from 'node:url';
const [runtime, manifestPath, wasmPath, casesPath, referencePath, output] = process.argv.slice(2);
const report = {cases: [], completeRendererPort: false, fullRenderPerformanceMeasured: false};
try {
  const {createSymbolicKernel} = await import(pathToFileURL(runtime));
  const manifest = JSON.parse(await readFile(manifestPath));
  const {instance} = await WebAssembly.instantiate(await readFile(wasmPath));
  const kernel = createSymbolicKernel({instance, manifest});
  const cases = JSON.parse(await readFile(casesPath));
  const references = JSON.parse(await readFile(referencePath));
  for (let index = 0; index < cases.length; index++) {
    const item = cases[index], expected = references[index], start = performance.now();
    const actual = kernel.invokeValue('preprocess', [item.source, JSON.stringify(item.files ?? {}),
      item.jobName ?? 'document', item.entry ?? '']);
    assert.equal(actual.source, expected.source, `case ${index} expanded source`);
    assert.equal(actual.valid, expected.valid, `case ${index} front-end status`);
    assert.equal(actual.expansions, expected.expansions, `case ${index} expansion count`);
    assert.equal(actual.diagnostics, expected.diagnostics.map(value => value+'\n').join(''));
    const metadata = {};
    for (const {name, ...definition} of JSON.parse(actual.declarations)) metadata[name] = definition;
    assert.deepEqual(metadata, expected.theorems, `case ${index} theorem metadata`);
    const inputBytes = new TextEncoder().encode(actual.input_names), inputs = [];
    for (let i = 0; i < actual.input_count; i++) {
      inputs.push(new TextDecoder().decode(inputBytes.subarray(actual.input_starts[i], actual.input_stops[i])));
    }
    assert.deepEqual(inputs, expected.inputs, `case ${index} ordered project inputs`);
    report.cases.push({index, sourceBytes: new TextEncoder().encode(item.source).length,
      expansions: actual.expansions, declarations: actual.declaration_count,
      milliseconds: performance.now()-start, equal: true});
    await writeFile(output, JSON.stringify(report, null, 2)+'\n');
  }
  report.passed = true;
} catch (error) {
  report.failure = {name: error.name, message: error.message, stack: error.stack};
  throw error;
} finally {
  await writeFile(output, JSON.stringify(report, null, 2)+'\n');
}
process.stdout.write(JSON.stringify({passed: true, cases: report.cases.length})+'\n');
