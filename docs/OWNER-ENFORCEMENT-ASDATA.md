# Shared library source PR policy — source only, unrun and undeployed

`packages/<publisher>/<package>` has one maintained source folder. Its single
`vkf.lock` stores settings and generated source-address pins. Merged Git commit
plus subdirectory/tree/content identity is the version. No version folders,
per-version indexes or release assets are required. Personal GitHub imports need
no registration or approval in this shared repository.

`.vkf/package-owners.json` is repository governance, outside consumer metadata.
The current known administrator is `svenviktorjonsson`; no team/account is invented.
Owners initiate normal package updates; maintainers retain administrative source
and ownership-transfer authority. New package registration and changes outside
registered package folders require a trusted maintainer. Owner assignments come
from current trusted base, never the proposed PR or editable package lock.
Both paths of renames are checked. The check authenticates the PR author's GitHub
account; Git author name/email are attribution, not ownership authentication.

The workflow checks out only the trusted base commit, never PR source. It reads
PR metadata and current default-branch ownership. Its token has contents/PR read
and commit-status write only; the latter is needed to put `package-ownership`
on the exact PR head, since pull_request_target otherwise runs on the base.
No untrusted module/tests/scripts execute with this token. Pagination, file
count, PR/head/current-base changes fail closed. Normal up-to-date branch checks
must rerun the status on the updated head when the base changes.

Before claiming enforcement, the actual owner must independently review this
exact workflow/policy, install them through the normal reviewed repository path,
and configure supported protection on the existing default branch:

- Require PRs and the `package-ownership` status, strict/up to date, bound to the
  trusted GitHub Actions app observed in the repository; don't accept a same-name
  status from arbitrary integrations. Preserve stronger existing required checks.
- Enforce for administrators; no review/status bypass allowance, force push or
  deletion. Preserve any stronger existing normal human review settings.
- CODEOWNERS routes review but is not a folder write ACL. The ownership status
  checks the author separately; it never requires an author to approve their own
  PR. With the one presently known maintainer, do not invent a second reviewer
  or configure an impossible required self-approval. A manual maintainer merge
  still follows inspection; add independent reviewers through normal governance.
- Restrict installation of apps that can emit the trusted required context, and
  preserve normal administrator recovery authority as an explicitly audited
  administrative exception. GitHub administrators can always change protections;
  this is not a claim of cryptographic prevention against repository admins.

Observed 2026-11-01 through authenticated read-only APIs: private repository,
default main at 68d103b494e6434161174c5e5095be5500250793, admin/push permissions,
main unprotected. Ruleset GET returned HTTP403 with upgrade/public-visibility
message. Therefore these controls are NOT currently deployed/enforced and may
need a supported private-repository plan. Do not flip visibility or purchase a
plan as part of this source handoff. `vkf publish` refuses before writes if branch
protection/required app-bound owner check is absent. No remote mutation occurred.

Source commands for the actual owner (ASDATA; unrun): inspect repository/branch
protection and app identities with `gh api`, preserve stronger existing settings,
review this commit, then install/check protection through supported GitHub
repository controls. Do not blindly PUT a minimal protection body over stronger
rules. No ready-to-run settings mutation is included because the current API
reports that enforcement is unavailable. A later actual permission/settings
recheck, workflow run and independent review are required before publication.

Later backlog: package format/API standards, real module build/test execution,
function coverage and explicit lists of untested functions. This workflow is the
minimal ownership gate only. It is not evidence of package correctness.
