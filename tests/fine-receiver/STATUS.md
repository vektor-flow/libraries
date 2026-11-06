Root-owned standalone fine-mask capture port, 2026-11-06.
Source FineReceiver.vkf only; do not edit Fluid.vkf or parent's state geometry.
AoS20 accepted UNWRAPPED segments → AoS25; preserves origin, endpoint velocity,
mass/RGBA/species/lineage. Updates endpoint, cumulative exposure and liveness.
Capture momentum is NOT qualified until the fluid finaliser resamples air at the
capture point. Native renderer must exclude dead records from visible gas.
Reference: PP source e665fbc research/physical-smoke/fine_receiver_reference.py.
Compiler/emitter must match current075; no IR/WGSL edits. Native/GPU gate pending.
