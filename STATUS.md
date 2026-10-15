# Direct pinch, wheel and drag for document cameras — 2026-10-15

Replaces the phone zoom panel with two-finger pinch, cursor-anchored wheel zoom,
one-finger panning and left-mouse dragging, including at1x. The pointer/finger
anchor stays fixed during zoom; fingers can be lifted/added without a jump.
The existing canvas and draw packets remain in place. Camera redraws are
coalesced to animation frames and redraw only the active page, without layout
or texture rebuilding. Multiple pages retain independent cameras; More contains
a page selector and the optional Fit text/Fit page actions. Native browser
scroll/zoom remains available outside the document canvases.

Evidence: Cuvami staging/artifacts/gpu-math/20261015/document-gestures/.
The first two local touch-driver attempts selected the wrong release event;
local-v3 and final check actual pinch-to-one-finger transitions. No physical GPU
or phone testing was performed. Document geometry/atlas and previous full-match
failures are unchanged. Local gesture, four phone viewports, DPR3 and desktop1/4/16/64x edge checks
pass; uploaded figure and all187 report-image checks pass. No errors/overflow.
Compositor screenshots confirm a50×35px pointer drag moves ink50×35px.
Publication receipts will record the reviewed source/site pins.

---

# Phone document preview controls — 2026-10-15

Phone UI now folds the source and auxiliary controls when Render is pressed,
clears text-field focus and returns to the preview. Edit restores the source.
Files/images, zoom and diagnostics are independent collapsed panels. A compact
sticky toolbar retains Render/Edit and puts secondary navigation behind More.
On <=600px screens Render frames native content bounds rather than paper
margins; Fit page restores the complete paper and Fit text is available in Zoom.
Camera framing changes neither document geometry nor the prior accuracy results.
Explicit software browser checks cover320/390/430px phones and844px landscape;
physical Safari and on-screen keyboard behavior remain unqualified.
Evidence: Cuvami staging/artifacts/gpu-math/20261015/phone-layout/.
Local and live phone-flow checks pass all four viewports; local DPR3 zoom and
187-image/upload/report checks pass with no errors/overflow. Source c5d64d5,
site b6b0e8d, successful Pages workflow38710881659. Three changed HTTPS files
match reviewed bytes. Receipts: fit-text/, dpr/, ui-fit/, live/, publication.json.

---

# Spatial accuracy, text alignment and practical zoom — 2026-10-15

This checkpoint supersedes the document results below. Scope remains independent
LaTeX rendering; morphology and compiler publication are separate projects.

Text layout now uses native TFM widths/kerns, optical font sizes, ligatures,
English hyphenation, bounded paragraph optimization, sentence space factors and
italic correction. Explicit control-space followed by ordinary whitespace was
counted twice; it is fixed. All 746 glyphs in small2e match native positions
within .0742px. All 1,693 glyphs on sample2e page1 match within .1217px, and the
102-glyph figure fixture within .0412px. Original PDF positions are compared by
font/glyph identity, without registration. Later sample2e pages still fail.

Accuracy now separates raw ink IoU, ink coverage within one pixel, local
connected-component failures and one-to-one glyph/image geometry. Acceptance
requires >=99.5% ink coverage on BOTH outputs, >=95% coverage per component,
matching pages and no missing/extra/unmeasured or >1px displaced glyphs.
White background never increases accuracy. A synthetic missing-symbol test
proves a 99.5% global result can still be rejected locally.

The default renderer remains smooth MTSDF, with DPR-aware backing resolution,
a fixed viewport camera, pan/reset and 1–64x zoom. Shader derivatives keep edge
softness in physical screen pixels. Desktop and DPR3 phone simulations pass
1/4/16/64x checks; partial edge width is 1–2 physical pixels. Curved text, Greek,
TC dollar and integral captures retain vector-derived outlines. Six formerly
bitmap-derived TC outlines were replaced using privately extracted CM-Super
Type1 fonts with native metrics. Sources/licenses are bundled. This finite
atlas is NOT a proof of exact curves at unbounded zoom; adaptive analytic or
vector fallback remains necessary for that guarantee. No physical GPU/device
qualification was performed.

