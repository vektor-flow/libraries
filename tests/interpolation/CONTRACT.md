# Interpolation source contract and integration seam

Documentation worker handoff: completed `interpolation/README.md`,
`examples/interpolation-basics.vkf` and this contract only. Public signatures
follow the agreed facade/kernel plan. Source checks verified whitespace, Markdown
fences, four example output calls and 48 patch control scalars. One metadata
check confirmed an independent `gpt-6.1-sol` Mathematics project chat. Native
qualification and final outcome edits remain with the coordinator.

2026-10-31. Source-only review against base `b1c40844` in the assigned worktree.
New native execution is pending coordinator qualification; this document is a
reviewable draft, not a test receipt. The coordinator owns the shared harness,
compiler/runtime checks, execution lock and final numerical evidence. No compiler,
VKF program, browser, GPU or product build was executed by this documentation worker.

## Finite contract to qualify

- `blend(start,finish,coordinate)` operates on equal, nonempty numeric channel
  vectors over `[0,1]`. Endpoints retain the original endpoint values.
- `prepare_bezier(controls,width)` prepares point-major polynomial controls;
  `sample_polynomial(plan,coordinate)` returns `value`, `first`, `second`.
  First/last controls are endpoint anchors. Interior handles need not be visited.
  Constant and linear nets must return zero derivatives of absent orders.
- `prepare_hermite(start,finish,start_derivative,finish_derivative)` accepts equal,
  nonempty channel widths and normalized endpoint first jets. Its cubic Bezier
  encoding selects the same parameterized Hermite polynomial in exact arithmetic.
  Converted controls and endpoint derivative reconstruction can round in machine
  arithmetic; avoid promising bitwise endpoint-jet equality.
- `prepare_patch(controls,width,u_count,v_count)` uses flat index
  `((v*u_count+u)*width+c)`; `sample_patch(plan,u,v)` returns `value`, `du`, `dv`,
  `duu`, `duv`, `dvv`. Each direction is normalized independently. Constants,
  curves embedded as one-row/one-column nets, corners, asymmetric nets and a
  genuine nonzero mixed derivative need coverage.
- Invalid dimensions/storage, nonfinite or excessive numeric data and parameters
  outside the closed domain must reject. The input magnitude guard follows
  Morphing's `abs(value)<10^100`; this is not a certified evaluation error bound.
  Repeated sampling must leave prepared controls unchanged. The coordinator should
  qualify these conditions against the final kernel implementation, including
  any practical degree/allocation limits.

`examples/interpolation-basics.vkf` uses native import `i:.Interpolation`, native
assertions `condition ?! "message"`, and four scalar output calls. Its intended
lines are `1`, `3`, `0.5`, `9` (allow numeric formatting differences). The 4x4 3D
net represents `(3u,3v,9uv)`, with `duv=(0,0,9)`. This checks tensor coupling;
a pair of independent curves would fail that mixed partial. Hermite converts
normalized speed to physical velocity by dividing by duration; acceleration uses
duration squared. No Python or JavaScript interpolation fallback is present.

## Compatibility contract

The public wrapper retains all 16 `Morphing.vkf` facade function signatures and
delegates to those same implementations. `Morphing.vkf` and `morphing/` remain
unchanged. Historical imports keep their namespace; the new `Sample` keeps the
`value`/`first`/`second` shape. Existing state coordinates may be arbitrary strictly
increasing knots; the new polynomial/patch domains are normalized. Explicit mode
and smoothing flags are retained, without invented default-record syntax.

Source evidence: `Morphing.vkf` defines `Curve`, `Plan`, `Sample`, `MaterialPlan`,
`EmbeddingPlan`, `ViewBinding` and `ViewSample`. `tests/morphing/core.vkf` exercises
state derivatives, embedding product rules, conserved carrier weights and stable
view/layer IDs; `tests/morphing/material.vkf` checks carrier ownership/marginals.
Those files are existing coverage, not newly rerun evidence. The coordinator's
new harness should compare old/new facade results for state and material calls
and check the full signature list in `interpolation/README.md`.

## Actual branch UI evidence

`tests/fixtures/canonical-add-071.vkf` contains precisely this existing API:

```vkf
viewport: .ui.viewport
viewport.add(x:[-1,1]_u,y:[0,0]_u,id:"line",color:[0.2,0.7,1,1])
viewport.show()
```

The accompanying JSON retains a compiled arena. `PROVENANCE.json` pins its
canonical compiler to 0.7.1 and describes the separate 0.7.2 preview/native-input
fixture; the root README reports the historical compile/run. These are historical
source/artifact facts, not fresh execution of this source on installed 0.7.3.
The symbolic coordinate form `[... ]_u` is evidenced for those literal arrays;
passing dynamically sampled vectors or derivative records through the same path
still needs an actual compile/packaging probe. Source review found no native VKF
`viewport.push`, `viewport.plot` or `viewport.append` example/declaration in this
branch. JavaScript array `.push` calls are unrelated API evidence.

The existing library's `ViewBinding` contains string IDs, integer channel offsets
and a `Plan`; `ViewSample` returns those IDs/offsets and numeric value/derivative
arrays. These are adapter records, not native `.ui` View/Layer handles. The
Morphing README records imported root `type_alias` and function-local View
construction packaging failures. Their current status requires coordinator
qualification; do not infer a fix from pure numerical compilation.

## Next integration work supported by that evidence

1. Qualify the numerical additions with the actual installed native compiler
   under the coordinator's execution lock and retain source/compiler hashes.
2. Probe whether native sampled `[num]` channels can supply the real
   `viewport.add` x/y coordinate inputs. Preserve the existing stable string ID;
   use the native projection/packet path and record accepted concrete types.
3. Test top-level viewport creation separately from imported record types and
   function-local View construction. Reuse real supported handles if available;
   do not relabel `ViewBinding` as a native View. Bind derivative arrays only to
   an actual consumer that declares their units and update semantics.
4. For patches, separately design sampling topology and transport of position /
   tangent data into a supported native geometry packet. Tensor evaluation alone
   supplies neither triangles nor a tessellation/error policy. Probe mixed
   derivative channel transport before claiming a surface integration.

## Qualification update — 2026-10-31

The preceding handoff records the source-only starting point. Native CPU
qualification is now recorded in `QUALIFICATION.json`: all 16 planned fixtures
passed their specified outcomes on pinned VKF 0.7.5, with 1,050 independent
scalar oracle comparisons and separate exact component/width checks. The example
and coupled patch grid executed in VKF. Both failed development runs are retained;
the facade alias was repaired, and array value checks use exact components plus
width rather than representation-dependent whole-array comparison. No original
core regression was dropped. Morphing source remains unchanged.

WASM, native/WASM agreement, renderer/GPU routes and performance are still
unqualified. The following exclusions continue to apply.

No `interpolation:{...}` runtime hook is defined. No hard-constraint engine,
temperature/activation policy, graph interpolator, automatic C2 phase joining,
patch-gluing/injectivity proof, or adaptive tessellation is implemented by this
slice. Material amount, object identity and geometric topology remain distinct;
existing material conservation does not establish the other properties. New
polynomial/patch native, WASM, GPU, renderer and performance claims each need
their own evidence; historical Morphing results do not transfer automatically.
