import {createSourceSnapshot, createSourceEditSession} from './latex_source_revision.mjs';
import {beginProvenance, documentAndNoteEntryRoutes, bindOperationDocument} from './latex_operation_binding.mjs';

const check = (ok, message) => { if (!ok) throw Error(message); };
const integer = n => Number.isSafeInteger(n) && n >= 0;
const id = x => typeof x === 'string' && x.length > 0;
const bytes = text => new TextEncoder().encode(text).length;
const boundary = (text, n) => n === 0 || n === text.length ||
  !(text.charCodeAt(n - 1) >= 0xd800 && text.charCodeAt(n - 1) <= 0xdbff &&
    text.charCodeAt(n) >= 0xdc00 && text.charCodeAt(n) <= 0xdfff);

// A bounded plain-data transport. Reject accessors, sparse arrays, exotic mutable
// containers and cycles before reading values; freeze our copy, never the caller.
function copy(value, active = new Set(), depth = 0) {
  check(depth <= 256, 'Unsupported binding depth');
  if (value === null || ['string', 'boolean', 'undefined'].includes(typeof value)) return value;
  if (typeof value === 'number') { check(Number.isFinite(value), 'Invalid binding number'); return value; }
  check(value && typeof value === 'object' &&
    (Array.isArray(value) || Object.getPrototypeOf(value) === Object.prototype), 'Unsupported binding container');
  check(!active.has(value), 'Cyclic binding data'); active.add(value);
  const array = Array.isArray(value), result = array ? [] : {};
  const keys = Reflect.ownKeys(value).filter(key => !(array && key === 'length'));
  if (array) check(keys.length === value.length && keys.every((key, i) => key === String(i)), 'Invalid binding array');
  for (const key of keys) {
    const d = Object.getOwnPropertyDescriptor(value, key);
    check(typeof key === 'string' && d.enumerable && Object.hasOwn(d, 'value'), 'Unsupported binding property');
    Object.defineProperty(result, key, {value: copy(d.value, active, depth + 1), enumerable: true});
  }
  active.delete(value); return Object.freeze(result);
}

// Entry validation is deliberately stronger than legacy beginProvenance: every
// declared operation needs a nonempty authored origin contained by its group.
// beginProvenance remains the authority for parser byte/scalar/scope validation.
function mappedOwner(snapshot, owner) {
  check(owner && createSourceSnapshot(owner.sources).revision === snapshot.revision, 'Owner/source revision mismatch');
  const session = beginProvenance(owner);
  check(id(session.documentId) && integer(session.revision) && Array.isArray(session.resources), 'Invalid owner identity');
  const sources = new Map(snapshot.sources.map(s => [s.id, s]));
  for (const s of snapshot.sources) for (const scalar of s.text) {
    const cp = scalar.codePointAt(0); check(cp < 0xd800 || cp > 0xdfff, 'Unpaired surrogate source');
  }
  const resources = new Set();
  for (const r of session.resources) {
    check(id(r.id) && integer(r.version) && id(r.binding) && !resources.has(r.id), 'Invalid immutable resource');
    resources.add(r.id);
  }
  const groups = new Map(session.groups.map(g => [g.id, g])), groupBytes = new Map(), used = new Set();
  for (const g of session.groups) {
    check(id(g.id) && id(g.contentKey) && id(g.layoutKey) && integer(g.contentVersion) &&
      integer(g.layoutVersion) && Array.isArray(g.edges), 'Invalid group identity/version');
    check(g.edges.every(e => e && ['flow', 'macro', 'reference', 'font'].includes(e.kind) && groups.has(e.target)) &&
      new Set(g.edges.map(e => JSON.stringify([e.kind, e.target]))).size === g.edges.length, 'Invalid dependency');
    check(Array.isArray(g.spans) && g.spans.length > 0, 'Missing group origins');
    groupBytes.set(g.id, g.spans.map(span => {
      const source = sources.get(span?.sourceId);
      check(source && integer(span.start) && integer(span.end) && span.start < span.end && span.end <= source.text.length, 'Invalid authored group span');
      check(boundary(source.text, span.start) && boundary(source.text, span.end), 'Split Unicode scalar');
      return {sourceId: source.id, start: bytes(source.text.slice(0, span.start)), stop: bytes(source.text.slice(0, span.end))};
    }));
  }
  check(session.scopes.length > 0, 'Missing authored mapping');
  for (const scope of session.scopes) {
    check(scope.operations.length > 0, 'Missing authored operation mapping');
    for (const op of scope.operations) {
      const origins = scope.a262_originMode === 'explicit' ? op.a262_origins :
        [{sourceId: scope.sourceId, startByte: scope.baseByte + op.start, stopByte: scope.baseByte + op.stop}];
      for (const origin of origins) check(origin.startByte < origin.stopByte && groupBytes.get(op.groupId).some(span =>
        span.sourceId === origin.sourceId && span.start <= origin.startByte && origin.stopByte <= span.stop), 'Missing/ungrouped authored origin');
      check(op.leaves.length > 0, 'Missing authored emission mapping'); used.add(op.groupId);
      for (const leaf of op.leaves) check(leaf.resources.every(r => resources.has(r)) &&
        new Set(leaf.resources).size === leaf.resources.length && (leaf.link === undefined || id(leaf.link)), 'Invalid leaf resources/link');
    }
  }
  check(used.size === groups.size, 'Unused owner group');
  return session;
}

