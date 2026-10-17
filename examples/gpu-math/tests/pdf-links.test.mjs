import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {gunzipSync} from 'node:zlib';
import {typesetDocument} from '../document-layout.mjs';
import {exportVectorPdf} from '../vector-pdf.mjs';

const data = JSON.parse(readFileSync(new URL('../typing-demo/typing-data.json', import.meta.url)));
const vectors = JSON.parse(gunzipSync(readFileSync(new URL('../typing-demo/pdf-vectors.json.gz', import.meta.url))));
const document = (body, options = '') => String.raw`\documentclass{article}\usepackage{amsmath}\usepackage[${options}]{hyperref}\begin{document}${body}\end{document}`;
const links = layout => layout.pages.flatMap(p => p.items.filter(i => i.kind === 'link'));
const glyphs = layout => layout.pages.map(p => p.items.filter(i => i.kind === 'glyph').map(({key,x,y,sx,sy}) => ({key,x,y,sx,sy})));

test('references, equations, citations and explicit destinations retain independent targets', async () => {
  const layout = await typesetDocument(document(String.raw`Section \ref{sec}, Equation \eqref{eq}, \cite{book}, \hyperlink{named}{jump}, \hyperref[sec]{custom text}.\newpage\section{Second}\label{sec}\begin{equation}x=y\label{eq}\end{equation}\hypertarget{named}{Here}\begin{thebibliography}{9}\bibitem{book}Author.\end{thebibliography}`), data);
  assert.deepEqual(layout.diagnostics, []);
  assert.deepEqual(links(layout).map(i => i.target.value), ['label:sec', 'label:eq', 'cite:book', 'named:named', 'label:sec']);
  for (const item of links(layout)) assert.equal(layout.destinations[item.target.value].page, 1);
  assert.notEqual(layout.destinations['label:sec'].y, layout.destinations['label:eq'].y);
  const bytes = await exportVectorPdf(layout, vectors);
  assert.equal((Buffer.from(bytes).toString().match(/\/Subtype \/Link/g) ?? []).length, 5);
  assert.ok(!Buffer.from(bytes).toString().includes('/Subtype /Image'));
});

test('href preserves percent/hash/escaped punctuation and nolinkurl remains unlinked', async () => {
  const layout = await typesetDocument(document(String.raw`\href{https://example.org/a?x=1\&y=2%20ok#part}{First} \url{https://example.org/two#part} \nolinkurl{https://example.org/plain}`), data);
  assert.deepEqual(layout.diagnostics, []);
  assert.deepEqual(links(layout).map(i => i.target), [{type: 'uri', value: 'https://example.org/a?x=1&y=2%20ok#part'}, {type: 'uri', value: 'https://example.org/two#part'}]);
  const plain = await typesetDocument(String.raw`\documentclass{article}\usepackage{url}\begin{document}\url{https://example.org}\end{document}`, data);
  assert.equal(links(plain).length, 0);
});

test('a wrapped href is clickable per line without changing glyph positions or hyphenation', async () => {
  const text = 'This is a linked phrase with enough ordinary words and representation to wrap across several lines in the narrow paragraph.';
  const source = body => document(body).replace('\\begin{document}', String.raw`\usepackage[textwidth=100bp]{geometry}\begin{document}`);
  const linked = await typesetDocument(source(String.raw`\href{https://example.org}{${text}}`), data);
  const plain = await typesetDocument(source(text), data);
  assert.deepEqual(glyphs(linked), glyphs(plain));
  assert.ok(links(linked).length >= 3);
  assert.ok(new Set(links(linked).map(i => i.y)).size >= 3);
  assert.ok(links(linked).every(i => i.width > 0 && i.height > 0));
});

test('hidelinks and colorlinks preserve clickable annotations with no visible border', async () => {
  const hidden = await typesetDocument(document(String.raw`\href{https://example.org}{Link}`, 'hidelinks'), data);
  const colored = await typesetDocument(document(String.raw`\hypersetup{colorlinks=true,urlcolor=blue}\href{https://example.org}{Link}`), data);
  for (const layout of [hidden, colored]) {
    assert.deepEqual(layout.diagnostics, []);
    assert.equal(links(layout)[0].borderWidth, 0);
    const raw = Buffer.from(await exportVectorPdf(layout, vectors)).toString();
    assert.ok(raw.includes('/Subtype /Link'));
    assert.ok(raw.includes('/Border [0 0 0]'));
  }
  assert.ok(colored.pages[0].items.filter(i => i.kind === 'glyph').slice(0, 4).every(i => JSON.stringify(i.color) === '[0,0,1,1]'));
});

