Native fine receiver — qualified capture operator, not a full presentation

FineReceiver.vkf runs native-pixel hazard integration along accepted, unwrapped
three-dimensional marker segments. It supports a fixed mask or an affine moving
front. It never integrates air, invents paths, changes mass/color/identity, or
forms text. Captured velocity must be sampled by the fluid finaliser at the
capture point and time. Dead records must not be drawn as moving gas.

The four-buffer current075 GPU ABI uses AoS20 markers followed by native alpha
occupancy in values, and produces AoS25. Controls are documented in the source.
Output endpoints3..5 are wrapped gas ends or capture points. Original segment
origins0..2 and nonposition material channels are preserved. Extra20..24 channels
are capturedNow,fraction,pixelX,pixelY,exposureIncrement.

WASM.json:86 reference probes, exact f64 output,3 rejected inputs.
GPU.json:15 cases/330 probes, mixed materials/IDs, exact discrete channels and
same-device replay;4 rejected native conditions. Position/fraction budget2e-6,
optical-depth budget1e-4 for the finite tested profile. The optical-depth measured
error is3.55e-5; f32 coordinate/rate rounding dominates it, not cumulative DDA
stepping. The optical-depth budget also bounds absolute capture-probability error
since exp(-x) is1-Lipschitz for x>=0. This is not a universal precision guarantee;
near-threshold cross-backend decisions can differ. Material and identity checks
are exact, not covered by a relaxed whole-output tolerance.

DIAGNOSTIC.json preserves the stronger-case observation. SOURCE_CLOSURE.json
binds the final committed native source and runtime/artifact bytes. There is no
host physics implementation or edited IR/WGSL; all code is emitted by the pinned
current075 compiler and qualified canonical GPU emitter.

Reproduce: python3 scripts/fine-receiver/make-fixtures.py <PP-research-directory>
then node scripts/fine-receiver/verify-wasm.mjs. Serve this repository locally and
open tests/fine-receiver/qualify.html, calling window.run() for the actual GPU
checks. Generated binary fixtures are ignored; hashes and generation are saved.

Low-level loader: vf-ui/vf-native-fine-receiver.mjs,
createNativeFineReceiverKernel(device).bind({params,values,result,errors,count}).
Check the native error summary before committing a simulation state. The loader
uses immutable provenance and validates artifact hashes. No physical-device,
whole-fluid, source-emission, fine-air-pressure or glyph-formation claim follows.
