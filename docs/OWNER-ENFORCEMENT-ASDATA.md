# Shared library owner route

Status: source candidate only. Tests and remote deployment are unrun here.
The actual runner must record fresh tests, permissions, controls and live PR
proof before marking the route deployed. Saved actual1874 evidence shows the
existing `vektor-flow/libraries` repository is now public, with unchanged main
`68d103b494e6434161174c5e5095be5500250793`. This is not protection/PR proof.

There is one maintained `packages/<publisher>/<package>` source folder. Its
single `vkf.lock` stores settings and pins. A merged Git commit is a published
source version. There are no per-version folders, assets or second registry.
Personal GitHub imports remain independent of shared-library registration.

## The enforceable minimal route

GitHub must require a PR for every main update, including administrators, and
restrict main push/merge permission to the trusted maintainers recorded in
current base `.vkf/package-owners.json`. Initially the only known maintainer and
owner is `svenviktorjonsson`. No teams/apps, PR bypass, force push or deletion are
allowed. Other writers, PR authors, later branch pushers and Actions results
cannot authorize a main update. A trusted maintainer inspects the *current* diff
and explicitly merges with its expected head SHA. GitHub's merge endpoint rejects
a stale expected SHA. After any new head, inspect that head before a new merge.
This is a manual reviewed PR route; neither uploader nor workflow auto-merges.

This is the existing **trusted-maintainer-only merge route**, with maintainers
retaining administrative and owner-assignment authority. It does not promise an
automatic per-folder merge ACL delegated to every registered owner. Registered
owners control their proposals; maintainers review and publish them. Adding an
owner in policy grants no GitHub permission. Owners with existing proposal-branch
write access can use `vkf publish` in the same runner; others can propose a normal
public fork PR. The uploader creates no fork, grants no access and never writes
main. If fully automatic delegated multi-owner merging is later required, this
route is insufficient; do not silently add write accounts or claim that feature.

The server restrictions govern actual publication regardless of the original PR
author or a later writer. Git author/email, CODEOWNERS and a client preflight are
not server authorization. Org/repository administrators remain trusted governance
actors who can change protections: audit them and app grants before deployment;
no solution here claims to prevent a trusted administrator changing governance.

## Honest single-account review

GitHub does not let an author APPROVE their own PR. There is no second known
reviewer. The initial server PR requirement therefore has review count **zero**,
but is a **non-null PR requirement**: direct main pushes must still be refused.
The maintainer reviews the actual diff and records a COMMENT review at its exact
commit, then explicitly merges that SHA. This provides no independent second
person review, and does not claim one. Never configure an impossible required
self-approval or use an administrator/PR bypass to get around it. Preserve any
stronger existing independent review requirement; if it cannot be satisfied with
existing actors, report that precise limitation instead of weakening it.

## Ownership inspection is advisory

The trusted-base workflow has only contents/PR read permission. It checks out
`github.sha`, never PR code, imports no PR modules and writes no commit statuses.
It binds the authentic GitHub event sender to the exact event/current head. An
old queued owner event cannot inspect a later head as though the owner wrote it;
a later nonowner sender fails; metadata edits/reopens cannot reauthorize a head.
The current-base policy and both paths of renames are checked. Head/base changes
or incomplete files fail closed. These are useful review signals, not merge ACLs.

Do **not** require the old `package-ownership` context or the new advisory job as
owner authorization. Arbitrary PR workflows can emit a same-name GitHub Actions
check. Binding to the Actions app does not identify which workflow emitted it.
The protected branch's trusted-maintainer restriction is the authorization
mechanism, independent of any such signal. Retain unrelated stronger build/test
checks and their app binding. No required ownership workflow is installed here.
The uploader refuses the old ownership context so it cannot be mislabeled as an
authorization gate. The former status writer is removed.

## Bootstrap and actual validation

Use [actual commands](owner-policy/ACTUAL-COMMANDS-ASDATA.md) and
[initial protection](owner-policy/initial-main-protection.json), as data only.
The initial body is valid only after fresh readback shows no existing protection
and no conflicting rulesets. If stronger controls exist, preserve them and derive
a reviewed merged request; do not PUT the initial body over them.

1. Read authenticated actor/admin permission, exact public target, default/main
   SHA, protection, rulesets, access and Actions grants. Check the frozen source
   descends from that current main. Stop on unexplained drift or broader actors.
2. Independently inspect the candidate policy and maintainer identity. Install
   main restriction + PR requirement before any package source enters main.
   Verify readback and a safe empty-commit direct-push refusal. No status from
   an undeployed workflow is required, so there is no bootstrap check cycle.
3. Push the frozen candidate to a new proposal branch and open the normal PR.
   Inspect its complete exact-head diff and record the maintainer COMMENT review.
   Demonstrate a wrong expected-head merge refusal, then merge the inspected
   actual SHA. Do not directly push packages or enable auto-merge/bypass.
4. Read back main policy/protection alignment and run the same runner's publisher
   on a meaningful package source update. It must open an unmerged proposal only.
   Inspect the current head. Change its head with a harmless package comment;
   the prior expected SHA must fail to merge. Inspect and merge the new SHA.
5. Verify merged source bytes, one maintained folder, preserved unrelated packages
   and policy/workflow, then resolve the merged commit using the already working
   normal source import route. Record actual commits, review/PR URLs and results.

A distinct unauthorized user's live merge cannot be demonstrated with the single
known authenticated account. Never invent an actor/token or label metadata-double
tests live proof. Record that limitation; actual server restrictions, direct-push
and expected-head refusals establish the available maintainer-only route. If the
platform ignores zero-count PR requirements, restrictions or admin enforcement,
stop and report the precise limit; do not silently weaken the route.

Tests as data: `node --test tests/package-policy.test.mjs` here; in the paired
compiler checkout `node --test tests/packages/publish.test.mjs`. Neither was run
by this source worker. No compiler/C++/WASM/renderer rebuild is needed for the
host-only publisher correction. Preserve current healthy actual jobs and clocks.

Later backlog: function coverage/API standards and module correctness validation.
This ownership route is not evidence of package runtime correctness.
