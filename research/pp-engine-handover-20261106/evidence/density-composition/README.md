# Native density composition transport

Use `createResidentMeshRenderer(canvas, {device, profile: 'implicit-material-density-2d', densityKernels: {accumulate, resolve}})`. Both kernels are native compiler-produced `createCompiledFieldKernel` objects, width four. `await renderer.setResidentLineages([{buffer, count, offset: 0}, ...])` consumes native XYZ/rhoRGB/rho triangle packets; count is a multiple of three, offset is bytes. Geometry, densities and colours come from VKF. The renderer does not infer them.

RGBA16float MSAA4 rasterization is reused per lineage, avoiding repeated half-float summation. A persistent MAX coverage attachment represents the union independently. Generic channel-copy shaders gather into native f32 accumulation and resolve kernels. Output is premultiplied numerical colour, not a radiometric model. Half-float quantization remains in each lineage layer; native density preparation bounds relative density to at least 1/16384.

The caller awaits each draw. Every dispatch clears/checks native errors; invalid numerical results reject without replacing the accepted GPU image. `captureBitmap()` redraws that retained image before snapshotting. Shared device and input geometry remain caller-owned. Renderer statistics include its own buffers, MSAA/resolve textures and diagnostic staging, with a maximum 256 MiB; callers must separately account for their other shared resources. Canvas presentation-chain allocation is browser-owned.

The reproducible browser test uses the actual unmodified compiler-emitted accumulation/resolve artifacts in tests/density-composition/artifacts. These are qualification fixtures, not a Product runtime release. GPU.json reports software-GPU browser evidence, not physical hardware or full-presentation acceptance.
