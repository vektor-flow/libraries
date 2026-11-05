# Interp settings and native playback

`Interp.vkf` owns the typed `Interp` record and named construction API. Import
`i:.Interpolation` for the public facade, or `i:.Interp` for settings and scalar
text channels only. Existing `m:.Morphing` numerical APIs are unchanged. The
public Interpolation facade delegates state sampling to that exact backend.
Copy all three root modules and both `morphing/` and `interpolation/` directories.

```vkf
i:.Interpolation
state:i.state_interp(path:1)
reveal:i.spectral_interp(k:4,velocity:0.54,overshoot:0.32,grow:true)
vapor:i.vapor_interp(seed:17,spread:0.35,lift:0.65)
plan:i.prepare_interp(state,[0,1,2],[0,1,0],1)
q:i.time_coordinate(0.25)
::i.sample(plan,q).value
```

Mode-specific optional arguments are named factory parameters, resolved by native
VKF defaults. The matching JSON Schema and mode descriptor are canonical client
metadata: `interp-settings.schema.json` and `interp-modes.json`. Reject unknown
fields and fields from other modes before calling the selected factory. A JSON
schema default is documentation; native factory omission actually applies it.
The client must pass only supplied named fields, or their declared native defaults.

| Factory | Optional named arguments and native types |
| --- | --- |
| `state_interp` | `path:int=0` (0 linear, 1 natural cubic) |
| `spectral_interp` | `k:num=4, velocity:num=0.54, overshoot:num=0.32, grow:bit=true` |
| `vapor_interp` | `temperature:num=1, spread:num=0.35, lift:num=0.65, seed:int=0`, then the same reveal arguments |

Direct `Interp` module factory names are `state`, `spectral`, `evaporate`.
`temperature=1` is the sole implemented evaporation setting. Lower temperature
values reject explicitly; research activation policies are not a thermodynamic
solver. Spread/lift lie in `[0,4]` in the chosen renderer-local coordinate units;
seed is an integer in `[0,65535]`. Reveal uses k `[1,10]`, velocity `[0,1]`,
overshoot `[0,0.5]`, and boolean grow. Velocity zero holds the reading front.

The current finite record ABI is `Interp:(mode:int,path:int,reveal:[num],vapor:[num])`.
Mode tags are 0 state, 1 spectral, 2 vapor. Absent payloads are `[]`; reveal's
internal layout is `[k,velocity,overshoot,grow_as_0_or_1]` and vapor's is
`[temperature,spread,lift,seed]`. Empty payloads resolve to named defaults.
This representation needs no unverified optional/union record syntax. Native
`settings` validates supplied payloads, including irrelevant-mode rejection.
Editors should expose named parameters, never these positional arrays. A future
nominal optional-record ABI can replace this storage after compiler qualification.

`prepare_interp(settings,coordinates,states,width)` accepts only state mode.
It returns the existing Plan, with the legacy endpoint-map flags off. Apply the
shared `time_coordinate(q)` once before sampling. For knot ranges other than
`[0,1]`, the caller maps the eased fraction to the declared coordinate range.
This quadratic clock is C1, piecewise C2, and not globally C2 at its midpoint.
Do not apply the old endpoint clock as well. Cubic path choice and time easing
remain independent; cubic overshoot and all prior backend limits remain explicit.

`reveal_channel(settings,distance,channel)` returns scalar alpha, growth, red,
green, blue for channels 0–4 using the existing native unfolding implementation.
`distance` comes from cached native glyph/row reading indices, not a new layout
or parser. `reveal_advance(settings,front,elapsed)` advances that front by native
velocity; `elapsed>=0`. Prepare growth coefficients once when using the lower
level unfold API for resident-GPU playback; the convenient record API computes
it when requested. No claim of a new optimized GPU path is made here.

`vapor_channel(settings,q,index,channel)` returns dx, dy, alpha, size for channels
0–3. `q` is the already eased `[0,1]` coordinate. Indexed deterministic modular
sampling uses bounded integers, no frame integration, ambient random seed or
mutable PRNG. Index must be `[0,65535]`; no arrays allocate in this kernel.
Renderer prepares a bounded immutable sample set from the **actual native source
glyph distance/coverage field**, then adds dx/dy in local glyph coordinates and
multiplies gas alpha by that sample's ink coverage. Gas samples are presentation
carriers, never thousands of authorable rigid bodies. Gas alpha is zero at both
endpoints. `source_alpha(q)` is `(1-q)^2` and remains independent of gas alpha.

Reveal target rows through `reveal_channel` with a reading front that completes
by q=1; rows start during gas decay so they appear from the fumes. Keep source
native glyph rendering exact at q=0 and target native glyph rendering exact at
q=1. Keep original native glyph geometry/distance fields unchanged throughout.
At final reveal, map the existing white spectral finish to authored ink color in
the native renderer, preserving native UV/coverage and linear color handling.
This contract returns channels, not a compositor or native font sampler.

Caller retains cancellation and memory/resource ownership. Stop requesting
channels when superseded; do not integrate late worker frames. Keep at most the
bounded prepared source set and current/next packets. Carrier memory is O(N),
channel evaluation O(1), and indexed samples reproduce at arbitrary seek order.
No opacity/material conservation, temperature physics, automatic glyph matching,
ink resampling policy, topology proof or native View implementation is implied.

Current verification is finite canonical client WASM execution in
`tests/interp/evidence/qualification.json`. Native ELF, GPU lowering/execution,
renderer pixels, physical devices, visual quality and PP integration remain
separate gates. The descriptor intentionally does not label those routes ready.


## One-call native packet

`text_frame(settings:Interp,q:num,source_ink:[num],target_reading:[num],front:num)`
returns `TextFrame:(source_alpha:num,gas:[num],target:[num])`. The facade and the
Interp module share this exact function name. `source_ink` packs local x, y,
coverage triples; `target_reading` contains cached native glyph reading positions.
Only vapor mode accepts nonempty source carriers. Each input set is capped at
65,536 entries. Coverage must be `[0,1]`, positions and reading coordinates finite
with magnitude below `10^10`. Output gas packs x, y, alpha, size per carrier;
output target packs alpha, growth, red, green, blue per glyph. Gas positions
already include the source x/y; alpha already multiplies source coverage.
Keep glyph native UV/geometry, author color and sample point footprint separately.

The batch validates settings once, prepares the growth coefficient once and
computes all channels inside VKF. Browser integration makes **one guest call per
frame**, not one RPC per carrier/channel. No native font geometry is recreated.
For reveal-only mode, pass `source_ink=[]`. Empty arrays are valid. Target opacity
is forced to zero at q=0 and to one at q=1; final target growth and color are exact.
Schedule the reading front to complete by the end to avoid a final reveal jump.
The scalar `reveal_channel` retains its independent reading-front semantics;
only the transition batch imposes the exact scene endpoint guards.

The canonical guest ABI is synchronous and has no cooperative in-call cancel
hook. Check generation/cancel before dispatch and discard superseded results.
This is an explicit integration limitation; bounded arrays prevent unbounded
work but do not by themselves establish realtime latency. GPU execution, bulk
performance and genuine native-glyph compositor integration remain unqualified.
Batch qualification is separately recorded in
`tests/interp/evidence/batch-qualification.json`.
