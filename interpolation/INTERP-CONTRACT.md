# Native Interp contract

`Interp` is a typed structural record with optional zero/one named groups:

```vkf
StateSettings:(path:int)
RevealSettings:(k:num,velocity:num,overshoot:num,grow:bit)
VaporSettings:(temperature:num,spread:num,lift:num,seed:int)
Interp:(mode:int,state:[StateSettings],reveal:[RevealSettings],vapor:[VaporSettings])
```

Named factories remain `state(path=0)`, `spectral(k=4,velocity=.54,
overshoot=.32,grow=true)` and `evaporate(temperature=1,spread=.35,lift=.65,
seed=0,...reveal)`. The Interpolation facade calls these `state_interp`,
`spectral_interp`, `vapor_interp`. Mode0 accepts only state; mode1 only reveal;
mode2 reveal+vapor. Empty groups use native defaults. Factories enforce named
parameters and finite supported ranges. Temperature is now a dimensionless
activation control `[0,1]`; it is not a thermodynamic temperature/energy model.

State `prepare`/`sample` still delegates to the same Morphing backend. The shared
`time_coordinate(q)` is applied **once**, outside native sampling, independently
of linear/natural-cubic path choice. Its two quadratic pieces are C1, not globally
C2. Scalar browser export forwards the existing `Morphing.sample` directly.
Simple polynomial/tensor methods remain independently usable without Interp.

## Material-carrying vapor

The former outward-only drift/fade is superseded and removed from the active
vapor API. `text_frame` now accepts spectral mode only. Conserved vapor uses:

- `prepare_vapor_transport(settings,sourceInk,targetInk,glyphs) -> VaporTransport`
- `vapor_front(settings,q,travel) -> num`
- `sample_vapor_transport(plan,q,front) -> VaporFrame`

Ink storage is `[x,y,r,g,b,coverage,footprint]` per actual native ink sample;
glyph storage is `[x,y,reading,r,g,b,alpha]` per actual native glyph/rule. Positions
use the same CSS-height coordinate chart, y up. Footprint is in CSS pixels.
RGB/coverage/alpha are `[0,1]`, ink coverage and footprint positive. Each ink
endpoint has a positive power-of-two sample count <=4096. Actual native pixel
sampling is a bounded renderer intake, not an interpolation implementation.

The constructor reuses **Morphing.prepare_material** with positive equal dyadic
weights per endpoint, normalized total1, seven channels and the existing state
segment evaluator. Dyadic endpoints produce at most4096 persistent carriers,
including split/merge owners. This tracks normalized material, not physical ink
area. Different endpoint stroke areas represent different density/coverage views
of the same ledger; no raster-area/opacity conservation theorem is asserted.

Correspondence is the existing ordered cumulative material coupling. It is not
an optimal transport solver or semantic character matcher. Each actual target
ink point gets a nearest native glyph-anchor capture control, with declared
native order breaking ties. This controls arrival timing, not proof of physical
or semantic identity. Endpoint ink positions themselves are actual native pixels.

A seeded finite cubic noise field is prepared with the existing natural-cubic
state backend. Native lifted/noisy offsets vanish during suction. This produces
seekable non-direct Brownian-like/turbulent motion; it is not an integrated
Wiener process, Navier–Stokes solver or imaginary thermodynamics. Temperature
scales dissolved motion and release duration. Spread/lift use a tenth-scale
CSS-height chart. All random control values and seeking are deterministic.

The delayed front first permits dissolution/lift, then suction begins ahead of
spectral formation. A carrier reaches the target glyph's current native growth
transform before its capture fraction rises. Target RGB uses the existing native
spectral wave finishing at authored ink; carrier RGB interpolates its real source
and target ink colors with the same native state segment. Exact q0 positions and
colors are source; exact q1 positions and colors are target.

Gas rows are `[x,y,alpha,footprint,r,g,b,weight,capture]`; target rows are
`[alpha,growth,r,g,b]`. Ledger output is `[attachedSource,gas,capturedTarget]`,
whose sum is1 in the declared model (finite floating residuals tested/reported).
Material weights never fade. Display alpha is a separate observation of source,
gas or target ownership. This replaces independent outgoing fade/target reveal.

