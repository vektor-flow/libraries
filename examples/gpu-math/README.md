## Native VKF LaTeX diagnostics — 2026-10-16

`native-vkf/math_kernel.vkf` exports
`math_diagnostics(source, font_source, native=true, source_name="<math>")`.
It returns JSON with `status` (`valid`, `incomplete`, `edit-required`) and `issues`.
Each issue has a stable `VKF-LATEX-*` code, `message`, `hint`, `severity`,
`recovery` (`append` or `edit-existing`) and a half-open `range`. Range endpoints
contain zero-based UTF-8 `byte` offsets and one-based `line`/`column` values;
columns count Unicode scalars, with a tab counting as one. `relatedStart` points
back to the opening scope for missing closers. `sourceName` is caller supplied.
An unfinished command is appendable only when it is a proven supported prefix;
a space terminates that command name. An existing error wins over unfinished
input when choosing the report status. Diagnostics are bounded to 25 issues;
`truncated=true` means the bound was reached and the report stays conservative.

For example, `\frac{a}` reports a missing denominator at byte8/line1/column9
with `status=incomplete`; `x^2^3` reports `VKF-LATEX-REPEATED-SCRIPT` on the second
`^` at byte3/line1/column4, with guidance to combine scripts in a single group.
An extra `}` identifies that exact token and parsing continues to later errors.
These statuses describe how to repair LaTeX; they do not prevent saving drafts.

`math_parser.analyze` provides both the current AST arena and structured issues;
`math_parser.diagnose` provides the report. Existing `parse`/`json` consumers keep
their packet format. `native-vkf/latex_diagnostics_dump.vkf` is the native CLI;
it reads the font-catalog, source-file and output-file paths on separate stdin
lines. Eight affected VKF suites pass native and WASM, with 13 real-font API cases
matching exactly across backends; see the rendering handover for evidence.

This is the native math API, awaiting editor integration. Ranges describe the
supplied math source, without include/macro-expansion source maps. Merged nested
text/unit semantic issues currently highlight the containing argument. Supported
syntax/resource validation is not universal TeX/package validation. The broader
layout check initially encountered an existing syntax error; after concurrent
layout edits it compiles but fails a two-headed-decoration geometry assertion.
No layout source was edited for this task, and no full renderer or UI
qualification is claimed.

## Vector PDF output

