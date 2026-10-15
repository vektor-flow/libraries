# Live typing test

The GitHub Pages preview at `/previews/gpu-math-typing/` is linked from Coming soon.
It renders the current source on a WebGPU canvas. Missing script/fraction operands
become empty outlined placeholders; unfinished groups, environments and nested
left/right scopes are closed for preview only. Source remains untouched and deleted
operands never come from a previous valid formula. Unknown commands show a placeholder.

Inline and Display controls choose real TeX text/display math styles: operator size,
side versus stacked limits, fractions and script placement change accordingly.
Explicit style commands and limits/nolimits override the defaults. All lowercase
and uppercase Greek are available, including upright aliases for capitals normally
written with Latin letter commands in TeX. Regular Sigma/Pi differ from sum/prod.
Contour integrals come from the development-only esint package.

Matrices and column vectors support matrix, pmatrix, bmatrix, Bmatrix, vmatrix,
Vmatrix, smallmatrix, cases, aligned, align, gathered and basic clr array alignment.
Nested fractions, scripts, power towers, angle/floor/ceiling brackets, explicit
big/Big/bigg/Bigg and nested left/right are supported. Very tall delimiters extend
font-derived stems; those extensions are a visual approximation of TeX recipes.
Standard accents include hat/widehat, tilde/widetilde, bar, vec, dot/ddot,
acute, grave, breve, check and mathring. Overline/underline span their arguments;
fixed font brace pieces and connecting rules support nested overbrace/underbrace
with labels. Overset/underset/stackrel preserve the underlying relation class.
Arrow families include long, hooked, diagonal and harpoon glyphs; over/under
left/right/bidirectional arrows and xrightarrow/xleftarrow with optional lower
labels use font-derived heads and continuous shafts. Triple/quad dots use an
independent dot arrangement; exact AMS placement of those two accents is unverified.
Arrow fixtures verify outer ink envelopes and label positions, not shaft interiors.

Common siunitx syntax supports qty/unit, legacy SI/si, num and ang, upright SI
base/derived units, prefixes, per, squared/cubed/tothe/raiseto, decimal/scientific
numbers, digit grouping, angles and literal unit abbreviations such as m/s.
Options: per-mode=power/symbol/fraction, group-digits and output-decimal-marker.
Unknown options/units produce draft diagnostics. Rounding, uncertainty notation,
locale profiles, lists/ranges, custom unit declarations and the full siunitx
option surface are not implemented. units.mjs is independent of the package.
The development oracle uses unmodified siunitx 3.6.4 (2026-10-12).

Arbitrary packages/macros and full TeX document compatibility are not implemented.
See the extended math/document notes below for newly supported roots and arrays.

Real LaTeX is used only during development. The browser loads 1,541 mapped symbols
in display/text/script/scriptscript styles (6,164 keys, 3,675 distinct outlines),
using a 4096×8192 MTSDF atlas and one batched draw per edit. No LaTeX, KaTeX,
font loading, DOM math or Canvas2D text runtime is used. Native VKF compiler
integration is pending. Source is never evaluated as JavaScript or inserted as HTML.

Input-to-GPU timing measures handler entry through layout, upload and completed
queue submission. The next animation frame is an estimate, not physical screen
presentation. Cold download and pipeline preparation are reported separately.
The p95 window covers 120 updates; 10 ms is a target, not a guarantee.
Budgets: 12,000 source characters, 3,000 atoms, 32 nested levels, 32 columns,
100 matrix rows, 12,000 draw instances and 2,500 CSS pixels of canvas height.
Extra-wide grouped atoms and taller output may clip.

