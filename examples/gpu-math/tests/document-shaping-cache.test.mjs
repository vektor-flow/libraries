import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {typesetDocumentText} from '../document-text.mjs';
import {typesetDocument} from '../document-layout.mjs';
const data = JSON.parse(readFileSync(new URL('../typing-demo/typing-data.json', import.meta.url)));

test('reused word shaping preserves ligatures, font changes, hyphens and atom counts', () => {
  const shapeCache = new Map();
  for (const source of [
    String.raw`Office affinity office affinity. \textit{Office affinity} office $x_i^2+1$.`,
    String.raw`A long computational approximation uses state-of-the-art mathematical methods.`,
    String.raw`\textbf{Office} office \texttt{office} office affinity.`,
  ]) {
    for (const width of [95, 200, 400]) {
      const options = {width, justify: true, tolerance: 9999, emergencyStretch: 10};
      const expected = typesetDocumentText(source, data, options);
      assert.deepEqual(typesetDocumentText(source, data, {...options, shapeCache}), expected);
      assert.deepEqual(typesetDocumentText(source, data, {...options, shapeCache}), expected);
    }
  }
});

test('a local source edit rebuilds layout and cannot reuse stale word placements', async () => {
  const source = String.raw`\documentclass{article}\begin{document}Office affinity office affinity. $x_i^2+1$.\end{document}`;
  const before = await typesetDocument(source, data);
  const edited = await typesetDocument(source.replace('x_i^2', 'x_i^3'), data);
  const restored = await typesetDocument(source, data);
  assert.notDeepEqual(edited.pages, before.pages);
  assert.deepEqual(restored.pages, before.pages);
  assert.deepEqual(restored.destinations, before.destinations);
});
