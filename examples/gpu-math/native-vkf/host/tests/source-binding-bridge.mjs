import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {join} from 'node:path';
import {createSourceBindingBridge} from '../latex_source_binding_bridge.mjs';
import {stageSourceEdits, createSourceSnapshot} from '../latex_source_revision.mjs';
import {beginProvenance, bindOperationDocument} from '../latex_operation_binding.mjs';
import {fixture as establishedFixture} from './fixtures/owner-lookup-fixture.mjs';

const byteLength = s => new TextEncoder().encode(s).length;
const request = (bridge, edits = []) => ({expectedSnapshot: bridge.current.snapshot, expectedRevision: bridge.current.snapshot.revision, edits});
// Schema-shaped resource fixtures, not loaded fonts/language or native handles.
const resources = () => ({fonts: {source: 'catalog fixture', capacity: 0, count: 0, payload: 0, size: 0, valid: false}, operators: 'fixture operators', ordered_roles: ['roman'],
  language: {source: 'language fixture', nodes: 0, edges: 0, weights: 0, exceptions: 0, node_start: 0, edge_start: 0, weight_start: 0, exception_start: 0, size: 0}});
const documentResources = () => { const r = resources(); return {fonts: r.fonts, roles: r.ordered_roles, language: r.language,
  tables: {values: [], ems: [], delim1: [], delim2: [], mus: []}, resource_id: 'resources'}; };
const deferred = () => { let resolve, reject; const promise = new Promise((a, b) => { resolve = a; reject = b; }); return {promise, resolve, reject}; };
const frozen = x => { if (x && typeof x === 'object') { assert.ok(Object.isFrozen(x)); Object.values(x).forEach(frozen); } };

// Explicit HOST fixtures only. No native parser/renderer is run or simulated.
function direct(text = 'é😀\r\nx', version = 0, revision = 0) {
  const {o, r} = establishedFixture(1, 1, true);
  o.revision = revision; o.sources[0] = {id: 's', version, text};
  const scope = o.scopes[0]; scope.text = text; scope.operations[0].stop = byteLength(text);
  Object.assign(o.groups[0], {contentVersion: revision, layoutVersion: revision, contentKey: text, layoutKey: text, spans: [{sourceId: 's', start: 0, end: text.length}]});
  r.document.arena.a260_texts[0] = text; r.document.arena.a260_stops[0] = byteLength(text);
  return {mapping: {owner: o, sourceId: 's', bodyRoutes: [{block: 0, scope: 'scope'}], noteRoutes: []}, result: r};
}
function start(f = direct()) { const bridge = createSourceBindingBridge(f.mapping.owner.sources); return {...f, bridge, preparation: bridge.prepare(request(bridge), f.mapping)}; }

test('direct authored source uses real owner/routes/binder and exact PDF argument order', () => {
  const {bridge, preparation: p, result} = start();
  const raw = resources(), args = bridge.pdfArguments(p, raw);
  assert.deepEqual(args, ['é😀\r\nx', raw.fonts, raw.operators, raw.ordered_roles, raw.language, '{}', 'main', 'main.tex', true,
    [0], ['scope'], ['é😀\r\nx'], ['body'], [], [], [], []]);
  assert.deepEqual(Object.keys(p.columns), ['a261_blocks', 'a261_scopes', 'a261_texts', 'a263_kinds', 'a267_notes', 'a267_scopes', 'a267_texts', 'a267_kinds']);
  const bound = bridge.bindDocument(p, result);
  assert.deepEqual(bound, bindOperationDocument(result, beginProvenance(direct().mapping.owner)));
  assert.deepEqual(bound.sourceBinding.leaves, [{id: 'leaf0-0', spans: [{sourceId: 's', start: 0, end: 6}]}]);
  assert.equal(bound.sourceBinding.sources[0].text, 'é😀\r\nx');
  frozen(p); frozen(args); frozen(bound);
  raw.fonts.source = 'mutated'; raw.ordered_roles.push('mutated'); result.document.arena.a260_texts[0] = 'mutated';
  assert.equal(args[1].source, 'catalog fixture'); assert.deepEqual(args[3], ['roman']); assert.equal(bound.document.arena.a260_texts[0], 'é😀\r\nx');
});

