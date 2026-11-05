# Interpolation

Optional native VKF interpolation for numeric channels: affine blends, polynomial
curves, tensor-product patches, and the existing Morphing state/material API.
This is a finite first slice, not a general constraint solver. Copy
`Interpolation.vkf`, `Interp.vkf`, `interpolation/`, `Morphing.vkf` and `morphing/` beside the
importing project. Existing `m:.Morphing` imports remain valid and unchanged.

```vkf
i:.Interpolation
::i.blend([0,2],[4,6],0.25)
```

The blend is `[1,3]`. For scalar values, `i.lerp(0,4,0.25)` returns `1`;
vector blending uses that same scalar kernel. Coordinates are parameters; they need not represent time.
The new constructors use normalized coordinates in `[0,1]`, without extrapolation.

## Curves and derivatives

```vkf
i:.Interpolation
curve:i.prepare_bezier([0,0,1,2,2,2,3,0],2)
at:i.sample_polynomial[plan:curve]
s:at(0.5)
::s.value
::s.first
```

Controls are flat, point-major: `[x0,y0,x1,y1,...]` at width `2`.
A Bezier curve passes through its first and last controls. Interior controls are
handles, not required passage points. `Sample` contains `value`, `first`, `second`,
all arrays of channel width; derivatives are with respect to the supplied
coordinate. `Polynomial` stores `controls`, `width`, `count`.

```vkf
jets:i.prepare_hermite([0],[2],[2],[2])
s:i.sample_polynomial(jets,0.5)
# If q=(time-time_start)/duration, velocity = ds/dq / duration.
duration:4
velocity:s.first.(0)/duration
acceleration:s.second.(0)/(duration*duration)
::velocity
```

Hermite supplies endpoint values and first derivatives with respect to normalized
`q`. A physical endpoint velocity must be multiplied by duration before preparing
this cubic. Second derivatives are outputs, not extra Hermite inputs. Preparation
converts once to Bezier controls; floating-point conversion can round endpoint
jets. It does not select an automatic easing or phase-joining policy.

## A bicubic surface with a mixed term

`prepare_patch(controls,3,4,4)` constructs a 3D bicubic patch. Control `(a,b)` in
the example is `(a,b,a*b)` for integer indices `0..3`; the represented surface is
`(3*u,3*v,9*u*v)`, so its mixed derivative is nonzero. This is a surface in two
independent coordinates, not a curve or an interpolation between two surfaces.

```vkf
surface:i.prepare_patch([0,0,0,1,0,0,2,0,0,3,0,0,0,1,0,1,1,1,2,1,2,3,1,3,0,2,0,1,2,2,2,2,4,3,2,6,0,3,0,1,3,3,2,3,6,3,3,9],3,4,4)
p:i.sample_patch(surface,0.5,0.25)
::p.duv
```

`PatchSample` contains `value`, `du`, `dv`, `duu`, `duv`, `dvv`. Here `duv` is
`[0,0,9]`. Storage index is `((v*u_count+u)*width+c)`: `u` varies fastest.
`Patch` stores `controls`, `width`, `u_count`, `v_count`. Physical chart lengths
require dividing `du` by the u length, `dv` by the v length, and `duv` by their
product. The library does not glue neighboring patches or tessellate a surface.

## Public additions

| Native signature | Result |
| --- | --- |
| `lerp(start:num,finish:num,coordinate:num)` | `num` |
| `blend(start:[num],finish:[num],coordinate:num)` | `[num]` |
| `prepare_bezier(controls:[num],width:int)` | `Polynomial` |
| `prepare_hermite(start:[num],finish:[num],start_derivative:[num],finish_derivative:[num])` | `Polynomial` |
| `sample_polynomial(plan:Polynomial,coordinate:num)` | `Sample` |
| `prepare_patch(controls:[num],width:int,u_count:int,v_count:int)` | `Patch` |
| `sample_patch(plan:Patch,u:num,v:num)` | `PatchSample` |

Positive channel widths, matching nonempty arrays, valid control layouts and
bounded finite numeric inputs are required. Preparation follows the existing
numeric guard `abs(value)<10^100`; this is an input guard, not a universal error
bound. Polynomial and patch counts may be one (constant in that direction).
High degree, large derivatives and poorly scaled inputs still require care.
There is no certified floating-point error estimate or unlimited-allocation promise.

## Existing state and material programs

```vkf
i:.Interpolation
plan:i.prepare([0,1,2],[0,0,1,2,3,0],2,1,true,true)
state:i.sample(plan,0.5)
material:i.prepare_material([0,1],[0,1,3],[2,1,1],[0,-1,1],1,0,false,false)
carriers:i.sample(material.state,0.5)
```

The 16 existing facade functions delegate to the SAME Morphing implementation,
with unchanged signatures: `prepare`, `sample`, `weights`, `channel`,
`prepare_affine_embedding`, `sample_embedding`, `prepare_material`, `bind_view`,
`sample_view`, `reserve_groups`, `prepare_geometry`, `geometry_measure`,
`sample_geometry`, `geometry_row`, `unfold_defaults`, `field_grid2`.
See [Morphing](../morphing/README.md) for their contracts and integration limits.
`prepare(coordinates,states,width,mode,smooth_start,smooth_end)` remains explicit:
mode `0` is piecewise linear, mode `1` natural cubic. Endpoint smoothing is an
optional coordinate map; it changes the original curvature-minimization claim.
Natural cubic can overshoot. Material correspondence remains caller-supplied;
conserved carrier weights do not establish every geometric quantity or constraint.

The `Interp` settings record now supplies mode-specific named/default factories;
see [the contract](INTERP-CONTRACT.md). No new language syntax, interpolation
runtime hook, general hard-constraint engine, physical temperature policy or
automatic C2 phase joining is provided. Source-only graph/conic/rounding research
was migrated with provenance and remains unqualified.
Renderer identities remain renderer-owned. The next integration steps and actual
branch API evidence are in [the contract](../tests/interpolation/CONTRACT.md).

## Current qualification

The first native CPU batch passed on the current selected VKF **0.7.5** compiler:
16 planned fixtures (five positive programs and eleven expected assertion
rejections), including 83 oracle samples and 1,050 scalar comparisons against
independent exact-rational references. A focused rerun also checked exact result
widths and retained control components. The complete existing core fixture ran
through the new entry point; its Morphing implementation was unchanged.

The [four-line example](../examples/interpolation-basics.vkf) compiled and printed
`1`, `3`, `0.5`, `9`. A coupled bicubic surface fixture evaluated 441 positions
in VKF; its offline figure only plots those saved native coordinates.

[QUALIFICATION.json](../tests/interpolation/QUALIFICATION.json) pins the tested
compiler, numerical sources, test harnesses, outcomes, and retained failed runs.
The native test command, inside the project's admitted execution session, is:

```sh
python3 tests/interpolation/verify.py --compiler "$VKF_COMPILER" --output /new/evidence/path
```

This is finite native evidence, not a certified continuum error bound. WASM,
native/WASM agreement, GPU execution, renderer/native-View integration and
performance remain unqualified for these new methods. Explicit runtime NaN or
infinity injection was not tested. Combined native-and-WASM qualification is
therefore incomplete.

Two initial failures are retained in the receipt. A facade import alias collision
caused self-recursion and was fixed in the new entry point. A dynamic-versus-literal
whole-array comparison failed despite matching scalar components; numerical-map
tests now check exact components and widths without weakening tolerances. The
session-specific `execute_native.py` preserves that admitted run's lifecycle; it
is not a reusable authorization or a second interpolation implementation.
