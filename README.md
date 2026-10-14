# Vektor Flow — libraries

Official language-level libraries and their correctness tests. Library source
migration is unfinished; current checks run through bootstrap.

## Function syntax

```vkf
f(x,step):x+step
g:f[step:2]
::g(3)
```

This prints `5` with the native compiler on Linux. Parentheses call; square
brackets specialize. See the [language examples](https://github.com/vektor-flow/spec/blob/working/README.md#examples).

Contents use the [MIT License](LICENSE). Preserve third-party notices during migration.

## Browser UI preview branch

`@vektor-flow/ui` owns reusable retained geometry presentation, selection contours,
gradient paths, marker impostors, antialiased drawing, visible-grid snapping and
the 2D/3D coordinate views transferred from Platonic Play. The existing pinned
`vektor-flow` renderer, symbolic plotting and physics engine remain its backend.
There are no Tesseracs credentials, Session state or Product menus in this package.

The source syntax remains native VKF. This program was compiled and executed by
the pinned 0.7.1 WASM compiler to produce the retained-arena fixture in tests:

```vkf
viewport: .ui.viewport
viewport.add(x:[-1,1]_u,y:[0,0]_u,id:"line",color:[0.2,0.7,1,1])
viewport.show()
```

`mountRetainedPlot(container, packet)` mounts a bounded canvas for one compiled
arena. It derives initial dimensionality and coordinate bounds from the packet,
supports mouse/touch selection, pan, wheel zoom and Escape, and returns `update`,
`selection` and `dispose`. `update` accepts the next compiler/World packet without
resetting the user's view. Resize and GPU resource lifetime belong to the mount.
The caller supplies compilation and physics; mounting a packet executes no source.

`createRetainedPlotView` accepts those compiler-owned packets through
`replaceArena(packet)`, or materialized field meshes through `replace(scene)`.
Its coordinate view supplies world-to-screen projection. `selectAt` uses CSS
pixels; selection contours use device pixels and stay attached to stable mesh IDs.
Replacing a frame updates positions/colors and prunes removed IDs. Physics stays
in World/the physics engine; the view does not execute source or integrate laws.
Plotting remains outside a custom physics update function.

Line-list, line-strip, triangle-list and point-list packets are supported by this
screen presentation. It does not replace the existing lighting, depth, text,
toolbar or full 3D material renderer. Programmatic selection and the portable
selection interaction FSM are presentation APIs, not new VKF syntax. Applications
own their input/selection policy and supply the view with resulting geometry.

`npm test` runs public behavior tests. `PROVENANCE.json` records source pins and
the actual compiler fixture. This branch is a preview candidate, not a compiler
release, C0 acceptance or physical GPU verification. No hardware GPU is exercised.

## Isolated compiler0.7.2 capabilities

The 0.7.2 preview adds boolean native `viewport.add(...,selectable:true,draggable:false)` flags. Selection and object dragging are independent. Legacy pickable=false still blocks both. Following the Owner's October11 revision, this integration candidate defaults both selectable and draggable to false for data plots. Graphical scenes opt in with explicit selectable:true and draggable:true. Updating geometry does not enable interaction. Published preview assets retain their earlier defaults until a reviewed update. Compiler packet geometry is unchanged. Non-draggable objects do not disable viewport navigation. Selection follows stable mesh IDs across packet updates.

`createNativePlotInteraction({targets})` binds stable geometry IDs to existing native writable-input runtimes. Each target declares runtime, inputFields, positionFields and referenceSystem. A 3D target must declare a world plane or axis constraint. The adapter writes native inputs and calls the native update interface; it never writes retained geometry. Pass it to `mountRetainedPlot(...,{interaction,onInteractionChange})`; the caller handles World/compilation and supplies resulting packets. Missing bindings keep pan available.

The interaction candidate additionally accepts a declared `camera-plane` constraint
with its picked world point. Camera changes rebase the cursor mapping at the last
pointer position before applying further cursor movement. Camera changes alone do
not change native position and a stationary pointer performs no runtime update.
This prevents camera-only events from advancing a simulation through its update
hook. This is an adapter contract, not added VKF source syntax.

The verified record-input fixture uses the existing legacy emitter's integer num fields and explicitly enables quantized:true. Continuous f64 record-input updates remain a compiler preview gap, rather than silently claiming continuous dragging from integer storage. The adapter accepts f64/f32 native bindings when supplied by a compatible runtime. Physics remains outside the renderer.

Explicit line-list segments retain their sample geometry and disconnected curves. Antialiasing changes stroke presentation only. Native interpolation and symbolic plotting retain their original semantics; the UI infers no splines. The full lighting, depth, text and toolbar renderer remains available separately. Source983 preview checks pass86 library tests and desktop/phone SwiftShader selection; no physical GPU or C0/P0 acceptance. Historical0.7.1 fixture provenance remains unchanged.

## Embedding transition research — 2026-10-14

An isolated shared-library candidate adds affine-first transport, a moving split
example and smooth visual properties. These are JavaScript research APIs, not
new VKF syntax or compiler/physics acceptance. `npm run test:embedding` uses
Node's built-in test runner with no additional dependencies. See
[the prototype notes](examples/embedding-transport/README.md).

Pixel-only sentence/shape matching and collision-checked MP4 studies are in
[the raster research notes](examples/pixel-transport/README.md).
