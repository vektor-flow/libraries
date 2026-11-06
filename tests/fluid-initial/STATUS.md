# FluidInitial checkpoint — UNQUALIFIED — 2026-11-06

Owner balanced_ports; branch codex/native-fluid-initial-20261106 from source
94bba2a8b577139c45b9f13fe6ba6868e1a87ed2. New FluidInitial.vkf only; no existing
Fluid/source/session/Product edits. Physical owner retains stage/ports coupling.

Objective was native seed881 initial velocity, exact discrete projection, RMS.055
and zero temperature/three diagnostic scalars in7N, plus preserved initial2N
complex pressure. Accepted profile uses ten NumPyseed881 modes on domain1.6x1x.4.
A complete explicit finite70-coefficient preset is now native source, with offline
coefficient provenance in renderer docs/fluid-initial/PRESET.json. No runtime RNG
or host-generated random velocity array is used by the experimental candidate.

Exact current075 source SHA256
5feda0b8eeab80f547d7fe23b651aa22de971c8e16ba524b59fcb8a9be0f372b.
Compiler sourcebinding ffcaeaae; unchanged emitter SHA
 a5305eb01c6d36d5234402471750f0c4ed2f1c892fcec628649325bee315676f.
Four emitted entries: synthesize, energy_chunks, normalization, state7.
Existing native Fluid pressure-rhs/DFT/spectrum/project are reused unchanged;
projection usesdt1/60 and preserves mean-zero initial diagnostic pressure BEFORE
RMS scaling, matching accepted reference. Initial pressure is not stage pressure.

WASM f64 tests GREEN: exact preset identity, native synthesis four cells/component
on8x6x4 and24x16x8 <=4.11e-15, existing native discrete-project point checks
<=1.39e-17, native compensated energy/RMS/state samples <=1.39e-17;8 malformed
rejections. These are explicit point/energy checks, not a new full f64 solver gate.

Actual experimental GPU END-TO-END FAILED first8x6x4 case: state error
1.1695618120782791e-5 (limit2e-6), initial pressure error.0011940449428741728
(limit2e-5). RMS.054999998056675437, divergence6.426125764846802e-8 and zero scalars
remain finite/in bounds. Root cause NOT isolated; cos-based f32 candidate differs
from independent accepted reference. No compiler-defect claim, precision
relaxation, shader/IR patch or substitute was introduced.24x16x8 GPU/replay/
malformed/cancel tests were not reached after first accuracy failure.

Original earlier emitter error "WGSL array return requires explicit output width"
was caused by a reachable array-return coefficient helper. Replaced it with native
scalar coefficient lookup before final build, without emitter changes. Current
GPU accuracy failure is separate. Original error retained in renderer evidence.

Direct steering: read FULL PP-AUTOMATIC-GPU-COMPUTE-INTEGRATION-HANDOVER-
COORDINATOR125.txt at Vektor Flow/.coordination/atomic-chats446. Done. Stop new
experiments and checkpoint/return; no fallback experiment started. No PP intake,
deployment, engine migration or external coordinator worker policy adopted.

Renderer candidate defaults to explicit NATIVE_FLUID_INITIAL_UNQUALIFIED failure;
experimental opt-in exists only to reproduce the recorded failed qualifier when
future work is authorized. Not a public SDK/API, hardware, automatic GPU,
complete under10ms, fullNS, formation/session or factory readiness claim.
Native initial-field capability remains unavailable to Product. Preserve prior
qualified ports and MaterialCoverage branches unchanged. Root owns next routing.

Next only when authorized: isolate synthesis/projection discrepancy upstream,
respect genuine-GPU/public-SDK contracts, qualify matching artifacts/hardware.
Do not silently select a CPU/WASM physics fallback. Historical permission for
native once-per-session initialization does not override latest steering.

Workflow FT2/L3 bounded specialist. Source/WASM→experimental emitted WebGPU
accuracy gate RED; shared GPU flock respected. No performance or speedup claim;
no token/cache telemetry. Checkpoint ends experiments, not completed initializer.
