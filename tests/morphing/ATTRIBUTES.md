Native per-carrier attributes extend the existing canonical geometry plan:

```
Morphing.prepare_geometry_attributes(plan, offsets, owners, attributes, width)
biological.attributes(plan, offsets, owners, attributes, width)
field.field(values, dimension, size, stride, carrier, x, y, z, scale, offset=0)
field.dominant(values, dimension, size, stride, carriers, x, y, z, scale, offset=0)
```

`offsets` and `owners` use the same state-local object mapping supplied during
geometry preparation. `attributes` is object-major, `width` finite channels per
object. The helper appends channels after the prior carrier stride and calls the
same state.prepare with unchanged knots and interpolation mode. Existing channels
and geometry flags retain their exact ordering and values. Repeated attributes
append after any previous attributes; callers own channel names/offset semantics.
The plan's record shape is unchanged, while stride and curve.width grow.

RGBA uses width4 and the renderer validates authored RGBA bounds. This generic
helper accepts finite numeric attributes, not only colors. Component interpolation
uses the authored numeric color space; this is not perceptual mixing or a material
physics claim. Two endpoints are qualified for linear and natural cubic modes;
no bounded-color guarantee is made for arbitrary multi-key cubic curves.

The field offset permits original carrier data in a larger packed GPU input.
Default0 preserves existing arithmetic. Dominance chooses the greatest native
signed field; exact ties choose the last carrier in authored input order. It does
not alter geometric union/area calibration, average colors, infer semantics or
claim a unique physical mixture. Outside the union it selects the greatest field
as well; the caller still owns geometry clipping.

Run the bounded current075 WASM qualification:

```
node tests/morphing/verify-attributes.mjs CANONICAL_COMPILER_DIRECTORY
```

Evidence is in attributes-qualification.json. Original geometry channels and
field queries remain exactly equal with appended attributes. Tests cover endpoint
and intermediate RGBA, split ownership, both state paths, packed offsets, dominant
regions/ties and malformed width/storage/owner/nonfinite inputs. GPU color rendering
and actual mixed-row integration are a separate renderer-owned qualification.
