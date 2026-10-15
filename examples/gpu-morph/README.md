# Live GPU morphology — optimization checkpoint,2026-10-15

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

Matching is O(N²), with serial source order and parallel candidate reduction,
not optimal transport.
Field solve is O(N × grid² × iterations); drawing also depends on pixel coverage.
The benchmark must therefore hold viewport and solver quality fixed when comparing
object counts. The measurements below are bounded hardware evidence, not a universal10ms guarantee. Software
adapters are rejected publicly; localhost ?validation permits clearly labelled
SwiftShader correctness tests. Physical browser tests were explicitly resumed by
the owner, then stopped again after a new driver fault; see below.

This baseline is NOT parity with the offline research solver: topology, collision,
branching, monotonic mass/area/count and affine-priority guarantees remain unported.
The source and target fields deform geometrically; this is not opacity crossfade.
A fast result here is not evidence that the final constrained solver is fast.

Run tests/gpu-morph-browser.mjs from the site repository with
VKF_PLAYWRIGHT_MODULE pointing to Playwright and a local server on127.0.0.1:8857.
It validates GPU code via explicit software Vulkan, arbitrary-phase reversibility,
resident endpoint data, fresh solve on every frame, scene editing, responsive
widths and the five-size sweep. Software timings are never hardware results.

## Measured optimization result

The research candidate is retained here; the public preview remains at its
previous implementation. No VKF compiler/runtime integration or acceptance is
claimed. Measurements use standalone Chrome WebGPU on a physical NVIDIA GT1030,
Pascal, driver580.178.04, fallback=false, timestamp queries enabled. Same1200×760
render size,32×32 field grid,12 iterations and full fresh solve each frame.
The paired comparison has4warmups+12measured frames per scene/implementation;
these short samples are exploratory, not reliable production tail-latency bounds.
The earlier standalone baseline used8warmups+32measurements. Timings vary with
GPU clocks and scheduling; prefer paired results in research/gt1030-comparison.json.

| Scene | Bodies | Original wall median | Candidate wall median | Candidate GPU median | Candidate wall p95 |
|---|---:|---:|---:|---:|---:|
| Mixed math |52|6.2ms|5.3ms|0.37ms|5.5ms|
| Mixed math |247|26.4ms|5.3ms|1.12ms|7.0ms|
| Mixed math |507|71.7ms|5.2ms|2.51ms|6.4ms|
| Mixed math |1014|257.8ms|9.7ms|6.01ms|9.8ms|
| Longer equations |1012|254.3ms|11.0ms|6.33ms|11.7ms|
| Geometry |1014|247.5ms|10.8ms|6.66ms|10.9ms|

Wall time includes command submission, completion and timestamp readback. The
roughly4ms measurement/synchronization floor is not a proven unavoidable runtime
cost. No actual display FPS or iPhone timing is claimed. GPU work is below10ms in
these samples; total time exceeds10ms for the largest long-math and geometry cases.
None of this adds the still-missing full topology/collision/material constraints.

## What changed, with research basis