Reproduce by running map_symbols.py --extended --style STYLE --oracle-extras DIR
for the four styles into fresh typing-STYLE directories. DIR contains the unmodified
esint LaTeX/Type1 oracle files. Run prepare_typing.py --oracle-extras DIR; copy the
atlas and typing-data.json here, and copy typing-layout.mjs draft-parser.mjs and units.mjs
from the parent directory. Serve through HTTPS/localhost. verify_extended_layout.py
checks fresh native LaTeX ink bounds and fraction rules in either mode. Node tests
cover draft recovery and deletion; verify_typing_browser.mjs drives real textarea
input, style changes, feature examples and canvas output using headed SwiftShader.
Physical GPU stop remains unchanged.

MIT applies to runtime source. Font-derived atlas data retains applicable AMS/SIL
OFL and esint/LPPL notices; MSDFgen also has its own notice. EC/TC glyphs have separate notices and their complete unmodified source archive. esint-source archives
provide the unmodified upstream sources. esint symbols are mapped to a differently
named combined atlas and are never installed as modified esint font files.

For this extension, --reuse DIR reuses earlier oracle glyph folders without
changing them; add siunitx.sty and its translation dependency to the development
oracle directory. Font skew, advance and accent-font x-height are extracted from
actual TFM/DVI data. Include the unmodified siunitx and EC source archives and
notices when distributing these prepared assets. Common geometry is checked
against fresh LaTeX independently; browser tests also drive partially typed accents,
arrows and quantities. All recorded browser evidence uses software SwiftShader.

## Page flow and appearance

In Math input, a top-level `\\` or `\newline` starts a new left-aligned row.
Matrix/environment row separators retain their existing meaning. This bare-math
linebreak is a preview extension; standard LaTeX uses a multiline environment.
Row spacing follows struts and the actual height/depth, so tall fractions and
scripts do not collide. General equation alignment uses the existing aligned
or array support; automatic wrapping of grouped math remains bounded.

Text + math input uses the same Computer Modern Roman family and measured
native advances, kerning, ligatures, punctuation and common Latin accents.
Embed math with $…$ / $$…$$ or \(…\) / \[…\]. Blank lines create paragraphs;
\\ creates a hard break. Prose uses independent greedy word flow; it does not
implement TeX paragraph optimization, justification or automatic hyphenation.
Long words can split between glyphs. Source text is never inserted as HTML.

Page-width and text-size sliders reflow or scale the canvas. The colour swatches
and picker change default ink; explicit source colours stay assigned to their
own glyphs. Opacity affects both default and explicit ink so blending is visible.
All glyphs/rules carry their colours in the GPU instance packet, with premultiplied
alpha. Colour-only edits reuse cached layout and submit a new instance draw.
Named \color and \textcolor, HTML/RGB/rgb values and nested colour scopes are
supported in math. The Colour example includes several source colours.

Native math alphabet families include mathrm, mathbf, mathit, mathsf, mathtt,
mathnormal, mathfrak, mathcal, mathscr, mathbb and boldsymbol (bm alias). All
families have display/text/script/scriptscript mappings. Calligraphic and RSFS
script use their native capital alphabets; missing lowercase is a diagnostic,
not a different glyph from that font slot. AMS mathbb capitals retain their
standard appearance; lowercase/digits use a documented BBOLD extension, with
mathbbold selecting BBOLD for the whole Latin/digit alphabet. This extension
is checked against the native BBOLD LaTeX alphabet, not unsupported AMS slots.
The regular Roman/bold/italic/sans/monospace/normal faces also map Greek capitals;
boldsymbol handles the mapped Greek and ordinary symbols. Full arbitrary font
package selection and every possible alphabet/glyph combination remain outside scope.

Prepared assets include new AMS/Euler notices and the unmodified RSFS/BBOLD source
archives. The GPL mathrsfs adapter is used only by the development oracle; its
source and GPLv2 text are supplied separately. It does not execute in the browser.

## Equation transitions

The owner rejected the following backend for the requested general visual
morphology. Its compact UI can be retained, but symbol pairing/crossfades must be
replaced with the shared solver. See
[the VKF implementation handover](../VKF_MORPHOLOGY_HANDOVER.md).


