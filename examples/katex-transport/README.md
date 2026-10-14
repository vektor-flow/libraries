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


## Local pinch-off without long tethers — latest owner correction

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