A separate opt-in 96dpi glyph-coverage cache diagnoses rasterizer differences;
it is generated from font outlines, never PDFs/documents. It is not used for
interactive zoom. small2e, sample2e page1 and the figure pass this diagnostic,
while ALL FOUR complete documents still fail the default MTSDF policy. MTSDF
first-page one-pixel ink coverage: small2e99.2685%, sample2e99.4727%,
figure99.6515%; local errors remain even when aggregate coverage exceeds99.5%.

Full corpus: original46 pages preserved, GPU49 pages (1/3/44/1). AMS reference
has41 pages; GPU has44 and62 unsupported-feature diagnostics. Nested text/math,
lists/page breaking, floats, macro scoping and package-specific font selection
remain incomplete. Standard integrals currently use the esint-prepared mapping;
documents without that package can require different native glyphs. Do not
claim package completeness or full-document match.

Final evidence: Cuvami staging/artifacts/gpu-math/20261015/document-parity/:
corpus-mtsdf-frozen/, corpus-coverage-frozen/, report-publication/ (compact phone report; full audits per page), report-frozen/,
zoom-frozen/,
dpr-reviewed/, sample-spaces-geometry.json. Browser datasets/report include
SHA256 runtime hashes. All earlier failed attempts remain preserved. Reports
retain all46 reference and49 GPU pages, raw differences, local errors and
worst-region closeups. No acceptance images are aligned, cropped or excluded.

Checks:29 Node and10 Python tests pass;32 display and32 inline independent
formula goldens pass.
Main browser passes17 families/9 drafts with no errors or phone overflow;60 warm
edits p50 6.1ms, p95 9.6ms, max26ms (software only). Document/report UI
verification passes187 page-image resources, uploaded figures and phone controls
without errors or overflow (ui-publication/).
Frozen MTSDF three-run software medians, layout/GPU completion ms:
small2e6.8/48.2; sample2e22.2/161.0; AMS290.4/1886.5; figure2.3/70.2.
These are SwiftShader full-page completion timings with fresh layout. Captures
are untimed. They do not establish the <10ms goal or hardware performance.

Published runtime source9b44ef8; reviewed site74f1dbe. Pages workflow
38704142708 succeeded. HTTPS verification matches19 reviewed runtime/report/font
files, including the atlas and all12 frozen runtime hashes. Live touch UI checks
all187 page images and figure upload with no errors/overflow. Live desktop and
DPR3 phone simulations pass 1/4/16/64x MTSDF zoom. Receipts: publication.json,
live-ui/, live-dpr/, live-zoom/ under the evidence root. These remain software
simulations, not physical-device qualification.

---

# Modular LaTeX documents and full pixel comparison — 2026-10-15

Scope is independent LaTeX rendering; morphology is a separate project. Runtime
uses prepared native-font distance fields, its own parser/layout and WebGPU.
No TeX engine, KaTeX, PDF raster or DOM text is used to render runtime pages.

New math mappings include roots, generalized fractions/binomials, native tall
extension pieces, boxes/phantoms, text styles, modulo/negation, tagged math
environments, arrays/rules and draft recovery. Class/package modules now have
real dependency/configuration/command hooks: initial article, amsmath, amsfonts,
amssymb, mathrsfs, graphicx, geometry, xcolor/color and siunitx subsets. Unsupported
imports/options emit diagnostics; these names do not imply complete packages.
Document UI accepts original .tex and named local images. GPU textures share the
page pass with text. Paragraphs, headings, basic references and simple figures
are experimental; full float/TeX paragraph layout is not implemented.

Full unregistered 96dpi PDF comparison uses unmodified official small2e (1 page),
sample2e (3), AMS testmath (41), plus a controlled image fixture (1). All46 native
PDF pages are retained. GPU produces45: testmath loses page41. ALL FOUR DOCUMENTS
FAIL acceptance. Mean page ink IoU: .372406/.072420/.030262/.470842 respectively.
Policy requires same pages/dimensions, >=.99 ink IoU and <=1px maximum boundary
error. Exact RGB and per-page errors are recorded too. Formula-position goldens
are separate evidence and do not establish PDF equivalence.

