# Existing interpolation editor → shared native methods

This maps the Owner's existing editor controls to available research/library
methods. It does not add primitive editors or claim Product integration. The
existing editor is retained; vectors/arrows remain line styles, arcs and circles
already have authoring surfaces. PP should consume native capability descriptors
and expose unsupported choices honestly until their route is qualified.

| Existing control | Native/research correspondence | Status in this branch |
| --- | --- | --- |
| Linear state path | `state_interp(path:0)` → unchanged `Morphing.prepare(...,0,...)` | canonical WASM scalar qualification |
| Natural cubic state path | `state_interp(path:1)` → unchanged natural cubic | canonical WASM fixture; inherited backend evidence remains scoped |
| Arrow placement/orientation | Native line marker/style driven by sampled native line tangent | renderer style; no new interpolation primitive or host algorithm |
| Spline order | `polynomial.prepare_bezier` arbitrary finite control count; degree=count−1 | migrated, earlier native CPU-qualified finite fixtures; current route not requalified |
| Cubic endpoint slopes | `prepare_hermite` with normalized-chart derivatives | migrated same polynomial kernel; not a tension dial |
| Tension | Could map explicit declared endpoint-jet policy to Hermite or graph targets/weights | no verified editor mapping; do not equate tension to degree or natural cubic |
| Arc/circle | `conic.prepare_positive_quadratic` rational quadratic segments, positive weights | source-only migration; analytic circle construction/segmentation adapter missing |
| Radius absolute/relative | `rounding.prepare_cyclic` and reference/current rounding with physical coordinate + roundness | source-only finite cyclic rounding; direct editor radius/unit mapping missing |
| Smoothing/joins | `graph.prepare/with_joins/evaluate`, graph Hermite jets/constraints | source-only finite implementation; not current runtime capability |
| Tensor surface | `prepare_patch/sample_patch` with declared independent u/v | migrated finite native CPU evidence; no generic surface interpolation claim |
| Fractal controls | Refinement/convergence research is distinct from interpolation coordinate | no native implementation/editor contract migrated; unavailable |
| Graph face fill | Authored selected bounded faces and harmonic polynomial illustration | research only; no automatic extraction/PDE/native solver claim |
| Spectral text/list reveal | `spectral_interp` + cached row/glyph reading indices | native unfolded channels qualified in client WASM; compositor integration pending |
| Maximum-temperature evaporation | `vapor_interp` + actual source-ink samples + target row reveal | deterministic native scalar channel qualification; native font/compositor and visual verification pending |

Polynomial/tensor, conic, graph and rounding source is intentionally migrated
from the read-only owner worktree, with file hashes in
`MIGRATION-PROVENANCE.json`. The original worktree is untouched. The new public
Interp settings do not silently enable source-only research capabilities.
The historical Morphing backend remains the sole state/material numerical core.

The mathematical contract separates parameter-domain topology, admissible target,
anchors versus controls, observable/quantity policies and route qualification.
The general core contract, local activation algebra and graph-fill illustration
are proposals or finite evidence, not a universal interpolation/constraint engine.
Hard endpoints cannot be relaxed by heating. A scalar activation value does not
supply physical energy, correspondence, carrier creation or missing operations.
See the provenance and Interp contract for exact implemented limits.
