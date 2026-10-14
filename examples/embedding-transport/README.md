# Continuous embedding research prototype

This is an isolated VKF shared visual-library experiment for Cuvami/Platonic Play.
It does not alter the current compiler, source grammar, accepted baseline or GPU
stop policy. Base: bf3dc9cc8af41155623d0678ace48948632806f9.

Run `npm run test:embedding` for 24 focused numerical/contract tests.
Run `npm test` with the existing package dependencies for 88 original library checks.
Run `python3 -m http.server 8874 --bind 127.0.0.1` from the repository root and open
http://127.0.0.1:8874/examples/embedding-transport/ for the CPU Canvas preview.

Seven examples: translation, rotation, affine scale/shear, moving one-to-two copies,
constructed O-to-D annulus, conserved weighted point transport and changing
mass/area/colour. Scrub, play/pause and toggle analytic sample velocity vectors.
The fixed four-second duration applies to all channels. Viewport pixel flow is
not inferred from these vectors.

The default createEmbeddingTransport path selects translation, rigid, similarity,
then proper affine fit before residual morphology, conditional on supplied
correspondences. Affine polar decomposition avoids an unintended collapse during
large rotation. `motion: 'linear'` is the explicitly requested comparison/bridge
path; it is not the default planner. 3D supports only that explicit point path.
Ordered mass coupling respects declared order and marginal weights, not minimum
spatial cost or semantic correspondence. Midpoint equality is by a shared plan,
not two independently computed paths. Samples/plan snapshots are immutable inputs
and pure outputs; no stateful physics integration is performed.

The branch example moves a common centre with a progressively increasing relative
separation. Equal-radius disk union gives a continuous visual set, initially one
connected shape and finally two full-size copies. This is visual duplication,
not mass conservation or an optimized transport network. Its silhouette can have
a nonsmooth boundary at the topology event. The annulus is a constructed radial
family with one hole, not automatic matching of arbitrary font outlines.

A common quintic clock supplies zero velocity and acceleration at both endpoints.
Analytic derivatives are checked against independent numerical differences.
A deliberately reversing quadratic path demonstrates why clock easing alone
cannot remove geometric stalls. Changing geometric routes in the demonstrated
translation, rotation, affine and moving split stay in motion at sampled interior
times. Fixed points and general-path regularity need explicit policies.

Mass, continuous area, opacity and declared linear-sRGB channels interpolate with
the same clock. Premultiplied colour derivatives use the product rule; straight
linear RGB is converted to sRGB only for display. A mass change is an explicit
source/sink, not physical conservation. The material demo binds geometric circle
area to the continuous coverage value; integer raster pixel count remains discrete.
All smooth observables of a state with zero endpoint velocity/acceleration inherit
those endpoint conditions. This does not apply to topology or discontinuous counts,
and it does not make arbitrary constraints on derived quantities simultaneously
feasible.

Remaining research: semantic/topological correspondence, concave shared-path cost,
branch-event optimization, globally nonintersecting morphology, hole events, feature
metrics, coverage/optical-flow guarantees and version-matched VKF integration.
The detailed research contract lives in cuvami/core contracts/EMBEDDING_TRANSITIONS.md.

Verification on 2026-10-14: 24 focused tests pass; 88 existing library tests pass.
Chrome and Linux WebKit at 1280x850 and 390x844 exercised all seven examples,
six seek positions, endpoint sample derivatives, play/pause, visible hole pixels
and no page errors. Screenshots inspected. Software browser evidence is not native
compiler, physical GPU or physical-phone acceptance. Local artifacts are under
Cuvami/staging/artifacts/embedding-transport; no staging deployment was made.

Initial broader checks failed because the isolated worktree had no dependencies;
a local ignored dependency symlink allowed the original 88 tests to pass. One
second-difference acceleration harness lost precision; a five-point stencil
removed that cancellation without weakening the analytic endpoint contract.
