# VKF native LaTeX fields and general visual morphology handover

Native renderer update: read [VKF LaTeX rendering integration](VKF_LATEX_RENDERING_HANDOVER.md).
The native source pins/counts below are historical. Morphology is now a separate project.

Date: 2026-10-14. Recipient: VKF implementation owner.

Replace KaTeX-generated math endpoints with the native LaTeX-mapped distance-field
renderer and connect its two-equation UI to the shared visual morphology solver.
LaTeX describes the endpoints; the solver infers transformation from visual states.
The same solver must accept text, geometry and mixed visuals.

The owner rejected the published `typing-demo/transitions.mjs` implementation:
it pairs identical atlas regions, moves rectangles and crossfades other symbols.
That is not the requested morphology. Retain the compact UI and independent
endpoint renderer, but replace this transition backend. Passing its browser tests
establishes UI/rendering behavior only, not morphology acceptance.

## Source locations and release identities

Repository: `vektor-flow/libraries`. Work in an isolated repository worktree and
read its instructions/status before edits. Do not modify the other chat's active
worktree or adopt its uncommitted files as a release.

| Component | Location or identity |
| --- | --- |
| Native math working branch | `codex/gpu-math-20261014` |
| Native math worktree | `/home/viktor/Projects/Vektor Flow/.worktrees/gpu-math-20261014-libraries` |
| Published renderer and compact UI source | `331e1322a1d215a225d4d95018432679bd218084` |
| Later documentation checkpoint | `8352880` |
| Shared morphology branch | `codex/embedding-transport-20261014` |
| Shared morphology worktree | `/home/viktor/Projects/Vektor Flow/.worktrees/cuvami-embedding-20261014-libraries` |
| Observed committed morphology checkpoint | `bedb894872281e968200383466efeafc8b7ed2c8` |
| Governing owner contract | `/home/viktor/Projects/Cuvami/core/contracts/EMBEDDING_TRANSITIONS.md` |
| Cross-chat checkpoint | `/home/viktor/Projects/Cuvami/company/docs/CHAT_HANDOVER_2026-10-13.md` |
| Live UI | `https://vektorflow.org/previews/gpu-math-typing/` |
| Public Pages source | `vektor-flow/vektor-flow.github.io`, commit `8309ba2070ad52cf2007233fbb1f01f8558daa18` |

The shared branch is advancing concurrently. Compare its latest committed README,
STATUS and verification receipts before choosing a new integration pin.
At inspection, `replica_transport.py` was untracked; it is not accepted evidence.

Native source files are under `examples/gpu-math/`:

- `typing-layout.mjs` and `draft-parser.mjs`: independent typesetting and draft recovery.
- `text-flow.mjs`: Computer Modern prose with inline/display math and word wrapping.
- `colors.mjs` and `units.mjs`: scoped ink and supported SI syntax.
- `typing-demo/demo.mjs`, `index.html`, `draw.wgsl`: compact UI and WebGPU rendering.
- `typing-demo/typing-data.json` and `atlas.rgba.gz`: prepared native metrics/fields.
- `typing-demo/README.md` and `THIRD_PARTY.md`: support limits and attribution.

Shared morphology implementation lives under `examples/field-transport/`:
`field_transport.py`, `scene_transport.py`, `rigid_routes.py`,
`prepare_scenes.mjs`, `prepare_math_scenes.mjs` and their verification scripts.
Earlier `examples/katex-transport/` and `examples/pixel-transport/` remain useful
regression material. Preserve them and their failed trials while changing the
endpoint provider; do not replace the general solver with a math-specific one.

## Native endpoint provider

Real LaTeX is the development layout/font oracle. The current mapping was produced
with TeX Live; MiKTeX equivalence has not been separately qualified. No TeX engine,
KaTeX, DOM math, browser font loading or Canvas2D text rendering runs during typing.
The independent runtime implements a documented subset, not arbitrary TeX packages.

The prepared atlas contains 1,411 source symbols across four optical styles,
5,644 keys and 3,315 distinct outlines. It is 4096 by 8192 RGBA8; decompressed
storage is 128 MiB. Cold loading, memory and atlas partitioning matter on phones.
The following hashes identify the available native assets at this handover:

