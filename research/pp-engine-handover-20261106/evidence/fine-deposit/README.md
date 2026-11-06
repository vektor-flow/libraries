# Native fine deposited-material operators

Source4c97a606172a2ca873d5269d0f93b18a7431be7e, FineDeposit.vkf. SOURCE_CLOSURE.json binds the exact committed native source to current075 compiler/emitter artifacts. No hand-edited shader or IR, floating atomic requirement, endpoint reprojection or input thinning.

`createNativeFineDepositKernels(device)` authenticates artifacts and exposes capturePixel, supportCheck, classify, tiledMoments and reduceMoments bind adapters. The caller owns the shared device, buffers and transaction. Clear/check every dispatch summary before accepting any result. Validate support once before classification; buffers must remain bound to that same validated support revision.

Seven controls are [C,K,ownerKey,fullWidth,fullHeight,Lx,Ly]. C<=131072, K<=65536, C*K<=64000000, full raster<=4194304 pixels. Public classification input is records20C ++ ownersC ++ storedCapturePixels2C ++ immutableCoverageC ++ targetSupport2K. Support pairs are strictly ascending unique full-raster top-down pixelID and actual native alpha>0. SupportCheck output is the validated alpha.

Classify emits six values per lineage: [supportIndex,mR,mG,mB,m,mOpacity]. Unselected gas or other-owner stock has index-1 and zero moments. Selected inactive matching-owner stock must have valid stored capture pixels in genuine support, positive mass, bounded display coefficients and immutable coverage. mOpacity=m*(displayA/coverage), separating sampled raster coverage from authored opacity. Positions are never used for binning. These are display coefficients, not conserved pigment chemistry.

TiledMoments consumes classify6C and returns five raw moments per (tile,supportPixel), tile-major. Each tile scans at most4096 lineages; dispatch count is K*ceil(C/4096). ReduceMoments consumes that packet and returns5K raw moments. Both levels use native compensated sums. Raw moments are not clamped to an optical density or alpha. Immutable fine lineage mass remains authoritative even when a later optical mapping saturates.

CapturePixel has controls [C,fullWidth,fullHeight], input oldPixels2C ++ FineReceiver25C, output2C. Only new capture events copy FineReceiver slots22/23; older metadata persists exactly. New event pixels are validated. The caller commits pixels, owners, marker state and other accepted fields atomically.

Finite gates: WASM small/4101-record boundary error<=1.14e-13; GPU10k lineages against actual1089 native glyph pixels and synthetic3000 pixels, plus concentrated non-dyadic10k. Actual-support mass residual0; concentrated reduced mass residual5.65e-5 near half an f32 ULP at mass1240. Initial naive reduction residual-0.00544 is preserved in SUMMATION-DIAGNOSTIC.json. Tested normal/nonnegative moment budget is1e-7+8*2^-24*abs(f64 reference); no arbitrary-precision or subnormal guarantee. Nine malformed deposit cases and five malformed capture cases reject.

Latest software-GPU wall time including per-stage summary readback: actual1089-pixel gather61.6ms,3000-pixel gather118.2ms. Test-owned GPU peak1.59MB, limit64MiB, no leaks/errors. These are isolated operator timings, not hardware/60Hz, optical, glyph-formation, NS session or complete Product-presentation acceptance.
