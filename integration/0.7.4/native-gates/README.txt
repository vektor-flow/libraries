NATIVE37 SHARED-SOURCE GATE PREPARATION — 2026-10-17

This is executable preparation and result assessment, not native execution or a
release qualification. No compile/run is performed by prepare.py. Only the sole
coordinator's external guarded launcher may execute the emitted commands after
fresh resource admission. Existing 30-second per-child ceilings apply to
normalization, compilation and native execution. No budget/guard resets.

From the repository root:
  python3 -B integration/0.7.4/native-gates/prepare.py prepare
  python3 -B integration/0.7.4/native-gates/prepare.py check
  python3 -B integration/0.7.4/native-gates/prepare.py plan --output-root /ABSOLUTE/NEW/ADMITTED/OUTPUT
  python3 -B integration/0.7.4/native-gates/prepare.py assess --receipt /ABSOLUTE/GUARDED/RECEIPT.json

Preparation reads the old integration inventory solely for suite names, stdin,
asset pins and reference authentication. It does NOT invoke the stale historical
driver/config, import its candidate production files or adopt held B347 changes.
Every production dependency comes from the current shared native-vkf directory.
All 110 historical frozen285 reference files match on-disk shared-base hashes.
Reference closure edges must stay frozen or reach pinned external stdlib only.
Any missing input, leaking reference or unresolved assertion entry blocks/fails;
there is no fallback to worker snapshots or implicit import discovery.

manifest.json pins each case's complete source closure, derivative assertion
entry, compiler D288, runtime B318, stdlib, assets and environment. Each generated
entry retains the original suite assertions; main definitions become
native_gate_main and are explicitly called, route test functions are explicitly
asserted, and existing boolean renderer/tests invocations are asserted. Existing
checked run() invocations remain intact. identical_source_to identifies repeated
suite sources; these are not independent correctness evidence.

37 historical suite names produce 47 cases: 35 positive and 12 rejection cases.
F354's root-reviewed pinned control establishes clean assertion exit 1 with exact
stderr message plus newline and empty stdout (no signal/timeout). Each rejection
now carries that explicit contract; normalization and compilation still require
exit 0. Readiness means an inspectable plan, never a native pass.

F355 first execution stopped at the third case, as required: malformed scene and
invalid ID passed exact runtime contracts; document_routes__reject_changed_source
failed compilation with "invalid $ in string" in the retained source. No runtime
for that case, and nine remaining cases were not launched. No unchanged retry.
Its suite contains an unescaped dollar in a positive fixture even in the negative
entry derivative; a separately reviewed fixture adaptation is needed. The shared
production source was not edited. Evidence is retained privately under F's
iteration355-rejections01; root must authenticate receipts before adoption.

External launcher contract:
- Pin manifest.json and every referenced input in a fresh admission. Admit all
  output paths and resource costs using the current owner and cumulative limits.
- Refuse existing output roots. Materialize each case's exact pinned closure and
  derivative under its raw directory; create the specified stdlib symlinks.
- Apply the pinned environment and unset list; use the emitted cwd and exact argv.
- Run normalize, compile, run in dependency order, each with <=30-second owned
  process-tree deadline and descendant joining. A failed stage stops that case.
- Require a new executable before run; capture file-backed stdin/stdout/stderr,
  binary hash, input pre/posthashes, stage exit, elapsed time, timeout and join.
- Do not start any blocked case or retry a failed unchanged boundary. Preserve complete evidence even after failure.

The assess action inspects an UNTRUSTED summary shaped as:
  {"owner":"01a14893-cb1e-7203-97dd-de3da44dcf31",
   "manifest":{"path":"ABSOLUTE manifest.json","sha256":"HASH"},
   "cases":[{"id":"EXACT CASE ID","binary_produced":true,
     "posthash_match":true,
     "normalize":{"exit":0,"timed_out":false,"no_live_descendants":true,"elapsed_seconds":1},
     "compile":{"exit":0,"timed_out":false,"no_live_descendants":true,"elapsed_seconds":1},
     "run":{"exit":0,"timed_out":false,"no_live_descendants":true,"elapsed_seconds":1}}]}
This summary is not authenticated execution evidence or an admission token.
Owner and manifest fields alone are NOT proof of an external guarded launch. Assessment rechecks source/tool pins, rejects foreign manifests and duplicate/
unknown results. It requires normalize/compile exit 0, per-case run exit, exact
pinned runtime output where specified, and no timeout or unjoined descendants.
Assessment ALWAYS exits nonzero, reports execution_verified false and null pass
totals. All apparent successes are explicitly UNVERIFIED. The external controller
receipt, executable hash, actual argv/stdin/source binding and terminal descendant
join still require authenticated coordinator review before any real pass claim.
No external guard evidence verification is implemented here. Blocked cases must
also be resolved before all37 can pass. release_qualified is always false: native37 cannot establish the
original419 compiler suite, full document build, PDF/API correctness or timings.

Static validation only:
  python3 -B integration/0.7.4/native-gates/test_prepare.py
No native child processes are used by these tests.