The document editor now offers **More → Export PDF**, independently of the
LaTeX engine and WebGPU. It reuses native layout and original vector glyph
curves, preserving sharp zoom. Text is currently outlined rather than searchable.
See [export APIs, CLI and verification](typing-demo/README.md#independent-vector-pdf-export--2026-10-15).

The live typing extension now supports recoverable drafts, Inline/Display styles,
large operators, all Greek capitals/lowercase, matrices/cases and nested scopes.
See [typing-demo/README.md](typing-demo/README.md) for the current runtime scope,
reproduction and limits. The older research stages below retain their own scope.

# LaTeX mapping and generated GPU code — research candidate, 2026-10-14

LaTeX source is the input and real LaTeX output is the reference. There is no KaTeX
parser, font substitution or DOM overlay in this path. The host currently has
TeX Live, not MiKTeX; this candidate verifies the real pdfTeX LaTeX format from
TeX Live 2025/Debian. MiKTeX is a separate distribution of TeX engines/packages;
matching engine, format, packages, fonts and options matters for reproducibility.
No MiKTeX run or distribution equivalence is claimed.

## Independent runtime direction

The owner requires LaTeX during development as a reference, followed by a runtime
independent of TeX when the mapping is known. `map_symbols.py` is a development
oracle. It produces `symbol-mapping.json`: 88 standard symbols with measured real
LaTeX box advances/heights/depths and actual vector outlines. `math-layout.mjs`
uses that data and bounded TeX atom-spacing/bin-correction rules to lay out new
ordinary expressions without launching LaTeX or loading fonts. Seven fresh oracle
fixtures check relative positions and exact outline identity. Maximum observed
position discrepancy is 0.000227 SVG units. Unsupported scripts, fractions,
macros, composite symbols and unverified adjacency rules are explicitly rejected.
The older direct-LaTeX fixtures remain useful for extending that grammar.

`generate_gpu.py` accepts either a real LaTeX packet or an independent runtime
packet. It emits an executable `expression.gpu.mjs`, WGSL and hashed binary
geometry/index buffers. The GPU builds an SDF from flattened curves and then
renders it in the same host-provided pass as other geometry. No CPU-generated
pixel image or character atlas is consumed by this new GPU generation route.
Line-segment approximation has a recorded tolerance and float32 endpoint error;
this is not an exact Bezier distance evaluator. Distance lookup uses conservative
local bins; nonzero fill uses binary search of scanline crossings. Curve flattening,
index generation and scanline crossings currently occur in the preparation tool.

The performance target is under 10 ms for long-expression display, with separate
fresh-source-to-pixels reporting. `benchmark_layout.mjs` prepares a 975-atom,
25-row case with no LaTeX process. `verify_webgpu.mjs` requires an explicit
SwiftShader executable/ICD and checks the actual adapter before GPU operations.
It records completed-submission wall timing and compares drawn pixels to a
separate Path2D rasterization of retained curves. Cold resource preparation is
reported separately. These software timings are not native VKF or physical GPU
qualification. Current independent layout supports only the bounded atom subset.

## Working reference slice

`latex_paths.py` compiles a math body (or a full single-page LaTeX document) with
amsmath/amssymb to DVI. dvisvgm emits positioned vector paths and rectangles using
an explicitly resolved font map. The adapter expands every path reference and
rule, preserving original relative placement, then produces:

- A path packet with line/quadratic/cubic commands, per-primitive affine placement,
  local opaque IDs and outline hashes. Repeated exact outlines share geometry.
- A normalized single-path SVG containing the entire expression, including rules.
- One RGBA MTSDF texture for the entire expression, plus raw linear RGBA bytes for
  GPU upload and mapping metadata. RGB median reconstructs sharp edges; alpha is
  scalar signed distance, **not opacity**.
- Build receipts with source/document hashes, actual engine/converter/tool bytes,
  explicit font-map entries, TFM/Type1 file hashes, recorder inputs and output hashes.

`field-packet.mjs` positions that field in a shared viewport. Its WebGPU adapter
uploads the raw bytes into a linear rgba8unorm texture and issues a six-vertex
quad in a host-provided render pass. `mtsdf.wgsl` contains median reconstruction,
derivative-based antialiasing and premultiplied compositing. The host can apply
colour, translation and scale without rerunning TeX. Its original MTSDF route remains a reference. The newer generated SDF route has
software WebGPU execution evidence; physical GPU and VKF integration remain untested.
Use one draw invocation per renderer per submitted frame; its uniform/instance
buffers currently store one placement.

Vector curves remain the canonical visual geometry. A sampled, quantized distance
texture is an acceleration representation, not an exact mathematical distance
function. MSDF channels have edge-colouring semantics; their median is not a
universally valid Euclidean field for physical transport. A uniformly scaled
scalar distance can be rescaled, but general affine warping does not preserve
Euclidean distance. Smooth unions and field blending can alter corners and holes.
The other chat's endpoint-only transport solver remains separate and receives
images only; these path IDs are not inferred semantic correspondence.

## Actual evidence

Six real LaTeX sources cover general symbols, scripts, fractions/sums, integrals,
radicals, matrices and extensible delimiters. The final pinned study contains
106 positioned primitives and 93 per-expression unique outlines, with 8 rules.
Independent fontTools nonzero-winding checks compare decoded RGB-median signs
against the extracted vector paths at PNG texel centres. Results are in
`Cuvami/staging/artifacts/gpu-math/20261014/direct-latex-pinned`.
These are finite sign samples excluding points within one reconstructed texel of
the edge; they do not certify distance magnitudes, subpixel quality or GPU pixels.
Source tests cover reference reuse/placement, cubic curves/rules, transform order,
explicit rejection of unsupported SVG, texture format and viewport placement.

Earlier exploratory KaTeX assets are preserved in the parent artifact directory.
Their sampled outline-sign check failed on three font faces under its threshold;
they are historical exploratory evidence, not adopted assets or an acceptance result.
The user's final direction is direct LaTeX, and current source has no KaTeX dependency.

## Reproduce

Use existing LaTeX, dvisvgm, dvitype, kpsewhich, CMake/C++, FreeType, libpng and
libtinyxml2-dev. Python dependencies are pinned in requirements.txt. No Node
packages are needed for the source tests or the candidate WebGPU adapter.

```bash
export PATH=/home/viktor/.local/bin:$PATH
python -m venv /tmp/vkf-latex-tools
/tmp/vkf-latex-tools/bin/pip install -r examples/gpu-math/requirements.txt
examples/gpu-math/build-generator.sh /tmp/vkf-msdfgen
/tmp/vkf-latex-tools/bin/python examples/gpu-math/run_study.py \
  --output /tmp/vkf-latex-study \
  --generator /tmp/vkf-msdfgen/build/msdfgen
/tmp/vkf-latex-tools/bin/python -m unittest discover \
  -s examples/gpu-math/tests -p 'test_*.py'
node --test examples/gpu-math/tests/*.test.mjs
```

For one expression, pass a file containing the LaTeX math body:

```bash
/tmp/vkf-latex-tools/bin/python examples/gpu-math/latex_paths.py \
  --source examples/gpu-math/formulas/fraction.tex \
  --output /tmp/vkf-latex-fraction \
  --generator /tmp/vkf-msdfgen/build/msdfgen
```

`--document` accepts a complete document rather than wrapping a math body. The
current engine route requires DVI and exactly one page. `--engine` can select a
MiKTeX latex executable later; MiKTeX kpathsea/tool/font-map compatibility still
needs a real validation run, not just changing that flag. Run authored local TeX
only: no-shell-escape is used, but this tool is not an untrusted-TeX sandbox.

All output directories must be fresh so failed and passing evidence remains.

## Next steps, in order

1. Extend the existing software shader/adapter evidence, with
   decoded pixels compared against independently rendered LaTeX reference geometry
   at multiple sizes, especially tiny scripts, thin rules and sharp corners. Preserve
   the existing physical GPU STOP until separately resumed. First measure and fix
   quality; no current speed or native VKF integration claim.
2. Cache complete expression fields by source plus a pinned engine/package/font
   environment. This eliminates TeX and field regeneration during animation. Current
   build timings are offline CPU costs, not GPU frame timings.
3. Tile/cache repeated vector outlines by hash and bake rules analytically or as
   paths. Preserve optical-size-specific outlines; a TeX glyph at 7pt is not assumed
   identical to the corresponding 10pt glyph. Expand field resolution adaptively
   or evaluate/tessellate curves for extreme zoom, using retained vector geometry.
4. Establish MiKTeX reference fixtures and compare actual bytes/geometry. Add a PDF
   route for pdfLaTeX/LuaLaTeX/XeLaTeX, including embedded/subset fonts and arbitrary
   paths; avoid assuming DVI supports every package/output feature.
5. Expand paint support to colour, strokes, clipping, images and document pages with
   explicit coverage reporting. Arbitrary LaTeX can emit raster content, external
   assets and output-specific specials: those need appropriate GPU primitives,
   not a claim that all output is a distance field. Repeated-reference documents
   need bounded multipass compilation, which is not implemented here.
6. Propose the language/compiler asset boundary upstream: compile LaTeX source once
   into a versioned visual asset, then reference its field/path packet in the same
   VKF scene/material pass as other visuals. Resource budgets, cancellation,
   missing-package diagnostics and accessible source/MathML belong to that contract.
   No new VKF syntax is invented or advertised as implemented in this candidate.

The intended division is CPU typesetting/preparation and GPU display/effects.
Running the entire TeX macro expansion/layout engine inside a GPU shader is a
separate undertaking; it is not required to eliminate CPU text painting overlays.

## Research basis

- [dvisvgm manual](https://dvisvgm.de/Manpage/): DVI/PDF conversion, path references,
  exact outline bounds, font maps and output constraints.
- [msdfgen](https://github.com/Chlumsky/msdfgen): vector-shape distance generation and
  reconstruction method; source pin is in build-generator.sh.
- [Chlumský et al., Improved Corners with Multi-Channel Signed Distance Fields](https://dcgi.fel.cvut.cz/wp-content/wpallimport-dist/publications/pdf/publications-2018-sloup-cgf-msdf-paper.pdf):
  preserving corners with multiple distance channels.
- [Loop and Blinn, Resolution Independent Curve Rendering](https://www.microsoft.com/en-us/research/publication/resolution-independent-curve-rendering-using-programmable-graphics-hardware/):
  a direct GPU curve alternative when finite textures are insufficient.

This isolated libraries branch does not alter the other chat's worktree, compiler,
physical GPU stop markers, Cuvami deployment or registry evidence.

## Generate GPU code from a packet

```bash
/tmp/vkf-latex-tools/bin/python examples/gpu-math/generate_gpu.py \
  --packet /tmp/vkf-latex-fraction/path-packet.json \
  --output /tmp/vkf-fraction-gpu --texels-per-unit 8
```

Serve the generated directory on loopback or your host's asset route, then import:

```js
const { create } = await import('./expression.gpu.mjs');
const expression = await create(device, targetFormat);
// In the shared render pass, once per submitted frame:
expression.draw(pass, { viewport: [width, height], x: 16, y: 16, unitsToPixels: 2 });
// On release:
expression.dispose();
```

This is a JavaScript/WGSL research integration boundary. It adds no VKF syntax
and has not been wired to a native compiler-generated VKF scene. Full independent
TeX math layout and fresh-expression preparation below 10 ms remain open.

## Measured second slice

Accepted software run: `software-webgpu-aa4` in the local artifact root. Both compute
and render shaders execute on verified SwiftShader, with zero WebGPU/page errors.
The independent 975-atom case renders at 7.7 ms p95 and 8.7 ms maximum over 120
completed submissions, with an 800x800 target. Its independent layout and row
assembly take 0.63 ms p95 in Node. These stages are measured separately.
Cold asset loading, pipeline setup and field computation take about 557 ms and
exclude Python geometry/index preparation, so cold source-to-pixels is **not**
under 10 ms. Physical GPU and native VKF integration remain unverified.

The SDF renderer uses four subpixel samples for thin strokes at the tested scale.
Against a separately supersampled (4x, area-downsampled) vector reference, relative
alpha coverage error is 3.43% for the fraction fixture and 3.79% for the long case.
The current prototype area-error gate is 5%; binary threshold IoU is also recorded
(0.885/0.926) as a diagnostic. Earlier attempts used a 0.95 binary-IoU gate and
failed. That change is explicit: binary masks near half coverage are unstable for
small antialiased strokes, while area coverage directly measures displayed ink.
This does not establish pixel-exact LaTeX fidelity. Independent sampled vector
winding checks of the actual GPU field readback pass 780 non-boundary points.
Initial low-resolution, high-resolution, 16-sample and harness-memory-failure
evidence remains preserved. Sixteen subpixel samples improve area agreement but
miss the software 10 ms target for the long case.

Immediate next work: cache/tile repeated mapped outlines and instance their
placements, avoiding a complete field rebuild after ordinary expression edits;
extend the independent grammar to scripts and fractions using fresh oracle cases.
Dynamic browser curve/index preparation is not wired into the typesetter yet:
new runtime packets currently feed the offline code generator. The generated GPU
module itself runs independently of Python, LaTeX, KaTeX and font loading.

## Live typing third slice

The typing-demo source now uses264 prepared MTSDF tiles across10/7/5pt mappings
and batched glyph/rule instances. It extends the independent grammar with scripts
and nested fractions, checked against eight fresh LaTeX fixtures. Maximum observed
position discrepancy is0.000243SVG points; exact outline identity is checked.
The browser runs no LaTeX, KaTeX, font loader or Canvas2D math layer.

See typing-demo/README.md for supported syntax, limits and timing semantics.
A headed software Vulkan/SwiftShader test checks actual visible canvas pixels,
keyboard typing, recovery from incomplete braces, long input and phone layout.
Warm edits currently measure11.9ms p95 in that lane, above the10ms target; one
899-instance first update measures39ms. The public preview reports measurements
on the visitor’s device rather than asserting those software timings universally.


For source-fidelity comparison against downloaded arXiv PDFs, run
`compare_document_pixels.py CORPUS CAPTURE --mapping MAPPING --exclude-arxiv-stamp`
(with the usual optional `--oracle-extras` directory). The owner excludes the
archive-added stamp from the LaTeX renderer's scope. This explicit option checks
for a complete rotated arXiv mark isolated in the left margin, excludes only its
reference glyphs and ink, and records the exclusion in each page's geometry
report. It preserves original PDFs/rasters and every source-content/page check.
Without the option, the original full-PDF comparison remains available. The
runtime neither reads nor renders these external marks.


The owner-approved glyph-origin tolerance is now0.1 pixels at96dpi. The comparison
CLI defaults to this limit; `--position-tolerance-pixels` records any explicit
alternative in its report. Ink error remains a separate .01 normalized limit.
For subpixel audits use `--pdf-text-origins` and install development dependency
`pypdf==6.20.1`. This preserves the original Type1 PDF font widths rather than
MuPDF's three-decimal approximation. Independent font/glyph/count matching and
trace agreement are still required; unsupported fonts retain trace origins.
PDF decoding is an oracle only and never enters document layout or rendering.
The complete39-page focus paper passes all61,949 glyphs with maximum0.0084px
position error. Raster acceptance and broader full-paper compatibility remain
incomplete; see STATUS.md and the shared LaTeX rendering handover.
