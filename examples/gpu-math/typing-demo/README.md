# Live typing test

Development source: isolated VKF libraries GPU-math branch. Static GitHub Pages
preview: `/previews/gpu-math-typing/`, linked from Coming soon. The browser has
no LaTeX, KaTeX, installed font or Canvas2D math runtime. It uses measured 10/7/5pt
symbol metrics, bounded independent math layout, one reusable MTSDF atlas and
batched WebGPU glyph/rule instances. Changing input updates layout and the instance
buffer; it does not regenerate a whole-expression field.

The supported subset is listed on the page. Unsupported/incomplete input keeps
the last valid formula and a visible diagnostic. Formula syntax is never evaluated
as JavaScript or inserted as HTML. This is a rendering-library research preview,
not native VKF compiler integration or full LaTeX package compatibility.

Measurements: input event-handler entry to GPU queue completion, layout time and
next requestAnimationFrame estimate. Screen/compositor presentation is not directly
measured. Initial atlas/pipeline preparation is separate. The p95 window is the
last120 successful updates. Software evidence is scoped to the recorded browser
and backend. Resource budgets:12,000 source characters,3,000 parsed atoms,16-level
nesting,12,000 draw instances and2,500 CSS-pixel preview height. Extra-wide grouped
atoms or taller output may clip; general document linebreaking is not implemented.

Reproduction: map_symbols.py --style display/script/scriptscript into fresh
artifact `typing-{style}` directories, then prepare_typing.py packs the atlas.
Copy typing-layout.mjs into this directory alongside typing-data.json and
atlas.rgba.gz, then serve through localhost/HTTPS. verify_typing_layout.py checks
fresh real-LaTeX glyph/rule placement; verify_typing_browser.mjs drives actual input
and WebGPU canvas on SwiftShader. The browser test uses Vulkan compositor flags
and --disable-vulkan-surface: the earlier ANGLE-GL software configuration worked
offscreen but failed canvas completion. Physical GPU stop remains unchanged.

Assets include applicable AMS/SIL OFL and MSDFgen notices. Root source is MIT;
font-derived atlas data retains its upstream font licensing.