1. **Cooperative exact assignment.** Profiling found about224ms in serial
   assignment at1014bodies. Parallel minimum reductions preserve source order and
   lowest-target-index tie-breaking. Optional WebGPU subgroups reduce synchronization;
   a64-lane workgroup reduction is the portable GPU fallback. Subgroup slots are
   allocated by elected leaders, never inferred from local invocation ordering.
   Basis: [Mark Harris, Optimizing Parallel Reduction](https://developer.download.nvidia.com/assets/cuda/files/reduction.pdf),
   [WGSL subgroup semantics](https://www.w3.org/TR/WGSL/#subgroup-builtin-functions).
2. **Tiled pair costs.** Descriptor storage is transposed, and a16×16 pair tile
   shares each64-sample descriptor across16 comparisons. Arithmetic order and cost
   definition stay unchanged. Basis: [NVIDIA shared-memory/coalescing guidance](https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/index.html#shared-memory).
3. **Factor out invariant field terms.** Gradient, residual and denominator are
   computed once per frame, then reused by the12 iterations. This is within-frame
   common-subexpression reuse, not a cached transition. Basis: the fixed derivative
   terms in [Horn and Schunck's iterative formulation](https://doi.org/10.1016/0004-3702(81)90024-2).
   This implementation applies that style of regularization to local distance fields;
   it is not claimed to reproduce the paper's complete optical-flow method.
4. **Shared-memory Jacobi solve.** One workgroup owns a32×32 body field, retaining
   both ping-pong states in16KiB shared memory through all iterations. Other grid
   sizes use the equivalent multi-dispatch path. No iteration or precision reduction.
5. **Exact affine-only recognition.** When matched object-space field definitions
   are identical, their residual is exactly zero and zero flow is a fixed point.
   Skip deformation, while retaining interpolated placement, scale and colour.
   This is derived from the current equations, not a label-specific or letter-specific
   shortcut. It does not add a general rotation-registration algorithm.

## Rejected algorithmic candidate

research/deferred.wgsl and deferred-engine.mjs retain a bounded parallel
proposal/rejection experiment inspired by [Gale and Shapley1962](https://doi.org/10.1080/00029890.1962.11989827).
Sources rank targets by (cost,target index); all targets rank sources by source
index. With these common target priorities, a complete stable matching equals
source-ordered greedy: source0 must receive its first choice, and induction applies
to the remaining market. This equivalence is our application-specific deduction,
not a minimum-total-transport guarantee. After16rounds an exact greedy fallback
ensures completion. It passed observed equality tests but failed to converge within
the budget on the representative scenes and increased their frame cost. It is
therefore excluded from the selected implementation. Preserve it as rejected
performance evidence, not as the new default.

## Correctness evidence and reproduction

-18paired scene/tie cases: exact assignment equality, max flow error0 and max
 rendered byte difference0 in the recorded comparisons.
-48independent cost-matrix fixtures: random, quantized, all-tied, unique, chained
 and near-ULP costs at sizes1/17/63/64/65/127/256/1024. CPU reference exists only in
 tests; the runtime does not read back matches or use CPU correspondence.
-36additional random-placement/scale flow/render comparisons across phases
 0/.17/.5/.83/1/.17, grid16/32 and iteration counts1/4/7/12/32. Recorded max errors0.
-Native subgroup path passed; the portable GPU path passed under explicit
 SwiftShader. Physical portable-path acceptance is pending after the fault below.
-Input checks bound grid/iterations to1–32 and reject nonfinite endpoint packets.

reference/ preserves the original engine/shader as an independent oracle.
validate.mjs runs only explicit software Vulkan; it cannot accidentally choose
physical hardware. Start a local server for the public site (including the GPU math
atlas), then set VKF_PLAYWRIGHT_MODULE to Playwright's module and run:

```bash
NO_SUBGROUPS=1 LIBGL_ALWAYS_SOFTWARE=1 node examples/gpu-morph/validate.mjs
```

VKF_PREVIEW_URL defaults to http://127.0.0.1:8857/previews/gpu-morph/.
VKF_RESULTS_DIR chooses a results directory; otherwise a fresh/tmp directory is
created. Software times are not hardware performance results. Engine declarations
in the website are overridden by the test's explicit reference/candidate modules.

## Hardware stop and evidence boundary

A new NVIDIA Xid appeared during the next portable-path browser setup, before
"engines ready". That run did not complete; its failure is preserved. All earlier
recorded candidate and native-quality runs finished with no new Xid. Testing
stopped, browser processes exited, and no reset/reboot/driver unload was performed.
Cause is unknown; do not attribute it to the new kernels, or declare them harmless.
The planned longer64-sample timing run did not execute. Do not rerun physical tests
until the owner explicitly resumes hardware diagnosis/testing.

Private evidence: Cuvami staging/artifacts/gpu-morph-browser-20261015/optimization/,
including per-variant results, stage profiles, scripts and hardware-stop receipt.
Kernel reports remain private/local; only sanitized measurements are copied here.
Old VKF fault evidence and stop markers remain intact. Source correctness and the
successful timing samples do not establish driver health or production readiness.

## Vektor Flow integration contract

Keep this as a standalone backend experiment until the VKF GPU lane supports it.
Use the compiler's typed arena/resource boundaries rather than embedding a second
language runtime. Required inputs and responsibilities:

-Endpoint Item is64bytes: rect vec4f, atlas UV vec4f, colour vec4f, field info vec4f.
 Inputs are two equally padded arrays,1–1024 bodies, with a resident field atlas.
 Endpoint typesetting/layout/upload happens on edits; all matching/flow remains GPU.
-Params is32bytes: count:u32, grid:u32, phase:f32, iterations:u32, viewport:vec2f,
 reserved:vec2f. Only this control block changes during playback.
-Dispatch dependencies: descriptor → tiled cost → exact assignment → coefficient
 field → local Jacobi or portable ping-pong → signed-distance draw. Storage hazards
 must retain this order. There is no CPU correspondence readback in that path.
-Current requirements: eight storage bindings,16KiB workgroup memory,256invocations,
 atlas size4096×8192. Subgroups and timestamp-query are optional features. Match the
 atlas provenance/licensing and shader's signed-distance convention.
-Own resource lifetime, revision and device-loss handling in the VKF host adapter.
 Reuse buffer capacities and asynchronous timing-readback slots when integrating;
 the prototype currently reallocates on endpoint edits and awaits diagnostic fences.
 Keep queue depth bounded and distinguish GPU duration, submission cost and display
 cadence. Avoid a cached-plan shortcut in the fresh-frame acceptance benchmark.
-Retain reference output checks, adversarial tie cases, capability fallback tests,
 actual-device scaling curves and all fault evidence. Add affine registration,
 topology/material/collision constraints as separately measured quality milestones.
-The10ms target must be remeasured after each added constraint and on presenter and
 phone hardware. These findings do not certify VKF runtime/compiler GPU acceptance.
