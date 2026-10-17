import {createHash} from 'node:crypto';
import {createSourceBindingBridge} from './latex_source_binding_bridge.mjs';

const check = (ok, message) => { if (!ok) throw Error(message); };
export const selectionPlanSchemaSha256 = '87743151910c573b7f03d622c02fcee922b89fa2dc9ece644af8ddace112827b';
const digest = value => createHash('sha256').update(value).digest('hex');
const bytes = s => new TextEncoder().encode(s).length;
const freeze = x => { if (x && typeof x === 'object') { Object.values(x).forEach(freeze); Object.freeze(x); } return x; };
const literal = s => s.length > 0 && !/[\x00-\x20\\%{}$^_&#~\-`']/u.test(s);
// Deliberately no caller-supplied replacement text. Only direct, exact, literal
// authored spans are currently supported. Expanded TeX needs a real producer.
function makePlan(preparation, bound) {
  const owner = preparation.owner, document = bound.document, a = document.arena;
  check(a.count > 0, 'Empty selection has no authored plan');
  check(a.kinds?.length === a.count && a.draws?.length === a.count &&
    a.kinds.every(k => k === 0) && a.draws.every(x => x === true), 'Nonliteral/generated selection leaf');
  check(owner.groups.length === bound.metadata.groups.length &&
    owner.groups.every((g, i) => g.id === bound.metadata.groups[i].id), 'Nonlogical selection group order');
  const sources = new Map(owner.sources.map((s, i) => [s.id, i]));
  const scopes = new Map(owner.scopes.map((s, i) => [s.id, i]));
  const groups = new Map(owner.groups.map((g, i) => [g.id, i]));
  const operationMaps = owner.scopes.map(s => new Map(s.operations.map(o => [o.operation, o])));
  const p = {schema: 1, document_id: owner.documentId, revision: owner.revision, source_revision: preparation.sourceRevision,
    source_ids: owner.sources.map(s => s.id), source_versions: owner.sources.map(s => s.version), source_texts: owner.sources.map(s => s.text),
    scope_ids: owner.scopes.map(s => s.id), scope_sources: owner.scopes.map(s => sources.get(s.sourceId)),
    scope_bases: owner.scopes.map(s => s.baseByte), scope_texts: owner.scopes.map(s => s.text),
    group_ids: owner.groups.map(g => g.id), group_sources: [], group_starts: [], group_stops: [],
    cluster_groups: [], cluster_scopes: [], cluster_operations: [], cluster_starts: [], cluster_stops: [], cluster_firsts: [], cluster_counts: [],
    leaf_ids: [...bound.metadata.leafIds], leaf_parts: [...a.a260_parts]};
  for (const s of owner.scopes) check(s.a262_originMode === undefined, 'Expanded selection needs authenticated logical producer');
  for (const g of owner.groups) {
    check(g.spans.length === 1, 'Multisource/disjoint group needs logical producer');
    const span = g.spans[0], source = owner.sources[sources.get(span.sourceId)];
    p.group_sources.push(sources.get(span.sourceId));
    p.group_starts.push(bytes(source.text.slice(0, span.start))); p.group_stops.push(bytes(source.text.slice(0, span.end)));
  }
  const seen = new Set(); let page = 0, group = -1, cursor = 0;
  for (let first = 0; first < a.count;) {
    while (page < document.page_count && first >= document.firsts[page] + document.counts[page]) page++;
    check(page < document.page_count, 'Cluster outside document pages');
    const si = scopes.get(a.a260_scopes[first]), scope = owner.scopes[si];
    const op = operationMaps[si].get(a.a260_operations[first]), gi = groups.get(op.groupId);
    const key = JSON.stringify([si, op.operation]); check(!seen.has(key), 'Repeated/noncontiguous cluster ownership'); seen.add(key);
    let stop = first + 1;
    while (stop < a.count && a.a260_scopes[stop] === scope.id && a.a260_operations[stop] === op.operation) stop++;
    check(stop <= document.firsts[page] + document.counts[page], 'Cross-page cluster needs producer split map');
    if (gi !== group) {
      if (group >= 0) check(cursor === p.group_stops[group], 'Missing authored group text');
      check(gi === group + 1, 'Nonlogical selection group order'); group = gi; cursor = p.group_starts[gi];
    }
    check(p.scope_sources[si] === p.group_sources[gi] && scope.baseByte + op.start === cursor &&
      scope.baseByte + op.stop <= p.group_stops[gi], 'Overlapping/missing authored cluster text');
    cursor = scope.baseByte + op.stop;
    // Existing binding already validated UTF-8 -> UTF-16 conversion and origins.
    const span = bound.sourceBinding.leaves[first].spans[0];
    const text = owner.sources[sources.get(span.sourceId)].text.slice(span.start, span.end);
    check(literal(text), 'Nonliteral text needs exact logical producer');
    p.cluster_groups.push(gi); p.cluster_scopes.push(si); p.cluster_operations.push(op.operation);
    p.cluster_starts.push(op.start); p.cluster_stops.push(op.stop); p.cluster_firsts.push(first); p.cluster_counts.push(stop - first);
    first = stop;
  }
  check(group === owner.groups.length - 1 && cursor === p.group_stops[group], 'Incomplete selection plan');
  return freeze(p);
}

/** Preparation only, not a native-completion registry or selectable PDF API.
 * Uses the actual bridge internally: no supplied authenticator or boolean bypass.
 * plan() accepts an exact typed layout Result, not API21's enclosing typed render.
 * A trusted adapter must supply result.layout from the SAME invocation and later
 * bind native PDF bytes and all hashes in its private completion registry.
 */
export function createPdfSelectionSession(sources) {
  const bridge = createSourceBindingBridge(sources), tickets = new WeakMap();
  function guard(ticket) {
    const state = tickets.get(ticket); check(state, 'Foreign selection ticket');
    check(bridge.current === state.base && bridge.current.snapshot === state.preparation.snapshot &&
      bridge.current.snapshot.revision === ticket.plan.source_revision, 'Stale selection ticket');
    return state;
  }
  return Object.freeze({
    get current() { return bridge.current; },
    prepare: (request, mapping) => bridge.prepare(request, mapping),
    documentArguments: (preparation, resources) => bridge.documentArguments(preparation, resources),
    apply: (request, mapping, prepareDocument) => bridge.apply(request, mapping, prepareDocument),
    plan(preparation, result) {
      // bindDocument rejects stale/foreign preparations, incomplete/render-shaped
      // values, unknown generated leaves, parser mismatches and missing emissions.
      const base = bridge.current, boundDocument = bridge.bindDocument(preparation, result);
      const ticket = Object.freeze({boundDocument, plan: makePlan(preparation, boundDocument)});
      const planBytes = new TextEncoder().encode(JSON.stringify(ticket.plan));
      tickets.set(ticket, {base, preparation, planBytes, planSha256: digest(planBytes)}); guard(ticket); return ticket;
    },
    // Retained exact UTF-8 JSON bytes, NOT canonicalized/reencoded on read.
    // Copies may be transported; registry must still authenticate native custody.
    serializePlan(ticket) {
      const state = guard(ticket);
      return Object.freeze({schemaSha256: selectionPlanSchemaSha256, planSha256: state.planSha256,
        byteLength: state.planBytes.length, bytes: state.planBytes.slice()});
    },
    encoderArguments(ticket, resources) {
      const state = guard(ticket);
      // Reuse existing plain-data copy/guard for the actual resource pair.
      // This validates data shape, NOT immutable native resource identity.
      const args = bridge.pdfArguments(state.preparation, resources);
      guard(ticket);
      return Object.freeze([ticket.boundDocument.document, args[1], args[2], ticket.plan]);
    }
  });
}
