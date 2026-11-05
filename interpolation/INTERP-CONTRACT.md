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

The public **typed structural record** (ABI 2) is:

```vkf
StateSettings:(path:int)
RevealSettings:(k:num,velocity:num,overshoot:num,grow:bit)
VaporSettings:(temperature:num,spread:num,lift:num,seed:int)
Interp:(mode:int,state:[StateSettings],reveal:[RevealSettings],vapor:[VaporSettings])
```

Each optional group holds zero or one typed named record; `[]` means absent.
This is the actually qualified finite native encoding, not invented nullable,
union, dependent-field or record-default language syntax. These are structural
record types, not a claim of nominal constructor identity. Mode tags are 0
state, 1 spectral, 2 vapor. Omitted groups retain native defaults on evaluation.
Mode0 permits only `state`; mode1 permits only `reveal`; mode2 permits `reveal`
and `vapor`. Any inapplicable group rejects, even a text-mode state group with
`path:0`. More than one record in a group rejects. Every present setting is
accessible by its actual name, including native boolean `grow` and integer `seed`.
There are **no positional numeric settings payloads** in this public ABI.

```vkf
i:.Interpolation
config:i.spectral_interp(k:7,grow:false)
::config.reveal.(0).k
::config.reveal.(0).grow
# Advanced direct construction with a complete named typed group:
manual:i.interp(mode:0,state:[(path:1,)])
```

Primary callers use the named factories, whose omitted parameters apply actual
native defaults. The low-level `interp(mode,state,reveal,vapor)` facade, or
`Interp.settings`, accepts named typed optional groups for inspection/advanced
construction; partially specified record literals are not a supported syntax.
A caller that wants only `k` to change uses `spectral_interp(k:...)`, rather than
inventing `k?`, nulls or partial records. The native record schema is `interp-native-record.schema.json`; it enforces
the same named fields/cardinalities/mode groups for host ABI transport. The
strict named factory JSON schema remains unchanged: it already separates the three modes with `additionalProperties:false`.

ABI2 replaces d2952a9's earlier opaque numeric record payloads. This is a
source/record-ABI correction, not another interpolation engine. Native factory
names, arguments and numerical behavior remain compatible. Previously emitted
renderer artifacts remain pinned to their old source until explicitly rebuilt;
never pass a new-ABI record into an old-ABI WASM kernel or vice versa.

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
