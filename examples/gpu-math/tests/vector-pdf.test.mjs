import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {gunzipSync, inflateSync} from 'node:zlib';
import {exportVectorPdf, verifyVectorMapping} from '../vector-pdf.mjs';
import {typesetDocument} from '../document-layout.mjs';

const mapping = readFileSync(new URL('../typing-demo/typing-data.json', import.meta.url));
const data = JSON.parse(mapping);
const vectors = JSON.parse(gunzipSync(readFileSync(new URL('../typing-demo/pdf-vectors.json.gz', import.meta.url))));
function streams(bytes) {
  const buffer = Buffer.from(bytes), result = [];
  let at = 0;
  while ((at = buffer.indexOf('stream\n', at)) >= 0) {
    const start = at + 7, end = buffer.indexOf('\nendstream', start);
    const dictionary = buffer.subarray(buffer.lastIndexOf(' obj\n', at), at).toString();
    result.push((dictionary.includes('/FlateDecode') ? inflateSync(buffer.subarray(start, end)) : buffer.subarray(start, end)).toString()); at = end + 10;
  }
  return result;
}
const page = items => ({pages: [{width: 200, height: 300, items}]});

test('vector fonts cover every current tile and match the pinned mapping', async () => {
  await verifyVectorMapping(vectors, mapping);
  assert.deepEqual(Object.keys(vectors.keys).sort(), Object.keys(data.tiles).sort());
  await assert.rejects(verifyVectorMapping(vectors, new Uint8Array([1])), /does not match/);
});

test('real native source exports without TeX, GPU, atlas or text rasterization', async () => {
  const source = String.raw`\documentclass{article}\usepackage{amsmath}\begin{document}Vector $E=mc^2$, $\frac{a}{b}$, $\sqrt{x}$.\end{document}`;
  const result = await typesetDocument(source, data);
  assert.deepEqual(result.diagnostics, []);
  const bytes = await exportVectorPdf(result, vectors);
  const text = Buffer.from(bytes).toString();
  assert.ok(text.startsWith('%PDF-1.7'));
  assert.ok(!text.includes('/Subtype /Image'));
  assert.ok(streams(bytes).some(s => s.includes(' c\n')), 'Cubic curves survive export');
  const startxref = Number(/startxref\n(\d+)/.exec(text)[1]);
  assert.equal(Buffer.from(bytes).subarray(startxref, startxref + 4).toString(), 'xref');
});

test('layout placements remain full precision, independent of camera and PDF raster profiles', async () => {
  const bytes = await exportVectorPdf(page([{kind: 'glyph', key: 'text/x', x: 20.123456789, y: 50.987654321, pdfX: 999, pdfY: 999, sx: 2, sy: 3, crop: [-3, 1], cropX: [1, 4]}]), vectors);
  const content = streams(bytes).at(-1);
  assert.ok(content.includes('2 0 0 3 20.123456789 50.987654321 cm'));
  assert.ok(content.includes(' re W n'));
  assert.ok(!content.includes('999'));
});

test('identical outlines are reused across pages; rules and opacity remain vector', async () => {
  const items = [{kind: 'glyph', key: 'text/x', x: 10, y: 20}, {kind: 'glyph', key: 'text/x', x: 30, y: 20}, {kind: 'rule', x: 10, y: 30, width: 50, height: .2, color: [1, 0, 0, .4]}];
  const bytes = await exportVectorPdf({pages: [page(items).pages[0], page(items).pages[0]]}, vectors);
  const raw = Buffer.from(bytes).toString();
  assert.equal((raw.match(/\/Subtype \/Form/g) ?? []).length, 1);
  assert.ok(raw.includes('/Count 2'));
  assert.ok(raw.includes('/ca 0.4 /CA 0.4'));
  assert.ok(streams(bytes).some(s => s.includes('10 30 50 0.2 re f')));
});

test('only explicit source illustrations become images, preserving orientation and alpha', async () => {
  const images = {'figure.png': {width: 1, height: 2, rgba: new Uint8Array([255, 0, 0, 255, 0, 0, 255, 128])}};
  const bytes = await exportVectorPdf(page([{kind: 'image', asset: 'figure.png', x: 10, y: 20, width: 30, height: 40}]), vectors, {images});
  assert.ok(Buffer.from(bytes).toString().includes('/SMask'));
  assert.ok(streams(bytes).at(-1).includes('30 0 0 -40 10 60 cm'));
});

test('missing curves, invalid coordinates and incomplete items never raster-fallback silently', async () => {
  await assert.rejects(exportVectorPdf(page([{kind: 'glyph', key: 'missing', x: 0, y: 0}]), vectors), /Missing PDF vector/);
  await assert.rejects(exportVectorPdf(page([{kind: 'glyph', key: 'text/x', x: NaN, y: 0}]), vectors), /Invalid PDF coordinate/);
  await assert.rejects(exportVectorPdf(page([{kind: 'placeholder', x: 0, y: 0}]), vectors), /Unsupported PDF layout item/);
  await assert.rejects(exportVectorPdf(page([{kind: 'image', asset: 'missing.png', x: 0, y: 0}]), vectors), /Missing PDF illustration/);
});

test('native lines, cubic curves and filled/stroked shapes remain vector paths', async () => {
  const items = [
    {kind: 'segment', x: 10, y: 20, delta: [20, 0], lineWidth: .5, dash: 'dashed'},
    {kind: 'bezier', x: 10, y: 30, delta: [20, 0], controls: [{x: 5, y: -10}, {x: 15, y: -10}], lineWidth: .5},
    {kind: 'circle', x: 10, y: 50, width: 20, height: 20, fill: true, fillColor: [1, 0, 0], strokeColor: [0, 0, 1], lineWidth: 1},
    {kind: 'vectorrect', x: 10, y: 80, width: 20, height: 10, lineWidth: 1, dash: 'dotted'},
  ];
  const bytes = await exportVectorPdf(page(items), vectors);
  const content = streams(bytes).at(-1);
  assert.ok(!Buffer.from(bytes).toString().includes('/Subtype /Image'));
  assert.ok(content.includes('5 -10 15 -10 20 0 c'));
  assert.ok(content.includes('1 0 0 rg'));
  assert.ok(content.includes('0 0 1 RG'));
  assert.ok(content.includes('] 0 d 1 J'));
});
