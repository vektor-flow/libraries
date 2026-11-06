Root-owned standalone fine-mask capture port, 2026-11-06.
Source FineReceiver.vkf only; do not edit Fluid.vkf or parent's state geometry.
AoS20 accepted UNWRAPPED segments → AoS25; preserves origin, endpoint velocity,
mass/RGBA/species/lineage. Updates endpoint, cumulative exposure and liveness.
Capture momentum is NOT qualified until the fluid finaliser resamples air at the
capture point. Native renderer must exclude dead records from visible gas.
Reference: PP source e665fbc research/physical-smoke/fine_receiver_reference.py.
Compiler/emitter must match current075; no IR/WGSL edits. Native/GPU gate pending.

Native WASM qualification: 86 probes against the independent Python reference,
including actual native glyph masks and affine front, all 25 output channels
exact after direct integer-edge crossing evaluation. Three rejection cases pass.
GPU qualification: 15 cases/330 probes, varied mass/RGBA/species/lineages, exact
same-device replay, exact discrete/material channels. Four native rejection flags
(front width, crossing budget, negative mass, invalid native alpha) pass.
Measured f32 optical-depth error max3.55e-5 remains after avoiding accumulated
crossing time: coordinate/rate rounding dominates this stress case. Validation
uses separate fixture budgets:2e-6 position/fraction,1e-4 optical depth. It is not
a universal error bound; near-threshold decisions across backends may differ.
Capture probability sensitivity is bounded by optical-depth error for nonnegative
exposure. No threshold/whole-output relaxation masks identity or material errors.
Renderer docs/fine-receiver/{WASM,GPU,DIAGNOSTIC}.json preserve measured evidence.
This is a low-level capture operator, NOT a complete fluid/text-formation claim.
