// Standalone host adapter for the same independent layout and PDF backend.
// Reads project data and prepared fonts; never launches TeX, Chromium or a GPU.
import {readFile, readdir} from 'node:fs/promises';
import {resolve, relative} from 'node:path';
import {gunzipSync, deflate} from 'node:zlib';
import {requestedFontProfile, validateFontProfile} from './font-profile.mjs';
import {typesetDocument} from './document-layout.mjs';
import {exportVectorPdf, verifyVectorMapping} from './vector-pdf.mjs';
const resources = new Map();
const compressionQueue = []; let activeCompression = 0;
function compressStream(bytes) {
  const output = new Promise((resolve, reject) => compressionQueue.push({bytes, resolve, reject}));
  drainCompression(); return output;
}
function drainCompression() {
  while (activeCompression < 4 && compressionQueue.length) {
    const job = compressionQueue.shift(); activeCompression++;
    deflate(job.bytes, (error, result) => {
      if (error) job.reject(error); else job.resolve(result);
      activeCompression--; drainCompression();
    });
  }
}

export async function readPdfProject(directory) {
  const root = resolve(directory), files = {};
  let total = 0;
  async function visit(folder) {
    for (const entry of await readdir(folder, {withFileTypes: true})) {
      if (entry.name.startsWith('.') || entry.name === 'node_modules') continue;
      const path = resolve(folder, entry.name);
      if (entry.isDirectory()) await visit(path);
      else if (entry.isFile() && /\.(tex|bib|bbl|txt|m)$/i.test(entry.name)) {
        const bytes = await readFile(path); total += bytes.length;
        if (total > 10000000) throw Error('PDF project text exceeds 10MB');
        files[relative(root, path).split('\\').join('/')] = bytes.toString('utf8');
      }
    }
  }
  await visit(root);
  return files;
}

function fontResources(name, fontRoot) {
  const folder = new URL(name ? 'font-profiles/'+encodeURIComponent(name)+'/' : './', fontRoot);
  const key = folder.href;
  if (!resources.has(key)) {
    const mapping = readFile(new URL('pdf-metrics.json.gz', folder)).then(compressed => {
      const bytes = gunzipSync(compressed);
      const data = JSON.parse(bytes);
      if (name) validateFontProfile(name, data);
      return {bytes, mapping: data};
    });
    const vectors = Promise.all([
      readFile(new URL('pdf-vector-index.json.gz', folder)),
      readFile(new URL('pdf-paths.bin', folder)),
    ]).then(([bytes, operators]) => {
      const index = JSON.parse(gunzipSync(bytes));
      if (index.schema !== 'vkf.pdf-vector-index/1') throw Error('Unsupported indexed PDF font bundle');
      const decoded = Object.create(null);
      const paths = new Proxy(index.paths, {get(table, key) {
        if (typeof key !== 'string' || !Object.hasOwn(table, key)) return undefined;
        if (!decoded[key]) {
          const {bounds, offset, length} = table[key];
          if (!Number.isSafeInteger(offset) || !Number.isSafeInteger(length) || offset < 0 || length < 0 || offset+length > operators.length)
            throw Error('Invalid indexed PDF glyph range');
          decoded[key] = {bounds, operators: operators.toString('utf8', offset, offset+length)};
        }
        return decoded[key];
      }});
      return {...index, schema: 'vkf.pdf-vectors/1', paths};
    });
    const ready = Promise.all([mapping, vectors]).then(async ([data, vectors]) => {
      await verifyVectorMapping({...vectors, mappingSha256: vectors.pdfMappingSha256}, data.bytes); return vectors;
    });
    // Both operations start together. Observe errors even if layout fails first.
    ready.catch(() => resources.delete(key));
    resources.set(key, {mapping, vectors: ready});
  }
  return resources.get(key);
}

export async function exportPdfProject(source, {files = {}, assets = {}, images = {}, buildContext = {},
  fontRoot = new URL('./typing-demo/', import.meta.url), profile = false} = {}) {
  const start = performance.now(), timings = {}; let checkpoint = start;
  const stage = key => {const now = performance.now(); timings[key] = now-checkpoint; checkpoint = now;};
  const name = await requestedFontProfile(source, {files, buildContext}); stage('inputPreparationMs');
  const fonts = fontResources(name, fontRoot);
  const {mapping} = await fonts.mapping; stage('fontMappingMs');
  const layout = await typesetDocument(source, mapping, {files, assets, buildContext}); stage('layoutMs');
  const vectors = await fonts.vectors; stage('remainingFontVectorsMs');
  if (!layout.complete || layout.diagnostics.length) throw Error('Incomplete PDF layout: '+layout.diagnostics.join('; '));
  const pdfMetrics = profile ? {} : null;
  const bytes = await exportVectorPdf(layout, vectors, {images, metrics: pdfMetrics, compressStream}); stage('pdfCoreMs');
  timings.totalMs = performance.now()-start;
  return {bytes, layout, pages: layout.pages.length, diagnostics: layout.diagnostics, timings, pdfMetrics};
}
