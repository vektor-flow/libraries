# Native glyph material state — 2026-11-06

Numerical source pin ad9f85b8ddf28f3ec86aff79f33c3ad8e0d8f266;
renderer integration/proofs922fab8d3a55f317d658c73c0a7a1013243d459a.
The previous pose-only glyph API faded unmatched symbols at their final shape.
That was not material interpolation. Its native preparation now rejects unequal
physical-ID sequences; it is not a split/merge or renderer fallback API.

Ordinary public Interp state mode continues to use the ONE existing Morphing
backend. Its existing biological/field implementation supplies persistent
replicated carriers, signed implicit geometry and prescribed ink-area law.
The renderer now connects genuine physical glyph outlines to that existing path
instead of the fading pose-only bypass. Identity/affine sampling is an internal
canonical state optimization. Samephysical unchanged glyphs keep exact objects.
No interpolation of renderer triangles or host interpolation formulas is added.

The native polygon field has an optional nonzero flag, defaultfalse for existing
polygon callers, true for physical fonts. Native geometric area calibration now
finds an actual sign-changing bracket before bisection, rather than assuming
fixed large scale4 remains inside the measurement domain. Renderer bounds and
samplingresolution grow proportionally, preserving physical samplingprecision.
All numerical geometry remains in these original canonical modules.

GPU/native finite evidence in renderer docs/glyph-material-state: grouped
unequalcounts, digit6→7, positive interior, authoredalpha1/color, exact fixed
heading/suffix/endpoints/seek, sharedoptional clock, source-only geometric removal.
Hollowring oldnative trap→new residual2.31e-6 at1e-4 tolerance. Actual6frameVP9
GPUclipdecoded. Existing material kernels retain16caseparityworst5.96e-8/4.47e-8.

Limits: local signedfield is sampled, not exact cubicdistance; area law is
percohort and finite raster tolerance, not universal discreteglyphcount or3Dvolume
conservation. Overlapping independent cohorts affectvisible union. Connected
mixedcolor cohorts require explicitpercarriercolor extension andcurrentlyreject.
≤256glyphs/endpoint and256MiB GPUbufferbudget. Full accepted Navier–Stokes prototype
is NOT ported; current task does not activate superseded analytic smoke.

Research basis: interpolation-exploration/research/core_contract/round_1,
generalization/working_reference, existingbiological persistentlineage/implicit
geometry/quantitypolicy. These are finite qualified adapters, not generalityproofs.