Use the **Equations** tab, type or select examples independently for
A and B, and press **Transform A → B**. Duration, swap and a scrub slider are
provided. Matching atlas glyph regions are paired once by nearest position,
then their rectangles and ink interpolate with quintic easing. Different outlines
crossfade, retaining their own atlas coordinates. This is visual matching rather
than semantic algebra, contour morphing, or the other chat's merge/split solver.
Layouts are prepared once per transition; each animation frame uploads a bounded
instance packet and draws it on the existing WebGPU canvas. The CPU computes
correspondence/interpolation; native VKF compiler integration remains pending.
Editing either source or appearance cancels playback. Resizing preserves the
paused progress, and reduced-motion users get an immediate endpoint transition.
The combined packet is bounded by the existing 12,000-instance limit.

Phone widths stack editors and controls, retain 16px editor text and at least44px
button/swatch targets. Compact **Equations**, **Style** and **Examples** tabs keep controls near the
canvas; notes are reduced to a closed help section. Phone viewport/software-browser checks do not certify
physical iOS/Android WebGPU support or actual device latency.

## Extended math and modular documents

The 2026-10-15 renderer adds square/indexed roots, nested radicals, binom/dbinom/
tbinom, genfrac with numeric rule dimensions, not overlays, pmod/pod/mod/bmod,
operatorname*, boxed/fbox, phantom variants, smash options, mathstrut and numeric
hspace/kern/mkern spacing. Text arguments support nested textbf/textit/textsf/
texttt/emph, escaped characters, native kerning/ligatures and italic correction.
Roots and tall delimiters use native font next-larger chains and extension pieces;
the old cropped/stretch approximation has been replaced for supported delimiters.

Equation/equation*, align/align*, split, gather/gather*, multline/multline* and
gathered are recognized, alongside prior matrices/arrays. Numbered variants add
tags, starred variants omit them; tag/tag*, notag/nonumber and optional row gaps
are supported. Array clr specifications include vertical bars, hline and cline.
Middle delimiters inherit their left/right scope size. Full TeX display layout
and line placement remain subject to the independent document comparison.

`document.html` accepts a whole .tex source and local image assets. It uses
`document-layout.mjs` and separate class/package modules in `latex-modules/`.
Article flow, basic section headings, inline/display math, page breaks, simple
section/equation/figure references and includegraphics image boxes are available.
PNG/JPEG/browser-decodable images draw as GPU textures in the same page pass as
distance-field text. Upload assets with the names used in the source. PDF image
assets, general float placement and complete document classes are not supported.
Missing assets/imports emit diagnostics. Multi-row/custom-tag reference binding
is explicitly incomplete. This is an experimental document preview, not a
pixel-equivalent replacement for TeX document layout.

Prepared fields now contain1541 symbols in four styles:6164 keys/3675 outlines.
Height-sorted atlas packing retains4096×8192 RGBA8 (128MiB decoded); glyph roles
include raw CM extension pieces. All existing font notices/source archives apply.
Font space metrics and style-dependent rule thickness come from native TFM data.

`fetch_document_corpus.py` downloads unmodified LaTeX project small2e/sample2e
and AMS testmath sources with reviewed hashes. `benchmark_latex_documents.py`
measures fresh-process PDF compilation and96dpi page rasterization separately.
`benchmark_documents.mjs` renders original source independently in WebGPU and
measures layout/queue completion. A separate untimed framebuffer readback supplies
pixels without CSS screenshot scaling. `compare_document_pixels.py` compares all
pages without registration/cropping and returns failure for incompatible output.
`build_document_report.py` creates the source/PDF/GPU/difference browser report.
Full-document acceptance is failing; successful formula fixtures do not override
those page-level failures. Timing stages and actual software backend are explicit.

## Accuracy and practical zoom — 2026-10-15

