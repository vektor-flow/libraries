# VKF native LaTeX rendering: shared handover

Updated 15 October 2026 for joining the native LaTeX renderer and VKF integration work.

Adopt the native LaTeX endpoint renderer in VKF's shared GPU viewport. The browser
uses prepared native font metrics/outlines, independent parsing/layout and WebGPU;
LaTeX and PDF engines are development oracles. This is a working subset with
explicit diagnostics. Complete document equivalence remains failing. Morphology
is a separate project and is outside this integration.

## Source and preview

Repository `vektor-flow/libraries`, branch `codex/gpu-math-20261014`.
Worktree `/home/viktor/Projects/Vektor Flow/.worktrees/gpu-math-20261014-libraries`.
Read `STATUS.md` and `examples/gpu-math/typing-demo/README.md` first. This handover
supersedes the native renderer information in `VKF_MORPHOLOGY_HANDOVER.md`;
that older file's source pins, counts and solver integration are historical.

The live document UI is https://vektorflow.org/previews/gpu-math-typing/document.html.
The tested runtime is source `c0be0ab`; source checkpoint `e26182d` also records
the live containment verification. The site repository is
`vektor-flow/vektor-flow.github.io`, published commit `2400f32`, Pages workflow
`38720679089` (succeeded). Its worktree is
`/home/viktor/Projects/Vektor Flow/.worktrees/math-typing-site` on
`codex/math-typing-20261014`. Live file hashes and gestures are recorded in
`pan-containment/publication.json` under the evidence root below. This handover
update changes documentation only; it does not require another renderer release.

## Join forces: scope and proposed work split

The shared goal is native LaTeX layout rendered inside VKF's GPU scene, with
responsive editing and sharp zoom. The long-expression rendering target is
under 10 ms; this is a target, not a measured full-document guarantee. LaTeX is
the development reference, with no runtime LaTeX or KaTeX dependency. Complete
document fidelity is still unfinished. Morphology remains a separate project.

These are proposed responsibilities, not assignments to an already-running agent:

- **VKF integration owner:** extract the current packet builder and draw pass,
  use the host's shared device/resources, connect document cameras and clipping,
  and preserve premultiplied blending and screen-space antialiasing.
- **Layout and parity owner:** fix native class/package behavior, paragraph and
  page building, font selection and missing commands; retain original TeX/PDF
  fixtures and reproduce failures with geometry and pixel evidence.
- **Shared boundary:** agree the packet, camera uniform and asset versions before
  changing them. Keep atlas, font metrics and shader pinned together. Coordinate
  edits to shared files; land small tested commits from separate worktrees.

The first joint task is to locate the earliest sample2e page 2 divergence while
preserving its accurate page 1. Reduce that divergence to a native LaTeX fixture,
fix the responsible layout rule, then regenerate affected pixel captures and a
fresh glyph-identity/geometry audit. Report which failures improve or regress.
Do not reuse a geometry audit after layout or font mappings change. In parallel,
the host integration can consume the unchanged packet contract described below.
Native VKF integration has not yet been completed.

Keep the existing renderer as the public entry point. The requested UI is compact
Render/Edit, page selection, document-local drag/pinch/wheel and optional fit
actions. Panning must leave the site stationary. Do not add a zoom-grid/report
interface or zoom buttons to the main flow; keep diagnostic suites as developer
tools. Preserve the archived evidence rather than turning it into another site.

## Layout and draw contract

`typing-layout.mjs` exports `typeset(source, data.maps, options)`. It returns
positioned glyph/rule/placeholder items and diagnostics. `document-layout.mjs`
exports async `typesetDocument(source, data, {assets})`, returning pages, configured
class/package modules and diagnostics. `document-text.mjs` provides native prose
shaping, paragraph breaking, optical fonts, ligatures, kerning and hyphenation.
`latex-modules/` separates the article class, core expansion and package subsets.
Unsupported packages/options/commands must remain visible as diagnostics.

Use `typing-demo/typing-data.json`, `atlas.rgba.gz` and `draw.wgsl` together.
The atlas is linear RGBA8, 4096 by 8192, 128MiB decoded. Preserve all font notices
and source bundles, including CM-Super. Treat loading, memory and later atlas
partitioning as integration concerns. Do not use an sRGB atlas.

