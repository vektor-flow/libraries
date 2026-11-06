# Balanced native port operators — 2026-11-06

Owner: balanced_ports; branch codex/native-balanced-ports-20261106; base
4c97a606172a2ca873d5269d0f93b18a7431be7e. Only new FluidPorts.vkf and
fluid-ports evidence are owned. No Fluid/FineReceiver/MaterialStock/FineDeposit,
StateEvents/StateControls, emitter, Product or presentation changes.

Exact current075 compiler and unchanged emitter a5305eb0 produce seven operators:
normalize2, unit_rhs2, pack6, boundary6, add_lift, remove_lift, port_drag.
Canonical source SHA2562422df3c5eab2dab6a49739447d974b6704afedfe2a24715df2891f716fb8b66.
Raw sum correctness is an explicit caller-owned native once-per-mask reduction
contract; normalize2 checks finite/nonnegative each cell and positive sums, but
cannot establish that supplied sums match all cells. Grid4..64 per axis and
N<=131072; finite domain/output and underflow/overflow guards are explicit.

ABI agreed with physical-session owner: normalize raw collectorN++supplyN,
p24/25 raw sums ->AoS2; unit_rhs2 consumes sameAoS2 ->complex2 collector-supply.
Existing native Fluid DFT plus project zero3N makes unitLiftSoA3N with
D(lift)=supply-collector. pack6 consumes normAoS2N++liftSoA3N++potentialComplex2N
and outputsAoS6 [collector,supply,liftXYZ,potentialReal]. boundary6 takes oldAoS6N
++optionalnextAoS6N, p24..30=[time,start,Q,rampDuration,hasNext,maskStart,duration],
outputsAoS6 [sink,source,liftXYZ,pressureRate]. Uses reference C2 quintic with
qd*potential+q*dmix*(newPotential-oldPotential), not state/time easing.
add/remove consume stateSoA7N++boundaryAoS6N; drag consumes actual7N++rawRhs7N
++boundaryAoS6N and adds only face-averaged sink drag/cell sink scalar removal.
Cooling stays raw RHS. Fine probes authoritative; coarse C diagnostic/loading0.

Renderer branch same name owns authenticated artifacts/runtime and reproducible
CPU fixture generation and WASM/GPU tests under scripts/tests/docs/fluid-ports.
Accepted independent CPU reference SHAe086923ab53c81da9a30aa0fcbaebe36c18f6fd5bc49d76280d273d67c699d3e.
Native f64 WASM parity8x6x4/24x16x8 four sampled cells x ten boundary times
<=1.39e-17. Actual GPU all-cell normalization, native DFT lift, temporal derivative,
reconstruction and face drag gates are in renderer GPU.json. GPU uses shared
flock /tmp/vkf-qualification-gpu.lock. No full NS source/receiver/SSPRK session,
suction, glyph formation, native FFT or real-time60Hz claim. Physical-session
owner binds accepted stages, constraints, diagnostics, adaptive ticks, and replay.

Workflow evidence: single specialist FT2/L3 bounded operators; CPU reference
preceded native/GPU qualification. Draft wrapper string substitution duplicated
unit_rhs2; corrected before qualification. A redeclared native j was corrected
to .j before final build; compiler/emitter untouched. Platform tokens/timing
telemetry unavailable; reported GPU wall includes test readbacks, not throughput.