Empty changed ink endpoints explicitly reject conserved vapor. Source creation,
removal/reservoir accounting and semantic matching are not invented. Use the
separate spectral mode for appearance/removal. A wholly unchanged native scene
requires no transfer and remains stable. Native exact matching in the browser
keeps identical id/source/anchor/style specs fixed; style/color changes transport.

The native guest call is synchronous; cancel/drop before dispatch or discard
superseded results. Prepared data and carrier count are bounded. GPU rendering
uses existing native fonts/simplex rendering; compute remains canonical WASM CPU.
Native/WASM finite tests, actual decoded clip and route details are recorded
separately. No physical GPU, universal conservation/topology/collision guarantee
or general source-event solver is claimed.

## Refined state/material row ABI3

Interp adds optional `capture:[CaptureSettings]`; CaptureSettings is named
`(width:num,velocity:num)`. State keeps `state(path=0)`; legacy spectral keeps its
own reveal group. Vapor now rejects reveal fields and uses
`evaporate(temperature=1,spread=.35,lift=.65,seed=0,footprint=.45,
captureWidth=.45,velocity=.54,boundary=3)`. VaporSettings includes named footprint
and boundary. Boundary0closed,1emit,2exit,3exchange; native schema describes all
applicable fields. Overshoot/grow/spectral RGB are absent from material capture.

`GlyphEndpoint:(identity:[int],matrix:[num],color:[num])` contains exact physical
font/rule IDs supplied by native layout, six affine coefficients and four RGBA
components per glyph. `prepare_glyph_state` performs bounded monotone exact-ID
matching within ONE explicitly authored related row (<=256glyphs/endpoint), then
uses existing state prepare/sample for pose+color. It is a bounded new address
adapter, not a semantic equation matcher or universal correspondence theorem.
Unmatched insertions/removals use declared zero-opacity state endpoints; retained
physical glyphs preserve their authentic paths. No renderer triangles interpolate.

`sample_text_rows(rows,q,fronts)` applies time_coordinate once to the entire
state/material batch. TextRowPlan contains mode, optional state/vapor prepared
groups and native travel. Output rows contain native poses, source ownership,
carrier channels, target channels and named MaterialLedger.

MaterialLedger is `(source,gas,target,reservoir,emitted,exited)`, normalized in
one row unit. Closed transfer retains source+gas+target=1. Birth has no source
ink: declared external reservoir1 is released into gas and captured target;
reservoir+gas+target=1 while visible gas+target=emitted grows0→1. Exit records
source→gas→exited. No closed-system conservation claim is made for external
emission, or for physical raster area/density. Both-empty material has no event.
Research policy_algebra_1/principles80–86 distinguishes explicit external source
creation from redistribution; its proposal is not an existing general source
solver. This implementation is the bounded declared boundary adapter above.

Capture width sets the native arrival interval. Target alpha is the accumulated
captured carrier weight assigned to its native glyph control divided by that
control's weight, multiplied by authored alpha. RGB stays authored, growth1.
Gas RGB follows source→target native state interpolation. Carrier destination
positions are actual native ink samples; nearest-anchor capture controls and
positive coverage assignment are explicit timing controls, not semantic identity.
The budget must address every target native glyph. Coherent rising/convection
motion and a mild shared seeded cubic field replace independent Brownian paths.
This is deterministic finite flow, not CFD or physical thermodynamics.

ABI4 adds CaptureSettings.start_coordinate/finish_coordinate. The named vapor
factory accepts raw captureStart=.35/captureEnd=.85, converts those constants
through time_coordinate during preparation, and rejects invalid order. Playback
still clocks the requested q once. The active incoming row chart excludes fixed/
calculation rows. Front reaches first active ink atcaptureStart and completes
last active ink atcaptureEnd; width controls per-glyph spatial capture softness.
Velocity is the absolute-coordinate advance/duration contract, not another warp
of an explicitly normalized q. Presentation profile being qualified is footprint
.75CSS (still subpixel), captureWidth.25, captureStart.35/end.85, temperature1.
