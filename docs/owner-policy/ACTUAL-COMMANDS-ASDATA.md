# Actual-only commands — data; unrun by source e1875

The sole admitted actual runner may execute these at a natural job boundary.
No source worker network/test execution is authorized. Preserve original actual
clocks and healthy jobs. Do not run commands with unresolved uppercase values.
Save exact stdout/stderr/exit codes and fresh responses as ordinary evidence;
never save credentials. No force push, auto-merge, PR bypass or direct-main
package write is part of this route.

## 1. Fresh preflight

```bash
export PATH=/home/viktor/.local/bin:$PATH
gh api user --jq '{login,id}'
gh api repos/vektor-flow/libraries --jq '{full_name,private,visibility,default_branch,owner_type:.owner.type,permissions,allow_auto_merge}'
gh api repos/vektor-flow/libraries/branches/main
gh api repos/vektor-flow/libraries/branches/main/protection
gh api repos/vektor-flow/libraries/rulesets
gh api --paginate 'repos/vektor-flow/libraries/collaborators?affiliation=all&per_page=100' --jq '.[]|{login,role_name,permissions}'
gh api repos/vektor-flow/libraries/actions/permissions
gh api repos/vektor-flow/libraries/actions/permissions/workflow
```

Require actual login `svenviktorjonsson`, exact existing public target/admin,
main current parent and platform support for organization branch restrictions.
Audit inherited org/admin/app access as trusted governance: no new permission
grant is needed. Public contributors can fork; do not grant shared-repo write.
Do not change visibility again. Initial base expected from saved evidence:
`68d103b494e6434161174c5e5095be5500250793`. Reconcile real drift before acting.
Rulesets can strengthen these controls; preserve them. Protection GET 404 is
expected only if genuinely absent; distinguish it from 403/transport failure.

## 2. Tests at frozen code pins

In e1875's frozen libraries checkout:

```bash
node --test tests/package-policy.test.mjs
```

In e1875's frozen compiler checkout (or a clean actual host checkout after the
precise host commit delta is admitted):

```bash
node --test tests/packages/publish.test.mjs
```

These use metadata doubles/temporary local Git fixtures, never live GitHub proof.
Run existing normal host tests if touched imports reveal a new concern. No
renderer/core/native/WASM build is required by this host-only change. Use the
existing normal runner for the later actual package upload/source fetch proof.

## 3. Protect main before package bootstrap

Only if fresh protection is absent and no stronger/conflicting ruleset exists,
independently inspect the frozen initial request, then:

```bash
gh api --method PUT repos/vektor-flow/libraries/branches/main/protection --input docs/owner-policy/initial-main-protection.json
gh api repos/vektor-flow/libraries/branches/main/protection
gh api repos/vektor-flow/libraries/branches/main
gh api repos/vektor-flow/libraries/rulesets
```

The file path above is relative to the frozen libraries checkout. If protection
already exists, first derive a reviewed body preserving every stronger existing
control and unrelated required check. Remove only legacy/advisory ownership
contexts, since they are not owner authorization. Do not replace existing
independent reviews with count zero. API writes must be followed by readback.

Required readback oracle:

- branch protected=true; exact fresh main SHA still the intended parent;
- enforce_admins.enabled=true;
- required_pull_request_reviews is an object, required_approving_review_count=0
  for this initially unprotected single-account route; dismiss_stale_reviews=true;
- no PR bypass allowances for users, teams or apps;
- restrictions.users exactly the intended trusted main merge actors (initially
  `[svenviktorjonsson]`), restrictions.teams/apps empty;
- allow_force_pushes.enabled=false; allow_deletions.enabled=false;
- no required `package-ownership`/advisory context. Preserve unrelated required
  checks and stronger constraints. No enabling auto-merge or bypass;
- current policy maintainers and allowed main writers align after bootstrap.

Do not claim a per-folder ACL or independent reviewer. If the endpoint rejects
these controls, stop the owner-route work with exact error/limit; no fallback to
client-only/optional check enforcement.

A safe direct-push refusal probe can use an empty commit with the *same main tree*
and current main parent: create its commit object via the Git commits API, then
attempt the normal non-force ref update. This changes no package bytes even if a
misconfigured server unexpectedly accepts it. Record the parent/tree first.
The commit object and attempted update are explicit actual remote operations.

```bash
gh api repos/vektor-flow/libraries/git/commits/MAIN_PARENT_SHA
# Write empty-probe.json as JSON: {"message":"Verify protected PR-only main","tree":"EXACT_MAIN_TREE_SHA","parents":["MAIN_PARENT_SHA"]}.
gh api --method POST repos/vektor-flow/libraries/git/commits --input empty-probe.json
# Write probe-ref.json as JSON: {"sha":"RETURNED_EMPTY_COMMIT_SHA","force":false}.
gh api --method PATCH repos/vektor-flow/libraries/git/refs/heads/main --input probe-ref.json
gh api repos/vektor-flow/libraries/branches/main
```

