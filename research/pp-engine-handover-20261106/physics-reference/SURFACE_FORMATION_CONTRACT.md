# Fine captured-material surface formation

This is a declared, mass-conserving **opaque areal-fill constitutive model** for
reconstructing native glyph support from captured material. It is a separate
surface closure coupled to the accepted dilute-aerosol/NS transport. Its algebra
is derived here and tested in surface_formation_reference.py. Thermal phase
change, surface diffusion and radiative transfer are outside this closure.

## Inputs and units

For each genuine target support pixel, retain native sampled area fraction
`a in (0,1]`, world-plane area `A`, and declared one-layer areal mass density
`sigma` (material mass / world area). Given CSS-world pixel area `A_css` and
physical pixel ratio `r`, `A=A_css/r²`. Equivalently,
`sigma*A = massPerCSSPixel/r²` when the source mass scale uses that same plane.
The physical pixel ID and alpha come from the actual VKF text raster, preserving
its font, position and aspect. The closure does not create its own text layout.

FineDeposit supplies five approximate f32 moments from authoritative lineages:
`(sum(mR),sum(mG),sum(mB),M,sum(m*authoredOpacity))`. Raster coverage is already
separated from authored opacity. Keep original fine lineages, owners, immutable
coverage, actual capture pixels, colour bases and IDs as the authoritative
attached stock. Reconstructing an image never changes or resamples that stock.

## Constitutive rule

The mass needed to fill one layer of this pixel's genuine support is
`cap=sigma*A*a`. Partition provided mass into

- `layerMass=min(M,cap)`;
- `excessMass=M-layerMass`;
- geometric pixel coverage `c=layerMass/(sigma*A)`, bounded by `a`;
- occupied world area `c*A`;
- thickness in layer units `M/layerMass` when material is present.

Thus partial coverage grows linearly with deposited mass. After the native
support fills, additional mass thickens the attached material. It is retained
for future removal/re-emission; it cannot disappear through optical saturation.
The mass partition adds back to the provided moment mass within numeric error.

For M>0 the declared mixed-surface display coefficients are
`RGB=sum(mRGB)/M` and `P=sum(m*authoredOpacity)/M`. Output premultiplied colour is
`(c*P*RGB,c*P)`. For M=0 all ink and coverage are exactly zero. There is no time,
q, easing, independent opacity ramp, or missing-mass top-up in this rule.
Mean colour times mean authored opacity is an explicit mixture approximation;
it does not recover pigment/opacity correlations omitted by the five moments.
For the current opaque profile P=1, PMA colour below saturation is directly
proportional to the corresponding colour moment.

Small ratio excursions within the declared positive f32 reduction budget may be
clipped to the display interval and must be reported. Larger inconsistencies,
negative/nonfinite moments, or colour/opacity without mass reject explicitly.
The raw fine ledger is unchanged by any display clamp.

## Causality and lifecycle

Only FineReceiver's accepted capture events add attached mass. Its moving native
front and true target occupancy determine which pixels may capture. Empty pixels
remain invisible even if a planned wave has passed. Later ordinary list items
use the existing native wave; they cannot spend this first-row reservoir again.
A completed timing interval does not certify a completed material layer.
Report actual filled/partial/empty support and covered area. Insufficient incoming
material leaves an incomplete row; extending timings/flux is an authored/runtime
choice, not permission to synthesize missing mass.

When removing a formed row, MaterialStock re-emits its actual owned lineages
with their exact stored mass/IDs/current display coefficients and positions,
resampling current air velocity. Excess thickness is part of those same stocks.
A failed/retried activation cannot duplicate them. Remaining gas stays in the
shared physical session and remains moving; attached solids are not drawn as
frozen gas markers.

## Evidence and boundaries

Nine reference tests cover zero-source causality, linear partial fill, genuine
support bounds, excess retention, separate opacity, partition invariance,
DPR subdivision, immutable inputs and malformed finite data. DPR invariance is
for conservative subdivision of the same occupancy/mass. Separate real raster
samples can differ due to their actual anti-aliasing; it is not an assertion of
bit-identical independently sampled DPR images.

This is an opaque coverage model. Transmission would additionally require
absorption/path-length parameters: see the [IUPAC Beer–Lambert definition](https://goldbook.iupac.org/terms/view/B00626).
RGBA UI colours do not provide those parameters. No empirical thermodynamic or
optical validation is claimed by these algebraic tests.