test('nonzero source base uses byte offsets without newline or Unicode normalization', () => {
  const f = direct('é😀\r\nx'); f.mapping.owner.sources[0].text = '前\r\n' + f.mapping.owner.sources[0].text;
  f.mapping.owner.scopes[0].baseByte = byteLength('前\r\n'); f.mapping.owner.groups[0].spans = [{sourceId: 's', start: 3, end: 9}];
  const {bridge, preparation, result} = start(f);
  assert.equal(bridge.pdfArguments(preparation, resources())[0], '前\r\né😀\r\nx');
  assert.deepEqual(bridge.bindDocument(preparation, result).sourceBinding.leaves[0].spans, [{sourceId: 's', start: 3, end: 9}]);
});

test('explicit macro origins preserve separate authored files and repeated origins', () => {
  const f = direct('Ω'); const o = f.mapping.owner;
  o.sources = [{id: 's', version: 4, text: '\\macro{😀}\r\n'}, {id: 'defs', version: 2, text: '\\newcommand{\\macro}{Ω}\r\n'}];
  const invocation = {sourceId: 's', startByte: 0, stopByte: byteLength(o.sources[0].text)};
  o.scopes[0].a262_originMode = 'explicit';
  o.scopes[0].operations[0].a262_origins = [invocation, {sourceId: 'defs', startByte: 0, stopByte: byteLength(o.sources[1].text)}, {...invocation}];
  o.groups[0].spans = o.sources.map(s => ({sourceId: s.id, start: 0, end: s.text.length}));
  f.mapping.files = [{path: 'defs.tex', sourceId: 'defs'}]; f.mapping.entry = 'root.tex'; f.mapping.job = 'exact';
  const {bridge, preparation, result} = start(f), args = bridge.pdfArguments(preparation, resources());
  assert.equal(args[0], o.sources[0].text); assert.deepEqual(JSON.parse(args[5]), {'defs.tex': o.sources[1].text});
  assert.deepEqual(args.slice(6, 9), ['exact', 'root.tex', true]); assert.deepEqual(args[11], ['Ω']);
  assert.deepEqual(bridge.bindDocument(preparation, result).sourceBinding.leaves[0].spans,
    [o.groups[0].spans[0], o.groups[0].spans[1], o.groups[0].spans[0]]);
});

test('body, outer, label and synthetic note routes occupy their real independent namespaces', () => {
  const f = direct('\\footnote{é}\r\n'), o = f.mapping.owner, original = structuredClone(o.scopes[0]);
  const names = ['body', 'label', 'outer', 'note', 'marker'];
  o.scopes = names.map((name, i) => {
    const s = structuredClone(original); s.id = name;
    s.operations[0].leaves[0].id = 'leaf-' + name;
    if (i === 4) { s.text = '1'; s.a262_originMode = 'explicit'; s.operations[0].stop = 1;
      s.operations[0].a262_origins = [{sourceId: 's', startByte: 0, stopByte: byteLength(o.sources[0].text)}]; }
    return s;
  });
  f.mapping.bodyRoutes = [{block: 2, scope: 'body'}, {block: 2, scope: 'label', kind: 'label'}, {block: 2, scope: 'outer', kind: 'outer:0'}];
  f.mapping.noteRoutes = [{block: 0, scope: 'note'}, {block: 0, scope: 'marker', kind: 'label'}];
  const {bridge, preparation: p} = start(f);
  assert.deepEqual(Object.values(p.columns), [[2, 2, 2], ['body', 'label', 'outer'], Array(3).fill(o.sources[0].text), ['body', 'label', 'outer:0'],
    [0, 0], ['note', 'marker'], [o.sources[0].text, '1'], ['body', 'label']]);
  const doc = documentResources(), args = bridge.documentArguments(p, doc);
  assert.deepEqual(args, [p.source, doc, [2, 2, 2], ['body', 'label', 'outer'], Array(3).fill(p.source), '{}', 'main', 'main.tex',
    ['body', 'label', 'outer:0'], [0, 0], ['note', 'marker'], [p.source, '1'], ['body', 'label']]);
  // A typed fixture with all explicitly mapped emissions, not generated output.
  const a = f.result.document.arena;
  a.count = 5; a.kinds = Array(5).fill(2); a.a260_scopes = names; a.a260_texts = o.scopes.map(s => s.text);
  a.a260_operations = Array(5).fill(0); a.a260_starts = Array(5).fill(0); a.a260_stops = o.scopes.map(s => s.operations[0].stop); a.a260_parts = Array(5).fill(0);
  f.result.document.counts = [5];
  assert.equal(bridge.bindDocument(p, f.result).sourceBinding.leaves[4].spans[0].end, p.source.length);
});

