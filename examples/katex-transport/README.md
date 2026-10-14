# KaTeX stress images for the general pixel matcher

The transformation solver receives only two thresholded PNG arrays. There are no
LaTeX strings, math tokens, object IDs, DOM boxes, formula rules or case-specific
mappings in `pixel_transport.infer_pixel_pair`. This interface is shared with the
ordinary shape tests. KaTeX is an endpoint-image generator, not a transformation
engine. Current input handling remains binary foreground, not arbitrary full RGB.

Nine progressively harder image pairs: translation, a+b→b+a, common-factor
extraction, perfect-square factorisation, difference of squares, rational
cancellation, repeated-term collection, fraction simplification, and a visually
similar expression pair that is not algebraically equivalent. Algebra labels and
an independent SymPy oracle are benchmark metadata only. They do not guide, veto,
or score geometric matching or paths. A visually valid transition may connect any
two images regardless of whether the equations are equivalent. The cancellation
example records x != 1 as presentation context, never as an inference input.

The shared baseline tries four segmentation scales and rotation-aware partial
assignments. Dummy assignment slots leave unsupported material unresolved instead
of forcing a bad match. Repeated shapes can report ambiguity. Candidate selection
maximises recovered source material with a small part-count penalty; this is still
a heuristic, not jointly optimized partitions or many-to-many transport.

## Reproduce

    npm ci --prefix examples/katex-transport --ignore-scripts
    # Python virtualenv with requirements.txt; ffmpeg and browser Playwright installed.
    PLAYWRIGHT_MODULE=/absolute/path/to/playwright/index.mjs node examples/katex-transport/render_inputs.mjs /path/to/evidence
    python examples/katex-transport/benchmark.py /path/to/evidence
    ffmpeg -f concat -safe 0 -i /path/to/evidence/concat.txt -c copy -movflags +faststart /path/to/evidence/katex-stress-tests.mp4