The document renderer defaults to MTSDF at every zoom. Zoom1–64× and drag-to-pan
use a fixed backing viewport and a camera, rather than enlarging a canvas bitmap.
Fragment derivatives keep the antialias transition in device pixels. UI backing
resolution follows CSS width and device pixel ratio; comparison captures explicitly
request96dpi. DPR3 phone simulation verifies1098 backing pixels for366 CSS pixels,
and a one-pixel transition on the tested H stems at1/4/16/64×. Curved g, Greek,
integral and dollar fields have separate zoom captures. This is bounded software
browser evidence, not infinite-resolution curve or physical-phone qualification.
A finite atlas can eventually show contour approximation; analytic outline
rendering remains the route to stronger unbounded-zoom guarantees.

Two text-companion symbols previously inherited PK bitmap outlines. Their eight
style keys now use six CM-Super vector outlines with the original TFM box/advance
metrics. Original PDF references remain unchanged. The exact unmodified Type1
programs, TS1 encoding, copyright, license and hashes are in `cm-super-source/`.
Those font-data terms apply independently of the repository's code license.
No global TeX font maps were changed during this work.

Document text now has native optical fonts for article headings/titles/authors
and footnotes, standard English TeX hyphenation data, paragraph demerits with
stretch/shrink, and reconstruction of unbroken ligatures across discretionary
hyphen positions. Explicit control-space handling, escaped-symbol space factors,
italic corrections around font changes and text ellipsis kerns are corrected.
Simple orphan/widow protection, theorem/proof flow, lists, quotations, verse,
references/citations, bibliography entries and footnotes are experimental subsets.
Author newcommand/renewcommand, aliases, optional arguments and simple conditionals
expand within resource limits. Verbatim examples retain their literal contents.
These additions do not establish full TeX page-building or arbitrary macro parity.

Accuracy is reported without moving or registering pages:

- Raw ink IoU and RGB errors remain visible. White background cannot inflate ink
  overlap; ink is defined as mean RGB below178/255 for these black/blue fixtures.
- A second measure reports ink within a one-pixel x/y neighbourhood. A99.5%
  aggregate threshold is combined with local connected-component checks.
- Native PDF font/glyph identities and baseline positions are matched one-to-one
  on each original page. Missing, extra, unmeasured, moved and wrong-size glyphs
  are counted separately. A good page average cannot hide a missing symbol.
- Local-error maps and PDF/GPU/error close-ups show where the remaining error lies.
  Connected components are glyph parts, not necessarily whole characters.

`compare_document_pixels.py` now accepts `--mapping typing-demo/typing-data.json`
and `--oracle-extras PATH`. `mutool` supplies independent PDF vector traces for
`compare_document_geometry.py`; it is never a runtime dependency. The metadata's
`glyphParts` come from the development DVI files, including composite symbols.
All original reference pages and extra/missing GPU pages remain in the report.
Full-document acceptance still fails, especially the AMS testmath source.

`pdfPixels:true` is a separate96dpi calibration diagnostic: reusable Type1 glyph
coverage masks, generated without any document/PDF input, approximate the native
PDF rasterizer. It is opt-in, never the interactive zoom default, and automatically
falls back to MTSDF beyond1×. It must not be used to claim distance-field pixel
parity. The report provides separate views for both rendering paths.

The development preparation sequence is `prepare_typing.py`, then
`prepare_document_fonts.py`, `prepare_document_coverage.py`,
`prepare_glyph_provenance.py` and `prepare_vector_textcomp.py`. Each stage takes a
fresh output directory. The optional coverage stage requires freetype-py; glyph
provenance consumes the existing oracle DVI files. Vector text-companion generation
uses the supplied CM-Super Type1 programs and original native TFM files.

`window.renderDocument(source,{zoom:16,pan:[x,y]})` uses DPR-aware MTSDF rendering.
For reproducible comparisons use
`{scale:96/72,black:true,capture:true,forceLayout:true}`. Timed corpus runs force a
fresh layout on every trial; zoom/pan can reuse layout. GPU-completion times include
layout and are measured separately from the untimed readback. Software timings do
not establish the10ms target on a physical device.

