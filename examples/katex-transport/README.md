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
