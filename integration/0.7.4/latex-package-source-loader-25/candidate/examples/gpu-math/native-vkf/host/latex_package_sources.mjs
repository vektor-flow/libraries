import {createHash} from 'node:crypto';
import {createSourceSnapshot} from './latex_source_revision.mjs';

// Source preparation only. No TeX evaluation, filesystem search, format fallback,
// or PDF binding is performed here. All positions are original UTF-8 byte offsets.
export const PACKAGE_SOURCE_ABI = 'vkf.tex.package-sources/1';
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const check = (ok, message) => { if (!ok) throw Error(message); };
const integer = x => Number.isSafeInteger(x) && x >= 0;
const nonempty = x => typeof x === 'string' && x.length > 0;
const digest = x => typeof x === 'string' && /^[0-9a-f]{64}$/.test(x);
const freeze = x => Object.freeze(x);
const strings = xs => {
  check(Array.isArray(xs) && Array.from(xs).every(x => typeof x === 'string'), 'Invalid ordered options');
  return freeze([...xs]);
};

/** Host supplies exact bytes and trusted expected hashes; hash equality verifies
 * those bytes, not the authority of that expectation. No implicit paths/search.
 * The complete supplied source universe is hashed, including currently unused
 * files: changing any candidate invalidates the preparation conservatively.
 */
