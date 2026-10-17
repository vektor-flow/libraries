FOUR ORIGINAL PYTHON NATIVE TOKEN TESTS — GUARDED ADAPTER PREPARATION
2026-10-17. No native/compiler execution has occurred in this preparation.

adapter.py imports the pinned original test_native_vkf.py. Its four test methods
and check_tokens are the original function objects, unchanged. Only class setup,
teardown and tokens child launching/parsing are overridden. Setup never compiles
or creates a TemporaryDirectory; teardown never deletes evidence. The original
class-level environment skip is disabled only on the derivative class. Runtime
success requires exactly4 executed tests, zero skips,9 native calls and posthashes.

preparation.json pins original Python source, owned-processes.py, D288 compiler,
B318 runtime, normalizer and shared stdlib. Local closure is exactly token_dump,
tex_tokens and tex_text (8114 source bytes); io comes from pinned shared stdlib.
No application or compiler implementation is copied from an old worker snapshot.
The binary is deliberately null until the external admitted driver builds it.

EXTERNAL DRIVER SEQUENCE — NOT AUTOMATIC AUTHORIZATION
1. Obtain fresh owner-bound admission covering unique OUTPUT, all pinned inputs,
   environment, retained outputs and limits. Pin preparation.json AND adapter.py.
   An argument or a matching hash is not admission. Run under the existing bounded
   driver/cgroup with3GiB maximum memory,swap0 and owned descendant containment.
2. Materialize each preparation.modules file as OUTPUT/raw/NAME.vkf. Create the
   pinned stdlib symlinks beneath OUTPUT, relative to preparation.environment.VKF_HOME,
   exactly as native-gates/prepare.py plan specifies. Apply the pinned environment
   and unset list; set VKF_COMPILER to preparation.compiler.path. Cwd is OUTPUT.
3. Guarded normalization,<=30 seconds:
   /usr/bin/python3 -B PINNED_NORMALIZER --source-dir OUTPUT/raw --output-dir OUTPUT/normalized
4. Guarded compilation,<=30 seconds:
   PINNED_COMPILER -b OUTPUT/normalized/source/token_dump.vkf -o OUTPUT/token-dump --diagnostics
   Require fresh binary, successful joined compilation and preserved raw evidence.
   Compute its SHA256 and bind it to this exact closure/toolchain/compile receipt.
5. Inside the already admitted bounded driver, with cwd OUTPUT:
   python3 -B ABSOLUTE_ADAPTER run --preparation ABSOLUTE_PREPARATION \
     --preparation-sha256 PREPARATION_SHA256 --binary OUTPUT/token-dump \
     --binary-sha256 BINARY_SHA256 --output-dir OUTPUT
   No compiler or shell is started by the adapter. Its only Popen site launches
   the verified prebuilt binary with file-backed stdin/stdout/stderr and a new
   process session, immediately followed by pinned owned.wait_owned(...,10).
   Parent-driver admission and cgroup containment remain mandatory; the helper's
   documented observation race is not promoted into whole-system custody proof.
6. Review compilation/admission receipts, exact argv/environment/stdin and binary
   hash alongside python-native-evidence/summary.json. Test success does not
   authenticate the external compilation/launch automatically.

EVIDENCE AND FAILURE BEHAVIOR
OUTPUT/python-native-evidence must not exist before the adapter runs. It retains
inputs.json, unittest.log, summary.json and call-01 through call-09 directories.
Every call preserves source.tex, raw stdin/stdout/stderr and receipt.json. The
active changed-after-compilation.tex path is reused across calls, preserving the
original fresh/changed/restored/empty-source test. Encoding is exact UTF-8 bytes.
Binary and fixture hashes are checked before/during/after each call; all pinned
inputs are checked before and after the suite. No file cleanup occurs.
Native runtime deadline is10 seconds; the pinned helper may spend additional
bounded time joining/killing owned descendants. Missing join evidence (including
the helper's early-exit receipt), nonzero exit, timeout, orphan, guard failure,
malformed integer output or original assertion failure cannot pass.
The suite stops at its first error/failure; it never launches later tests after
that boundary. Successful completion still requires all4 original tests.

STATIC SELF-CHECK — NO NATIVE PROCESSES
python3 -B ABSOLUTE_ADAPTER self-check --preparation ABSOLUTE_PREPARATION \
  --preparation-sha256 PREPARATION_SHA256
The self-check verifies input pins, exactly4 collected original methods and
unchanged check_tokens identity. Seven mocked child receipts exercise rejection
of nonzero exit, timeout, failed guard, orphan, unjoined descendants, residual
identities and missing custody metadata. These are not native negative tests.
Preparation self-check passed:4 collected,7 negative controls,0 native launches.

PROSPECTIVE RESOURCE ESTIMATE
Source closure8114 bytes; at most9 native invocations, serial. Reserve1MiB for
normal adapter evidence and32MiB for normalized sources/compiled output as an
initial estimate. These are not measured peaks or permission to allocate. External
admission must account measured retained outputs and compile/runtime resource use;
if inadequate, stop and revise admission rather than widening limits silently.

This qualifies only the four application token tests skipped by the Python
baseline. It is separate from the37 application suites/47 native-gate cases and
from original419 compiler obligations. Original419 credit is always0. No native
performance or compiler0.7.4 release qualification is asserted. D267/D289/A333 and
all previously excluded scopes remain untouched.
