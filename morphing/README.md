# Morphing

An optional VKF library for interpolation of states and embeddings. It belongs to
projects that use it; it is not a new standard-library or core-language feature.
Copy `Morphing.vkf` and `morphing/` beside the importing VKF project.

The independent coordinate can represent time or any other ordered quantity.
The result is a callable state function. The renderer continues to own its View,
Embedding and Layer identities. Morphing computes channels and derivatives; it
must not create a parallel scene hierarchy or substitute an image crossfade.

```vkf
m:.Morphing
plan:m.prepare([0,1,2],[0,0,1,2,3,0],2,1,true,true)
at:m.sample[plan:plan]
state:at(0.5)
::state.value
```

`prepare(coordinates, states, width, mode, smooth_start, smooth_end)` accepts
state-major numeric channel storage. Mode `0` is piecewise linear; mode `1` is
natural cubic, minimizing integrated squared parameter curvature. Coordinates
must strictly increase. Two states, or any larger count, use the same API.

`sample(plan, coordinate)` returns `value`, `first`, `second`. These are coordinate
derivatives, not necessarily time derivatives. Endpoint easing independently sets
both derivatives to zero at the selected outer boundaries, keeps all key states
exact, and does not stop at intermediate states. Easing is a separate coordinate
map; its composition does not retain the original curvature-minimization claim.
Natural cubic can overshoot; this does not guarantee monotonicity of all geometric
measurements or interpolation on rotation/manifold constraints.

`weights(plan, coordinate)` supplies shared interpolation weights.
`channel(plan, coordinates, component)` exports a sampled renderer property.
An application-defined embedding can consume `sample` to produce its View data.
`prepare_affine_embedding(...)` / `sample_embedding(...)` additionally interpolate
an affine embedding and the state it maps, including the complete first/second
product-rule derivatives. Each embedding row stores its coefficients then offset.
This optional adapter does not restrict general application embeddings to affine.

`bind_view(view_id, layer_ids, offsets, plan)` binds channel ranges to existing
renderer identities. `sample_view(binding, coordinate)` returns those same IDs
and the sampled channels; it never creates replacement identities. This is an
explicit adapter packet, **not** a counterfeit implementation of the renderer's
native `View` or `Layer` type. Native-handle extraction/application is not yet wired.

`prepare_material(coordinates, offsets, weights, positions, dimension, mode,
smooth_start, smooth_end)` constructs a persistent material carrier through
multiple states with different object counts. Every carrier has a positive,
constant weight and an owner in every state: children split from existing parents
and can merge again. Total measure must agree (relative tolerance 1e-10); numerical
roundoff is normalized to the first state's total. There are no empty/transparent
endpoints and no birth/death fallback. Object ordering is caller-supplied material
correspondence, not automatic spatial or semantic matching. `sample(plan.state,q)`
samples carrier positions; `owners` is state-major and local to each input state.

`reserve_groups(source_count, target_count, source_groups, target_groups, costs)`
reserves the largest unchanged semantic groups first, choosing repeated occurrences
by whole-group cost. Group triples are `[identity, first_member, member_count]`.
This preserves terms such as `4ac` against character-by-character reassignment.
Unresolved entries are `-1` correspondences to plan, never empty visible objects.

`prepare_geometry` creates a connected split/merge cohort from local signed-distance
fields (2D or 3D), embeddings and persistent ownership. `geometry_measure` prepares
endpoint areas/volumes; `sample_geometry` produces geometry with a piecewise
monotone measure target. Coincident carriers at a parent separate geometrically
and rejoin with rounded contact regions. All field evaluation, interpolation,
union, rasterization and scale calibration execute in VKF. `polygon_field` in
`morphing/biological.vkf` constructs fields from contours including holes.

Independent cohorts must use separate plans. Empty objects, missing lineage,
invalid fields, nonpositive interpolated extents, clipped output and failed measure
calibration are rejected. The measure is a sampled-grid integral, not an analytic
solid-volume proof. Exact key-state geometry is retained when its measured endpoint
target is used. For an explicitly constant measure, use `biological.sample` with
that target; this can rescale supplied endpoints if their measures differ.

This is a general implicit-field operation, not a completed port of every prior
shape constraint. Automatic correspondence, collision routing between independent
cohorts, medial thin-stroke guarantees and controlled hole-event scheduling remain
unfinished. Natural cubic field/embedding interpolation can change topology or
overshoot; conservation alone does not certify topology or thickness.

## Verification and integration boundary

`tests/morphing/verify.py --compiler /path/to/vkf --output /new/evidence/path`
builds an independent project and runs the actual native library. SciPy is solely
a test oracle. No Python, JavaScript or handwritten WGSL executes interpolation.
Evidence records the compiler and source hashes. The first successful run used
installed VKF 0.7.3; this does not change the site's pinned 0.7.2 compiler release.

The current native UI packager rejects a root `type_alias` from imported libraries,
and rejects calls constructing a View inside a function. The probes are retained
in Cuvami `staging/artifacts/morphing-library-20261016/probes` and `project/view.vkf`.
Pure VKF compilation/execution succeeds. Direct animated Linux native View
packaging remains **incomplete**, and the old browser matcher is not a fallback.