Three-run warm software-SwiftShader medians, layout/GPU completion ms:
small2e4.0/35.9; sample2e8.3/148.7; testmath148.1/1657.3; figure2.1/65.3.
Native PDF compile medians are approximately59/67/183/79ms; PDF plus PNG about
141/346/4057/130ms. Output stages differ; this is not a like-for-like speed claim.
The <10ms goal is not established for full documents or physical devices.

Validation:24 Node and7 Python checks pass.32 new real-LaTeX formula goldens in
each of inline/display match positioned geometry within0.000200bp;20 regression
cases per mode within0.001103bp. Continuous rule geometry is compared by union
when TeX partitions a rule. Main UI:17 example families,9 drafts,390px viewport,
no errors/overflow;60 edits p50 6ms,p95 10.5ms,max18.9ms, SwiftShader only.

Evidence and every failed attempt are retained at Cuvami staging/artifacts/
gpu-math/20261015/latex-completion/. Final page dataset is
 document-modules-float-final/; human-readable report is document-report/.
Report includes original sources/PDFs, direct untimed GPU framebuffer pixels,
red/blue differences, package diagnostics and timings. Reference image padding
and hidden-image CSS defects found by phone UI verification were corrected.
Public preview paths: /previews/gpu-math-typing/document.html and
/previews/gpu-math-typing/document-checks/.
Published runtime source eefd317; reviewed site20e6d7e. Pages workflow38690107903
succeeded. Eleven live HTTPS files match reviewed bytes; PUBLICATION.json preserves
the checks. Formula goldens and failed whole-document results are both published. Source scripts reproduce downloads,
PDF compilation, GPU measurements, comparison and static report generation.
Physical GPU STOP, unrelated morph work and compiler releases remain untouched.

# Owner correction and VKF morphology handover — 2026-10-14

The owner rejected the published glyph matching/movement/crossfade transition as
an interpretation of the requested general visual morphology. Its UI/browser
checks establish controls/rendering behavior only. Retain the compact UI and
native LaTeX endpoint renderer; integrate the shared endpoint-only field solver.
Implementation handover: examples/gpu-math/VKF_MORPHOLOGY_HANDOVER.md.
It pins source/assets, describes the scalar-alpha boundary, crop/placement gaps,
the shared solver contract, integration sequence and unresolved algebra cases.
The published transition has not been replaced by this documentation change.

# GPU math transitions and compact phone tabs — 2026-10-14

Owner requested two selectable equations and Transform, then a compact phone UI
with tabs and less text. Equations/Style/Examples tabs now replace the long page;
A/B editors and example selectors are small, appearance lives in Style, and notes
are compressed into a closed Help & timing section. Two-equation mode defaults on.
Transform, swap, duration and scrubbing use the existing WebGPU canvas. Matching
atlas regions interpolate positions/size/ink with quintic easing; others crossfade.
This is CPU instance interpolation plus GPU drawing, not contour morphing,
semantic algebra or integration of the other chat's experimental merge solver.
Editing cancels animation; resizing preserves paused progress; reduced-motion
uses the exact target immediately. Combined packets retain the12000 instance cap.
A screenshot-related transient zero size found during checks now uses bounded
DPR/dimensions rather than deriving DPR from a transient CSS rectangle.

Nineteen Node tests pass. Forced headed SwiftShader browser checks all13 prior
example families, recovery, controls, playback, endpoints, scrubbing, edit
cancellation, matrix target, swap and reduced motion. No page/GPU errors;320/390/430
widths have no overflow and16px editor type. Independent touch-enabled390×844
cold phone check places Transform bottom400px and canvas bottom659px, both within
viewport, and verifies tabs/colour/example selection. Local warm edits p95/max
9.3/39.3ms; cold setup1072ms.10ms remains a target, not device acceptance.
Evidence/failures preserved in Cuvami staging/artifacts/gpu-math/20261014/transitions.
Physical GPU/device, physical presentation and native VKF integration unverified.
Other-chat worktrees, Cuvami deployments, registry archives and GPU stop untouched.

Published runtime331e1322a1d215a225d4d95018432679bd218084; public main
8309ba2070ad52cf2007233fbb1f01f8558daa18. Reviewed-byte Pages workflow
38588077803 succeeds. Live HTTPS runtime hashes match; fresh touch-enabled
390×844 SwiftShader check verifies playback/scrubbing/tabs/colours with no page/GPU
errors or overflow. Transform/canvas bottoms remain400/659px; cold setup1477ms.
Publication receipt and phone-live screenshots remain in the transitions artifacts.

