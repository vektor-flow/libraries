# Native resolved material coverage

The production objective is CSS ink area: native compensated sum(resolved alpha)
/ pixelRatio squared. MaterialCoverage.vkf owns both reductions; existing native
geometric calibration remains the sole scale chooser. The generic copy shader
only transports textureLoad(...).a to f32 storage. No geometry, colour, area or
scale arithmetic is added to transport. No per-lineage density MRT runs here.

```js
const kernels = await createNativeMaterialCoverageKernels(device);
const measure = await createNativeMaterialCoverage({device, kernels, maxBytes});
const borrowed = renderer.coverageTexture();
const {area, areaBuffer, controlReadbackBytes} = await measure.measure({
  ...borrowed, pixelRatio, signal
});
measure.dispose();
```

The renderer supplies its borrowed resolved single-sample TEXTURE_BINDING texture
from the same implicit-material-2d/coverageOnly MSAA4 union. Queue measurement
before next draw/resize/destroy. The helper submits its copy before the first
measurement await; subsequent same-device draws remain ordered. Initialization
is async. Device/texture remain caller-owned; helper dispose never destroys them.
Returned4B native areaBuffer is borrowed until next measure/dispose. Each measure
reads12B: row error summary, total error summary, native scalar. Both native
error buffers are cleared on every dispatch and both summaries checked before
acceptance. Failed native results never become accepted area. Buffers persist
across equal-size measurements; resizing replaces helper buffers. Concurrent
measurements reject. Cancellation checks surround bounded submitted GPU work;
no GPU-preemption promise. Dispose while pending rejects result and frees owned
buffers after mapping completes. Artifact size/SHA256 checks precede compilation.

Controls exactly[deviceWidth,deviceHeight,pixelRatio]. Native/runtime limits:
width,height1..8192; pixels<=16777216; pixelRatio.125..16. Caller may impose a
smaller maxBytes cap (default96MiB, maximum256MiB). Owned allocation is exactly
4*width*height+8*height+40 bytes, including params, alpha, row result, both native
error buffers, area and12B staging; checked before allocation. GPU pipeline/
driver allocations and caller renderer textures are outside that explicit count.
Actual device storage/dispatch limits also reject explicitly. Accepted RGBA/BGRA
normalized/sRGB/float resolved formats all copy alpha unchanged. Finite alpha in
[0,1] is required by native rows; all shader/IR numerical operations come from
unchanged current075 compiler and emittera5305eb0.

Validation:

```bash
node scripts/material-coverage/build.mjs /path/to/native-library
node scripts/material-coverage/verify-wasm.mjs
node scripts/material-coverage/package.mjs
flock -w60 /tmp/vkf-qualification-gpu.lock node tests/material-coverage/qualify.cjs
flock -w60 /tmp/vkf-qualification-gpu.lock node tests/material-coverage/actual.cjs
```

Actual fixture runner accepts NATIVE_COVERAGE_RENDERER, _PROTOTYPE, _PLAN,
_CONTROLS environment paths; defaults point to the parent's qualified native27
fixture and geometry build. ACTUAL27.json records their current hashes/provenance.
WASM.json covers compensated numerical fixtures and malformed native controls.
GPU.json covers independent test-only CPU alpha sums on actualMSAA4 resolved
empty/full/partial/overlap, DPR/non-square,8192-axis bounds,800/1280 profiles;
native NaN/negative/out-of-range/storage failures and clear/recovery; caps,
cancellation/dispose and artifact tampering. Budget1e-6+8*2^-24*CSSarea is finite
f32 numerical scope, not exact area. Empty/full dyadic cases are exact.
ACTUAL27.json uses native state/carrier geometry at q.5/scale1, no calibration or
density execution. CPU texture alpha readback exists only in test harnesses.

Measured actual27 SwiftShader warm8.7–8.8ms at800x800 and12.1–13ms at1280x720,
including copy, native reductions and12B mapping. Controlled fixtures may take
longer. These are objective-only tests, not full frame or60Hz evidence. No native
calibration convergence, optical/physical formation, session/Product readiness or
publication follows. Parent owns state driver and integration.
