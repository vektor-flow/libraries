// Pure trusted-base policy. Shared with the repository check; no PR-supplied
// owner list, CODEOWNERS interpretation, network, or code execution.
import {fail, keys, ID, relativeFile} from './metadata.mjs';
const LOGIN = /^[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,38})$/;
const equal = (a, b) => a.toLowerCase() === b.toLowerCase();
export function ownerPolicy(p) {
  keys(p, ['schema', 'maintainers', 'packages'], 'owner policy');
  if (p.schema !== 1 || !Array.isArray(p.maintainers) || !p.maintainers.length) fail('invalid trusted maintainers');
  function logins(values) {
    if (!Array.isArray(values) || !values.length || !values.every(v => typeof v === 'string' && LOGIN.test(v)) || new Set(values.map(v => v.toLowerCase())).size !== values.length) fail('invalid owner identities');
  }
  logins(p.maintainers);
  if (!p.packages || typeof p.packages !== 'object' || Array.isArray(p.packages)) fail('invalid package ownership');
  for (const [id, owners] of Object.entries(p.packages)) { if (!ID.test(id)) fail('invalid owned package id'); logins(owners); }
  return p;
}
export function authorizePackage(p, actor, id) {
  ownerPolicy(p);
  if (typeof actor !== 'string' || !LOGIN.test(actor) || !ID.test(id)) fail('invalid authenticated actor/package');
  if (!Object.hasOwn(p.packages, id)) fail(`package ${id} requires maintainer-controlled registration before upload`);
  if (!p.packages[id].some(owner => equal(owner, actor)) && !p.maintainers.some(owner => equal(owner, actor))) fail(`authenticated actor is not an owner of ${id}`);
}
export function authorizeChanges(p, actor, files) {
  ownerPolicy(p);
  if (typeof actor !== 'string' || !LOGIN.test(actor) || !Array.isArray(files) || !files.length || files.length > 3000) fail('invalid actor/change list');
  const maintainer = p.maintainers.some(v => equal(v, actor));
  for (const item of files) {
    if (!item || typeof item !== 'object' || typeof item.filename !== 'string') fail('invalid changed-file metadata');
    // Inspect BOTH paths of a rename, never allow moving another owner's file.
    for (const name of [item.filename, item.previous_filename].filter(v => v !== undefined)) {
      if (typeof name !== 'string' || name.includes('\\') || name.startsWith('/') || name.split('/').some(v => !v || v === '.' || v === '..')) fail('unsafe changed path');
      if (name.startsWith('packages/')) {
        const parts = name.split('/'), id = `${parts[1]}/${parts[2]}`;
        relativeFile(name);
        if (!ID.test(id) || parts.length < 4) fail('invalid package path');
        if (!Object.hasOwn(p.packages, id)) { if (!maintainer) fail('new package requires trusted maintainer'); }
        else authorizePackage(p, actor, id);
      } else if (!maintainer) fail('ownership/policy/repository changes require a trusted maintainer');
    }
  }
  return {authorized: true, actor, maintainer, changedFiles: files.length};
}