test('owner version, text, source set, scope and scalar errors fail before transport', () => {
  const mutations = [
    o => o.sources[0].version++, o => o.sources[0].text = 'different', o => o.sources.push({id: 'extra', version: 0, text: 'x'}),
    o => o.sources = [], o => o.sources.push({...o.sources[0]}), o => o.documentId = '', o => o.revision = -1,
    o => o.scopes[0].text = 'wrong', o => o.scopes[0].sourceId = 'absent', o => o.scopes[0].baseByte = 1,
    o => o.scopes[0].operations[0].start = 1, o => o.scopes[0].operations[0].stop = 4,
    o => o.groups[0].spans[0].end = 2, o => o.groups[0].spans = [], o => o.groups[0].spans[0].end = 99,
    o => o.scopes[0].operations[0].stop = 0, o => o.scopes[0].operations = [], o => o.scopes[0].operations[0].leaves = [],
    o => o.scopes = [], o => o.groups[0].spans[0].start = 3, o => o.scopes[0].operations[0].leaves[0].resources = ['missing'],
    o => o.scopes[0].operations.push(structuredClone(o.scopes[0].operations[0])), o => o.scopes[0].a262_originMode = 'generated'
  ];
  for (const mutate of mutations) { const f = direct(), bridge = createSourceBindingBridge(f.mapping.owner.sources); mutate(f.mapping.owner); assert.throws(() => bridge.prepare(request(bridge), f.mapping)); }
  const f = direct('x\ud800'); assert.throws(() => start(f), /surrogate/);
});

test('synthetic text never acquires authored ownership without explicit valid origins', () => {
  for (const origins of [undefined, [], [{sourceId: 'missing', startByte: 0, stopByte: 1}], [{sourceId: 's', startByte: 1, stopByte: 2}], [{sourceId: 's', startByte: 0, stopByte: 100}]]) {
    const f = direct(), s = f.mapping.owner.scopes[0]; s.a262_originMode = 'explicit'; s.text = '1'; s.operations[0].stop = 1; s.operations[0].a262_origins = origins;
    assert.throws(() => start(f));
  }
  const f = direct(); f.mapping.owner.scopes[0].text = '1'; f.mapping.owner.scopes[0].operations[0].stop = 1;
  assert.throws(() => start(f), /differs from source|splits scalar/);
});

test('duplicate, conflicting, aliased, missing and unknown routes fail', () => {
  for (const mutate of [
    m => m.bodyRoutes.push({...m.bodyRoutes[0]}), m => m.bodyRoutes.push({block: 0, scope: 'missing'}),
    m => m.bodyRoutes.push({block: 1, scope: 'scope', kind: 'label'}), m => m.noteRoutes.push({block: 0, scope: 'scope'}),
    m => m.bodyRoutes = [], m => m.bodyRoutes[0].scope = 'unknown', m => m.bodyRoutes[0].kind = 'generated',
    m => m.bodyRoutes[0].kind = 'outer:01', m => m.bodyRoutes[0].block = -1,
    m => { m.noteRoutes = [{block: 0, scope: 'scope', kind: 'outer:0'}]; m.bodyRoutes = []; }
  ]) { const f = direct(); mutate(f.mapping); assert.throws(() => start(f)); }
  const f = direct(), other = structuredClone(f.mapping.owner.scopes[0]);
  other.id = 'other'; other.operations[0].leaves[0].id = 'other-leaf'; f.mapping.owner.scopes.push(other);
  f.mapping.bodyRoutes.push({block: 0, scope: 'other'});
  assert.throws(() => start(f), /duplicate/);
});