| Asset | SHA256 |
| --- | --- |
| `typing-data.json` | `b5781cc6797202ef287e45acb25b912a209db811049a52c928b8b6433d6461f7` |
| `atlas.rgba.gz` | `a4ee09b88a164100e9c6e9aae98b878515f906fc2aa49c33cb463e6027b8be4a` |

`typeset(source, data.maps, {mode: 'display' | 'inline'})` returns placed glyphs,
rules, dimensions, draft diagnostics and placeholder operands.
`typesetText(source, data.maps, {width})` supplies prose flow and embedded math.
`demo.mjs` currently packs that layout into GPU rectangles, UVs and premultiplied
ink. Its viewport packing also wraps math atoms, so typesetter output alone may
not match the visible canvas. Extract a shared placement stage for rendering and
endpoint export to prevent baseline/wrapping drift.

RGB stores multi-channel distances for sharp text antialiasing. Alpha stores the
scalar signed distance: `(alphaByte / 255 - 0.5) * data.range`, with range 8 in
atlas texel units and positive values inside. Alpha is not opacity, and RGB median
is not a Euclidean distance field for morphology. Texture data must stay linear.

Each tile has a `plane` in layout coordinates and normalized `uv` bounds. Resolve
its field inside the endpoint adapter, applying placed `x/y`, `sx/sy`, `crop` and
`cropX`, then the common viewport transform. Rules, extended delimiter pieces,
source colours and multi-line positions must agree with the renderer. The current
Python `scene_transport.endpoint` handles basic glyph placement/rules but does not
apply the full crop/viewport/colour behavior; complete this before calling it a
faithful endpoint exporter. Glyph records are draw primitives, not inferred bodies:
a single symbol can have disconnected parts, and overlapping pieces can join.

A clipped narrow-band scalar atlas is not a whole-scene signed-distance field.
When a planner needs scene distances, reconstruct coverage/zero contours in a
common coordinate system and recompute distances as needed. Anisotropic placement
changes distance units; do not simply scale the stored scalar by an arbitrary
factor. Preserve contour hierarchy and field sign.

## Shared solver boundary

Use this pipeline:

`LaTeX or other visual source -> endpoint geometry/material -> shared planner -> GPU visual state`

Atlas keys are permitted inside the endpoint adapter to retrieve fields. Strip
LaTeX source, glyph/font names, formula IDs, AST meaning and supplied symbol
correspondences before inference. The solver receives anonymous endpoint visual
geometry or sampled coverage/material. It infers bodies, hierarchy and matches
from those visuals. Analytic geometry and arbitrary image providers use the same
boundary and constraints. Do not build separate KaTeX and native-math planners.

Preserve the owner's contract:

- Prefer translation, rigid, similarity and proper affine explanations before
  residual deformation. Unchanged geometry retains its shape while travelling.
- Move and deform concurrently under a common duration and quintic clock, with
  zero endpoint velocity/acceleration. Avoid a stop or representation swap halfway.
- Infer persistent split/merge lineages; visible component count must be monotone
  toward the target, or constant when endpoint counts agree.
- Preserve holes where appropriate; introduce topology changes through explicit
  events. Check contours and visible raster topology, including between frames.
- Keep unrelated opaque bodies disjoint. Plan planar paths rather than avoiding
  collisions by shrinking, fading, teleporting or adding hidden depth.
- Carry colour in declared linear-light space and composite with premultiplied
  alpha. Coverage, visual area and physical mass are distinct quantities.
- Report unsupported plans explicitly. Never silently invoke the rejected
  glyph-pair/crossfade backend as a morphology fallback.

## Existing acceptance and gaps

The shared work already consumes a captured native scalar atlas. Same-topology
hole-preserving studies, selected geometry/text scenes and fixed-shape polynomial
rearrangement are verified in offline CPU experiments. Routing has generated
regressions; consult the latest committed README for corpus results and limits.
This is a foundation for integration, not a completed arbitrary browser/GPU solver.

The actual math benchmark retains all five operations:

