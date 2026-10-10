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
