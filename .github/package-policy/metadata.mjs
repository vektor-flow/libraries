// Shared, network-free metadata contract. Git commits version source; numeric ranges constrain the compiler.
export const FORMAT = 'vkf-source-json-v1';
export const MAX_BYTES = 8 * 1024 * 1024;
export const MAX_FILES = 2048;
export const ID = /^[a-z][a-z0-9-]*\/[a-z][a-z0-9-]*$/;
export const MODULE = /^[a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*$/;
export const SHA = /^[0-9a-f]{40}$/;
export function gitRef(value) {
  if (typeof value !== 'string' || value.length > 200 || !/^[a-zA-Z0-9][a-zA-Z0-9_./-]*$/.test(value) ||
      value.includes('..') || value.includes('//') || value.endsWith('/') || value.endsWith('.lock')) fail('invalid Git ref');
  return value;
}
export function requirement(value, id) {
  keys(value, ['ref', 'subdirectory'], 'Git dependency'); gitRef(value.ref);
  if (value.subdirectory !== undefined) relativeFile(value.subdirectory);
  return {ref: value.ref, subdirectory: value.subdirectory ?? `packages/${id}`};
}
export const fail = message => { throw new Error(`VKF packages: ${message}`); };
export function object(value, label) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) fail(`invalid ${label}`);
  return value;
}
export function keys(value, allowed, label) {
  object(value, label);
  for (const key of Object.keys(value)) if (!allowed.includes(key)) fail(`unsupported ${label} field ${key}`);
}
export function version(text) {
  if (typeof text !== 'string' || !/^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$/.test(text)) fail(`unsupported version ${text}`);
  const parts = text.split('.').map(Number);
  if (!parts.every(Number.isSafeInteger)) fail(`version out of range ${text}`);
  return parts;
}
export function compare(a, b) {
  const x = version(a), y = version(b);
  for (let i = 0; i < 3; i++) if (x[i] !== y[i]) return x[i] < y[i] ? -1 : 1;
  return 0;
}
export function range(text) {
  if (typeof text !== 'string' || !text || text.trim() !== text) fail(`unsupported range ${text}`);
  if (text.startsWith('^')) {
    const lower = text.slice(1), p = version(lower);
    const upper = p[0] ? `${p[0] + 1}.0.0` : p[1] ? `0.${p[1] + 1}.0` : `0.0.${p[2] + 1}`;
    version(upper);
    return v => compare(v, lower) >= 0 && compare(v, upper) < 0;
  }
  if (/^[0-9]/.test(text)) { version(text); return v => compare(v, text) === 0; }
  const terms = text.split(' ');
  const predicates = terms.map(term => {
    const m = /^(>=|<=|>|<)(.+)$/.exec(term);
    if (!m) fail(`unsupported range ${text}`);
    version(m[2]);
    return v => ({'>=': c => c >= 0, '<=': c => c <= 0, '>': c => c > 0, '<': c => c < 0})[m[1]](compare(v, m[2]));
  });
  return v => predicates.every(test => test(v));
}
export function dependencies(value) {
  object(value, 'dependencies');
  for (const [id, wanted] of Object.entries(value)) { if (!ID.test(id)) fail(`invalid package id ${id}`); requirement(wanted, id); }
  return value;
}
export function relativeFile(name) {
  if (typeof name !== 'string' || name.length > 240 || !/^[a-zA-Z0-9_./-]+$/.test(name) ||
      name.split('/').some(s => !s || s === '.' || s === '..' || s.startsWith('.')) || name.includes('//')) fail(`unsafe archive path ${name}`);
  return name;
}
export function manifest(m) {
  keys(m, ['schema', 'name', 'version', 'compiler', 'targets', 'dependencies', 'exports', 'entry'], 'package manifest');
  if (m.schema !== 2 || typeof m.name !== 'string' || !ID.test(m.name)) fail('invalid package manifest identity');
  if (m.version !== undefined && (typeof m.version !== 'string' || !/^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,63}$/.test(m.version))) fail('invalid optional human version label');
  range(m.compiler); dependencies(m.dependencies);
  if (!Array.isArray(m.targets) || !m.targets.length || new Set(m.targets).size !== m.targets.length ||
      !m.targets.every(t => ['wasm', 'native'].includes(t))) fail(`invalid targets for ${m.name}`);
  if (m.entry !== undefined) { relativeFile(m.entry); if (!m.entry.endsWith('.vkf')) fail('invalid package entry'); }
  object(m.exports, 'exports');
  if (!Object.keys(m.exports).length) fail(`empty exports for ${m.name}`);
  for (const [name, file] of Object.entries(m.exports)) {
    if (!MODULE.test(name)) fail(`invalid ordinary module export ${name}`);
    relativeFile(file);
    if (!file.startsWith('src/') || !file.endsWith('.vkf')) fail(`export ${name} must name src/*.vkf`);
  }
  return m;
}
export function registryConfig(r) {
  if (r?.kind === 'directory') {
    keys(r, ['kind', 'path', 'repository', 'ref'], 'directory registry');
    repository(r.repository); gitRef(r.ref);
    if (typeof r.path !== 'string' || !r.path || r.path.startsWith('/') || r.path.includes('\\') || r.path.includes(':') || r.path.includes('\0')) fail('registry path must be relative');
  } else if (r?.kind === 'github') {
    keys(r, ['kind', 'repository', 'ref'], 'GitHub registry');
    repository(r.repository);
    gitRef(r.ref);
  } else fail('unsupported registry kind');
  return r;
}
export function project(p) {
  keys(p, ['schema', 'compiler', 'entry', 'registry', 'dependencies'], 'project');
  if (p.schema !== 2) fail('unsupported project schema');
  range(p.compiler); relativeFile(p.entry);
  if (!p.entry.startsWith('src/') || !p.entry.endsWith('.vkf')) fail('project entry must name src/*.vkf');
  registryConfig(p.registry); dependencies(p.dependencies);
  return p;
}
export function repository(value) {
  if (typeof value !== 'string' || !/^[a-zA-Z0-9][a-zA-Z0-9_-]*\/[a-zA-Z0-9][a-zA-Z0-9_.-]*$/.test(value)) fail('invalid repository identity');
}
export function record(r, id) {
  keys(r, ['schema', 'package', 'source', 'archive'], 'Git source record');
  if (r.schema !== 2) fail('old prerelease records/locks require explicit schema-2 migration and update');
  manifest(r.package);
  if (r.package.name !== id) fail(`record identity mismatch for ${id}`);
  keys(r.source, ['repository', 'commit', 'subdirectory', 'tree'], 'source identity');
  repository(r.source.repository); relativeFile(r.source.subdirectory);
  if (!SHA.test(r.source.commit) || !SHA.test(r.source.tree)) fail(`missing exact Git commit/tree for ${id}`);
  const a = r.archive;
  keys(a, ['format', 'sha256', 'size'], 'normalized source cache identity');
  if (a.format !== FORMAT || typeof a.sha256 !== 'string' || !/^[a-f0-9]{64}$/.test(a.sha256) || !Number.isSafeInteger(a.size) || a.size <= 0 || a.size > MAX_BYTES) fail(`invalid archive identity for ${id}`);
  return r;
}
export function canonical(value) {
  if (Array.isArray(value)) return '[' + value.map(canonical).join(',') + ']';
  if (value && typeof value === 'object') return '{' + Object.keys(value).sort().map(k => JSON.stringify(k) + ':' + canonical(value[k])).join(',') + '}';
  return JSON.stringify(value);
}
export function bundle(value, expectedManifest) {
  keys(value, ['schema', 'manifest', 'files'], 'source archive');
  if (value.schema !== 1) fail('unsupported source archive');
  manifest(value.manifest);
  if (expectedManifest && canonical(value.manifest) !== canonical(expectedManifest)) fail('archive manifest differs from trusted version record');
  object(value.files, 'source archive files');
  const names = Object.keys(value.files);
  if (!names.length || names.length > MAX_FILES) fail('invalid archive file count');
  for (const name of names) {
    relativeFile(name);
    if (!(name.startsWith('src/') && name.endsWith('.vkf')) && !['README.md', 'LICENSE'].includes(name)) fail(`unsupported package file ${name}`);
    if (typeof value.files[name] !== 'string' || value.files[name].includes('\0')) fail(`invalid source text ${name}`);
  }
  if (!Object.hasOwn(value.files, 'LICENSE')) fail('package LICENSE is required');
  for (const file of Object.values(value.manifest.exports)) if (!Object.hasOwn(value.files, file)) fail(`missing exported file ${file}`);
  return value;
}
export function decode(bytes) {
  if (!(bytes instanceof Uint8Array) || bytes.byteLength > MAX_BYTES) fail('source data exceeds byte limit');
  return JSON.parse(new TextDecoder('utf-8', {fatal: true}).decode(bytes));
}
export async function digest(bytes) {
  return Array.from(new Uint8Array(await globalThis.crypto.subtle.digest('SHA-256', bytes)), b => b.toString(16).padStart(2, '0')).join('');
}
export async function verifiedBundle(bytes, r) {
  record(r, r?.package?.name);
  if (bytes.byteLength !== r.archive.size || await digest(bytes) !== r.archive.sha256) fail(`archive checksum/size mismatch for ${r.package.name}`);
  return bundle(decode(bytes), r.package);
}
export function validateGraph(lock, p, compiler, target) {
  project(p);
  keys(lock, ['schema', 'project', 'compiler', 'target', 'packages', 'resolutions'], 'lock');
  version(compiler);
  if (!['wasm', 'native'].includes(target)) fail('unsupported target');
  if (lock.schema !== 2 || canonical(lock.project) !== canonical(p) || lock.compiler !== compiler || lock.target !== target) fail('lock does not match project/compiler/target; use explicit update');
  if (!range(p.compiler)(compiler)) fail(`project requires compiler ${p.compiler}`);
  object(lock.packages, 'locked packages');
  if (Object.keys(lock.packages).length > 256) fail('locked graph exceeds 256 packages');
  object(lock.resolutions, 'locked ref resolutions');
  const usedResolutions = new Set();
  const visited = new Set(), pending = Object.entries(p.dependencies).map(([id, wanted]) => [id, wanted, 'project']);
  while (pending.length) {
    const [id, wanted, via] = pending.pop(), r = lock.packages[id];
    if (!r) fail(`lock missing ${id} required by ${via}`);
    record(r, id);
    const q = requirement(wanted, id);
    const key = canonical([id, q.ref, q.subdirectory]);
    const resolved = lock.resolutions[key]; usedResolutions.add(key);
    if (!SHA.test(resolved) || (SHA.test(q.ref) && q.ref !== resolved) || r.source.commit !== resolved ||
        r.source.subdirectory !== q.subdirectory || r.source.repository !== p.registry.repository) fail(`locked Git identity conflicts for ${id} required by ${via}`);
    if (!range(r.package.compiler)(compiler) || !r.package.targets.includes(target)) fail(`locked ${id} incompatible with compiler/target`);
    if (visited.has(id)) continue;
    visited.add(id);
    for (const [dep, requirement] of Object.entries(r.package.dependencies)) pending.push([dep, requirement, `${id}@${r.source.commit}`]);
  }
  for (const id of Object.keys(lock.packages)) if (!visited.has(id)) fail(`lock has unreachable package ${id}`);
  for (const key of Object.keys(lock.resolutions)) if (!usedResolutions.has(key)) fail('lock has unreachable ref resolution');
  const exports = new Set();
  for (const r of Object.values(lock.packages)) for (const name of Object.keys(r.package.exports)) {
    if (exports.has(name)) fail(`duplicate module export ${name}`); exports.add(name);
  }
  return lock;
}