| Operation | Endpoints | Status at the inspected checkpoint |
| --- | --- | --- |
| Reorder | `x^2+y^2+z^2` -> `z^2+x^2+y^2` | Verified fixed-shape routing |
| Distribute | `a(b+c+d)` -> `ab+ac+ad` | Unsolved general branching |
| Collect | `x+x+x+y+y` -> `3x+2y` | Unsolved general branching |
| Factor | `x^2+2x+1` -> `(x+1)^2` | Unsolved nonrigid/branching mapping |
| Cancel | `\frac{x^2-1}{x-1}` -> `x+1` | Unsolved nonrigid/branching mapping |

Keep the failed cases visible in reports; more O-to-D clips do not establish those
operations. Earlier KaTeX movies accepted under older models do not automatically
satisfy the latest native-field contract. GPU execution, native VKF compiler
integration and physical-device performance remain to be implemented/qualified.

## Implementation sequence

1. Pin both source branches and hash the endpoint assets, preserving all font
   notices/source archives. Reproduce current native-layout and morphology checks.
2. Extract a shared endpoint placement/export adapter from the existing renderer.
   Verify full expressions against actual rendered endpoints, including cropped
   extensions, rules, colours, matrices, scripts, prose and mobile wrapping.
3. Switch the shared benchmark's endpoint provider from KaTeX raster generation
   to this native adapter. Keep historical KaTeX fixtures as comparison evidence.
   Confirm symbol labels do not cross the inference boundary.
4. Define a versioned anonymous endpoint/plan packet and deterministic sampling
   interface. Separate planning from playback; reject stale plans by source,
   layout, appearance and viewport revision. Expose ready/unsupported/failed states.
5. Port the verified shared algorithm to the appropriate VKF/WASM/GPU runtime,
   preserving the CPU reference for comparison. Specify which stages execute on
   CPU and GPU; handwritten WebGPU preview code alone is not compiler integration.
6. Replace `planTransition`/`transitionFrame` in `demo.mjs` with shared plan
   creation/sampling. Keep Equations/Style/Examples tabs, two example selectors,
   Transform, Swap, duration and scrub controls. Edits invalidate old plans;
   resizing rebuilds geometry-dependent plans while retaining normalized progress.
7. Extend general branching through the common algorithm and generated geometry
   tests, then re-run every math operation. Do not add formula-specific exceptions.

Planning can be more expensive than playback. Cache validated plans and avoid
re-typesetting, correspondence solving or atlas downloads inside the frame loop.
The user's long-expression target is under 10 ms. Measure input/layout, plan
construction, upload, GPU completion and frame scheduling separately; report
cold setup and warmed distributions with expression sizes and actual backend.
The existing UI's measured queue timings do not qualify morphology performance.

## Validation and delivery

From the native renderer worktree, run
`node --test examples/gpu-math/tests/*.test.mjs`. Retain the independent real-LaTeX
positioned-layout fixtures and text-flow checks; do not regenerate expected
answers from the new renderer itself. The old transition tests describe the
rejected backend and must be superseded by morphology behavior tests.

In an isolated shared-solver checkout, generate fresh native math endpoint layouts
with `prepare_math_scenes.mjs RUNTIME_MODULE ATLAS_JSON OUTPUT_JSON`, then run
`verify_math_cases.py ATLAS_FOLDER LAYOUTS_JSON REPORT_JSON`. This benchmark returns
failure while any operations remain unsupported. Use
`python -m unittest discover -s examples/field-transport -p 'test_*.py'` for the
focused reference checks and the committed stress generator for routing cases.
Keep generated outputs in fresh artifact folders with source/asset hashes.

Validate exact endpoint reconstruction within declared independent tolerances,
continuous near-end convergence, holes/component count, unrelated overlap,
self-intersections, colour and area/mass policies. Sample off-grid times and both
directions; retain denominator and failures. Include repeated/ambiguous shapes,
dense rearrangements and mixed text/analytic geometry to test generality.

Keep controls and the canvas close together on phones, with small selectable
expression fields, tabs and minimal explanatory text. Test 320/390/430 px widths,
keyboard/touch interaction, tab switching, source edits during planning/playback,
reduced motion, long expressions, unavailable adapters and device loss.

Deliver a shared solver integration, independent endpoint regressions, explicit
unsupported-case reporting, measured planning/playback receipts and the compact
browser example. Preserve the current physical GPU STOP and existing deployment
boundaries; software WebGPU tests do not authorize hardware GPU tests or production
changes. This handover requests implementation and does not claim it is complete.