## Phone document controls — 2026-10-15

Render folds the source editor, uploads, zoom and diagnostic panels, dismisses
text-field focus and returns the viewport to the preview. Edit reopens the
preserved source; Cmd/Ctrl+Enter renders it too. On screens up to600px wide,
Render fits the native content bounds into the canvas camera, removing wide
paper margins from the initial view. The collapsed Zoom panel exposes Fit text,
Fit page and the continuous zoom slider. No document reflow or glyph scaling
metrics are changed; this is camera framing. File selection renders into the
same preview. Failed initialization/rendering remains visible outside panels.

verify_document_phone.mjs exercises320/390/430px portrait and844px landscape,
preview placement, source reopening, uploads panel, zoom/reset and navigation
on explicit software WebGPU. Simulated touch/DPR coverage does not qualify a
physical phone browser or its on-screen keyboard.

## Direct document gestures — 2026-10-15

This supersedes the zoom panel described above. Pinch with two fingers or scroll
the mouse wheel over a page to zoom about the finger midpoint/cursor. Drag with
one finger or the left mouse button at any zoom, including1x; the page follows
the pointer. Touch-action is disabled only on the document canvases. Remaining
page chrome retains browser scrolling/zoom accessibility. Fit text and Fit page
are secondary actions under More, with a page selector for multi-page documents.
There is no zoom button or slider in the preview.

Gestures keep the existing canvas, native geometry and instance packets. A
coalesced animation frame redraws only the active page with a new camera uniform;
there is no LaTeX layout or atlas preparation per gesture. Every page retains its
own camera. Pointer capture survives dragging beyond the canvas; pinch/pan
transitions rebase on finger changes, and cancellation clears the active drag.
Camera zoom retains the tested1–64x bounds and derivative-based screen-space AA.

verify_document_gestures.mjs uses CDP multi-touch input plus real browser
mouse/wheel dispatch to check anchored zoom, one-finger drag, a lifted pinch
finger, cancellation, limits, pointer capture and independent page cameras.
Compositor captures separately check that a50×35px drag actually moves ink by
50×35px. This is explicit software WebGPU coverage, not physical iPhone/Safari
qualification. The original full-document accuracy report remains unchanged.

## Screen-space rule edges — 2026-10-15

The square-root vinculum, fraction bars, over/underlines and array rules now use
exact axis-aligned rectangle / pixel intersection in the shader. fwidth(local)
sets the physical-pixel footprint. The previous one-document-unit smoothing band
grew with camera magnification (36 partial-coverage pixels in the root-bar
profile at28.6x); the corrected root profile is one pixel at4/16/28.6/64x.
Thin rules retain area coverage instead of disappearing below one pixel.

verify_rule_edges.mjs records60 cases across1/4/16/28.6/64x. Horizontal and
vertical phantom fixtures isolate thin rules from glyphs; normal1x fraction
profiles can include adjacent glyph ink and are checked for visibility, while
magnified profiles must retain narrow edges. Test readback is96dpi in aDPR3
phone viewport using explicit software WebGPU. This does not qualify physical
Safari. The stored full-document comparison remains the original frozen capture;
its shader hash and pixel scores predate this correction. Native layout and
font mappings are unchanged; no new full-document parity claim is made.

## Exhaustive full-document zoom grids — 2026-10-15

Document pixel acceptance requires zoom coverage as well as the original96dpi
page/identity audit. `benchmark_document_zoom_grid.mjs` streams the entire union
of PDF and GPU page bounds at1x/2x/4x by default. Every1024px tile is captured,
including blank cells and extra/missing pages. A1px halo protects neighbour
coverage across tile boundaries; metric counts use disjoint tile cores. This
is exhaustive at the listed zooms, not a grid of sampled glyphs. Set
VKF_GRID_ZOOMS (up to64) and VKF_GRID_TILE for larger scans. High-zoom rule
fixtures through64x are separate; they do not certify every document pixel
at those higher levels.