test('explicit file bindings reject omitted, conflicting and unknown sources', () => {
  for (const mutate of [m => m.sourceId = 'missing', m => m.files = [{path: 'a', sourceId: 'missing'}],
    m => m.files = [{path: 'a', sourceId: 's'}, {path: 'a', sourceId: 's'}], m => m.files = [{path: 'main.tex', sourceId: 's'}],
    m => m.owner.sources.push({id: 'unmapped', version: 0, text: 'include'}), m => m.includeLayout = 'false']) {
    const f = direct(); mutate(f.mapping); assert.throws(() => start(f));
  }
});

test('caller mappings and source arrays are detached; exotic/accessor inputs fail without invocation', () => {
  const f = direct(), sources = structuredClone(f.mapping.owner.sources), bridge = createSourceBindingBridge(sources), p = bridge.prepare(request(bridge), f.mapping);
  sources[0].text = 'changed'; f.mapping.owner.sources[0].text = 'changed'; f.mapping.owner.scopes[0].operations[0].leaves[0].resources.push('changed'); f.mapping.bodyRoutes[0].block = 99;
  assert.equal(p.snapshot.sources[0].text, 'é😀\r\nx'); assert.deepEqual(p.columns.a261_blocks, [0]);
  assert.deepEqual(p.owner.scopes[0].operations[0].leaves[0].resources, []);
  let invoked = false; const accessor = {}; Object.defineProperty(accessor, 'owner', {enumerable: true, get() { invoked = true; return {}; }});
  assert.throws(() => bridge.prepare(request(bridge), accessor), /property/); assert.equal(invoked, false);
  for (const extension of [new Map(), new Date(), new Uint8Array(1), Array(2)]) { const g = direct(); g.mapping.extension = extension; assert.throws(() => bridge.prepare(request(bridge), g.mapping)); }
  const g = direct(); g.mapping.cycle = g.mapping; assert.throws(() => bridge.prepare(request(bridge), g.mapping), /Cyclic/);
  assert.throws(() => { p.owner.sources[0].text = 'bad'; }, TypeError);
});

test('preparations and snapshot tokens cannot cross sessions or be cloned/reconstructed', () => {
  const a = start(), b = start(); assert.equal(a.preparation.sourceRevision, b.preparation.sourceRevision);
  for (const p of [a.preparation, structuredClone(b.preparation), {...b.preparation}]) {
    assert.throws(() => b.bridge.pdfArguments(p, resources()), /Foreign/);
    assert.throws(() => b.bridge.documentArguments(p, documentResources()), /Foreign/);
    assert.throws(() => b.bridge.bindDocument(p, b.result), /Foreign/);
  }
  assert.throws(() => b.bridge.prepare(request(a.bridge), b.mapping), /cross-session/);
  assert.throws(() => a.bridge.prepare({...request(a.bridge), expectedSnapshot: createSourceSnapshot(a.mapping.owner.sources)}, a.mapping), /cross-session/);
  assert.throws(() => a.bridge.prepare({...request(a.bridge), expectedRevision: 'stale'}, a.mapping), /Stale/);
});

test('binding unknown/generated output, wrong parser spans, missing and duplicate emissions fails', () => {
  for (const mutate of [r => r.document.arena.a260_scopes[0] = '', r => r.document.arena.a260_scopes[0] = 'unknown',
    r => r.document.arena.a260_texts[0] = 'wrong', r => r.document.arena.a260_operations[0] = 99,
    r => r.document.arena.a260_starts[0] = 2, r => r.document.arena.a260_parts[0] = 99,
    r => delete r.document.arena.a260_stops, r => r.complete = false, r => r.diagnostics = 'warning', r => r.unresolved_json = '[{}]',
    r => { r.document.arena.count = 0; for (const k of Object.keys(r.document.arena)) if (Array.isArray(r.document.arena[k])) r.document.arena[k] = []; r.document.counts = [0]; },
    r => { r.document.arena.count = 2; for (const k of Object.keys(r.document.arena)) if (Array.isArray(r.document.arena[k])) r.document.arena[k].push(r.document.arena[k][0]); r.document.counts = [2]; }
  ]) { const f = start(); mutate(f.result); assert.throws(() => f.bridge.bindDocument(f.preparation, f.result)); }
});

