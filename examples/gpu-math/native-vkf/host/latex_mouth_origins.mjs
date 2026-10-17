// Transport adapter only: does not tokenize, execute TeX, or authenticate native
// custody. Source/occurrence/origin IDs remain package25 IDs, never token ordinals.
import {isDeepStrictEqual} from 'node:util';
const check = (ok, text) => { if (!ok) throw Error(text); };
const fields = ['source', 'occurrence', 'start', 'stop', 'role', 'definition', 'invocation'];
const frozen = value => Object.freeze(value);
export function mouthOriginTable(context) {
  const data = context.exportOrigins();
  check(data.schema === 1, 'Mouth origin schema');
  return frozen({revision: data.revision,
    occurrence_sources: frozen(data.occurrences.map(o => o.source)),
    occurrence_via: frozen(data.occurrences.map(o => o.via)),
    ...Object.fromEntries(fields.map(key => [key, frozen(data.origins.map(o => o[key]))]))});
}

/** Reissue exactly one native lexical origin through the existing context.
 * occurrences MUST be the actual objects returned by context.enter(), in issued
 * order. Caller serializes next()/accept() with all other origin issuers. This
 * function checks transport structure, not a proof of VKF/native execution.
 * Token IDs and origin IDs are distinct; EOF/input-derived zero-width tokens
 * have origin=-1. Preview recovery records are rejected before any issuance.
 */
export function acceptMouthOrigin(context, occurrences, sourceTable, before, result) {
  const current = mouthOriginTable(context);
  check(isDeepStrictEqual(current, before), 'Stale mouth origin prefix');
  const exported = context.exportOrigins();
  check(Array.isArray(occurrences) && occurrences.length === exported.occurrences.length &&
    occurrences.every((o, i) => o === exported.occurrences[i]), 'Foreign mouth occurrences');
  const {state, token, diagnostic, origins: after} = result;
  check(state && token && after && state.revision === before.revision, 'Mouth result revision');
  check([0, 1, 2, 3].includes(diagnostic), 'Mouth diagnostic');
  check(Number.isSafeInteger(token.source) && Number.isSafeInteger(token.occurrence) &&
    token.occurrence >= 0 && token.occurrence < occurrences.length &&
    occurrences[token.occurrence].source === token.source && state.source === token.source &&
    state.occurrence === token.occurrence, 'Mouth source occurrence');
  check([0, 1].includes(token.provenance), 'TEX_PREVIEW_TOKEN_FORBIDDEN');
  check(Number.isSafeInteger(token.start) && Number.isSafeInteger(token.stop) &&
    token.start >= 0 && token.stop >= token.start, 'Mouth span');
  check([0, 1, 2, 3].includes(token.kind), 'Mouth token kind');
  check(sourceTable.schema === 1 && sourceTable.revision === before.revision &&
    typeof sourceTable.texts[token.source] === 'string', 'Mouth source table');
  const raw = Buffer.from(sourceTable.texts[token.source], 'utf8');
  const boundary = n => n === raw.length || (raw[n] & 0xc0) !== 0x80;
  check(token.stop <= raw.length && boundary(token.start) && boundary(token.stop), 'Mouth source span or split UTF-8 scalar');
  check(diagnostic === 0 || token.kind === 0, 'Mouth diagnostic token');
  check(token.kind !== 0 || token.origin === -1, 'Mouth EOF/diagnostic origin');
  if (diagnostic === 0 && token.kind === 0) check(token.start === token.stop && token.stop === raw.length, 'Mouth EOF span');
  const appended = diagnostic === 0 && token.kind !== 0 && token.stop > token.start;
  const index = before.source.length;
  const row = {source: token.source, occurrence: token.occurrence, start: token.start,
    stop: token.stop, role: 'literal', definition: -1, invocation: -1};
  const expected = {...before};
  if (appended) for (const field of fields) expected[field] = [...before[field], row[field]];
  check(isDeepStrictEqual(after, expected), 'Mouth origin suffix differs');
  check(token.origin === (appended ? index : -1), 'Mouth origin ID differs');
  if (!appended) {
    check(token.kind === 0 || token.provenance === 1, 'Zero-width authored token');
    return null;
  }
  // All transport checks precede this sole registry mutation; context enforces
  // exact source bounds and UTF-8 scalar boundaries before issuing the origin.
  return context.origin(occurrences[token.occurrence], token.start, token.stop, 'literal');
}
