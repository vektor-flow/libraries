# Pixel correspondence follow-up — 2026-10-14

Added a pixel-only foreground research path: heuristic multiscale grouping,
rotation-aware shape assignment, curved collision-checked rigid routes, and three
real MP4s including full sentences. Six new Python tests pass. The shared JS
object adapter independently fits affine/residual motion for supplied object
identities; 27 embedding tests and all 88 existing library tests pass.
See examples/pixel-transport/README.md for exact limits. General RGB segmentation,
automatic split/merge and residual pixel transport are not solved. No deployment,
compiler modification, main merge, or physical GPU acceptance.

# Embedding research candidate — 2026-10-14

Branch codex/embedding-transport-20261014 is based on the immutable integration178
library candidate bf3dc9cc8af41155623d0678ace48948632806f9. New modules and an isolated
CPU Canvas preview implement the bounded research described in
examples/embedding-transport/README.md. 24 focused tests, 88 original tests and
four browser/viewport runs passed. No existing renderer/physics source was changed.
No compiler integration, main merge, public runtime release or staging deployment.
The active compiler workers and physical GPU STOP remain untouched.

The numerical fit depends on supplied correspondences; it is not a solved
arbitrary-visualization morph, optimal branched transport or universal topology
preservation. Keep these acceptance boundaries in future integration reports.

## Prior candidate evidence (retained)

# Platonic interaction candidate — 2026-10-11

The Owner subsequently revised the defaults on October11: data plots default to
selectable:false and draggable:false; graphical scenes explicitly enable either
capability. This supersedes the upstream48819e3 draggable-by-default rule. The
camera-only zero-update repair remains. Compiler fixtures and numerical oracles
are unchanged; selection tests explicitly opt into graphical-scene interaction.

Integrator interaction178 continues the immutable 48819e3 candidate in a separate
local worktree. A stationary pointer now returns null after rebasing, without
calling writeInput or update. All88 original library tests pass. A separate real
compiled integer-input audit verifies pan, rotation and zoom each execute zero
updates, while subsequent cursor movement executes one update. Fractional input
still truncates and has no continuous-input credit. No physical grab, full native
snapshot/restore, motion precedence or simultaneous physical grab qualification
is claimed. Original Product implementations and independently pinned backend
remain required. The upstream author's worktree and active compiler workers are
unchanged. This is a private integration candidate, not deployed browser assets.

Branch codex/platonic-interaction-20261011, base31b92ed. Single agent. Contract:
/home/viktor/Projects/Tesseracs/products.platonic-play.web/docs/INTERACTION_CONTRACT.md.

Implemented upstream presentation default draggable unless explicit false and a
camera-plane native input constraint with camera-change rebasing. Test proves camera
pan alone does not alter the real compiled integer native position; subsequent cursor
motion does. Existing plane/axis and explicit quantization checks remain unchanged.
Library9files/88tests pass. No continuous f64, physics grab/momentum, physical GPU or
full Product integration claim. Generated node_modules symlink is local test setup,
not an authored package file. Do not add it to Git.

Compiler0.7.2 public browser archive now matches vendored preview checksum
9011f6cfd67a925043cbdb33cbc3d55553db7d5a4470949c4d838cf37534629b.
Actual canonical compilation omits draggable when absent and preserves explicit
true/false, so this library default does not require a compiler emission change.
Continuous f64 record-input repair belongs to the already-started WASM lane in
reconciliation0136. Preserve its reserved source and compiler/GPU gates.

Next: validate accepted native continuous inputs, motion/constraint/runtime-snapshot
contracts, then pin the reviewed library candidate and remove Product duplicates only
after replacement proof. Current candidate is not installed into portable assets or
the public release. No push, publication, deployment or active worker interference.


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

Native DOM mount added: compiler-owned dimensionality/bounds, local mouse/touch
selection, drag pan, wheel zoom, Escape, ResizeObserver, stable updates and complete
disposal. Actual desktop and phone with DPR2 run native add compilation and select
through real pointer events at an offset container. Contours are visibly rendered;
selection persists after another compilation; disposal removes the canvas and
rejects updates. No JS page errors. Tests use explicitly forced SwiftShader and
preserve the upstream physical GPU STOP. Public syntax and the compiler arena ABI
are unchanged. Product integration remains eight thin re-exports; its main bundle
does not include this optional native mount until requested by a consumer.