test('actual native signatures and render return shape delimit the preparation interface', () => {
  const root = process.env.SOURCE_BINDING_NATIVE_ROOT ?? fileURLToPath(new URL('../../', import.meta.url));
  const latex = readFileSync(join(root, 'latex.vkf'), 'utf8'), library = readFileSync(join(root, 'latex_library.vkf'), 'utf8'), materialize = readFileSync(join(root, 'document_materialize.vkf'), 'utf8');
  const signature = (text, name) => text.match(new RegExp('^' + name + '\\(([^\\n]+)\\):', 'm'))[1].split(',').map(s => s.split(':')[0]);
  assert.deepEqual(signature(latex, 'tex2pdf'), ['source', 'fonts', 'operators', 'ordered_roles', 'language', 'files_json', 'job', 'entry', 'include_layout',
    'a261_blocks', 'a261_scopes', 'a261_texts', 'a263_kinds', 'a267_notes', 'a267_scopes', 'a267_texts', 'a267_kinds']);
  assert.deepEqual(signature(library, 'document_owned'), ['source', 'resources', 'blocks', 'scopes', 'texts', 'files_json', 'job', 'entry', 'a263_kinds', 'a267_notes', 'a267_scopes', 'a267_texts', 'a267_kinds']);
  const returnLine = materialize.slice(materialize.indexOf('\nrender(')).split('\n').find(line => line.includes('@:'));
  assert.equal(returnLine.trim(), '@:(pdf:pdf,layout_json:result.layout_json,diagnostics:result.diagnostics,unresolved_json:result.unresolved_json,complete:result.complete,block_count:result.block_count,page_count:result.page_count)');
  const f = start();
  const renderShapeOnly = {pdf: 'fixture bytes, not rendered', layout_json: '{}', diagnostics: '', unresolved_json: '[]', complete: true, block_count: 1, page_count: 1};
  assert.throws(() => f.bridge.bindDocument(f.preparation, renderShapeOnly), /tex2pdf returns no document/);
});

test('apply composes real revision staging with explicit mappings and existing document binder', async () => {
  const f = start(direct('x')), before = f.bridge.current, req = request(f.bridge, [{sourceId: 's', start: 0, end: 1, text: '😀\r\n'}]);
  const next = direct('😀\r\n', 1, 1), wait = deferred();
  const pending = f.bridge.apply(req, next.mapping, async p => {
    assert.equal(p.snapshot.revision, stageSourceEdits(before.snapshot, req).revision);
    assert.equal(f.bridge.pdfArguments(p, resources())[0], '😀\r\n');
    assert.equal(f.bridge.documentArguments(p, documentResources())[0], '😀\r\n');
    await wait.promise; return next.result;
  });
  req.edits[0].text = 'caller mutation'; next.mapping.owner.sources[0].text = 'caller mutation';
  assert.equal(f.bridge.current, before); wait.resolve(); const state = await pending;
  assert.equal(state.snapshot.sources[0].text, '😀\r\n'); assert.equal(state.snapshot.sources[0].version, 1);
  assert.equal(state.replacement.sourceRevision, state.snapshot.revision); frozen(state);
  assert.equal(state.replacement.boundDocument.sourceBinding.sources[0].text, '😀\r\n');
  assert.throws(() => f.bridge.pdfArguments(f.preparation, resources()), /Stale/);
  next.result.document.arena.a260_texts[0] = 'later mutation';
  assert.equal(state.replacement.boundDocument.document.arena.a260_texts[0], '😀\r\n');
});