# GPU math page flow, alphabets, size and colour controls — 2026-10-14

Owner requested bare \\ newlines, script/double-stroke alphabets, page-width
control, regular-text word wrapping in the same font family, size controls and
instant colour taps with a multicolour example. Math now has explicit rows;
Text + math mode uses CM Roman prose, kerning/ligatures/Latin accents and inline
or display math delimiters. Width/size sliders reflow text, and colour/opacity
changes repaint GPU instances using cached layout. Named/HTML/RGB source colours
scope glyphs and rules. Native compiler integration remains pending.

Math alphabet mappings cover Roman, bold, italic, sans, mono, normal, Fraktur,
CM calligraphic, RSFS script and double stroke. Native script/calligraphic are
capitals. AMS mathbb capitals plus a documented native BBOLD lowercase/digit
extension provide the full Latin/digit range. Boldsymbol/bm and Greek capitals
in ordinary faces are included. All families retain optical-size script maps.
1411 source symbols give5644 keys/3315 distinct outlines in a4096×8192 atlas.
TeX is only the development oracle. Font notices/complete source archives remain.

Sixteen Node and seven Python checks pass. Fifty-four fresh alphabet/script
fixtures match native LaTeX positioned ink within0.000118bp (BBOLD extensions
use explicit oracle aliases);40 prior cases still pass. Three fresh text lines
validate native advances, kerning, ligatures and Swedish accents within0.000076bp.
Word wrapping is independent greedy flow, not full TeX paragraph optimization.

Headed SwiftShader browser checks13 example families, row breaks, page width,
size, opacity, color taps and draft recovery with no page/GPU errors or390px
overflow. Width1000→300 and size30→48 change text row counts6→19→29.
Red/blue screenshots prove911/929 coloured pixels; opacity blend proves175 pink
pixels. Localwarm60-edit p95/max18.9/35.3ms; fresh10ms remains a target. Cold atlas
setup1296ms is separate. Physical GPU/device, physical presentation and full
LaTeX/font compatibility are not established. Earlier attempts/failures retained
under alphabets, alphabets-final and page-flow in the existing artifact root.
No other-chat worktree, GPU stop, Cuvami deployment or registry evidence changes.
Published runtime12b41904f29c66eb08fc6c736a8e7cf8a4b2f3eb;
public main8f3f3ced6524bad7186934d98c39e6d46131d7c8. Reviewed-byte Pages
workflow38583936681 succeeds. Live code/metric hashes,13 canvas examples,
width/size reflow, color/opacity taps and draft updates pass without page/GPU
errors or phone-width overflow. Livewarm60-edit p95/max11.2/32.6ms; cold setup1461ms.
Live color pixels and newlines/reflow counts are retained with all source/native
receipts in page-flow/PUBLICATION.json.

# GPU math accents, annotations, arrows and SI units — 2026-10-14

User requests accents/arrows, over/under lines, labelled braces and SI units.
The current-source draft renderer now supports hat/widehat, tilde/widetilde,
bar/vec, dots, acute/grave/breve/check/mathring, overline/underline, nested
labelled overbrace/underbrace, overset/underset/stackrel, extensible over/under
arrows and xrightarrow/xleftarrow labels. Long/hook/diagonal/harpoon arrows
are also mapped. Braces use actual fixed TeX font pieces; shafts are continuous
rules between font arrow heads. Triple/quad-dot arrangements remain approximate.

New independent units.mjs supports common qty/unit and SI/si, num and ang,
upright SI base/derived units, prefixes, powers/per, scientific notation,
grouped digits, angles, literal abbreviations and three documented option families.
Full siunitx options, uncertainty/rounding and custom declarations are outside scope.
Real siunitx3.6.4 is used only by the development LaTeX oracle, not runtime.

