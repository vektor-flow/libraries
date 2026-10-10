# 2026-10-10 Platonic Play upstream UI transfer

Owner: the user-requested single-agent task. Branch codex/platonic-ui-20261010,
base68d103b. User requests a common Vektor Flow rendering/selection/coordinate
implementation and compatibility with native add/physics semantics.

Transferred common drawing and view implementation from Product7f2f939; no shader,
physics solver or source grammar is invented. Existing legacy runtime623bd30
remains explicitly pinned. New retained plot view consumes actual canonical0.7.1
field_mesh arena output and preserves selected IDs across upstream physics updates.
Compiler ABI views validate storage, alignment, extents and topology.

73 public behavior checks pass. A real WASM compile/run of native viewport.add
returned one visual arena; source and original packet are retained as fixtures.
The physics test uses the upstream stepInertialBodies implementation, not a mocked
solver. Non-pickable geometry renders but cannot be selected. Current scope is
portable screen presentation; complete native lighting/depth/text/toolbar and
physical GPU acceptance are not established. No release/main/publication.

Next: pin the candidate in Product, delete Product-owned implementations in favor
of re-exports, run original common tests/build, then verify actual browser pixels.
The bootstrap branch provides compiler compatibility/packaging evidence without
modifying accepted seed, patches or active reconciliation0135 worker builds.

Final source:77 tests pass, including World data-unit marker sizing, selection of
actual compiler arena output, frame updates through upstream inertial physics,
face boundary without triangulation diagonals and physics-module descriptors.
Product's original68 focused /1237 eligible tests pass after seven implementation
deletions; its222-file build remains byte-identical to both native bundles.
Fresh canonical add2d/add3d/World checks pass using pinned0.7.1 with no new syntax
or frontend change. Software-rendered desktop1000x700 /phone390x844 actual compile,
mouse selection and recompiled y0→1 preserve selection, with zero page errors.
Direct same-frame GL readback sees1284/729 cyan contour pixels. Renderer is
explicitly SwiftShader, not a physical device. Screenshots are local QA evidence.
Initial browser import-map setup and post-presentation cleared-buffer readback
failed; correcting the harness and doing synchronous post-draw readback supplied
the final pixel proof. The first boundary test checked only endpoints; triangle
centroid sampling exposed the internal diagonal before its repair.

The new plot presentation remains a candidate; existing full native lighting,
depth/text/toolbar behavior is outside this screen view. Physics-property module
policy is now upstream and descriptors still come from the pinned native runtime.
No compiler release, public site activation, physical GPU test or main merge.