The live instance packet is16 float32 values,64bytes: rectangle4, UV4,
straight RGBA ink colour4, material information4. Material information x
selects MTSDF glyph0, analytic rectangle1, raster image2, or diagnostic96dpi
coverage3. The latter is a fixed-size development cache and must not become the
interactive zoom path. The shader's16byte uniform holds world viewport size
followed by world camera origin (currently named `View.unused`). The shader outputs premultiplied colour; host blending
is premultiplied `one / one-minus-src-alpha`.

`typing-demo/document-demo.mjs` demonstrates packet construction and `encodePage`.
Extract that draw logic into VKF's existing device, texture lifetime and shared
render pass. The standalone demo's DOM handlers/device initialization are not a
library API. `field-packet.mjs` is an older whole-expression texture adapter;
it is not the current per-glyph document packet producer.

CPU parsing/layout is still present. Runtime rendering does not call KaTeX,
LaTeX, PDF rasterization, browser text or Canvas2D text. Development mapping uses
TeX Live; separate MiKTeX compatibility has not been qualified.

## Rendering and interaction improvements

Incomplete input updates immediately: missing scopes are inferred for preview,
open operands receive placeholders, and deleting an exponent removes its glyph
without waiting for the caret operator to be deleted. Inline/display styles,
Greek and large operators, nested scripts, roots, matrices/cases, accents,
arrows, braces, lines, units and math alphabets have documented subset support.

Document text uses native optical metrics. Explicit control-space previously
counted following ordinary whitespace twice; that is fixed. The frozen geometry
audit matches all746 small2e glyphs within0.0742px and all1693 sample2e page1
glyphs within0.1217px at96dpi. Later pages remain incorrect.

The camera supports two-finger pinch, cursor-anchored wheel zoom and one-finger
or left-mouse dragging, including at1x. `document-gestures.mjs` coalesces changes
onto animation frames, captures pointers and rebases when fingers change.
`updateDocumentView` redraws the active page using retained geometry/canvas;
it does not retypeset or rebuild the atlas. Each page has its own camera. The document sits in a fixed clipped viewport;
pan/pinch/wheel do not scroll the site. Page selection switches canvases in
place, and DPR-aware resize keeps the canvas matched to the available area.
Render collapses the phone editor; Edit restores it. More contains page selection
and optional Fit text/Fit page actions. There is no zoom slider/button.

Glyph AA uses screen derivatives. Analytic bars now use rectangle/pixel overlap
from `fwidth(local)`. The old one-document-unit smoothing band grew with zoom:
the root-bar profile at28.6x had36 partial pixels; the corrected profile has1.
The fix also covers fraction bars, over/underlines, box/table borders, brace
connectors and arrow shafts. Keep this shader correction when porting packets.
Finite MTSDF sampling still cannot guarantee exact curves at unbounded zoom;
the tested camera range is1–64x. Analytic/adaptive vector fallback remains future
work for a stronger guarantee.

## Full document zoom evidence

Evidence root:
`/home/viktor/Projects/Cuvami/staging/artifacts/gpu-math/20261015/`.
The original four PDFs are in `latex-completion/documents/`. The initial exhaustive
scan is `document-zoom-grid/full-v2/`; original96dpi/identity evidence remains in
`document-parity/corpus-mtsdf-frozen/`. No source PDF was changed to improve a score.

The grid scans every pixel of every PDF/GPU page union at1x,2x,4x:1372 tiles,
916522896 core pixels,46 original pages versus49 GPU pages. A1px halo protects
neighbour checks; aggregate ink counts use disjoint cores. Blank tiles and the
three extra AMS GPU pages are included. Runtime file hashes and original PDF
hashes identify the capture. Higher zooms are targeted rule checks through64x,
not exhaustive full-document scans at64x.

`benchmark_document_zoom_grid.mjs` streams native WebGPU readbacks.
`document_zoom_worker.py` compares original PDF tiles using development-only
PyMuPDF1.28.2. The original report used Poppler, so raw scores from these two
oracles are not directly interchangeable. `build_document_zoom_report.py`
verifies complete tile coverage and only inherits the original font/glyph audit
after exact layout-item and mapping hashes match. Every nonblank tile retains
PDF/GPU/error PNGs. The report exposes the grid, worst tiles, local component
failures, ink overlap, one-pixel coverage and RGB error. White background never
increases ink accuracy. Missing/moved glyphs remain separate failures.