test('body link appearance changes apply from their source position onward', async () => {
  const layout = await typesetDocument(document(String.raw`\href{https://example.org/one}{First} \hypersetup{hidelinks}\href{https://example.org/two}{Second}.

\href{https://example.org/three}{Third}.`), data);
  assert.deepEqual(layout.diagnostics, []);
  assert.deepEqual(links(layout).map(i => i.borderWidth), [1, 0, 0]);
});

test('footnote link text inherits the source link appearance', async () => {
  const layout = await typesetDocument(document(String.raw`\hypersetup{hidelinks}Note\footnote{\href{https://example.org/note}{A linked note}.}`), data);
  assert.deepEqual(layout.diagnostics, []);
  assert.equal(links(layout).find(i => i.target?.type === 'uri').borderWidth, 0);
});

test('page references converge and starred references have no annotation', async () => {
  const layout = await typesetDocument(document(String.raw`\pageref{sec} \ref*{sec} \eqref*{eq}\newpage\section{Second}\label{sec}\begin{equation}x=y\label{eq}\end{equation}`), data);
  assert.deepEqual(layout.diagnostics, []);
  assert.equal(links(layout).length, 1);
  const first = layout.pages[0].items.find(i => i.kind === 'glyph');
  assert.equal(first.key, 'text/@document:roman:50', 'The target is on page 2');
});

test('align rows, moved floats and footnotes land on their own final geometry', async () => {
  const body = String.raw`\ref{b} \ref{fig} Note\footnote{A footnote.}\begin{align}x&=1\label{a}\\y&=2\label{b}\end{align}\begin{figure}[p]\includegraphics{plot.png}\caption{Plot}\label{fig}\end{figure}`;
  const layout = await typesetDocument(document(body).replace('\\usepackage{amsmath}', '\\usepackage{amsmath,graphicx}'), data, {assets: {'plot.png': {width: 200, height: 100}}});
  assert.ok(layout.destinations['label:b'].y > layout.destinations['label:a'].y);
  const page = layout.destinations['label:fig'].page;
  assert.equal(page, layout.pages.findIndex(p => p.items.some(i => i.kind === 'image')));
  assert.ok(layout.pages.some(p => p.links?.some(i => i.target.value === 'footnote:1')));
  assert.ok(layout.destinations['footnote:1']);
});

test('empty explicit targets resolve, and missing targets fail explicitly', async () => {
  const layout = await typesetDocument(document(String.raw`\hyperlink{end}{Jump}\newpage\hypertarget{end}{}`), data);
  assert.ok(layout.destinations['named:end']);
  assert.equal(layout.destinations['named:end'].page, 1);
  await exportVectorPdf(layout, vectors);
  const missing = await typesetDocument(document(String.raw`\hyperlink{missing}{Jump}`), data);
  assert.ok(missing.diagnostics.some(d => d.includes('Undefined link destination')));
  await assert.rejects(exportVectorPdf(missing, vectors), /Missing PDF link destination/);
});

test('annotation URI bytes cannot become PDF action syntax', async () => {
  const target = 'https://example.org/a) /Launch (é';
  const layout = {pages: [{width: 200, height: 300, items: [{kind: 'link', x: 10, y: 20, width: 30, height: 10, target: {type: 'uri', value: target}}]}]};
  const bytes = await exportVectorPdf(layout, vectors), raw = Buffer.from(bytes).toString();
  assert.ok(raw.includes('/S /URI'));
  assert.ok(!raw.includes('/Launch'));
  assert.ok(raw.includes(Buffer.from('https://example.org/a)%20/Launch%20(%C3%A9').toString('hex')));
});

test('custom float caption destinations survive deferred placement', async () => {
  const source = document(String.raw`See Listing~\ref{listing}.\begin{mfile}\begin{verbatim}code\end{verbatim}\caption{A listing}\label{listing}\end{mfile}`)
    .replace('\\begin{document}', String.raw`\usepackage{float}\newfloat{mfile}{tp}{mfi}\floatname{mfile}{Listing}\begin{document}`);
  const layout = await typesetDocument(source, data);
  assert.ok(layout.destinations['label:listing']);
  assert.ok(layout.pages[layout.destinations['label:listing'].page].items.some(i => i.destinationIds?.includes('float:mfile:1')));
  await exportVectorPdf(layout, vectors);
});
