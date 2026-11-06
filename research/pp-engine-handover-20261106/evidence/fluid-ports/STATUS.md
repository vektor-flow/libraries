# Native balanced ports — 2026-11-06

Objective complete at finite operator scope. Source94bba2a, exact source
SHA2562422df3c5eab2dab6a49739447d974b6704afedfe2a24715df2891f716fb8b66;
branch codex/native-balanced-ports-20261106 in source+renderer. Runtime artifacts
compiler0.7.5 sourcebindingffcaeaae and unchanged emittera5305eb0. Build metadata,
WASM.json and GPU.json contain exact source/IR/shader hashes and reference pins.

Independent accepted CPU ns_reference.py normalised_ports/boundary/rhs oracle
on8x6x4 and24x16x8: WASM f64 sampled error<=1.39e-17. Actual current GPU24x16x8
normalization<=2.73e-7, unitLift<=5.47e-8, D(lift)-source<=2.93e-6, boundary
<=8.36e-8, drag<=1.43e-8, reconstruction<=3.73e-9. Normalized integrals within
7.42e-8 of1. Native direct DFT uses the physical owner's unchanged pressure path.
Boundary pressure-rate temporal derivative -G check<=2.33e-6; tests cover onset,
ramp endpoints, mask knots and interior mixed derivatives. Stationary derivative0,
replay exact. Explicit malformed/underflow, buffer/work budget and cancellation
gates pass. GPU.json records actual memory and software GPU wall incl readbacks.

Artifact loader only authenticates and transports. No host math/IR/WGSL patch.
All7 operators native; AoS2/AoS6 agreed ABI in README.md. normalize2 raw sums
must come from caller's qualified native once-per-mask reduction; native cell
validation does not prove supplied sums. Cancellation cooperates before dispatch;
already-submitted GPU work is finite, not preempted. Grid4..64 each,N<=131072.
GPU rounding/balance and D(lift) residual are approximate, not exact divergence0.

Next belongs to physical owner: native mask reduction/preparation and stage-time
SSPRK projection/diagnostics/adaptive ticks plus actual fine source/receiver flow.
Fine probes authoritative; coarse scalar C only diagnostic/loading0. No suction,
formation, coupled session,60Hz/FFT or whole-application memory claim. Root owns
Product/presentation/capture; no Product edits, deployment or publication here.

Workflow: FT2/L3 single bounded specialist; CPU→WASM→actualGPU deterministic gates.
Shared GPU flock respected on each browser run. Failed unqualified draft wrapper
substitution and variable redeclaration were corrected without compiler/emitter
changes; overflow/underflow output guards added before final source qualification.
No token/cache telemetry available; no concurrency speedup claim inferred.