`verify_document_tiles.mjs` checks the tile capture against full-frame GPU output
for text, math, rules, colour, images and clipped tails. All nine1/2/4x comparisons
match exactly. `verify_document_zoom_report.mjs` checks147 page/zoom grids and438
worst-tile views at phone width, without errors/overflow. `verify_rule_edges.mjs`
checks60 cases through64x, including isolated horizontal/vertical thin rules.
At1x, adjacent glyphs can overlap a fraction/underline profile; those cases check
visibility while phantom fixtures isolate thin-rule edges.

The previous validation gap was real: normal-size page comparisons were already
failing, and zoom tests measured an H stem rather than analytic bars. They did not
establish scale-independent rule edges. Keep both the exhaustive page grid and
the dedicated multi-scale rule suite in the acceptance workflow.

## Fixes started from the completed scan

The figure fixture failed at4x because the PDF image has interpolation disabled
while the GPU enlarged it with linear filtering. Raster-image magnification now
uses nearest filtering, retaining linear minification and linear font sampling.
The affected fixture rescan is `document-zoom-grid/figure-nearest/`.
One-pixel ink coverage at4x improves98.6659% to100%;2x remains100%.
The1x local edge policy still fails, so the full fixture is not declared matched.

Inline `\begin{math}` / `\end{math}` now preserves surrounding paragraph flow and
uses the same inline layout as dollar delimiters. A regression compares complete
positioned pages for the two equivalent spellings. The AMS diagnostics decrease
62 to57; its page count remains44 against the original41. A fresh native geometry
audit is retained in `document-zoom-grid/math-env-fixed-geometry.json`.
Same-page unmatched reference glyphs14878→14882, extra14749→14729 and
moved/wrong-size26304→26299 remain large and change in both directions.
The syntax fix does not establish an overall document-accuracy improvement.

## Remaining work and acceptance

Start with the earliest divergence on sample2e page2: its page1 is already
positionally accurate. Repair paragraph/list/page-builder behavior before trying
to tune whole-page pixel percentages. AMS still needs many text commands,
package scopes, dimensions, display/tag behavior and correct page/float placement.
Standard integrals currently use an esint-prepared map; package-specific native
integral fonts must be selected correctly for documents without esint.

A full-document pass requires matching pages, >=99.5% reference AND GPU ink within
one physical pixel, >=95% local component coverage, and native glyph identity/
position/size checks without missing/extra/unmeasured glyphs. Preserve RGB metrics
and every failing tile. Never align/crop acceptance inputs or use the diagnostic
coverage cache as a distance-field zoom proof. Snapshot results predate later
fixes unless an affected case is explicitly rescanned with its own hashes.

All current browser validation uses explicit SwiftShader.30 Node tests pass.
The under10ms full-document/physical-phone goal remains unestablished. The existing
physical GPU stop in the Cuvami chat handover still governs hardware testing;
read that checkpoint before attempting physical browser/GPU runs. Preserve all
failed trials, original PDFs, licenses and other agents' worktrees.

## Latest containment verification

`pan-containment/` contains the latest local and live interaction receipts.
`gestures/gestures.json` and `live/gestures.json` cover mouse drag at 1x,
drag beyond canvas bounds, anchored wheel zoom, pinch with translation,
pinch-to-one-finger transition and single-touch pan. They check unchanged site
scroll, header position and viewport bounds, with no GPU/page errors or overflow.
`phone/phone.json` covers 320/390/430 px portrait and 844 px landscape layouts.
`dpr/dpr.json` checks DPR 3 backing resolution and 1–2 physical-pixel rule edges
at 1/4/16/64x. `tiles/tiles.json` retains nine exact tile/full-frame matches;
`uploads/document-ui.json` verifies file/image upload and direct developer report
navigation. These are software-browser checks, not physical iPhone qualification.

Before the next implementation change, read the current `STATUS.md` and
`typing-demo/README.md`, inspect worktree status, and identify who owns each
shared file. Keep source fixes and evidence together before publishing the
existing preview. Documentation-only changes do not need a site deployment.