411 symbols in four styles give1,644 keys/1,048 distinct outlines. Skew and
accent-font x-height follow actual font data, including the wider AMS variants.
All12 Node and7 Python checks pass. Fresh LaTeX validates68 new positioned
accent/brace/unit fixtures,40 prior fixtures,3 literal-unit examples and16
arrow-envelope/label fixtures. Exact shaft interiors and raster equivalence are
not claimed. Headed SwiftShader verifies nine example families, five incomplete
annotation/unit drafts, deletion, both modes and390px layout with no page/GPU
errors. Local60-edit p95/max9.2/20ms;10ms remains a target, not a guarantee.

Evidence and preserved failures: Cuvami staging/artifacts/gpu-math/20261014/
annotations, annotations-v2 and annotations-final. Applicable AMS, EC and esint
font notices/source archives are retained; siunitx source is supplied for oracle
reproduction. No other-chat branch, physical GPU stop, native compiler, Cuvami
staging/production or registry evidence changes. Published runtime de9cb4230eb9ff43b9318417e0563bd3013b55f4;
public main809fcbb7cc96becfa0671173b54165a093a47bef. Reviewed-byte Pages
workflow38572838462 succeeds. Live HTTPS code/metric hashes, nine nonblank
feature canvases, five incomplete drafts and both mode controls pass. Live60-edit
p95/max12.8/41.6ms. Publication and detailed software/browser/native-LaTeX
receipts are retained under annotations-final/PUBLICATION.json.

# Recoverable math drafts and Inline/Display styles — 2026-10-14

User requests Platonic-style visual recovery and wider native-LaTeX mappings.
Typing now previews current incomplete source, infers closing scopes/environments
and inserts empty operands. Deleting n from sum_x^n immediately removes n at
sum_x^; unknown commands show current placeholders rather than old expressions.
Separate Inline/Display controls and explicit TeX style/limit overrides are present.

The atlas maps 353 symbols in four styles: 1,412 keys and 874 distinct outlines.
All lowercase/uppercase Greek (standard TeX plus upright capital aliases), large
operators, esint contour integrals, angle brackets, nested delimiters, matrices,
column vectors, cases, aligned/array and power towers are supported. Very tall
delimiter extension is approximate; arbitrary TeX packages, radicals, accents and
full document layout remain outside this independent preview.

Ten Node checks pass. 20 fresh real-LaTeX formulas in each of Inline/Display pass
positioned ink-bound/fraction-rule comparison, max0.000976bp. Headed software
WebGPU verifies actual input deletion, draft recovery, both modes, five feature
examples and390px layout without page/GPU errors. Local60-edit p95/max8.6/28.8ms;
899-instance first long update is separately recorded. No consistent fresh10ms,
physical GPU, physical phone or native compiler acceptance claim. Earlier failed
oracle/atlas/browser receipts are preserved in extended/ alongside final evidence.

Source and publication work stay in the isolated math worktrees. Font-derived
assets retain AMS/OFL and esint/LPPL notices, including unmodified esint archives.
No Cuvami deployment, registry evidence, other-chat worktree or GPU stop change.
Published runtime source b450ae50c45538bcb8f5573e7a17f016fc1dd249;
public main31a601aecc08fb2b7728b695a729499a5d3e33ed. Pages workflow38565122499
passed. Live HTTPS code/data identity and headed software canvas checks pass;
live60-edit p95/max14.9/39ms and first899-instance long40.2ms. The deletion
sample sum_x^ updates in4.3ms with no n glyph. Live source, browser, pixel and
oracle receipts are recorded in extended/PUBLICATION.json. Full TeX and
consistent fresh10ms remain future work.

# Published math typing preview — 2026-10-14

Live https://vektorflow.org/previews/gpu-math-typing/ through existing GitHub Pages.
Coming soon links the preview; homepage now exposes Coming soon in navigation
and its introductory links. Runtime source pinab1a656578fded76af5aba9452c72b821207b3be
on the isolated GPU-math libraries branch. Public assets77ca8124ed596942541cf3bab2bc13cc2b680e60;
navigation b109b26300356d61c69e278f1d303919cea5e61b. Both reviewed-byte Pages workflows
succeeded. Existing public assets and compiler provenance remain preserved.

