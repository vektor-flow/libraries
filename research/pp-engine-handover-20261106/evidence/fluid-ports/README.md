# Native balanced ports finite qualification

FluidPorts.vkf source lives in libraries branch codex/native-balanced-ports-20261106.
Its seven operators use the unchanged current075 compiler and GPU emitter
SHAa5305eb01c6d36d5234402471750f0c4ed2f1c892fcec628649325bee315676f.
No host numerical substitute, shader/IR patch or independent fluid renderer.

Native ABI: x-fast periodic MAC index x+nx*(y+ny*z), existing flow24 prefix.
normalize2 takes raw collectorN++supplyN and appends raw sums atp24/25; output
AoS2. Raw sum correctness belongs to caller's native reduction; every mask cell
must complete normalization without diagnostics before acceptance. unit_rhs2
consumes thisAoS2 and emits complex2 [collector-supply,0]. Existing native
Fluid DFT axes0/1/2→spectrum→inverse2/1/0 plus project zero3N++potentialComplex2N
produces liftSoA3N withD(lift)=supply-collector. pack6 consumes
normAoS2N++liftSoA3N++potentialComplex2N ->AoS6 [collector,supply,liftXYZ,potential].
boundary6 receives oldAoS6N++optionalnextAoS6N and p24..30
[time,start,Q,rampDuration,hasNext,maskStart,maskDuration]; outputsAoS6
[sink,source,liftXYZ,pressureRate]. Uses C2 quintic and complete pressure derivative.
add_lift/remove_lift: stateSoA7N++boundaryAoS6N ->scalar7N.
port_drag: actualSoA7N++rawRhsSoA7N++boundaryAoS6N ->scalar7N. Adds only
face-averaged -sink*u and cell -sink*scalar. Raw RHS already includes cooling.

Run from renderer worktree:

```bash
python3 scripts/fluid-ports/reference.py [optional-accepted-ns_reference.py]
node scripts/fluid-ports/build.mjs /path/to/native-library
node scripts/fluid-ports/verify-wasm.mjs
node scripts/fluid-ports/package.mjs
flock -w60 /tmp/vkf-qualification-gpu.lock node tests/fluid-ports/qualify.cjs
```

Generated18MB reference.json is intentionally ignored; its recipe and independent
accepted CPU source hash are versioned. Build pins sources/compiler/IR/shaders;
packaging copies emitted artifacts unchanged and binds them by size/SHA256.
Runtime authenticates shaders/manifests, enforces finite count/buffer budgets,
and checks AbortSignal before loads, binds and encode. Already-submitted compute
is bounded; cancellation is cooperative between dispatches, not GPU preemption.
Native diagnostics reject invalid geometry, masks, sums, duration, storage,
underflow/overflow. Grid4..64 each, N<=131072; owned test memory64MiB hard budget.

WASM.json records native f64 oracle samples on8x6x4 and24x16x8. GPU.json records
actual all-cell GPU parity, normalization integral balance, same native direct
DFT lift and D(lift)=source, reference boundary values at10 times, discrete
pressure/lift temporal derivative including ramp/mask knots, exact replay,
add/remove reconstruction, face/cell drag, malformed cases and budget/cancel.
The DFT provenance is the existing physical owner's unchanged integrated build,
not a separate pressure solver. Direct DFT is not FFT performance evidence.

Fine material probes remain authoritative; coarse C is diagnostic withloading0.
No source/receiver/SSPRK stage integration, suction, formation, full session,
whole-app memory or real-time60Hz claim. Physical owner owns stage coupling;
root owns actual Platonic Play integration/capture. No Product/public deployment.