The native oracle is development-only PyMuPDF1.28.2, replaying original PDF
vector display lists at the same absolute pixel coordinates. No PDF paths or
pixels enter runtime layout or glyph preparation. The browser capture API uses
the same packets, shader, texture and draw path as the live camera. Independent
tile-vs-full-frame checks cover text, radicals, fractions, rules, colour and an
uploaded image at1/2/4x; all nine captures match exactly, including clipped tails.
The original Poppler comparison remains unchanged; scores from different native
rasterizers must not be interpreted as a calibration-only improvement.

Run the driver with URL, original corpus directory and a fresh output directory;
set VKF_PYTHON to an environment with PyMuPDF/numpy/scipy/Pillow. It also requires
the existing explicit SwiftShader Playwright environment. Then run
build_document_zoom_report.py with output, corpus, frozen audited dataset and
rule-sharpness evidence root. The builder verifies every grid cell, pixel count,
no overlaps/gaps, and exact native-layout/mapping hashes before inheriting the
original glyph-identity audit. After layout/font changes, pass --mapping for a
fresh native glyph audit instead of inheriting old results. It refuses incomplete scans. The report exposes
all grid cells and their full-resolution PDF/GPU/error tiles, worst local errors,
raw ink overlap, one-pixel ink coverage, RGB differences and missing/extra pages.
Global white background never increases ink coverage. Full-document acceptance
still requires the identity audit and every tile to pass.

`verify_document_zoom_report.mjs` checks every page/zoom grid and worst-tile
views at phone width. `verify_rule_edges.mjs` remains mandatory after shader
changes; a normal-size PDF diff cannot establish scale-invariant edge softness.

Initial zoom-grid follow-up fixes: raster images now magnify without interpolation,
matching the native PDF's default. The figure rescan improves4x ink coverage
98.6659%→100%;1x local edges still fail. Inline begin/end math environments now
share dollar-math paragraph geometry. The full scan remains a saved pre-fix
baseline; affected-case rescans have separate source hashes. The fresh AMS
geometry audit and per-direction changes are recorded in the VKF handover.

## Contained document viewport — 2026-10-15

The renderer now uses a fixed application shell and document viewport. Panning
and zoom operate inside that surface; the site stays still. Page selection
shows the chosen canvas in place. Automatic viewport sizing observes the
remaining screen area and DPR, including editor collapse and rotation; explicit
validation scales still capture complete native pages. The editor keeps its
own scrolling. Nonpassive touch/gesture cancellation on the document surface
supplements touch-action/overscroll containment for Safari. Report navigation
is removed from the renderer so its controls focus on rendering and viewing.

## Complete arXiv project corpus — 2026-10-15

`../fetch_arxiv_corpus.py OUTPUT [--cache DOWNLOADS]` preserves four versioned
projects and their original PDFs. `../arxiv-corpus.json` pins reviewed SHA-256
hashes for both downloads. It rejects changed bytes, archive traversal/links,
recursive inputs and resource-limit violations. Every extracted file is hashed.
`source.tex` substitutes local input files for the independent renderer; original
project files and compressed downloads remain intact. Sources are not rewritten
to remove failing packages, figures or sections. Missing inputs stay diagnostic.
Original article/font/asset terms apply; these downloads are local test evidence,
not relicensed library content or a publication authorization.

The four PDFs contain 80 original pages. The renderer currently produces
19/27/16/0 pages against 15/39/15/11 originals. The last project uses unsupported
`amsart`; its 11 missing pages remain failures. Conference styles, bibliography
packages, custom floats, tables, PDF/EPS images and long paragraphs remain major
limits. One paper takes about 38 seconds for layout on this software test host;
there is no full-document performance acceptance. Pixel comparisons include all
original pages and all extra GPU pages, without alignment/cropping.