test('subsequent commits retain binder document/version/dependency checks', async () => {
  const f = start(direct('x'));
  await f.bridge.apply(request(f.bridge), f.mapping, () => f.result);
  const base = f.bridge.current;
  let called = false;
  await assert.rejects(f.bridge.apply(request(f.bridge), f.mapping, () => { called = true; return f.result; }), /within document/);
  assert.equal(called, false); assert.equal(f.bridge.current, base);
  const changed = direct('y', 1, 1), req = request(f.bridge, [{sourceId: 's', start: 0, end: 1, text: 'y'}]);
  changed.mapping.owner.documentId = 'other';
  await assert.rejects(f.bridge.apply(req, changed.mapping, () => changed.result), /within document/); assert.equal(f.bridge.current, base);
  changed.mapping.owner.documentId = 'lookup'; changed.mapping.owner.groups[0].contentVersion = 0;
  await assert.rejects(f.bridge.apply(req, changed.mapping, () => changed.result), /Content changed without version/); assert.equal(f.bridge.current, base);
  changed.mapping.owner.groups[0].contentVersion = 1;
  const state = await f.bridge.apply(req, changed.mapping, () => changed.result);
  assert.equal(state.snapshot.sources[0].text, 'y'); assert.deepEqual(state.replacement.boundDocument.invalidated, ['g']);
});

test('async competing edits reject stale results before binding and retain the winner', async () => {
  const f = start(direct('x')), slow = deferred(), first = direct('a', 1, 1), second = direct('b', 1, 1);
  let old;
  const pending = f.bridge.apply(request(f.bridge, [{sourceId: 's', start: 0, end: 1, text: 'a'}]), first.mapping, p => { old = p; return slow.promise; });
  const state = await f.bridge.apply(request(f.bridge, [{sourceId: 's', start: 0, end: 1, text: 'b'}]), second.mapping, () => second.result);
  slow.resolve(first.result); await assert.rejects(pending, /Stale source completion/);
  assert.equal(f.bridge.current, state); assert.equal(state.snapshot.sources[0].text, 'b');
  assert.throws(() => f.bridge.documentArguments(old, documentResources()), /Stale/);
});

test('no-op hashes stay equal but snapshot identity and preparation generation still advance', async () => {
  const f = start(direct('x')), req = request(f.bridge), slow = deferred();
  const pending = f.bridge.apply(req, f.mapping, () => slow.promise);
  const state = await f.bridge.apply(req, f.mapping, () => f.result);
  assert.equal(state.snapshot.revision, req.expectedRevision); assert.notEqual(state.snapshot, req.expectedSnapshot);
  slow.resolve(f.result); await assert.rejects(pending, /Stale source completion/);
  assert.throws(() => f.bridge.apply(req, f.mapping, () => f.result), /cross-session/);
  assert.throws(() => f.bridge.prepare(req, f.mapping), /cross-session/);
  const next = direct('x', 0, 1);
  await f.bridge.apply(request(f.bridge), next.mapping, () => next.result);
  assert.equal(f.bridge.current.snapshot.revision, req.expectedRevision);
});

test('failed or incomplete preparation never commits and does not revoke a pending valid result', async () => {
  const f = start(direct('x')), before = f.bridge.current, slow = deferred(), req = request(f.bridge);
  const pending = f.bridge.apply(req, f.mapping, () => slow.promise);
  for (const callback of [() => { throw Error('failed'); }, () => Promise.reject(Error('failed')), () => ({complete: true, pdf: 'no document'}),
    () => ({...f.result, complete: false}), () => ({...f.result, diagnostics: 'bad'}), () => ({...f.result, unresolved_json: '[{}]'})]) {
    await assert.rejects(f.bridge.apply(req, f.mapping, callback)); assert.equal(f.bridge.current, before);
  }
  const bad = direct('y'); let invoked = false;
  await assert.rejects(f.bridge.apply(req, bad.mapping, () => { invoked = true; return bad.result; }), /revision mismatch/);
  assert.equal(invoked, false); assert.equal(f.bridge.current, before);
  slow.resolve(f.result); await pending;
});
