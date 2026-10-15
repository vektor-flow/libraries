# Live GPU morphology baseline

This experiment measures scene size against a fresh GPU solve and draw per frame.
It is not a video and does not reuse a precomputed transition. Each frame runs
64-sample field descriptors, all-pairs costs, deterministic greedy correspondence,
regularized field-flow iterations, and signed-distance drawing. JS only submits
commands and uploads32bytes of phase/viewport controls during playback.

CPU work is limited to endpoint math typesetting, scene layout and uploading when
inputs change, UI and command submission. The native GPU math distance-field atlas
is shared with ../gpu-math-typing (including its provenance and license). The
initial atlas download, pipeline compilation and endpoint upload are cold-start
costs, separate from resident-scene frame measurements. Endpoint edits report
layout plus generation wall time separately.

GPU timestamp queries span matching, flow solve and drawing. Buffer clears and
uniform upload precede that timestamp interval; wall time includes submission,
queue completion and timestamp readback. RAF cadence includes display scheduling
and instrumentation. No timestamp support means unavailable, not a substituted
CPU time. The sweep reports16 measured frames after4 warm-ups per scene size;
this is an exploratory measurement, not a statistically robust tail-latency claim.
Scene sizes are rounded down to complete expression copies. Resolution, solver
iterations,32×32 field grid and actual body counts are recorded in gpuMorph.stats.

Matching is O(N²) with a serial GPU greedy assignment, not optimal transport.
Field solve is O(N × grid² × iterations); drawing also depends on pixel coverage.
The benchmark must therefore hold viewport and solver quality fixed when comparing
object counts. It makes no hardware performance or10ms guarantee. Software
adapters are rejected publicly; localhost ?validation permits clearly labelled
SwiftShader correctness tests. No physical host GPU was used.

This baseline is NOT parity with the offline research solver: topology, collision,
branching, monotonic mass/area/count and affine-priority guarantees remain unported.
The source and target fields deform geometrically; this is not opacity crossfade.
A fast result here is not evidence that the final constrained solver is fast.

Run tests/gpu-morph-browser.mjs from the site repository with
VKF_PLAYWRIGHT_MODULE pointing to Playwright and a local server on127.0.0.1:8857.
It validates GPU code via explicit software Vulkan, arbitrary-phase reversibility,
resident endpoint data, fresh solve on every frame, scene editing, responsive
widths and the five-size sweep. Software timings are never hardware results.