/** Internal Node host bridge, with explicit prepared-plan mappings only.
 * prepare() produces immutable inputs, not authenticated output or a PDF API.
 * apply() accepts a preparation-only DocumentResult callback (layout/document_owned),
 * never a tex2pdf result. It must not save externally. No publication path exists.
 * Native/font transport and the truth of caller-supplied parse mappings are outside
 * this bridge. The native route must still compare its actual parser input.
 */
export function createSourceBindingBridge(sources) {
  const edits = createSourceEditSession(copy(sources)), issued = new WeakMap();

  function currentRequest(request) {
    const base = edits.current;
    check(request?.expectedSnapshot === base.snapshot, 'Stale/cross-session source snapshot');
    check(request.expectedRevision === base.snapshot.revision, 'Stale source revision');
    return base;
  }
  function prepareAt(base, snapshot, mapping) {
    const owner = mappedOwner(snapshot, mapping.owner);
    const previous = base.replacement?.boundDocument.metadata;
    if (previous) check(owner.documentId === previous.documentId && owner.revision > previous.revision, 'Revision must advance within document');
    const routes = documentAndNoteEntryRoutes(owner, mapping.bodyRoutes, mapping.noteRoutes);
    const byId = new Map(snapshot.sources.map(s => [s.id, s])), source = byId.get(mapping.sourceId);
    const {files = [], job = 'main', entry = 'main.tex', includeLayout = true} = mapping;
    check(source && Array.isArray(files) && id(job) && id(entry) && typeof includeLayout === 'boolean', 'Invalid native source input');
    const paths = new Set(), covered = new Set([source.id]), fileValues = {};
    for (const file of files) {
      check(file && id(file.path) && file.path !== entry && !paths.has(file.path) && byId.has(file.sourceId), 'Invalid/duplicate native file binding');
      paths.add(file.path); covered.add(file.sourceId);
      Object.defineProperty(fileValues, file.path, {value: byId.get(file.sourceId).text, enumerable: true});
    }
    check(covered.size === byId.size, 'Missing native source file binding');
    const columns = Object.freeze({
      a261_blocks: routes.body.blocks, a261_scopes: routes.body.scopes, a261_texts: routes.body.texts, a263_kinds: routes.body.kinds,
      a267_notes: routes.notes.blocks, a267_scopes: routes.notes.scopes, a267_texts: routes.notes.texts, a267_kinds: routes.notes.kinds
    });
    const preparation = Object.freeze({snapshot, sourceRevision: snapshot.revision, owner, columns,
      source: source.text, files_json: JSON.stringify(fileValues), job, entry, include_layout: includeLayout});
    issued.set(preparation, base); return preparation;
  }
  function guard(preparation) {
    check(issued.has(preparation), 'Foreign source binding preparation');
    check(issued.get(preparation) === edits.current, 'Stale source completion');
  }
  function bindDocument(preparation, result) {
    guard(preparation);
    const detached = copy(result);
    check(detached?.document, 'Typed DocumentResult required; tex2pdf returns no document');
    check(detached.complete === true && detached.diagnostics === '' && detached.unresolved_json === '[]', 'Incomplete document preparation');
    const bound = bindOperationDocument(detached, preparation.owner, edits.current.replacement?.boundDocument ?? null);
    guard(preparation); return bound;
  }
  return Object.freeze({
    get current() { return edits.current; },
    prepare(request, mapping) {
      const base = currentRequest(request), detached = copy(mapping);
      const result = prepareAt(base, base.snapshot, detached); guard(result); return result;
    },
    // Exact positional signatures in latex.tex2pdf and latex_library.document_owned.
    // Resource records must be plain host data; opaque native handles need transport.
    pdfArguments(preparation, resources) {
      guard(preparation);
      const {fonts, operators, ordered_roles, language} = copy(resources);
      check(fonts && language && typeof operators === 'string' && Array.isArray(ordered_roles) && ordered_roles.every(id), 'Missing native PDF resources');
      const p = preparation, c = p.columns;
      const args = Object.freeze([p.source, fonts, operators, ordered_roles, language, p.files_json, p.job, p.entry, p.include_layout,
        c.a261_blocks, c.a261_scopes, c.a261_texts, c.a263_kinds, c.a267_notes, c.a267_scopes, c.a267_texts, c.a267_kinds]);
      guard(preparation); return args;
    },
    documentArguments(preparation, resources) {
      guard(preparation);
      const detached = copy(resources), p = preparation, c = p.columns;
      check(detached?.fonts && detached?.language && Array.isArray(detached?.roles) && detached.roles.every(id), 'Missing native document resources');
      const args = Object.freeze([p.source, detached, c.a261_blocks, c.a261_scopes, c.a261_texts, p.files_json, p.job, p.entry,
        c.a263_kinds, c.a267_notes, c.a267_scopes, c.a267_texts, c.a267_kinds]);
      guard(preparation); return args;
    },
    bindDocument,
    apply(request, mapping, prepareDocument) {
      const base = currentRequest(request);
      check(typeof prepareDocument === 'function', 'Missing document preparation callback');
      const detached = copy(mapping), staged = copy({expectedRevision: request.expectedRevision, edits: request.edits});
      check(base === edits.current, 'Stale source completion');
      return edits.apply(staged, async snapshot => {
        const preparation = prepareAt(base, snapshot, detached);
        guard(preparation);
        const result = await prepareDocument(preparation);
        const boundDocument = bindDocument(preparation, result);
        return {complete: true, replacement: Object.freeze({sourceRevision: snapshot.revision, boundDocument})};
      });
    }
  });
}
