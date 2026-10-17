import test from 'node:test';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
import {createPdfSelectionSession} from './combined/examples/gpu-math/native-vkf/host/latex_pdf_selection.mjs';

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


test('overlapping no-op completions cannot reuse the same state', async () => {
 const s=start(), ticket=s.session.plan(s.preparation,s.result), oldBytes=s.session.serializePlan(ticket);
 let release, enteredResolve; const gate=new Promise(r=>release=r), entered=new Promise(r=>enteredResolve=r);
 const mapping=structuredClone(s.mapping); mapping.owner.revision=1;
 const slow=s.session.apply({...request(s.session),edits:[]},mapping,async () => {enteredResolve();await gate;return s.result;});
 const rejection=assert.rejects(slow,/Stale/); await entered;
 await s.session.apply({...request(s.session),edits:[]},mapping,async()=>s.result);
 release();await rejection;
 assert.equal(s.session.current.snapshot.revision,s.preparation.sourceRevision);
 assert.throws(()=>s.session.serializePlan(ticket),/Stale/);
 assert.throws(()=>s.session.encoderArguments(ticket,resources),/Stale/);
 assert.equal(createHash('sha256').update(oldBytes.bytes).digest('hex'),oldBytes.planSha256);
});
test('resources accessors and sparse arrays fail before encoder argument return', () => {
 const s=start(),t=s.session.plan(s.preparation,s.result);let accessed=false;
 const bad={...resources};Object.defineProperty(bad,'operators',{get(){accessed=true;return '';},enumerable:true});
 assert.throws(()=>s.session.encoderArguments(t,bad),/Unsupported binding property/);assert.equal(accessed,false);
 const sparse={...resources,ordered_roles:new Array(1)};
 assert.throws(()=>s.session.encoderArguments(t,sparse),/Invalid binding array/);
});
test('returned resource records are detached and immutable', () => {
 const s=start(),t=s.session.plan(s.preparation,s.result),r=structuredClone(resources),a=s.session.encoderArguments(t,r);
 r.fonts.source='changed';assert.equal(a[1].source,resources.fonts.source);assert.ok(Object.isFrozen(a[1]));
 assert.strictEqual(a[0],t.boundDocument.document);assert.strictEqual(a[3],t.plan);
});
test('schema pin hashes the actual exact schema file', () => {
 const s=start(),t=s.session.plan(s.preparation,s.result);
 const b=readFileSync(new URL('../pdf-selection-implementation-22/SelectionPlan.schema.json',import.meta.url));
 assert.equal(createHash('sha256').update(b).digest('hex'),s.session.serializePlan(t).schemaSha256);
});
test('empty pages at cluster boundaries do not duplicate or consume clusters', () => {
 const s=start(fixture(['x','y'],[1,1],[0,1,0,1,0])),t=s.session.plan(s.preparation,s.result);
 assert.deepEqual(t.plan.cluster_firsts,[0,1]);assert.deepEqual(logical(t.plan),['x','y']);
});
test('unpaired surrogate and scalar-split origin cannot be blessed by caller flags', () => {
 const f=fixture(['\ud800'],[1],[1]);f.result.authenticated=true;
 assert.throws(()=>start(f),/Unpaired surrogate/);
 const g=fixture(['😀'],[1],[1]);g.mapping.owner.groups[0].spans[0].end=1;
 assert.throws(()=>start(g),/Split Unicode scalar/);
});