KaTeX 0.19.0 and its actual CSS/fonts render in software Chrome at 960x540. All 18
endpoint renders await font loading and are checked for clipping and page errors.
The independent movie renderer produces 1200x900 H.264, 24 fps, six seconds/case.
Reference: [KaTeX browser setup](https://katex.org/docs/browser.html).

Green is matched material. Amber is unresolved source material, which stays visible.
Grey is the target reference, not additional transported mass. Unresolved movies
are clearly labelled PARTIAL DIAGNOSTIC and can have measured collisions. They are
not completed morphs or collision-free acceptance. Matched-only regions are not
silently omitted from endpoint or overlap measurements. Deposited source mass stays
constant; target coverage may differ. Rendering alpha clips density at one.

## 2026-10-14 results

Translation and reordering pass rigid correspondence and the conservative path
check. Translation endpoint IoU is 1.000; reorder is 0.893 because the target's
raster glyph samples differ. Even a successful rigid geometric match is not exact
endpoint raster reconstruction. No overlap was observed in those two movies.

| Image pair | Source material matched | Endpoint IoU | Observed overlap, pixels |
|---|---:|---:|---:|
| Translation | 100% | 1.000 | 0 |
| Reorder | 100% | 0.893 | 0 |
| Common factor | 65% | 0.537 | 103 |
| Perfect square | 53% | 0.446 | 104 |
| Difference of squares | 66% | 0.267 | 25 |
| Cancel factor | 29% | 0.264 | 30 |
| Collect repeats | 22% | 0.209 | 87 |
| Simplify fraction | 26% | 0.220 | 107 |
| Similar symbols, extra target parts | 100% | 0.721 | 0 |

The final row still has unmatched target parts: 100% source coverage is not complete
correspondence. All seven harder cases remain partial. Mass deltas, ambiguous
matches, all partition scales and full diagnostics are in results.json. The initial
reorder path failed: symmetric shapes were allowed gratuitous rotation and static
objects received a detour margin despite zero detour. Fixes prefer zero-angle ties
and use the actual detour-vector magnitude. Initial results/logs are preserved.

Eleven Python geometry/inference tests, 27 JS embedding checks and 88 existing
library tests pass. Software video frames were inspected for readable math and
visible failure labels. No physical phone/GPU, compiler integration or deployment.
Evidence: Cuvami/staging/artifacts/embedding-transport/katex.

## Clean presentation correction

Owner requests one evolving state, with actual KaTeX glyphs and no source/target
panels, ghost targets, diagnostic labels or colour-coded leftovers. The diagnostic
suite above remains preserved as evidence. `PIXEL_RATIO=3` on render_inputs.mjs
captures the real KaTeX alpha at three times resolution; render_clean.py extracts
those anti-aliased components and applies the existing blind pixel motion plan.
It does not feed DOM/TeX identities into matching. The clean a+b→b+a clip is 7 sec,
1280x720 at 30 fps, with one visible expression only. Source/midpoint/end inspected.
This is a presentation correction; approximate registration limits remain.

    PIXEL_RATIO=3 node examples/katex-transport/render_inputs.mjs /path/to/clean
    python examples/katex-transport/render_clean.py /path/to/evidence /path/to/clean

Output: /path/to/clean/katex-one-animation.mp4.

## Creation/removal and harder-only sequence

Owner requests creation of new symbols, multiple harder animations consecutively,
and video only: no still-frame outputs, overlays, source/target panels or simple
translation/reorder demos. `render_events.py` uses the generic coverage_transport
module, which receives endpoint alpha arrays only. Connected regions retain actual
KaTeX anti-aliasing; coverage mass replaces thresholded pixel counts for matching.
This recovers the existing plus in ab+ac without pretending it is a new glyph.
Unmatched target regions grow continuously from zero extent; unmatched source
regions contract. Matched glyphs share a moving frame, with aligned residual alpha
interpolation recovering the actual target raster. All use the same quintic clock.

Six clean movies: common factor, perfect square, difference of squares, cancellation,
collection and fraction simplification. Combined output is 36 sec, H.264, 1280x720,
30 fps: Cuvami/staging/artifacts/embedding-transport/katex-clean/
harder-katex-animations.mp4. Each animation displays only its evolving expression.
No source/target comparison is burned into frames. Every endpoint matches its
original supersampled KaTeX coverage within 1/255 (actual maxima below 1e-15).
Sixteen Python checks pass, including creation, removal, coverage and endpoint rates.

This is an explicit source/sink appearance policy, not a conservative material
split/merge solution. Source/sink regions are inferred from images, not math tokens.
Intermediate overlap still occurs: 0,736,497,36,0,44 high-resolution pixels across
the six movies. A bounded detour experiment could not clear every case and is not
part of this renderer. No collision-free or globally optimal transport claim.
Receipts and pre-path-search logs are preserved; compiler/staging are unchanged.

    python examples/katex-transport/render_events.py /path/to/clean
    # Concatenate event-concat.txt using ffmpeg as above.

## Fade, move, shrink; budding and absorption — previous revision

Disappearance now combines translation, fading and a moderate reduction in size
(1 to 0.45) under the common quintic clock. Appearance reverses those channels.
Shapes no longer disappear solely by collapsing to a point. New parts originate
at a parent inferred from the endpoint pixels; disappearing parts converge on an
inferred receiving part. Prefer geometrically similar retained parents, otherwise
choose a nearby retained part. No LaTeX, glyph identities or algebra is supplied.
A blank endpoint has no parent and uses the explicit unanchored appearance/removal
fallback. Ambiguous parent selection remains heuristic.

Parents follow the retained part's moving trajectory. A 25-candidate bounded path
search scores opacity-weighted intersections at 13 times and penalizes clipping
and excessive detours. Contact is allowed within a budding/absorption family;
unrelated parts are penalized. This reduces sampled overlap, not a continuous-time
nonintersection certificate. Full movie receipts separately report actual observed
unrelated overlap, including cases the coarse search misses. Source/sink appearance
is still not a conservative physical material solver.

The renderer now emits *-budding.mp4, budding-verification.json and
budding-concat.txt. It emits no still-frame previews. The clean six-case compilation
is budding-katex-animations.mp4 in the same local artifact directory. Nineteen
Python tests pass, including image-inferred parent selection, coupled fade/scale/
motion, parent trajectories, blank-image fallback, and allowed-family contact.
The prior source/sink movies and receipts are preserved for comparison.


## Material reuse and slower motion — previous revision

The six harder examples now last ten seconds each (60 seconds combined). Rigid
registration prefers translation when rotation improves RMS pixel distance by no
more than 0.35 logical pixels; substantial evidenced rotations remain supported.
This prevents near-symmetric raster noise from introducing gratuitous spins.

When both endpoints contain unmatched components, coverage_transport pools those
components into one residual material problem. Deterministic equal-mass samples
(up to 1,600) undergo minimum squared-distance assignment. Local interpolation
lifts their displacements onto both complete antialiased endpoint rasters. This
allows one-to-many and many-to-one reshaping without supplying glyph identities,
LaTeX, semantic hints or intermediate drawings. Geometry that already matches
continues through its independent rigid route. One-sided residuals retain the
previous moving/fading/shrinking budding or absorption behavior.

The renderer blends two moving quadratures of that shared transport, rather than
fading stationary old shapes out while independently growing new shapes. Particle
mass follows the quintic interpolation of endpoint coverage mass; paths use the
same endpoint-rest clock. This is approximate transport: sample interpolation,
coverage saturation and intersections can lose visible area, and interpolated
fields do not guarantee hole preservation, injectivity or collision avoidance.
It is not an exact continuum optimal-transport or topology solver. The bounded
path search penalizes intersections with retained objects; residual self-contact
is allowed for splitting/merging and is not separately certified.

Outputs: *-material.mp4, material-verification.json and material-concat.txt.
Concatenate with ffmpeg to material-katex-animations.mp4. No still previews are
emitted. Twenty-seven Python checks cover previous behavior plus material reuse,
one-to-many/many-to-one, actual in-transit coverage, exact antialiased endpoints,
particle mass interpolation, endpoint rest and evidence-based rotation selection.
Earlier videos, receipts and migration evidence remain intact.


## Solid boundaries and mitosis-style splitting — previous revision

The transported alpha field is now reconstructed as a solid surface rather than
showing individual particle splats. A local Gaussian density reconstruction
removes grain; an area-calibrated level set gives an opaque interior and a narrow
antialiased boundary. The selected area follows the same quintic interpolation
of endpoint coverage. The regularizer eases in/out during the first/last 12% of
the transition, preserving exact original antialiased endpoint pixels.

Source/target connected-component membership of the transport samples identifies
branch families. A minimal tree connects their inferred branch centers through
temporary capsule necks, which narrow while the branches move and pinch off.
Reverse families join through the same rule. This uses endpoint geometry only;
no glyph names, manually supplied split points or formula-specific instructions.
Neck width and density smoothing are visual regularization heuristics, not a
physical mitosis model or a universal topology-preservation guarantee. Close
unrelated residual regions can still merge, and some collision/shape artifacts
remain. The original rigid-part motion and slower ten-second timing are retained.

Outputs: *-solid.mp4, solid-verification.json and solid-concat.txt. Combined movie:
solid-katex-animations.mp4. Thirty-two Python tests pass, including measured grain
reduction, opaque interiors, smooth area, exact antialiased endpoints, a connected
body that narrows and separates into two, and reverse merging. All earlier video
and migration evidence remains preserved. No still previews are emitted.


## Local pinch-off without long tethers — previous correction

The old capsule neck extended across the entire distance between moving branch
centres, creating long strands. Necks now narrow at their centre first, then
retract into the bodies. Quintic distance and time gates limit this artificial
contact to nearby branches: bridge contribution is zero beyond six initial neck
radii and after the early split phase. Reverse merging uses the same local rule.
Area reconstruction reallocates the disappearing neck area to the moving bodies.
Original endpoint coverage, rigid routes and ten-second timing are unchanged.

Thirty-five Python checks pass. The split is connected early, disconnected from
30% of the test duration onwards, with a clear inter-body gap at intermediate
times. New checks cover distance-bounded contact and release with zero first and
second derivative. This bounds the explicit bridge, not every possible thin
feature in the underlying transported image; general topology/collision guarantees
remain out of scope. Outputs are *-pinch.mp4, pinch-verification.json and
pinch-concat.txt, combined into pinch-katex-animations.mp4. Previous movies remain.


## Monotone visible count and persistent lineages — latest owner contract

The owner requires monotone object count, with no split-then-merge or
merge-then-split families. Equal endpoint counts must stay constant. Event timing
should approximately follow a linear count ramp, but remain a soft objective
that can trade against deformation and collision avoidance.

`render_lineage.py` uses the separate endpoint-only `lineage_transport.py`
candidate. It does not use pooled material density or inferred reconnecting necks.
Connected source components receive persistent rooted binary families, with
connected geodesic partitions conserving source samples at each split. Reverse
playback of the same split construction gives merge-only families. One-to-one
rigid matches retain their rotation; remaining local shapes use aligned distance
fields. Local raster connectivity repair acts only inside an identity and never
joins separate identities. This repair can alter local geometry; hole topology
and exact intermediate mass conservation are not guaranteed.

Event slots approximate a linear count ramp; a bounded timing search also
penalizes insufficient deformation time and respects ancestry. Timing is neither
fixed at those slots nor a claimed global minimum. Crossing families receive
passing lanes before contact. Framewise separation and repeated trajectory
smoothing enforce disjoint coverage while avoiding large projection jumps. The
bounded planner rejects failures; it does not claim arbitrary scenes always fit.
Blank endpoints require a separate birth/death policy and are rejected here.

Acceptance is on every frame, including the decoded MP4: visible connected count
must equal the persistent active-family count, without dropping small fragments
from the count. Pixel topology uses 4-connectivity at half coverage. Coverage
ownership is checked down to 1/255 alpha. The video uses a small edge contrast
margin and higher-quality H.264 encoding to prevent compression from turning
thin connected strokes into extra components. The edge guard eases to a smaller nonzero guard at the held endpoint; its
display-only contrast change preserves the half-coverage silhouette. Exact
endpoint recovery is measured before this transfer and lossy encoding.

The last-frame check alone was insufficient. The renderer also rejects excessive
normalized coverage error at 98% and 99% of motion, verifies decoded near-target
silhouettes, and holds the final state. These are discrete offline frame checks,
not a continuous-time physical nonintersection proof or production acceptance.
Forty-four Python tests cover the existing candidates and new monotone one-to-five,
five-to-one, constant-count swaps, connected partitions, spread event timing,
rigid rotation and explicit unsupported-input rejection.

    python examples/katex-transport/render_lineage.py /path/to/clean

Outputs: *-lineage.mp4, *-lineage-frames.npz, lineage-verification.json and
lineage-concat.txt. Combined: lineage-katex-animations.mp4. The local independent
verify-lineage.py receipt checks decoded counts, near-final silhouette agreement
and disjoint reconstructed layer ownership. Previous videos and failed first
encoding evidence remain preserved. No still previews or staging changes.

## Shared weight sweep — 2026-10-14

`sweep_weights.py` compares five global surface/trajectory configurations on the
same six harder endpoint-only KaTeX pairs. It ranks them under three explicit
weight vectors (area-first, balanced, rounded). Configuration knobs and objective
weights are distinct: the knobs generate a bounded candidate set; weights rank
measured results across **all six cases**, never select a different style for each
formula. This is a small discrete search, not a global variational optimizer.

The baseline remains available. New candidates regularize signed distance fields
at a radius-relative scale, offset contours toward the smooth target area, and
connect disconnected lobes within an identity with finite-width rounded capsules.
Area correction and connection alternate twice; residual area error is scored,
not hidden. Inferred rigid one-to-one matches bypass these style operations.
The existing disjoint-coverage collision projection remains authoritative. A
surface callback is optional and leaves the earlier lineage renderer unchanged.

Costs measure area-curve error, excess area variation, centroid/area acceleration,
excess thin features, excess perimeter, transport, event spacing, hole-count
reversals, and temporal boundary differences. Areas are normalized by endpoint
area, distances by its square root, and thin-feature radius by input scale.
The ranking applies one common positive-median normalization per sampling grid to all
weight vectors. Boundary difference is a flicker proxy that also responds to
legitimate movement, not a material-velocity estimate. Hole count is not full
persistent topology. Event schedules are retained in this sweep, so their cost
cannot distinguish its configurations. This 2D experiment does not measure 3D
volume. Endpoint-relative perimeter/thin costs avoid simply penalizing all
legitimate thin glyph strokes.

    python examples/katex-transport/sweep_weights.py /path/to/clean --frames 81
    python examples/katex-transport/sweep_weights.py /path/to/clean \
      --frames 252 --candidates 2,3,4 --encode

Outputs are under `weight-sweep/`, preserving every previous movie and receipt.
Each candidate movie shows the same six transitions consecutively, one animation
at a time, with 24-frame endpoint holds and 252 motion frames per case. No stills,
side-by-side panels, semantic hints, or diagnostic overlays are rendered. Coarse
receipts can be rescored from saved frames without rerunning geometry. Failed
candidates are recorded and excluded from aggregate rankings unless all cases
pass. Full-rate generation also checks trajectory acceleration and near-target
convergence; encoding checks every decoded frame's visible object count.

These are comparisons for visual judgment, not a claim that topology, area,
contact geometry and motion are all solved. Raster repair, hard lineage event
handoffs, hole changes and residual thin geometry can remain. Rounded connections
are not a physical bacterial-division model. A visually convincing continuous
neck/contact construction remains a separate improvement if these weights do not
resolve the observed artifacts. No runtime, compiler, deployment or GPU changes.

The first full-rate trial exposed late target convergence in the moderate-rounding
configuration. That failed trial and its source snapshots are preserved in
`weight-sweep-initial/`. Weighted trajectories now taper projection corrections
over the final 16% of time, retaining the original renderer's 8% default. The
acceptance threshold was not relaxed. `verify_weight_movies.py` additionally
checks encoded held endpoint silhouettes and 98%/99% target convergence, recording
near-event area changes without producing still previews.

## Continuity, local thickness and compact routes — 2026-10-14

The owner observed excessive evasive motion, abrupt mass/shape changes and clumps
that resolved late, especially in thin symbols. `render_continuity.py` adds a
separate candidate using `continuous_transport.py`; previous movies and weighted
surface implementations remain available.

- Route search contracts previous passing trajectories and tests the current
  silhouettes. It retains a wider route where tighter candidates fail. Optional
  contact anticipation spreads required corrections earlier instead of repeatedly
  smoothing away their peaks and colliding again. The accepted centre step and
  second-difference limits are 10 and 2.5 output pixels per sampled frame.
- Area growth follows each piece's actual local deformation progress. It no longer
  assigns a thin daughter its eventual mass before its shape has stretched. Local
  thickness (coverage-weighted interior distance) measures temporary concentration
  relative to endpoint thickness; this is a proxy, not a full density optimizer.
- Fixed local fields are sampled directly on the output grid. Continuous extents
  replace rounded intermediate bounding-box sizes, avoiding double resampling.
  Small stroke-scale smoothing replaces strong blob-radius smoothing.
- A split starts from the parent's exact partitioned material. Sibling pieces can
  remain one attached body while they begin moving; once visibly separate, they
  cannot rejoin. Separate bodies still undergo collision checks. Attached coverage
  uses a clamped sum; overlap between unrelated bodies is rejected and independently
  checked. This changes the contact model, not just the timing weights.
- Correction tracks have continuous cubic interpolation between sampled positions.
  A smooth monotone display transfer replaces the old jump at half coverage.
  Inferred rigid matches continue to bypass residual morphology.

    python examples/katex-transport/render_continuity.py /path/to/clean --encode
    python examples/katex-transport/verify_continuity.py /path/to/clean

Outputs: `continuity/continuity-katex-animations.mp4`, six per-case movies, saved
frames and accepted centre trajectories, source/decoded receipts, diagnostics and
independent replay verification. Failed early trials remain in `continuity-initial`;
route rejections are logged rather than delivered. Cached accepted trajectories
are research results: replay their saved centres through the field sampler to
reproduce frames independently of the path-search iteration history.

Fifty-eight Python tests include shrinking time intervals around a split handoff,
mid-morph subframe checks, monotone separation, exact endpoints, continuous display
contrast, sampled/cubic trajectory agreement and anticipatory contact corrections.
These tests do **not** establish universal no-snap or continuous-time nonintersection
proofs. Raster connectivity repair and discrete collision projection remain.
Clamped attached coverage is not a solved physical material-transfer model; global
area reversals and residual local changes must remain visible in the evidence.
The independent verifier checks every saved frame's ownership/replay, then encoded
held endpoints and near-target convergence. Videos still show one animation at a
time, using only endpoint images and no formula-specific mapping hints.

### Future native endpoint distance fields

The owner is separately developing GPU math/text typesetting and symbol distance
fields. That work is independent and has not been modified or integrated here.
A future input adapter should accept evaluable signed-distance geometry plus
bounds, units, sign convention and glyph/layout transforms (including baselines
and placement). Gradients/outlines and stable geometry identifiers can be optional.
This avoids rasterizing outlines and recovering them from pixels, and supports
better boundary, thickness, hole and gap measurements. It does not itself solve
correspondence, branching or material conservation. Endpoint-only inference and a
raster fallback remain useful; no manually supplied transition hints are required.
No GPU/compiler work, deployment or new runtime dependency is adopted here.
