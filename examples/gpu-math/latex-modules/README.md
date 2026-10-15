# LaTeX document classes and package modules

`registry.mjs` resolves `\documentclass` and `\usepackage`, imports each selected
module, resolves package dependencies and reports unknown classes/packages/options.
It never executes TeX or imports a path supplied by the document. The browser's
mapped font atlas is currently shared by all modules; glyph data is not yet
loaded per package.

`classes/article.mjs` supplies the initial page, paragraph and heading parameters.
Its default physical page is A4, matching the development pdfTeX configuration;
default article text margins follow the measured 10pt article profile. Graphicx
and geometry modules apply their backend page-size effects through configure hooks. Explicit
paper options and geometry can change those settings. 11/12pt currently scale
the 10pt maps and emit a diagnostic. Header fonts, justification/hyphenation,
full page building and general floats still differ from TeX. Basic h figures wait
for the next paragraph boundary; other placement policies emit diagnostics.

Each package lives in `packages/NAME.mjs`. A module exports a default descriptor
with `name`, `dependencies`, `options`, and optionally command/environment names.
Math packages can additionally export `mathCommands` and `parseMathCommand`.
The latter receives the parser's argument/group readers, depth guard, draft
repair callback and token consumer. It returns ordinary renderer AST nodes.
The amsmath module uses this interface for binomials, generalized fractions,
modulo notation, operator names and tags. Existing math features are being moved
into these modules incrementally; the registry is not complete package emulation.

Trusted application code can call `registerModule('package', name, loader)` or
`registerModule('class', name, loader)` to add a module. Loaders return ES module
namespaces. A class descriptor provides `configure(options)` returning page/font
parameters. New math command handlers reach inline and display math through the
same interface; no core parser edit is needed. User TeX cannot register JS code.

Current imports: amsmath, amsfonts, amssymb (depends on amsfonts), graphicx,
geometry, xcolor/color, siunitx and mathrsfs. These expose supported subsets.
Recognized but unimplemented options produce diagnostics. Most legacy math
commands still use the shared renderer; not every package command is gated yet.

The expression-only Math lab retains its convenient bundled math feature set.
The document renderer supplies the explicitly resolved modules. Unsupported
content stays visible as diagnostics/placeholders; no LaTeX engine fallback runs.