Live HTTPS source identity, actual headed software WebGPU typing, incomplete-input
recovery and canvas pixels verified. Six Node and seven Python source checks pass;
eight fresh LaTeX oracle cases pass. Live test uses SwiftShader and390px browser
viewport, not a physical phone or GPU. Live60-edit queue latency p95/max15.1/47.4ms;
one typed formula3.1ms,899-instance first long edit39.1ms. Fresh10ms remains a target.
No claim of full independent TeX, physical GPU acceptance or native VKF integration.
Local detailed receipts: TYPING-PUBLICATION.json and typing-browser-live under
Cuvami staging/artifacts/gpu-math/20261014. No Cuvami deployment, registry migration
evidence, other-chat worktree, native compiler or physical GPU stop changes.

# Live WebGPU math typing preview — 2026-10-14

Owner authorized a browser typing test hosted through GitHub Pages and linked
from vektorflow.org Coming soon. New typing-layout.mjs supports bounded ordinary
atoms, optical-size scripts and nested fractions independently of LaTeX. All88
symbols are mapped in10/7/5pt:264 reusable MTSDF tiles, one shared atlas, glyph/rule
instancing and one draw per edit. No whole-expression distance rebuild while typing.
Eight fresh real-LaTeX fixtures match relative glyph/rule positions and outline
identity; maximum positional discrepancy0.000243SVG units. General TeX packages,
radicals, extensible operators and full document linebreaking remain unsupported.

Headed Xvfb SwiftShader browser test confirms actual canvas pixels, typed edits,
incomplete-input diagnostics, long expressions and390px responsive layout with no
horizontal overflow or GPU/page errors. The initial ANGLE-GL software lane failed
canvas completion; headless screenshots could be blank despite completed draws.
Accepted verification uses a headed software Vulkan compositor and explicit
SwiftShader ICD. No physical GPU gate, driver/reset or native compiler modification.

One live typed sample completes in1.7ms, but60 warm edits p95/max11.9/46.1ms and
one899-instance long update39ms: user’s10ms fresh input target is not yet met in
this software lane. Initial atlas/pipeline preparation600ms; actual physical screen
presentation is not measured. The page reports layout, input→queue completion and
next-frame estimate separately. Canvas-only screenshot contains visible math;
receipts in Cuvami staging/artifacts/gpu-math/20261014/typing-browser-headed and
typing-layout-final. Earlier failures retained. Publication identity follows below.

# Independent LaTeX mapping and generated GPU code — 2026-10-14

Owner requires real LaTeX only during development, then an independent runtime
for known mappings, targeting long-expression rendering under10ms. The isolated
GPU-math branch now exports88 measured standard symbols and has a bounded JS
atom typesetter independent of TeX/fonts. Seven fresh oracle cases match outline
identity and relative positions within0.000227SVG units. Scripts/fractions/macros
are not supported by the independent typesetter yet; real-LaTeX fixtures remain.

Generated ESM/WGSL and hashed segment/bin/crossing buffers build fields on the GPU.
Verified SwiftShader computes and draws a real fraction and a975-atom independent
case with zero WebGPU/page errors. At800x800, long cached draw p95/max7.7/8.7ms over
120 completed submissions; layout p95 0.63ms measured separately. Cold GPU module
setup/field generation is557ms plus offline curve/index generation, so fresh-source
10ms is not achieved. No physical GPU or native VKF integration qualification.

Seven Python and four Node source tests pass. Actual GPU field readbacks pass780
sampled non-boundary sign checks. Area-coverage error is3.43/3.79% against an
independently supersampled vector reference; prototype gate5%, not pixel-exact.
Earlier binary-IoU gate failed and remains recorded; its switch to area coverage
is explicit in examples/gpu-math/README.md. Sixteen-sample shading improved quality
but missed10ms on software; final uses four. Earlier runs/memory-failure evidence
remain. Local receipts: Cuvami staging/artifacts/gpu-math/20261014/software-webgpu-aa4,
runtime-layout-oracle and independent-layout-timing.json. No other-chat worktree,
compiler, staging deployment, registry evidence or physical GPU stop changed.

# Direct LaTeX GPU-field research — 2026-10-14

