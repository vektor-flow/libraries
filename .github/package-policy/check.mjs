// Advisory only. Server authorization is the protected default branch's
// trusted-maintainer-only PR merge route, never this Actions check's name/app.
// Only trusted base code runs; all PR source is metadata, never executable.
import fs from 'node:fs/promises';
import {pathToFileURL} from 'node:url';
import {githubClient} from './github.mjs';
import {ownerPolicy, authorizeChanges} from './ownership.mjs';
const SHA = /^[0-9a-f]{40}$/;
export async function inspectOwnership(api, event, repo, workflowBase) {
  if (event.repository?.full_name !== repo || !Number.isSafeInteger(event.pull_request?.number) ||
      !['opened', 'synchronize'].includes(event.action)) throw new Error('unsupported ownership event');
  const pr = await api(`repos/${repo}/pulls/${event.pull_request.number}`), meta = await api(`repos/${repo}`);
  const head = pr.head?.sha;
  // Original author is not the authenticated writer of later changes. Bind the
  // GitHub-provided event sender to the exact event/current head, never a newer
  // head fetched by an older queued opened/synchronize workflow.
  if (pr.base?.repo?.full_name !== repo || pr.base.ref !== meta.default_branch || pr.state !== 'open' ||
      !SHA.test(head ?? '') || event.pull_request.head?.sha !== head ||
      (event.after !== undefined && event.after !== head) ||
      !Number.isSafeInteger(event.sender?.id) || event.sender.type !== 'User' ||
      (event.action === 'opened' && event.sender.id !== pr.user?.id)) throw new Error('stale or unauthenticated current-head event');
  const branch = await api(`repos/${repo}/branches/${encodeURIComponent(meta.default_branch)}`), base = branch.commit?.sha;
  if (!SHA.test(base ?? '') || workflowBase !== base) throw new Error('trusted workflow base changed; inspect current base');
  const policyFile = await api(`repos/${repo}/contents/.vkf/package-owners.json?ref=${base}`);
  if (policyFile.type !== 'file' || policyFile.encoding !== 'base64') throw new Error('missing trusted base policy');
  const policy = ownerPolicy(JSON.parse(Buffer.from(policyFile.content, 'base64').toString('utf8')));
  if (!Number.isSafeInteger(pr.changed_files) || pr.changed_files < 1 || pr.changed_files > 3000) throw new Error('changed-file limit/incomplete list');
  const files = [];
  for (let page = 1; page <= 30; page++) {
    const batch = await api(`repos/${repo}/pulls/${pr.number}/files?per_page=100&page=${page}`);
    if (!Array.isArray(batch)) throw new Error('invalid PR file metadata');
    files.push(...batch);
    if (batch.length < 100) break;
  }
  if (files.length !== pr.changed_files) throw new Error('incomplete PR diff');
  authorizeChanges(policy, event.sender.login, files);
  const current = await api(`repos/${repo}/pulls/${pr.number}`);
  const currentBase = await api(`repos/${repo}/branches/${encodeURIComponent(meta.default_branch)}`);
  if (current.head?.sha !== head || currentBase.commit?.sha !== base) throw new Error('PR/base changed during inspection');
  return {advisory: true, authorizedEventWriter: event.sender.login, accountID: event.sender.id,
    head, trustedBase: base, files: files.length, mergeAuthorization: 'SEPARATE_TRUSTED_MAINTAINER_REVIEW_REQUIRED'};
}
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const event = JSON.parse(await fs.readFile(process.env.GITHUB_EVENT_PATH, 'utf8'));
  console.log(JSON.stringify(await inspectOwnership(githubClient(), event, process.env.GITHUB_REPOSITORY, process.env.GITHUB_SHA)));
}
