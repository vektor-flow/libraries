// Runs exclusively from trusted base checkout; PR source is never checked out,
// imported, executed or placed on a shell command line. Token can only read
// contents/PR metadata and post the ownership result to the PR head SHA.
import fs from 'node:fs/promises';
import {githubClient} from './github.mjs';
import {ownerPolicy, authorizeChanges} from './ownership.mjs';
const api = githubClient();
const event = JSON.parse(await fs.readFile(process.env.GITHUB_EVENT_PATH, 'utf8'));
const repo = process.env.GITHUB_REPOSITORY;
let head;
try {
  if (event.repository?.full_name !== repo || !event.pull_request?.number) throw new Error('wrong ownership event');
  const pr = await api(`repos/${repo}/pulls/${event.pull_request.number}`), meta = await api(`repos/${repo}`);
  head = pr.head?.sha;
  if (pr.base?.repo?.full_name !== repo || pr.base.ref !== meta.default_branch || pr.state !== 'open' || !/^[0-9a-f]{40}$/.test(head)) throw new Error('wrong PR target/state');
  await api(`repos/${repo}/statuses/${head}`, 'POST', {state: 'pending', context: 'package-ownership', description: 'Checking trusted current-base package ownership'});
  const branch = await api(`repos/${repo}/branches/${encodeURIComponent(meta.default_branch)}`), base = branch.commit?.sha;
  if (!/^[0-9a-f]{40}$/.test(base)) throw new Error('missing trusted base');
  const policyFile = await api(`repos/${repo}/contents/.vkf/package-owners.json?ref=${base}`);
  if (policyFile.type !== 'file' || policyFile.encoding !== 'base64') throw new Error('missing trusted base policy');
  const policy = ownerPolicy(JSON.parse(Buffer.from(policyFile.content, 'base64').toString('utf8')));
  if (!Number.isSafeInteger(pr.changed_files) || pr.changed_files < 1 || pr.changed_files > 3000) throw new Error('changed-file limit/incomplete list');
  const files = [];
  for (let page = 1; page <= 30; page++) {
    const batch = await api(`repos/${repo}/pulls/${pr.number}/files?per_page=100&page=${page}`);
    if (!Array.isArray(batch)) throw new Error('invalid PR file metadata'); files.push(...batch);
    if (batch.length < 100) break;
  }
  if (files.length !== pr.changed_files) throw new Error('incomplete PR diff');
  authorizeChanges(policy, pr.user?.login, files);
  const current = await api(`repos/${repo}/pulls/${pr.number}`);
  const currentBase = await api(`repos/${repo}/branches/${encodeURIComponent(meta.default_branch)}`);
  if (current.head?.sha !== head || currentBase.commit?.sha !== base || current.user?.id !== pr.user?.id) throw new Error('PR/base changed during check; rerun against current state');
  await api(`repos/${repo}/statuses/${head}`, 'POST', {state: 'success', context: 'package-ownership', description: 'PR author authorized by trusted current-base owner policy'});
  console.log(JSON.stringify({authorized: true, actor: pr.user.login, accountID: pr.user.id, head, trustedBase: base, files: files.length}));
} catch (error) {
  if (/^[0-9a-f]{40}$/.test(head ?? '')) await api(`repos/${repo}/statuses/${head}`, 'POST', {state: 'failure', context: 'package-ownership', description: 'Ownership validation failed; inspect trusted workflow log'});
  throw error;
}