Canonical WASM is a verified execution route for this same library. A prepared
scene is transported as an immutable canonical value and sampled at arbitrary
runtime coordinates. The browser only transports values and presents native geometry;
no JavaScript implements morph interpolation. `tests/morphing/build_wasm.py`
builds the canonical artifact and checks all eight interpolation/easing settings,
invalid-coordinate recovery and optional real Chromium execution. The source
fixture is `tests/morphing/wasm-demo.vkf`. The loader supplies `dispose()`; it drops
references for garbage collection because the canonical ABI has no explicit release.

The browser geometry path is not realtime: the current three-carrier, holed
fixture takes about 1.4–2.0 seconds per state at 24×24 area calibration, including
native triangle production on a 129×129 lattice. Use asynchronous latest-request handling.
The fast state-core benchmark below does not measure geometric calibration.
Native/WASM comparisons over five full geometric frames agree to 4.22e-15 across
2,890 values. The native 1→2→1 recording has separately sampled topology/area
checks; neither result establishes generic topology preservation.

## Native CPU benchmark — 2026-10-16

Measured with VKF 0.7.3 on AMD Ryzen 7 3700X, shared Linux host. Each entry is
median process wall time from seven alternating before/after pairs after an
untimed warmup. Compilation is excluded; launch and fixture preparation are
included. These are complete workload times, not per-frame or GPU measurements.
The baseline is library commit `2c8f442`.

| Workload | Before | Current | Speedup |
| --- | ---: | ---: | ---: |
| 10,000 linear samples, 1,024 states, 1 channel | 198.16 ms | 9.36 ms | 21.2× |
| 10,000 cubic samples, 1,024 states, 1 channel | 195.07 ms | 9.98 ms | 19.5× |
| 2,048 linear channel samples, 32 states, 1,024 channels | 95.17 ms | 6.85 ms | 13.9× |
| 2,048 cubic channel samples, 32 states, 1,024 channels | 95.93 ms | 7.20 ms | 13.3× |
| 2,000 full cubic samples, 32 states, 256 channels | 26.91 ms | 26.03 ms | 1.03× |
| 100 cubic preparations, 32 states, 256 channels | 58.96 ms | 59.02 ms | 1.00× |

Segment lookup now uses binary search. `channel` evaluates only the requested
component without allocating complete value/derivative vectors. State preparation
and full-vector arithmetic are unchanged. Reuse the prepared plan across samples;
use `sample` when all channels or derivatives are required and `channel` when
extracting one renderer property. `weights` still constructs a basis per call;
that convenience API and material/correspondence planning are not benchmarked here.

Reproduce with `tests/morphing/benchmark.py --compiler /path/to/vkf --library
/path/to/library --output /new/results`, once for each source revision. Then run
`tests/morphing/compare_benchmarks.py --before /baseline/results --after
/current/results --output /comparison.json`. Reports retain all timings, runtime
source/compiler hashes and checksums. Historical baselines belong in benchmark
artifacts, never in the runtime library. Full biological morph/render performance
remains unmeasured until that integration is complete.

Build the browser artifact with the same canonical compiler components:

```sh
python3 tests/morphing/build_wasm.py --library . \
  --source tests/morphing/wasm-demo.vkf --compiler /path/to/vkf \
  --wasm-compiler /path/to/vkf_symbolic_kernel_artifact \
  --runtime-root /path/to/canonical/ui-assets --output /new/wasm-evidence
```

Add `--playwright /path/to/playwright --chromium /path/to/chromium` for the
software-rendered browser check. This does not change the pinned public compiler.

## Native geometry presentation

`geometry_row(plan, coordinate, scale, size, row, lo, hi, extent, color)`
produces packed `[x,y,r,g,b,a]` triangles for the existing VKF
`createScreenSpaceSimplexRenderer`. Pass the scale returned by
`sample_geometry`; calibration and presentation use the same native field.
Rows cover a vertex lattice (`size - 1` rows), while calibration uses cell
centers. This is geometric contour extraction, not upscaling coverage pixels.
The adapter clips triangle edges at signed zero crossings, leaves holes empty,
and combines adjacent fully filled cells into rectangles. Input field and
contour sampling still bound geometric accuracy.

For repeated rows, `presentation.prepare_surface` evaluates the state once;
`presentation.surface_row` consumes that immutable resolved surface. Browser
glue only concatenates packed rows and scales the logical viewport for display.
The existing VKF renderer owns antialiasing; the existing media capture API owns
local video downloads. Native tests check winding, analytical half-plane area
and an annular hole.

The build requires the exact qualified canonical runtime hashes, including its
retained-value graph transport and diagnostic recovery. An older runtime copy
fails before compilation. The adapter does not replace canonical memory or
handle management. Eight interpolation/easing combinations, error recovery and
repeated browser frames are tested.

Current browser fixture: a lobed annulus splits into three perforated shapes
and rejoins. Equation, indexed 3D and image adapters are still not connected to
this presentation path. This fixture is not acceptance of that complete suite.
