# Material coverage handoff — 2026-11-06

Finite objective task complete. SourceSHA404a1bbcc1040a323609425b07e443aa7e64d0243c908b1705eb5f3e69b97601,
branch codex/native-material-coverage-20261106. Source MaterialCoverage.vkf is
independent of Fluid and existing interpolation sources. Exact075/unchanged
emitter; authenticated emitted rows/total plus native WASM manifest packaged.

API and limits in README.md. createNativeMaterialCoverageKernels(device) and
createNativeMaterialCoverage({device,kernels,maxBytes}) are async factories;
measure({...renderer.coverageTexture(),pixelRatio,signal}) returns CSS area,
borrowed native areaBuffer,12B controlReadbackBytes and memory accounting.
Device and resolved texture caller-owned. SameMSAA4 union is measured, with
only textureLoad.a generic copy. Native compensated sums own all area maths;
existing native calibrate remains sole scalechooser.

WASM max f64 error9.10e-13;12 malformed cases. GPU finite controls/storage/NaN
failure+recovery, memorycaps/cancel/dispose/tamper and exact replay pass.
Independent CPUalpha oracle is TESTONLY. Actual27 q.5/scale1 union texture:
800x800DPR1 area1715.5177002 vs1715.5176471 (5.32e-5);1280x720DPR2 area346.80685425
vs346.80686275 (8.50e-6). Actual warm8.7–8.8/12.1–13ms onSwiftShader;12B readback.
Controlled800/1280,overlap/partial,DPRs and8192-axis tests also pass. Helperowned
peak3,692,200B on tested profiles; zero afterdispose. No wholeGPU/app memoryclaim.

Parent /root/vkf_interp_struct owns renderer coverageTexture() modification and
state-driver/native calibration integration. Root owns FineFormation law and
actualProduct integration. Parent separately reported dense-q convergence RED;
this fixedscale coverage proof does not resolve or hide it. No formation/session,
calibrationconvergence,60Hz or publication claim. Existing source/renderer files
unchanged by this worker; all new files owned material-coverage paths.

Workflow FT2/L3 reused bounded specialist. Source/WASM→controlledGPU→native27GPU;
shared GPU flock honored. No failed implementation approaches. Tokens/cache
telemetry unavailable. GPU measurements are finite objective-only mapwall.
