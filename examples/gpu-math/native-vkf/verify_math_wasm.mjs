// Independent ABI/reference driver. All math parsing is compiled VKF.
import assert from 'node:assert/strict';
import {readFile, writeFile} from 'node:fs/promises';
import {pathToFileURL} from 'node:url';
const [runtime, manifestPath, wasmPath, catalogPath, casesPath, referencePath, output, native = 'true'] = process.argv.slice(2);
const report = {componentOnly: true, fullParserPort: false, completeRendererPort: false,
  timingScope: 'Same-kernel ABI call, JSON readback and comparison; includes font-argument transfer. Not file-cache cold or full PDF rendering.',
  cases: []};
try {
  const {createSymbolicKernel} = await import(pathToFileURL(runtime));
  const manifest = JSON.parse(await readFile(manifestPath));
  const {instance} = await WebAssembly.instantiate(await readFile(wasmPath));
  const kernel = createSymbolicKernel({instance, manifest});
  const catalog = await readFile(catalogPath, 'utf8');
  const cases = JSON.parse(await readFile(casesPath));
  const references = JSON.parse(await readFile(referencePath));
  for (let index = 0; index < cases.length; index++) {
    const started = performance.now();
    const actual = JSON.parse(kernel.invokeValue('math_ast', [cases[index], catalog, native === 'true']));
    assert.deepEqual(actual, references[index], 'Math AST case '+index);
    report.cases.push({index, equal: true, milliseconds: performance.now()-started});
    await writeFile(output, JSON.stringify(report, null, 2)+'\n');
  }
  report.passed = true;
} catch (error) {
  report.failure = {name: error.name, message: error.message, stack: error.stack};
  throw error;
} finally {
  await writeFile(output, JSON.stringify(report, null, 2)+'\n');
}
console.log(JSON.stringify({passed: true, cases: report.cases.length}));
