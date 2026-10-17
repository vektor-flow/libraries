import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import {createPackageSourceBundle} from '../latex_package_sources.mjs';
import {createSourceSnapshot} from '../latex_source_revision.mjs';
const hash = b => createHash('sha256').update(b).digest('hex');
const file = (id, text, kind = 'document', version = 1) => {
  const bytes = Buffer.from(text); return {id, version, kind, bytes, sha256: hash(bytes)};
};
const make = (files = [file('main', 'α😀\r\n\\input{defs}\\foo{x}'), file('defs', '\\newcommand{\\foo}[1]{#1}', 'package')], extra = {}) =>
  createPackageSourceBundle({files, engineIdentity: 'test-engine', initialStateIdentity: 'explicit-init-state', ...extra});

test('exact bytes and existing source revision, including BOM/CRLF/comments', () => {
  const row = file('main', '\ufeff%comment\r\nα😀\r\n'); const b = make([row]);
  assert.deepEqual(b.bytes('main'), row.bytes);
  assert.equal(b.sourceTable.texts[0], row.bytes.toString());
  assert.equal(b.snapshot.revision, createSourceSnapshot([{id: row.id, version: row.version, text: row.bytes.toString()}]).revision);
  row.bytes.fill(0); const bytes = b.bytes('main'); bytes.fill(0);
  assert.equal(b.sourceTable.texts[0], '\ufeff%comment\r\nα😀\r\n');
  assert.equal(b.bytes('main').toString(), '\ufeff%comment\r\nα😀\r\n');
  assert.throws(() => b.sourceTable.ids.push('other'), TypeError);
});
test('reject changed pins, malformed UTF-8, duplicate IDs, missing identities', () => {
  const row = file('a', 'a'); assert.throws(() => make([{...row, sha256: '0'.repeat(64)}]), /digest mismatch/);
  const bad = Buffer.from([0xc0, 0xaf]); assert.throws(() => make([{...row, bytes: bad, sha256: hash(bad)}]), /encoded data/);
  assert.throws(() => make([row, row]), /Duplicate/);
  assert.throws(() => make([row], {initialStateIdentity: ''}), /identity/);
  assert.throws(() => make([row], {requests: [{sourceId: 'absent'}]}), /Missing requested/);
  assert.throws(() => make([file('p', '', 'package')], {requests: [{sourceId: 'p', options: Array(1)}]}), /ordered options/);
});
test('strict original UTF-8 offsets, never UTF-16 or flattened-source positions', () => {
  const b = make(), c = b.context(), root = c.enter('main');
  assert.equal(c.textAt(c.origin(root, 2, 6)), '😀');
  assert.throws(() => c.origin(root, 2, 3), /scalar/);
  assert.throws(() => c.origin(root, 3, 6), /scalar/);
  assert.throws(() => c.origin(root, 0, 999), /span/);
  assert.throws(() => c.origin(root, 0, 0), /span/);
});
test('include occurrences retain caller directive; repeated includes stay distinct', () => {
  const b = make(), c = b.context(), root = c.enter('main');
  const directive = c.origin(root, 8, 20, 'include');
  assert.equal(c.textAt(directive), '\\input{defs}');
  const a = c.enter('defs', directive), other = c.enter('defs', directive);
  assert.notEqual(a, other); assert.equal(a.via, other.via);
  const da = c.origin(a, 0, 24, 'definition'), db = c.origin(other, 0, 24, 'definition');
  assert.notEqual(da.occurrence, db.occurrence);
  assert.equal(c.textAt(da), '\\newcommand{\\foo}[1]{#1}');
  assert.equal(c.textAt(db), c.textAt(da));
});
test('definition, invocation and argument origins remain distinct with nested calls', () => {
  const b = make(), c = b.context(), main = c.enter('main'), defs = c.enter('defs');
  const definition = c.origin(defs, 0, 24, 'definition');
  const invocation = c.origin(main, 20, 24, 'invocation', {definition});
  const argument = c.origin(main, 25, 26, 'argument', {invocation});
  assert.equal(c.textAt(invocation), '\\foo'); assert.equal(c.textAt(argument), 'x');
  const nested = c.origin(defs, 12, 16, 'invocation', {definition, invocation});
  assert.notEqual(nested.source, invocation.source);
  assert.equal(nested.invocation, argument.invocation);
  assert.throws(() => c.origin(main, 20, 24, 'invocation'), /Definition link/);
  assert.throws(() => c.origin(main, 25, 26, 'argument'), /needs invocation/);
  assert.throws(() => c.origin(defs, 0, 1, 'argument', {invocation}), /occurrence/);
});
test('cross-context and cloned provenance cannot be reused; missing sources never fall back', () => {
  const b = make(), a = b.context(), c = b.context(), root = a.enter('main');
  assert.throws(() => c.origin(root, 0, 2), /Foreign/);
  const span = a.origin(root, 0, 2); assert.throws(() => a.textAt({...span}), /Foreign/);
  assert.throws(() => a.enter('missing'), /Missing explicit/);
  assert.throws(() => a.enter('defs', span), /wrong-role/);
  assert.deepEqual(c.exportOrigins().origins, []);
});
test('cycle rejection follows include ancestry, not global already-seen file names', () => {
  const c = make().context(), root = c.enter('main');
  const directive = c.origin(root, 8, 20, 'include'), child = c.enter('defs', directive);
  const back = c.origin(child, 0, 1, 'include');
  assert.throws(() => c.enter('main', back), /Cyclic/);
  assert.doesNotThrow(() => c.enter('defs', directive));
});
test('cache preparation key covers exact source universe and versions, engine/state, ordered requests/options', () => {
  const a = file('a', 'a', 'package'), b = file('b', 'b', 'package');
  const base = {requests: [{sourceId: 'a', options: ['red', 'blue']}, {sourceId: 'b', options: []}]};
  const key = make([a, b], base).cacheKey;
  assert.equal(make([b, a], base).cacheKey, key);
  for (const [files, change] of [
    [[a, file('b', 'changed', 'package')], base], [[a, {...b, version: 2}], base],
    [[a, b], {...base, engineIdentity: 'other'}], [[a, b], {...base, initialStateIdentity: 'other'}],
    [[a, b], {requests: [...base.requests].reverse()}],
    [[a, b], {requests: [{sourceId: 'a', options: ['blue', 'red']}, base.requests[1]]}],
    [[a, b, file('unused', 'unused', 'include')], base]
  ]) assert.notEqual(make(files, change).cacheKey, key);
  const options = ['x'], mutable = make([a], {requests: [{sourceId: 'a', options}]}); options[0] = 'y';
  assert.deepEqual(mutable.requests[0].options, ['x']);
});
test('diagnostics name exact primitive at exact pinned byte span; interpretation always refuses', () => {
  const c = make([file('k', '\\catcode64=11', 'kernel')]).context(), k = c.enter('k');
  const span = c.origin(k, 0, 8), d = c.unsupported(span, 'catcode', 'Mutable category-code table and numeric scanner');
  assert.deepEqual([d.code, d.sourceId, d.startByte, d.stopByte], ['TEX_PACKAGE_PRIMITIVE_UNSUPPORTED', 'k', 0, 8]);
  assert.throws(() => c.unsupported(span, 'edef', 'expansion'), /differs/);
  assert.throws(() => c.interpret(), {code: 'TEX_PACKAGE_INTERPRETER_UNAVAILABLE'});
  const empty = make([file('empty', '', 'package')]).context();
  assert.throws(() => empty.interpret(), {code: 'TEX_PACKAGE_INTERPRETER_UNAVAILABLE'});
});
test('native transport is aligned, detached immutable original source data', () => {
  const b = make(); assert.deepEqual(b.sourceTable.ids, ['defs', 'main']);
  for (let i = 0; i < b.sourceTable.ids.length; ++i) {
    assert.equal(hash(Buffer.from(b.sourceTable.texts[i])), b.sourceTable.hashes[i]);
    assert.equal(b.sourceTable.versions[i], 1);
  }
  const c = b.context(), root = c.enter('main'); c.origin(root, 0, 2);
  const before = c.exportOrigins(); c.origin(root, 2, 6);
  assert.equal(before.origins.length, 1); assert.equal(c.exportOrigins().origins.length, 2);
});
// These installed sources are read-only pinned inputs. Passing this test proves
// exact loading and identified boundaries, never successful package evaluation.
if (process.env.PACKAGE_SOURCE_MANIFEST) test('load actual installed kernel/amsmath/xcolor bytes, retain headers and exact first boundary', () => {
  const manifest = JSON.parse(readFileSync(process.env.PACKAGE_SOURCE_MANIFEST));
  const files = manifest.files.map((p, i) => ({id: p.id, version: 0, kind: i ? 'package' : 'kernel', bytes: readFileSync(p.path), sha256: p.sha256}));
  const b = make(files, {requests: files.map(f => ({sourceId: f.id, options: []}))}), c = b.context();
  for (const p of manifest.files) {
    assert.equal(b.bytes(p.id).length, p.bytes);
    assert.equal(hash(b.bytes(p.id)), p.sha256);
    const occurrence = c.enter(p.id), boundary = p.first_boundary;
    const span = c.origin(occurrence, boundary.startByte, boundary.stopByte);
    assert.equal(c.textAt(span), boundary.text);
    const primitive = boundary.text.match(/^\\([A-Za-z]+)/)[1];
    const token = c.origin(occurrence, boundary.startByte, boundary.startByte + primitive.length + 1);
    const d = c.unsupported(token, primitive, boundary.reason);
    assert.equal(d.sourceId, p.id); assert.equal(d.sha256, p.sha256);
    const state = p.state_boundary;
    assert.equal(c.textAt(c.origin(occurrence, state.startByte, state.stopByte)), state.text);
  }
  assert.throws(() => c.interpret(), {code: 'TEX_PACKAGE_INTERPRETER_UNAVAILABLE'});
});
