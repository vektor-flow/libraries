import test from 'node:test';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
import {createPdfSelectionSession} from '../latex_pdf_selection.mjs';

const bytes = s => new TextEncoder().encode(s).length;
const request = session => ({expectedSnapshot: session.current.snapshot, expectedRevision: session.current.snapshot.revision});
const resources = {fonts: {source: 'HOST fixture only', valid: false}, operators: 'HOST fixture only', ordered_roles: ['roman'], language: {source: 'HOST fixture only'}};
// Explicit typed HOST fixtures; none are represented as actual native output.
function fixture(texts = ['😀', 'fi', 'e\u0301', 'x', 'x'], parts = [1, 1, 2, 1, 1], pages = [4, 2]) {
  const text = texts.join(''), leaves = [], operations = []; let byte = 0;
  texts.forEach((value, i) => {
    const op = {operation: i * 3, start: byte, stop: byte + bytes(value), groupId: 'g', leaves: []};
    for (let j = 0; j < parts[i]; j++) { op.leaves.push({part: j * 7, id: `leaf-${i}-${j}`, resources: []}); leaves.push({op, part: j * 7}); }
    byte = op.stop; operations.push(op);
  });
  const owner = {documentId: 'doc', revision: 0, resources: [], sources: [{id: 'main', version: 0, text}],
    groups: [{id: 'g', contentVersion: 0, layoutVersion: 0, contentKey: text, layoutKey: text, edges: [], spans: [{sourceId: 'main', start: 0, end: text.length}]}],
    scopes: [{id: 'parse', sourceId: 'main', text, baseByte: 0, operations}]};
  const arena = {count: leaves.length, kinds: leaves.map(() => 0), draws: leaves.map(() => true),
    a260_scopes: leaves.map(() => 'parse'), a260_texts: leaves.map(() => text), a260_operations: leaves.map(x => x.op.operation),
    a260_starts: leaves.map(x => x.op.start), a260_stops: leaves.map(x => x.op.stop), a260_parts: leaves.map(x => x.part)};
  let first = 0; const firsts = pages.map(n => { const v = first; first += n; return v; });
  return {mapping: {owner, sourceId: 'main', bodyRoutes: [{block: 0, scope: 'parse'}], noteRoutes: []},
    result: {complete: true, diagnostics: '', unresolved_json: '[]', block_count: 1, page_count: pages.length, layout_json: '',
      document: {arena, firsts, counts: pages, widths: pages.map(() => 100), heights: pages.map(() => 100), page_count: pages.length}}};
}
function start(f = fixture()) {
  const session = createPdfSelectionSession(f.mapping.owner.sources), preparation = session.prepare(request(session), f.mapping);
  return {...f, session, preparation};
}
function logical(p) { return p.cluster_firsts.map((_, i) => {
  const scope = p.cluster_scopes[i], source = p.source_texts[p.scope_sources[scope]];
  return Buffer.from(source).subarray(p.scope_bases[scope] + p.cluster_starts[i], p.scope_bases[scope] + p.cluster_stops[i]).toString();
}); }

test('supplementary, ligature, combining cluster and repeated glyph retain exact logical spans', () => {
  const {session, preparation, result} = start(), t = session.plan(preparation, result);
  assert.deepEqual(logical(t.plan), ['😀', 'fi', 'e\u0301', 'x', 'x']);
  assert.deepEqual(t.plan.cluster_firsts, [0, 1, 2, 4, 5]); assert.deepEqual(t.plan.cluster_counts, [1, 1, 2, 1, 1]);
  assert.deepEqual(t.plan.cluster_starts, [0, 4, 6, 9, 10]); assert.deepEqual(t.plan.cluster_stops, [4, 6, 9, 10, 11]);
  assert.equal(t.plan.source_revision, preparation.sourceRevision);
  const args = session.encoderArguments(t, resources);
  assert.strictEqual(args[0], t.boundDocument.document); assert.strictEqual(args[3], t.plan);
  assert.deepEqual(args.slice(1, 3), [resources.fonts, resources.operators]);
  // No invented native result/byte receipt or selectable success field.
  assert.deepEqual(Object.keys(t), ['boundDocument', 'plan']);
});

