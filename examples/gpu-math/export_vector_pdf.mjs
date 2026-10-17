// Command-line export for standalone source or a previously computed layout.
// No TeX executable, browser, GPU or network is used.
import {readFile, writeFile} from 'node:fs/promises';
import {gunzipSync} from 'node:zlib';
import {exportVectorPdf, verifyVectorMapping} from './vector-pdf.mjs';
import {typesetDocument} from './document-layout.mjs';
import {dirname, resolve, relative, basename} from 'node:path';
import {pathToFileURL} from 'node:url';
import {exportPdfProject, readPdfProject} from './document-pdf-node.mjs';
const [input, output, ...options] = process.argv.slice(2);
const settings = {};
for (let i = 0; i < options.length; i += 2) {
  if (!['--project', '--fonts'].includes(options[i]) || !options[i+1] || settings[options[i]]) throw Error('Invalid PDF export options');
  settings[options[i]] = options[i+1];
}
if (!input || !output) throw Error('Usage: node export_vector_pdf.mjs input.tex|layout.json output.pdf [--project directory] [--fonts directory]');
const fontRoot = settings['--fonts'] ? pathToFileURL(resolve(settings['--fonts'])+'/') : new URL('./typing-demo/', import.meta.url);
if (!input.endsWith('.json')) {
  const directory = resolve(settings['--project'] ?? dirname(input)), path = resolve(input), entry = relative(directory, path).split('\\').join('/');
  if (entry.startsWith('../') || entry === '..') throw Error('Input must be inside project directory');
  const [text, files] = await Promise.all([readFile(path, 'utf8'), readPdfProject(directory)]);
  const result = await exportPdfProject(text, {files, fontRoot, buildContext: {entry, jobName: basename(input, '.tex')}});
  await writeFile(output, result.bytes);
  console.log(JSON.stringify({pages: result.pages, bytes: result.bytes.length, diagnostics: result.diagnostics, timings: result.timings}));
} else {
const mapping = await readFile(new URL('typing-data.json', fontRoot));
const vectors = JSON.parse(gunzipSync(await readFile(new URL('pdf-vectors.json.gz', fontRoot))));
await verifyVectorMapping(vectors, mapping);
const text = await readFile(input, 'utf8');
const layout = input.endsWith('.json') ? JSON.parse(text) : await typesetDocument(text, JSON.parse(mapping));
const bytes = await exportVectorPdf(layout, vectors);
await writeFile(output, bytes);
console.log(JSON.stringify({pages: layout.pages.length, bytes: bytes.length, diagnostics: layout.diagnostics ?? []}));
}
