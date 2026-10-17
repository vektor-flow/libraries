import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {gunzipSync, inflateSync} from 'node:zlib';
import {exportVectorPdf, verifyVectorMapping} from '../vector-pdf.mjs';
import {typesetDocument} from '../document-layout.mjs';
import {exportPdfProject} from '../document-pdf-node.mjs';
const directory = new URL('../typing-demo/font-profiles/amsart-12/', import.meta.url);
const bytes = readFileSync(new URL('typing-data.json', directory));
const mapping = JSON.parse(bytes);
const vectors = JSON.parse(gunzipSync(readFileSync(new URL('pdf-vectors.json.gz', directory))));

test('PDF-only metrics preserve all optical layout metrics and footnote link planes', async () => {
  const compactBytes = gunzipSync(readFileSync(new URL('pdf-metrics.json.gz', directory)));
  const compact = JSON.parse(compactBytes);
  await verifyVectorMapping({...vectors, mappingSha256: vectors.pdfMappingSha256}, compactBytes);
  assert.deepEqual(compact.maps, mapping.maps);
  assert.deepEqual(compact.documentFonts, mapping.documentFonts);
  assert.ok(!compact.coverage96 && !compact.bitmapGlyphRects);
  for (const [key, tile] of Object.entries(mapping.tiles)) assert.deepEqual(compact.tiles[key].plane, tile.plane);
  const source = String.raw`\documentclass[12pt]{amsart}\usepackage{amsmath,bbm,tikz,hyperref}\begin{document}Office affinity\footnote{A linked footnote.} $x_i^2+\mathbbm{1}+\dots$. \begin{tikzpicture}\draw (0,0) -- (1,1);\end{tikzpicture}\end{document}`;
  const expected = await typesetDocument(source, mapping), actual = await typesetDocument(source, compact);
  assert.deepEqual(actual.pages, expected.pages);
  assert.deepEqual(actual.destinations, expected.destinations);
  const result = await exportPdfProject(source);
  assert.deepEqual(result.layout.pages, expected.pages);
  assert.ok(Buffer.from(result.bytes).includes(Buffer.from('/Annots')));
});

test('optical PDF resources cover every prepared glyph and bind to the exact metrics', async () => {
  await verifyVectorMapping(vectors, bytes);
  assert.deepEqual(Object.keys(vectors.keys).sort(), Object.keys(mapping.tiles).sort());
  for (const [key, rectangles] of Object.entries(mapping.bitmapGlyphRects)) {
    const path = vectors.paths[vectors.keys[key]];
    const operators = path.operators.split('\n').filter(Boolean);
    assert.equal(operators.length, rectangles.length);
    for (const [index, line] of operators.entries()) {
      const parts = line.split(' '); assert.equal(parts.pop(), 're');
      for (const [axis, value] of parts.map(Number).entries())
        assert.ok(Math.abs(value-rectangles[index][axis]) <= 5.1e-11);
    }
  }
});

test('a declared optical class exports BBM and source TikZ without raster page objects', async () => {
  const source = String.raw`\documentclass[12pt]{amsart}\usepackage{amsmath,bbm,tikz}\begin{document}Optical $\mathbbm{1}+x^2$. \begin{tikzpicture}\draw (0,0) -- (1,1);\end{tikzpicture}\end{document}`;
  const layout = await typesetDocument(source, mapping);
  assert.deepEqual(layout.diagnostics, []);
  assert.ok(layout.pages.some(p => p.items.some(i => i.kind === 'segment')));
  const pdf = Buffer.from(await exportVectorPdf(layout, vectors));
  assert.ok(pdf.includes(Buffer.from('/Subtype /Form')));
  assert.ok(!pdf.includes(Buffer.from('/Subtype /Image')));
  const text = pdf.toString('latin1');
  let curves = false;
  for (const match of text.matchAll(/<< ([\s\S]*?) >>\nstream\n/g)) {
    const dictionary = match[1], length = Number(/\/Length (\d+)/.exec(dictionary)[1]);
    const start = match.index + match[0].length;
    const raw = pdf.subarray(start, start+length);
    if (/ c(?:\n|$)/.test((dictionary.includes('/FlateDecode') ? inflateSync(raw) : raw).toString())) curves = true;
  }
  assert.ok(curves, 'Native Type1 cubic curves remain in the PDF');
});