test('one logical group spans pages only at complete cluster boundaries', () => {
  const {session, preparation, result} = start(), t = session.plan(preparation, result);
  assert.deepEqual(t.plan.cluster_groups, [0, 0, 0, 0, 0]);
  assert.deepEqual(t.boundDocument.document.firsts, [0, 4]);
  assert.equal(logical(t.plan).join(''), t.plan.source_texts[0]);
  const f = fixture(); f.result.document.firsts = [0, 3]; f.result.document.counts = [3, 3];
  const s = start(f); assert.throws(() => s.session.plan(s.preparation, s.result), /Cross-page cluster/);
});

test('actual owned sources preserve CRLF and nonzero byte base without inserting them into glyph text', () => {
  const f = fixture(), prefix = '前\r\n', o = f.mapping.owner;
  o.sources[0].text = prefix + o.sources[0].text; o.scopes[0].baseByte = bytes(prefix);
  o.groups[0].spans[0].start = prefix.length; o.groups[0].spans[0].end = o.sources[0].text.length;
  const s = start(f), t = s.session.plan(s.preparation, s.result);
  assert.equal(t.plan.source_texts[0], '前\r\n😀fie\u0301xx'); assert.equal(t.plan.scope_bases[0], 5);
  assert.equal(logical(t.plan).join(''), '😀fie\u0301xx');
});

test('typed result and parser ownership required; render-only and caller flags cannot bypass', () => {
  const mutations = [r => delete r.document, r => r.complete = false, r => r.diagnostics = 'bad', r => r.unresolved_json = '[1]',
    r => delete r.document.arena.a260_parts, r => r.document.arena.a260_scopes[0] = '',
    r => r.document.arena.a260_texts[0] = 'wrong', r => r.document.arena.a260_operations[0] = 123,
    r => r.document.arena.a260_starts[0] = 1, r => r.document.arena.a260_stops[0] = 5,
    r => r.document.arena.a260_parts[0] = 12, r => r.document.arena.a260_parts[3] = 0,
    r => r.document.arena.draws[0] = false, r => r.document.arena.kinds[0] = 2,
    r => r.document.firsts[1] = 3];
  for (const mutate of mutations) { const s = start(); mutate(s.result); s.result.authenticated = true; s.result.selectable = true;
    assert.throws(() => s.session.plan(s.preparation, s.result)); }
  const s = start(); assert.throws(() => s.session.plan(s.preparation, {pdf: 'fake', layout: s.result}), /Typed DocumentResult/);
});

test('missing, duplicate, mismatched or unconsumed owner emissions refuse', () => {
  for (const mutate of [o => o.scopes[0].operations[0].leaves = [],
    o => o.scopes[0].operations[0].leaves.push({...o.scopes[0].operations[0].leaves[0]}),
    o => o.scopes[0].operations[1].leaves[0].id = o.scopes[0].operations[0].leaves[0].id,
    o => o.scopes[0].operations[0].leaves.push({id: 'extra', part: 99, resources: []}),
    o => o.scopes[0].operations[0].stop = 3]) {
    const f = fixture(); mutate(f.mapping.owner);
    assert.throws(() => {const s = start(f); s.session.plan(s.preparation, s.result);});
  }
});

test('overlapping and omitted authored spans do not repeat/drop parser source', () => {
  const f = fixture(['x', 'x'], [1, 1], [2]);
  f.mapping.owner.scopes[0].operations[1].start = 0; f.mapping.owner.scopes[0].operations[1].stop = 1;
  f.result.document.arena.a260_starts[1] = 0; f.result.document.arena.a260_stops[1] = 1;
  const s = start(f); assert.throws(() => s.session.plan(s.preparation, s.result), /Overlapping/);
  const g = fixture(['x', 'y'], [1, 1], [2]);
  g.mapping.owner.sources[0].text += 'z'; g.mapping.owner.groups[0].spans[0].end++;
  const t = start(g); assert.throws(() => t.session.plan(t.preparation, t.result), /Incomplete selection plan/);
});

