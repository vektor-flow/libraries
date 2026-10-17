// Independent build adapter for a published canonical compiler package.
// This runs the real compiler in WASM; renderer execution uses its emitted core.
import {readFile, writeFile, mkdir} from 'node:fs/promises';
import {dirname, resolve, join} from 'node:path';
import {pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';

const digest = bytes => createHash('sha256').update(bytes).digest('hex');
export async function compileBrowserKernel({packageRoot, source, output, entry, entryCall}) {
  const files = new Map(), directory = dirname(resolve(source));
  async function collect(filename) {
    if (files.has(filename)) return;
    let code;
    try { code = await readFile(join(directory, filename), 'utf8'); }
    catch (error) {
      if (error.code === 'ENOENT') return; // Package stdlib resolves in the compiler.
      throw error;
    }
    files.set(filename, code);
    for (const match of code.matchAll(/^\w+:\.(\w+)\s*$/gm)) await collect(match[1] + '.vkf');
  }
  const filename = resolve(source).slice(directory.length + 1);
  await collect(filename);
  const base = resolve(packageRoot), messages = [];
  const modulePath = join(base, 'playground/canonical/compiler.mjs');
  const wasmPath = join(base, 'playground/canonical/compiler.wasm');
  const dataPath = join(base, 'playground/canonical/compiler.data');
  const [{default: factory}, wasmBinary, data] = await Promise.all([
    import(pathToFileURL(modulePath)), readFile(wasmPath), readFile(dataPath),
  ]);
  const compiler = await factory({wasmBinary,
    getPreloadedPackage: () => data.buffer.slice(data.byteOffset, data.byteOffset + data.byteLength),
    print: message => messages.push(message), printErr: message => messages.push(message)});
  compiler.FS.mkdir('/renderer');
  for (const [name, code] of files) compiler.FS.writeFile('/renderer/' + name, code);
  // Browser compilation retains the main call graph. Keep the requested public
  // entry reachable explicitly; compilation does not execute this call.
  const program = files.get(filename) + '\n' + entryCall + '\n';
  const status = compiler.ccall('vkf_browser_compile', 'number', ['string', 'number', 'string'],
    [program, new TextEncoder().encode(program).length, '/renderer/' + filename]);
  if (status !== 0) throw Error(compiler.ccall('vkf_browser_error', 'string', [], []));
  const manifestText = compiler.ccall('vkf_browser_manifest', 'string', [], []);
  const manifest = JSON.parse(manifestText);
  if (!manifest.functions?.[entry]) throw Error('Compiled kernel omitted entry: ' + entry);
  const pointer = compiler.ccall('vkf_browser_wasm', 'number', [], []);
  const length = compiler.ccall('vkf_browser_wasm_size', 'number', [], []);
  const wasm = compiler.HEAPU8.slice(pointer, pointer + length);
  await mkdir(output, {recursive: true});
  await writeFile(join(output, 'kernel.wasm'), wasm);
  await writeFile(join(output, 'manifest.json'), manifestText);
  const report = {entry, entryCall, wasmSha256: digest(wasm),
    packageHashes: {[modulePath]: digest(await readFile(modulePath)),
      [wasmPath]: digest(wasmBinary), [dataPath]: digest(data)},
    sourceHashes: Object.fromEntries([...files].map(([name, code]) => [name, digest(code)])),
    programSha256: digest(program), messages};
  await writeFile(join(output, 'build.json'), JSON.stringify(report, null, 2) + '\n');
  return {manifest, wasm, report};
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  const options = Object.fromEntries(process.argv.slice(2).reduce((pairs, value, index, args) => {
    if (index % 2 === 0) pairs.push([value.replace(/^--/, ''), args[index + 1]]);
    return pairs;
  }, []));
  for (const key of ['package', 'source', 'output', 'entry', 'entry-call']) {
    if (!options[key]) throw Error('Missing --' + key);
  }
  const result = await compileBrowserKernel({packageRoot: options.package, source: options.source,
    output: options.output, entry: options.entry, entryCall: options['entry-call']});
  console.log(JSON.stringify({entry: options.entry, wasmSha256: result.report.wasmSha256}));
}