New explicit package subsets: `bm`, `amstext`, `amsbsy` and `url`. The first three
expose already mapped bold/text math; they do not establish arbitrary package
compatibility. Default short ASCII `url` arguments retain literal percent, hash,
underscore, backslash and other punctuation through macro/comment processing.
Native OT1 tilde lowering uses the font's x-height. URL styles/options, line
breaking, whitespace and non-ASCII normalization remain diagnostic limitations.
Nonbreaking text spaces use ordinary interword width even after a period.

Evidence is in Cuvami `staging/artifacts/gpu-math/20261015/arxiv-expansion/`.
Original downloads, baseline/intermediate captures and rejected trials are retained.
`audit-final/` is the fresh full-page pixel/glyph audit of current renderer bytes;
`audit-corpus/` adds three controlled fixtures and three earlier document cases.
`report-final/` exposes all pages, differences, local-error maps, original PDFs,
source archives and per-page audits. Downloaded PDF compile times are unmeasured;
report timings state the actual sample count. Set `VKF_DOCUMENT_TRIALS=1` for a
correctness scan; the existing default remains three timing samples.

The URL and nonbreaking-space reductions pass strict pixel/glyph acceptance;
the bold-package fixture retains an existing display-placement failure. The
sample2e page2 spacing correction reduces moved/wrong-size glyphs 979 to 948,
while preserving all 1,693 accurately placed page1 glyphs. Its later-page failures
remain. Existing small2e and figure glyph geometry is unchanged. These are bounded
software-WebGPU checks, separate from exhaustive zoom grids and physical devices.

## Native flow corrections — 2026-10-15

All3559 glyphs on sample2e's three original pages now pass the native identity,
position and size audit, including the previously failing pages2/3. Normal-size
ink coverage improves58.05%→99.45% mean; strict pixel/local-component acceptance
still fails. The remaining full-paper and raster failures stay in the report.

`tex_font_metrics.py` reads the first executed match in each TFM lig/kern program.
The installed fontTools parser had overwritten earlier kerns with shared-tail
entries (e.g. native `va` is-.055555em rather than-.027779em). Both preparation
scripts now use that loader; `repair_font_kerns.py INPUT OUTPUT --oracle-extras PATH`
refreshes kern metadata alone. Native `\text{value}` width is22.50006pt.

`prepare_vector_textcomp.py --add-text-bullet` appends TS1 bullets using the
preserved CM-Super font programs and native TFM metrics. A flat `cm-super-source/`
font directory is accepted. Existing prepared vectors/UVs are reused, every changed
atlas pixel lies within a new bullet tile, and repeating preparation is exact.
No existing glyph outlines or font/atlas dimensions are changed.

Paragraph math now exposes native stretch/shrink glue and binary/relation break
penalties. Explicit hyphens retain their glyph when breaking. Article quote/list
spacing distinguishes nesting and entry mode; verse preserves hanging indents.
Text resumes correctly after lists/displays, including intervening figure spaces.
Normal and short display skips are selected from actual preceding line extent.
These remain bounded article rules, not arbitrary document-class emulation.

The line breaker merges paths with equal future cost dependencies at each break.
It retains fitness, penalties, first/forced indents and the best predecessor;
no line-count objective or looseness is currently implemented. Adding such an
objective would require revisiting the dominance key.160 seeded comparisons with
the old state key are exact. The prior38-second software layout is now about288ms
in the final single-sample browser audit; this is not physical-phone timing.

Latest evidence: `document-errors/` beside `arxiv-expansion/`, with15 documents,
133 original reference/118 GPU pages and a fresh mapping audit.39 Node/16 Python
checks,9 exact tile/full captures and471 present/93 missing report views pass.
Full arXiv documents/AMS still fail; arXiv aggregate coverage slightly regresses.
The report preserves those failures. Shader-alpha experiments are retained as
rejected trials; the default MTSDF shader is unchanged. No site was published.
