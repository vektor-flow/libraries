# Native physical-fluid port probe — 2026-11-06

Owned branch codex/native-physical-fluid-20261106 starts at library86d5841.
Only new Fluid.vkf and new tests/docs belong to this task. No Interp, Morphing,
existing glyph, field, source-font or Product file is modified.

First operator/projection GPU gate PASS on8x6x4 and24x16x8 using current075
compiler-owned typed IR and exact GPU emittera5305eb0. Fluid.vkf ports the accepted
periodic MAC D/G, conservative central momentum, full constant-viscosity stress,
and MINMOD scalar transport. A native separable direct DFT solves the SAME DG
pressure eigenproblem; this is not an FFT performance claim. At24x16x8 velocity
error vs accepted CPU reference was9.24e-8; pressure error7.55e-9; explicit native
postprojection divergence4.50e-6. Tests include actual reference initialization
RMS.055,nu.0004,unforced,Cs/D/forcing/collector0. Smaller-grid scalar fallback is
explicitly an operator test, not the accepted visual fixture.

This is NOT a running physical session or NS integration claim. SSPRK3, fixed
absolute clock/epoch, complete snapshot replay, native marker motion, reservoir
release, balanced receiver/pressure lift, actual glyph masks and materialization
remain separate implementation gates. Parent owns Product integration. Public
createNativePhysicalSmokeSession remains a proposed API with no ready factory.
The accepted CPU reference and source provenance are in Product research/
physical-smoke at source7fa8900 and later receiver/reservoir additions, read-only.

No qualified native FFT API was found. A foreign candidate at e2620/6f20861 is
uncompiled/unrun, read-only, and NOT promoted: its MC limiter differs from the
accepted MINMOD and key forcing/ports are absent. Standard MAC flux/stress
stencils were audited, not blindly copied as an accepted solver.

Exact GPU evidence is in the owned renderer worktree docs/physical-smoke/
OPERATORS.json, built under /tmp/vkf-physical-fluid-probe-bZYYCh. It records all
source/IR/shader hashes, actual f32 accuracy, and diagnostic/readback timing.
The initial23.5ms operator/29.7ms projection measurements include per-stage test
readbacks and are NOT a60Hz solver throughput result. No physical CFD, DNS,
thermal phase change, two-way particle coupling or native glyph SDF is claimed.

Second gate: native resident SSPRK3 and f64 fixed observation clock PASS. The
baseline advances7 SoA fields (3 MAC velocity, temperature,3 passive species).
Every RHS uses the accepted MINMOD scalar operator and Leray projection of the
momentum RHS; coefficients/stage ordering match the reference. At24x16x8 after
18 ticks (0.3s), max velocity/scalar reference errors were1.104e-7/3.327e-7;
absolute species mass drift <=7.103e-10 (initial species masses0.001 each).
Three observation partitions produce byte-identical GPU fields:0.3 once,
30*0.01, and10*(0.013+0.017). Native WASM/f64 clock tests cover nanosecond ties-even,
0..1e6 seconds, nonzero absolute epochs and invalid/rewind rejection. A checked
integer cast initially exposed a missing explicit floor in the clock; corrected
before this gate. The first draft clock is not a qualified source version.

Software GPU measurement is honest: median161ms per physical1/60s tick at24x16x8,
including three projections and one diagnostic readback per tick. This direct
DFT implementation is not a60Hz claim. Owned test GPU buffers7.10MB; this is not
whole-browser RSS or a deployment memory limit. Smaller8x6x4 median19.2ms.

New evidence: renderer docs/physical-smoke/SSPRK.json and clock.mjs. Native markers,
rendered fluid playback, runtime stage/CFL rejection policy, snapshots/session,
variable-viscosity SGS, ports/pressure lift, finite reservoirs and native glyph
receiver coupling are still unavailable. In particular, coarse averaged glyph
sink was falsified by parent research; its exact area preservation does NOT
qualify reaction. Parent's later native-pixel DDA interception remains a separate
model/port gate. No Product/public module was modified by this prototype.
