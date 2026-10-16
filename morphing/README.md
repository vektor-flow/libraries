# Morphing

An optional VKF library for interpolation of states and embeddings. It belongs to
projects that use it; it is not a new standard-library or core-language feature.
Copy `Morphing.vkf` and `morphing/` beside the importing VKF project.

The independent coordinate can represent time or any other ordered quantity.
The result is a callable state function. The renderer continues to own its View,
Embedding and Layer identities. Morphing computes channels and derivatives; it
must not create a parallel scene hierarchy or substitute an image crossfade.

```vkf
m:.Morphing
plan:m.prepare([0,1,2],[0,0,1,2,3,0],2,1,true,true)
at:m.sample[plan:plan]
state:at(0.5)
::state.value
```

`prepare(coordinates, states, width, mode, smooth_start, smooth_end)` accepts
state-major numeric channel storage. Mode `0` is piecewise linear; mode `1` is
natural cubic, minimizing integrated squared parameter curvature. Coordinates
must strictly increase. Two states, or any larger count, use the same API.

`sample(plan, coordinate)` returns `value`, `first`, `second`. These are coordinate
derivatives, not necessarily time derivatives. Endpoint easing independently sets
both derivatives to zero at the selected outer boundaries, keeps all key states
exact, and does not stop at intermediate states. Easing is a separate coordinate
map; its composition does not retain the original curvature-minimization claim.
Natural cubic can overshoot; this does not guarantee monotonicity of all geometric
measurements or interpolation on rotation/manifold constraints.

`weights(plan, coordinate)` supplies shared interpolation weights.
`channel(plan, coordinates, component)` exports a sampled renderer property.
An application-defined embedding can consume `sample` to produce its View data.
`prepare_affine_embedding(...)` / `sample_embedding(...)` additionally interpolate
an affine embedding and the state it maps, including the complete first/second
product-rule derivatives. Each embedding row stores its coefficients then offset.
This optional adapter does not restrict general application embeddings to affine.

`bind_view(view_id, layer_ids, offsets, plan)` binds channel ranges to existing
renderer identities. `sample_view(binding, coordinate)` returns those same IDs
and the sampled channels; it never creates replacement identities. This is an
explicit adapter packet, **not** a counterfeit implementation of the renderer's
native `View` or `Layer` type. Native-handle extraction/application is not yet wired.

`prepare_material(coordinates, offsets, weights, positions, dimension, mode,
smooth_start, smooth_end)` constructs a persistent material carrier through
multiple states with different object counts. Every carrier has a positive,
constant weight and an owner in every state: children split from existing parents
and can merge again. Total measure must agree (relative tolerance 1e-10); numerical
roundoff is normalized to the first state's total. There are no empty/transparent
endpoints and no birth/death fallback. Object ordering is caller-supplied material
correspondence, not automatic spatial or semantic matching. `sample(plan.state,q)`
samples carrier positions; `owners` is state-major and local to each input state.

`reserve_groups(source_count, target_count, source_groups, target_groups, costs)`
reserves the largest unchanged semantic groups first, choosing repeated occurrences
by whole-group cost. Group triples are `[identity, first_member, member_count]`.
This preserves terms such as `4ac` against character-by-character reassignment.
Unresolved entries are `-1` correspondences to plan, never empty visible objects.

Constant carrier measure is **not yet** conserved visible ink/solid volume. The
rounded connected-boundary solver, general correspondence, collision routing,
medial thin strokes and hole-event handling from the current reference still need
to be ported. This core must not be advertised as the completed biological solver.

## Verification and integration boundary

`tests/morphing/verify.py --compiler /path/to/vkf --output /new/evidence/path`
builds an independent project and runs the actual native library. SciPy is solely
a test oracle. No Python, JavaScript or handwritten WGSL executes interpolation.
Evidence records the compiler and source hashes. The first successful run used
installed VKF 0.7.3; this does not change the site's pinned 0.7.2 compiler release.

The current native UI packager rejects a root `type_alias` from imported libraries,
and rejects calls constructing a View inside a function. The probes are retained
in Cuvami `staging/artifacts/morphing-library-20261016/probes` and `project/view.vkf`.
Pure VKF compilation/execution succeeds. Direct animated native View packaging is
therefore **not complete**, and the old browser matcher is not a fallback.
