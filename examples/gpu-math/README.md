# Direct LaTeX to GPU fields — research candidate, 2026-10-14

LaTeX source is the input and real LaTeX output is the reference. There is no KaTeX
parser, font substitution or DOM overlay in this path. The host currently has
TeX Live, not MiKTeX; this candidate verifies the real pdfTeX LaTeX format from
TeX Live 2025/Debian. MiKTeX is a separate distribution of TeX engines/packages;
matching engine, format, packages, fonts and options matters for reproducibility.
No MiKTeX run or distribution equivalence is claimed.

## Working first slice

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
colour, translation and scale without rerunning TeX. The adapter is source-only:
shader compilation, actual drawing and physical GPU acceptance are not yet tested.
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

1. Verify the shader and adapter in an explicitly software-rendered browser, with
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
