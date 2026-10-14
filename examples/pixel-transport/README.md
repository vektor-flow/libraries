# Pixel-only correspondence research

The goal is a general raster-to-raster transformation, with inferred parts rather
than required word labels/object IDs. Matching and segmentation should be solved
jointly across scales. Use rigid/similarity/affine motion for each compatible part;
only residuals morph. Colour, multiscale shape, connectivity and appearance can
form a higher-dimensional matching descriptor, but descriptor distance does not
replace physical-space collision constraints. This prototype is the first rigid
foreground slice, not that complete solver.

## Implemented

- Input: two binary foreground masks. No OCR, word labels, source drawing commands
  or authored IDs enter segmentation/matching. Fixtures generate text with a
  system font, then discard that information before inference.
- Isotropic dilation defines a configurable grouping scale; original foreground
  pixels, including holes, remain the transported material. This is a heuristic,
  not semantic segmentation. It can group letters into words or complete lines.
- Per-region rotation search/refinement uses symmetric nearest-sample distance.
  Linear assignment matches regions by geometric fit plus mass discrepancy.
  There is no forced correspondence by screen order; a changed region can report
  needs-deformation while another independently reports rigid.
- Rigid geometry moves under a quintic clock. Translation and rotation introduce
  no morphology. Curved routes share endpoint position/velocity/acceleration rules.
- A bounded search tries simultaneous lateral detours. At 65 samples, separation
  is checked with conservative per-region motion margins: 1.875 times (translation
  length + four times detour amplitude + radius times rotation angle), divided by
  128, plus two pixels for raster support. Positive clearance bounds inter-object
  material separation between samples for this rigid path model. Canvas clipping
  is checked at those sample times. No arbitrary-shape navigation completeness or
  global optimality is claimed. Impossible/unsupported requests raise errors.
- Each source pixel carries unit material mass. Bilinear deposition preserves
  total mass numerically; displayed alpha clips density at one and is not itself
  conserved mass. No source/sink is introduced to match raster aliasing artifacts.

The sampled registration tolerance is heuristic (2 pixels RMS and 3.5% raster mass
change). A transformed raster is not exact target-pixel equality: the 32-degree
example estimates the correct rotation but thresholding/resampling changes the
input mask's covered area. Exact endpoint raster reconstruction, linear RGB/alpha
transport, ambiguous/occluded parts, object split/merge, automatic scale selection,
full affine estimation without correspondence, and residual deformation all remain
research. Do not market this as an arbitrary-image morphing solver.

The separate browser-ui/vf-object-transport.mjs adapter accepts explicit object
identity and atom correspondence. It demonstrates independent affine/residual fits
(one object translates while another morphs), and is intentionally distinguished
from the pixel-only inference path. Future inferred correspondence should feed the
shared geometry engine; these are not two product-specific visual engines.

## Reproduce

Use a separate virtual environment with requirements.txt. The renderer needs ffmpeg
with H.264 and the system DejaVu Sans font. No font file is redistributed.

    python -m unittest discover -s examples/pixel-transport -p 'test_*.py' -v
    python examples/pixel-transport/render_movies.py /path/to/evidence

Three MP4s: real sentences exchange positions without overlapping; a sentence
rotates 32 degrees without morphing; a triangle and annulus exchange places by
travelling around each other. Each clip has 180 frames at 24 fps (7.5 seconds).
Receipts contain matching errors, path clearance, component count and deposited
mass ranges. Rendering is an offline CPU study, not VKF compiler or GPU acceptance.

2026-10-14: six pixel tests, 27 shared embedding checks and 88 original library
checks passed. Three videos rendered; midpoint/end frames inspected for legibility.
Evidence: Cuvami/staging/artifacts/embedding-transport/pixel-movies. Earlier browser
verification remains historical and was not rerun for these standalone scripts.
