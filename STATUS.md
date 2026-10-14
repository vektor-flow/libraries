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