Separate branch codex/gpu-math-20261014, based on immutable libraries37fbc99.
The owner requires real LaTeX source/output as the reference, bypassing KaTeX.
New isolated examples/gpu-math compiles real TeX Live LaTeX to DVI, expands
positioned vector paths/rules via dvisvgm, and bakes a whole-expression MTSDF.
Canonical curve packets are retained alongside shader/upload source and field
receipts with actual TeX metrics/Type1 fonts, font maps and tool hashes.

Six sources cover symbols, scripts, fractions/sums, integrals, radicals and
matrix/extensible delimiters. All 19,530 sampled non-boundary outline sign checks
pass; four Python extraction checks and two JS field-placement checks pass.
This is offline CPU preparation. Shader compilation/drawing, actual GPU pixels,
MiKTeX equivalence, caching, arbitrary LaTeX paint/graphics and VKF compiler
integration are not verified. TeX Live is the installed distribution; there
is no MiKTeX test result. No physical GPU, compiler, main merge, deployment or
other-chat worktree changes. See examples/gpu-math/README.md for reproduction,
limits and staged next steps; local evidence is in Cuvami staging/artifacts/
gpu-math/20261014/direct-latex-pinned. Earlier exploratory evidence is preserved.

# Shared surface-weight comparison — 2026-10-14

A bounded five-configuration sweep now ranks common surface/trajectory settings
across six endpoint-only KaTeX pairs under three explicit objective weight sets.
New area-calibrated rounded surfaces retain rigid matches and hard disjoint
lineage checks. Fifty-two Python tests pass. Full movies and quantitative
receipts are separate local research artifacts; see examples/katex-transport/README.md.
This is a 2D discrete candidate search, not solved physical division, 3D volume,
full persistent topology or a global optimization. No deployment/compiler changes.

# Monotone object-lineage candidate — 2026-10-14

The owner's latest rule is monotone visible object count, with direction-pure
split/merge families and approximately evenly distributed event timing as a soft
objective. A separate endpoint-only candidate now tracks persistent binary
lineages, disjoint coverage, passing trajectories and target convergence, and
checks the actual decoded video for fragments/count reversals. Forty-four Python
tests cover this and the retained earlier candidates. See
examples/katex-transport/README.md for acceptance thresholds and limitations.
This remains bounded offline CPU research, not runtime/compiler/GPU acceptance.

# Local pinch-off correction — 2026-10-14

Inferred split necks now pinch centrally and retract early, with smooth distance
and time limits preventing long artificial tethers. Thirty-five Python checks
pass, including a clear gap during separation and smooth contact release. The
six-case clean KaTeX movie retains exact endpoints and ten-second timing. This
remains bounded offline research; no deployment, compiler or GPU changes.

# Solid transport surfaces follow-up — 2026-10-14

Transported material now has solid interiors and narrow antialiased boundaries,
with area-calibrated density reconstruction and image-inferred narrowing necks
for splitting/merging. Thirty-two Python tests pass. The six clean KaTeX cases
retain ten-second timing and exact endpoint coverage. This is bounded visual
research, not a physical mitosis, universal topology or collision guarantee.
See examples/katex-transport/README.md. No deployment/compiler/GPU changes.

# Residual material transport follow-up — 2026-10-14

Endpoint-only alpha research now reuses unmatched old material to form unmatched
new components through a bounded sampled assignment and interpolated displacement
fields. Existing rigid matches stay separate; one-sided appearance/removal keeps
the budding/absorption fallback. Translation wins over raster-noise rotations.
Six clean KaTeX examples run at ten seconds each; 27 Python checks pass. See
examples/katex-transport/README.md for reproduction and approximation limits.
This remains offline CPU research, with no topology/collision guarantee or
compiler, main-branch, physical GPU or staging acceptance.

# Endpoint-only KaTeX stress follow-up — 2026-10-14

Nine KaTeX image pairs now exercise the shared pixel-only inference entry, without
LaTeX, IDs or formula-specific correspondence. Translation and term reordering pass
rigid path checks; seven harder pairs remain visibly partial. Eleven Python tests,
27 embedding tests and 88 original library tests pass. Two general motion defects
found by the reorder case were fixed. See examples/katex-transport/README.md for
quantitative results, exact raster limits, source-mass versus target-coverage policy
and reproduction. Movies are offline CPU research, not a complete generic morph
solver, VKF compiler acceptance, main integration or staging deployment.

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
