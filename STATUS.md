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