Expected server refusal and unchanged parent. If accepted, the route is NOT
validated: stop, retain exact evidence, reconcile controls. Never test direct
main writes containing package or policy changes. Never force-reset main.

## 4. Normal bootstrap PR from the frozen commit

From the frozen local libraries repository, verify exact commit/ancestry and
remote destination first. `LIBRARIES_FROZEN_SHA` is supplied by root READY.json.
The remote branch below must not already exist; read refs before creating it.

```bash
git merge-base --is-ancestor 68d103b494e6434161174c5e5095be5500250793 LIBRARIES_FROZEN_SHA
gh api repos/vektor-flow/libraries/git/matching-refs/heads/bootstrap/owner-policy-e1875
git push origin LIBRARIES_FROZEN_SHA:refs/heads/bootstrap/owner-policy-e1875
gh pr create --repo vektor-flow/libraries --base main --head bootstrap/owner-policy-e1875 --title 'Establish reviewed library source and maintainer-only PR governance' --body-file BOOTSTRAP_BODY_FILE
```

Write the PR body to an actual file with real newlines. Describe source folders,
trusted base policy, advisory-only workflow, server restrictions, test results,
current head and explicit single-maintainer review limit. No direct main push.

The bootstrap base has no workflow; that is expected. No required ownership
check prevents bootstrap. Main protection must already enforce PR-only and
trusted-maintainer updates. Do not enable a required self-approval review.

## 5. Review current head and merge explicitly

```bash
gh api repos/vektor-flow/libraries/pulls/PR_NUMBER
gh pr diff --repo vektor-flow/libraries PR_NUMBER
```

Inspect the full diff, renamed paths, policy, workflow and package source. Save
the actual inspected head SHA. A GitHub COMMENT review records authenticated
maintainer inspection without pretending to be an independent APPROVE review.
Do not emit this review until the real diff has been inspected.

```bash
# reviewed.json: {"event":"COMMENT","commit_id":"INSPECTED_HEAD_SHA","body":"Maintainer review: inspected this exact head and its complete source/policy/workflow diff. Ready for explicit SHA-bound merge. Single-maintainer review; no independent second reviewer."}
gh api --method POST repos/vektor-flow/libraries/pulls/PR_NUMBER/reviews --input reviewed.json
gh api repos/vektor-flow/libraries/pulls/PR_NUMBER/reviews
# merge.json: {"sha":"INSPECTED_HEAD_SHA","merge_method":"merge"}
gh api --method PUT repos/vektor-flow/libraries/pulls/PR_NUMBER/merge --input merge.json
```

Use an already permitted merge method; preserve linear-history rules if present.
First demonstrate a wrong expected-head refusal: supply an earlier known commit
SHA, distinct from the actual PR head, to the same merge endpoint. Expect 409 or
other explicit head mismatch refusal and unchanged PR/main, not a generic error
misreported as proof. Then merge only the inspected current head. Explicit API
merge with expected SHA is a manual operation, not enabling GitHub auto-merge.

Read back PR merged state/merge commit, main tree, trusted policy and full main
protection. The PR current head SHA, reviewed commit ID and intended merge request
SHA must match. Report actual evidence; stale original PR author is irrelevant.

## 6. Same runner owner update and actual later-head refusal

Admit only e1875's host delta into the existing actual host checkout, preserving
all renderer/current actual changes. Include new package-tools/owner-protection.mjs
when materializing the host tool; no native/wasm rebuild. Run the same normal VKF
runner's existing publish command on a meaningful smoke-source update.

```bash
node package-tools/cli.mjs publish ABSOLUTE_PACKAGE_FOLDER
```

This opens an unmerged source PR and never publishes by itself. Save the result,
proposal tree/commit/parent and exact head. Verify only that package subtree changed.
Make a harmless source-comment update on this proposal branch, producing a new
head. Attempt merge with the earlier inspected SHA: require actual head mismatch
refusal and unchanged main. Inspect the full new head; record a COMMENT review at
that new SHA and explicitly merge it. A prior review does not authorize a newer
head in this route. Re-read merged package bytes and protected main. The existing
normal source-import path should resolve that merged Git commit/subtree; reuse
its established qualification rather than rerun unrelated provider/renderer banks.

An unauthorized distinct actor cannot be live-tested using only one credential.
Do not invent users or credentials, grant another account, or call doubles live.
Record that bounded limit separately from real server refusal/positive PR proof.
If the old source smoke folder already entered main, use a package comment update
for the new owner PR; do not create per-version copies or new canonical assets.
