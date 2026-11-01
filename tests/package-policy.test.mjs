// Metadata doubles only. These are NOT live GitHub actor/control/PR proofs.
import test from 'node:test';
import assert from 'node:assert/strict';
import {inspectOwnership} from '../.github/package-policy/check.mjs';
const repo = 'vektor-flow/libraries', head = '1'.repeat(40), base = '2'.repeat(40);
const policy = {schema: 1, maintainers: ['maintainer'], packages: {'acme/leaf': ['owner']}};
function fixture({sender = 'owner', action = 'synchronize', changedHead = false, changedBase = false,
  finalHeadDrift = false, files = [{filename: 'packages/acme/leaf/src/leaf.vkf'}], changedFiles = files.length} = {}) {
  const calls = [];
  let reads = 0;
  const pr = {number: 7, state: 'open', user: {login: 'owner', id: 11}, changed_files: changedFiles,
    head: {sha: head}, base: {ref: 'main', repo: {full_name: repo}}};
  const event = {action, repository: {full_name: repo}, pull_request: {number: 7, head: {sha: head}},
    sender: {login: sender, id: sender === 'owner' ? 11 : 22, type: 'User'}};
  async function api(endpoint, method = 'GET') {
    calls.push({endpoint, method});
    assert.equal(method, 'GET', 'advisory must never write statuses/reviews/branches');
    if (endpoint.endsWith('/pulls/7')) return {...pr, head: {sha: changedHead || (finalHeadDrift && reads++) ? '3'.repeat(40) : head}};
    if (endpoint === `repos/${repo}`) return {default_branch: 'main'};
    if (endpoint.endsWith('/branches/main')) return {commit: {sha: changedBase ? '4'.repeat(40) : base}};
    if (endpoint.includes('/contents/.vkf/package-owners.json')) return {type: 'file', encoding: 'base64', content: Buffer.from(JSON.stringify(policy)).toString('base64')};
    if (endpoint.includes('/files?')) return files;
    throw new Error('unexpected endpoint ' + endpoint);
  }
  return {api, event, calls};
}
test('legitimate current owner writer is advisory only and never mutates GitHub', async () => {
  const f = fixture();
  const result = await inspectOwnership(f.api, f.event, repo, base);
  assert.equal(result.authorizedEventWriter, 'owner'); assert.equal(result.head, head);
  assert.equal(result.mergeAuthorization, 'SEPARATE_TRUSTED_MAINTAINER_REVIEW_REQUIRED');
  assert(f.calls.every(c => c.method === 'GET'));
});
test('later nonowner pusher cannot inherit original owner PR author identity', async () => {
  const f = fixture({sender: 'intruder'});
  await assert.rejects(inspectOwnership(f.api, f.event, repo, base), /not an owner/);
});
test('queued old head event and changed trusted base fail closed', async () => {
  for (const options of [{changedHead: true}, {changedBase: true}, {finalHeadDrift: true}]) {
    const f = fixture(options);
    await assert.rejects(inspectOwnership(f.api, f.event, repo, base), /stale|base changed|changed during/);
  }
});
test('edited/reopened metadata cannot reauthorize someone else\'s later head', async () => {
  for (const action of ['edited', 'reopened', 'ready_for_review']) {
    const f = fixture({action});
    await assert.rejects(inspectOwnership(f.api, f.event, repo, base), /unsupported/);
  }
});
test('owner cannot alter policy/workflow or hide cross-owner renamed path', async () => {
  for (const files of [[{filename: '.github/workflows/package-ownership.yml'}],
    [{filename: 'packages/acme/leaf/src/new.vkf', previous_filename: '.vkf/package-owners.json'}]]) {
    const f = fixture({files});
    await assert.rejects(inspectOwnership(f.api, f.event, repo, base), /trusted maintainer/);
  }
});
test('maintainer can review governance changes; incomplete diffs refuse', async () => {
  const f = fixture({sender: 'maintainer', files: [{filename: '.vkf/package-owners.json'}]});
  assert.equal((await inspectOwnership(f.api, f.event, repo, base)).authorizedEventWriter, 'maintainer');
  const missing = fixture({changedFiles: 2});
  await assert.rejects(inspectOwnership(missing.api, missing.event, repo, base), /incomplete PR diff/);
});
