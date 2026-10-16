# Worked math derivations

24 original, annotated derivations with 146 states for the existing math
morphology player. `derivations.mjs` exports an array of IDs, titles, topic groups,
assumptions and `{math, note, geometry}` steps. The library is declarative: these
are supplied derivations, not results computed by a symbolic solver.

Topics include matrix least squares, ridge regression, Schur complements,
eigenvalues, Gaussian integrals, beta/gamma identities, parameter integrals,
linear/logistic/damped ODEs, variational mechanics, heat-equation modes, Fourier
analysis, statistical estimation, Bayesian updating, KL divergence, maximum
entropy and matrix inverse iteration. Domain restrictions are part of each case.

The same dataset is published at the online renderer's Examples → Math
derivations page. Each sequence opens in the existing morph player with play,
a timeline, editing and video export. Individual LaTeX and complete JSON downloads
are provided. The player remains experimental; adding worked examples does not
establish new guarantees for the morphing solver.

To update the website from this canonical source, run in the website repository:

    node scripts/prepare-math-derivations.mjs /path/to/examples/math-derivations
    node tests/math-workbench.mjs
    node tests/math-derivations-browser.cjs

The renderer test checks all 50 examples / 254 states (including the original
26 examples). The browser test checks all new endpoints and intermediate states
using explicit software rendering only, plus search, downloads and mobile layout.
Algebra and domain conditions have been reviewed; these checks are not a complete
formal proof of every derivation. No physical GPU benchmark is claimed.