export function createPackageSourceBundle({files, engineIdentity, initialStateIdentity, requests = []}) {
  check(nonempty(engineIdentity) && nonempty(initialStateIdentity), 'Missing engine/state identity');
  check(Array.isArray(files) && files.length > 0 && files.length <= 4096, 'Invalid source universe');
  let total = 0;
  const rows = files.map(file => {
    const {id, version, kind, bytes, sha256} = file;
    check(nonempty(id) && integer(version) && ['document', 'kernel', 'package', 'include'].includes(kind), 'Invalid source identity');
    check(bytes instanceof Uint8Array && digest(sha256), 'Expected pinned source bytes');
    total += bytes.byteLength;
    check(total <= 16 * 1024 * 1024, 'Package source universe exceeds 16 MiB');
    const retained = Buffer.from(bytes);
    check(hash(retained) === sha256, `Source digest mismatch: ${id}`);
    // Preserve the BOM as a scalar, CRLF, comments, and all original bytes.
    const text = new TextDecoder('utf-8', {fatal: true, ignoreBOM: true}).decode(retained);
    check(Buffer.from(text, 'utf8').equals(retained), 'Noncanonical UTF-8 source');
    return {id, version, kind, sha256, text, bytes: retained};
  }).sort((a, b) => a.id < b.id ? -1 : a.id > b.id ? 1 : 0);
  check(new Set(rows.map(r => r.id)).size === rows.length, 'Duplicate source ID');
  const indices = new Map(rows.map((r, i) => [r.id, i]));
  check(Array.isArray(requests), 'Invalid package requests');
  const ordered = freeze(requests.map(request => {
    check(indices.has(request.sourceId), 'Missing requested source');
    check(['kernel', 'package'].includes(rows[indices.get(request.sourceId)].kind), 'Invalid package request kind');
    return freeze({sourceId: request.sourceId, options: strings(request.options ?? [])});
  }));
  const snapshot = createSourceSnapshot(rows.map(({id, version, text}) => ({id, version, text})));
  const encodedKey = JSON.stringify([PACKAGE_SOURCE_ABI, engineIdentity, initialStateIdentity,
    rows.map(r => [r.id, r.version, r.kind, r.sha256]), ordered.map(r => [r.sourceId, r.options])]);
  const cacheKey = 'sha256:' + hash(encodedKey);
  const sourceTable = freeze({schema: 1, revision: snapshot.revision,
    ids: freeze(rows.map(r => r.id)), versions: freeze(rows.map(r => r.version)),
    texts: freeze(rows.map(r => r.text)), hashes: freeze(rows.map(r => r.sha256))});

  function context() {
    const occurrences = [], occurrenceIds = new WeakMap();
    const origins = [], originIds = new WeakMap();
    const occurrenceIndex = value => {
      check(occurrenceIds.has(value), 'Foreign source occurrence'); return occurrenceIds.get(value);
    };
    const originIndex = (value, role) => {
      check(originIds.has(value) && (!role || value.role === role), 'Foreign or wrong-role origin');
      return originIds.get(value);
    };
    function enter(sourceId, includeOrigin = null) {
      check(indices.has(sourceId), `Missing explicit source: ${sourceId}`);
      const source = indices.get(sourceId);
      const via = includeOrigin === null ? -1 : originIndex(includeOrigin, 'include');
      let ancestor = via < 0 ? -1 : includeOrigin.occurrence;
      let depth = 0;
      while (ancestor >= 0) {
        check(occurrences[ancestor].source !== source, 'Cyclic source include');
        check(++depth < 32, 'Source include nesting limit');
        const previous = occurrences[ancestor].via;
        ancestor = previous < 0 ? -1 : origins[previous].occurrence;
      }
      const result = freeze({source, via});
      occurrenceIds.set(result, occurrences.length); occurrences.push(result); return result;
    }
    /** These are declared preparation origins, NOT authenticated producer output.
     * Include = caller's directive span; definition = original replacement source;
     * invocation = authored call; argument = actual argument, linked to that call.
     * Definition and invocation must never be collapsed into the same source span.
     */
    function origin(occurrence, start, stop, role = 'literal', links = {}) {
      const occurrenceId = occurrenceIndex(occurrence), row = rows[occurrence.source];
      check(['literal', 'include', 'definition', 'invocation', 'argument'].includes(role), 'Invalid origin role');
      check(integer(start) && integer(stop) && start < stop && stop <= row.bytes.length, 'Invalid original byte span');
      const boundary = n => n === row.bytes.length || (row.bytes[n] & 0xc0) !== 0x80;
      check(boundary(start) && boundary(stop), 'Split UTF-8 scalar');
      const definition = links.definition === undefined ? -1 : originIndex(links.definition, 'definition');
      const invocation = links.invocation === undefined ? -1 : originIndex(links.invocation, 'invocation');
      check(role === 'invocation' ? definition >= 0 : definition < 0, 'Definition link required only on invocation');
      check(role === 'argument' ? invocation >= 0 : true, 'Argument needs invocation');
      check(role === 'argument' || role === 'invocation' || invocation < 0, 'Unexpected invocation link');
      if (role === 'argument') check(origins[invocation].occurrence === occurrenceId, 'Argument occurrence differs from invocation');
      const result = freeze({source: occurrence.source, occurrence: occurrenceId, start, stop, role, definition, invocation});
      originIds.set(result, origins.length); origins.push(result); return result;
    }
    function textAt(value) {
      originIndex(value); return rows[value.source].bytes.subarray(value.start, value.stop).toString('utf8');
    }
    function unsupported(value, primitive, requirement) {
      originIndex(value);
      check(nonempty(primitive) && nonempty(requirement), 'Missing unsupported primitive detail');
      check(textAt(value) === '\\' + primitive, 'Diagnostic primitive differs from source span');
      const source = rows[value.source];
      return freeze({code: 'TEX_PACKAGE_PRIMITIVE_UNSUPPORTED', primitive, requirement,
        sourceId: source.id, sha256: source.sha256, startByte: value.start, stopByte: value.stop,
        occurrence: value.occurrence, sourceRevision: snapshot.revision});
    }
    function interpret() {
      const error = new Error('Package execution requires a stateful token/namespace/scoping ABI; source preparation cannot execute packages');
      error.code = 'TEX_PACKAGE_INTERPRETER_UNAVAILABLE'; throw error;
    }
    return freeze({enter, origin, textAt, unsupported, interpret,
      exportOrigins: () => freeze({schema: 1, revision: snapshot.revision,
        occurrences: freeze([...occurrences]), origins: freeze([...origins])})});
  }
  return freeze({abi: PACKAGE_SOURCE_ABI, snapshot, cacheKey, requests: ordered, sourceTable,
    // Copies only: callers cannot mutate the retained hash-bound source buffers.
    bytes: id => { check(indices.has(id), 'Unknown source ID'); return Buffer.from(rows[indices.get(id)].bytes); },
    context});
}
