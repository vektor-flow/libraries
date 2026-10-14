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
Array rules/options, optional row spacing, arbitrary packages/macros, radicals,
accents, general document layout and full TeX compatibility are not implemented.

Real LaTeX is used only during development. The browser loads 353 mapped symbols
in display/text/script/scriptscript styles (1,412 keys, 874 distinct outlines),
using a 4096-square MTSDF atlas and one batched draw per edit. No LaTeX, KaTeX,
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
atlas and typing-data.json here, and copy typing-layout.mjs and draft-parser.mjs
from the parent directory. Serve through HTTPS/localhost. verify_extended_layout.py
checks fresh native LaTeX ink bounds and fraction rules in either mode. Node tests
cover draft recovery and deletion; verify_typing_browser.mjs drives real textarea
input, style changes, feature examples and canvas output using headed SwiftShader.
Physical GPU stop remains unchanged.

MIT applies to runtime source. Font-derived atlas data retains applicable AMS/SIL
OFL and esint/LPPL notices; MSDFgen also has its own notice. esint-source archives
provide the unmodified upstream sources. esint symbols are mapped to a differently
named combined atlas and are never installed as modified esint font files.