test('noncontiguous cluster emissions fail even when the same group is contiguous', () => {
  const f = fixture(['x', 'y'], [2, 1], [3]);
  for (const key of Object.keys(f.result.document.arena)) if (Array.isArray(f.result.document.arena[key])) {
    const a = f.result.document.arena[key]; [a[1], a[2]] = [a[2], a[1]];
  }
  const s = start(f); assert.throws(() => s.session.plan(s.preparation, s.result), /Repeated\/noncontiguous/);
});

test('expanded origins, TeX syntax, whitespace and transformed punctuation remain explicit dependencies', () => {
  for (const text of ['\\alpha', '{x}', '$x$', 'a b', 'a\r\nb', 'a-b', "a'b", 'a~b', 'a`b', 'a\0b']) {
    const s = start(fixture([text], [1], [1])); assert.throws(() => s.session.plan(s.preparation, s.result), /Nonliteral/);
  }
  const f = fixture(['x'], [1], [1]); f.mapping.owner.scopes[0].a262_originMode = 'explicit';
  f.mapping.owner.scopes[0].operations[0].a262_origins = [{sourceId: 'main', startByte: 0, stopByte: 1}];
  const s = start(f); assert.throws(() => s.session.plan(s.preparation, s.result), /Expanded/);
});

test('preparations and tickets cannot be cloned, crossed, or forged', () => {
  const s = start(), t = s.session.plan(s.preparation, s.result), other = start();
  for (const bad of [{...s.preparation}, structuredClone(s.preparation), other.preparation]) assert.throws(() => s.session.plan(bad, s.result), /Foreign/);
  for (const bad of [{...t}, structuredClone(t), {plan: t.plan, boundDocument: t.boundDocument}]) assert.throws(() => s.session.encoderArguments(bad, resources), /Foreign/);
  assert.throws(() => other.session.encoderArguments(t, resources), /Foreign/);
});

test('plan and document snapshot detached from caller mutations', () => {
  const s = start(), t = s.session.plan(s.preparation, s.result);
  s.result.document.arena.a260_texts[0] = 'mutated'; s.mapping.owner.sources[0].text = 'mutated';
  assert.equal(t.boundDocument.document.arena.a260_texts[0], '😀fie\u0301xx'); assert.equal(t.plan.source_texts[0], '😀fie\u0301xx');
  assert.ok(Object.isFrozen(t.plan.cluster_starts)); assert.throws(() => t.plan.cluster_starts[0] = 99);
});

test('no-op revision commits invalidate old ticket and preparation by current state identity', async () => {
  const s = start(), t = s.session.plan(s.preparation, s.result), mapping = structuredClone(s.mapping);
  mapping.owner.revision = 1;
  await s.session.apply({...request(s.session), edits: []}, mapping, async () => s.result);
  assert.throws(() => s.session.encoderArguments(t, resources), /Stale/);
  assert.throws(() => s.session.plan(s.preparation, s.result), /Stale/);
});

test('multiple authored groups are consumed in explicit logical order', () => {
  const f = fixture(['x', 'y'], [1, 1], [1, 1]), o = f.mapping.owner;
  o.groups[0].spans[0].end = 1;
  o.groups.push({...structuredClone(o.groups[0]), id: 'g2', spans: [{sourceId: 'main', start: 1, end: 2}]});
  o.scopes[0].operations[1].groupId = 'g2';
  const s = start(f); assert.deepEqual(s.session.plan(s.preparation, s.result).plan.cluster_groups, [0, 1]);
  o.groups.reverse(); const reversed = start(f); assert.throws(() => reversed.session.plan(reversed.preparation, reversed.result), /Nonlogical/);
});

 test('exact retained plan bytes and schema digest are integrity metadata, not completion proof', () => {
  const s = start(), t = s.session.plan(s.preparation, s.result), a = s.session.serializePlan(t);
  assert.equal(a.byteLength, a.bytes.length);
  assert.equal(a.planSha256, createHash('sha256').update(a.bytes).digest('hex'));
  assert.match(a.schemaSha256, /^[a-f0-9]{64}$/);
  assert.deepEqual(JSON.parse(new TextDecoder().decode(a.bytes)), t.plan);
  const original = a.bytes.slice(); a.bytes.fill(0);
  assert.deepEqual(s.session.serializePlan(t).bytes, original);
  assert.throws(() => s.session.serializePlan({...t}), /Foreign/);
 });
