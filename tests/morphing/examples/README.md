# Compiled surface examples

`morphing.examples.kernel(index, params, values)` returns one triangle as 21
numbers: xyzRGBA for each vertex. `params` is `[example, coordinate, mode,
smoothStart, smoothEnd, resolution]`; `values` is exactly `[0,1,2]`. Dispatch
`2 * resolution * resolution` invocations, resolution 2..256. Coordinate is
0..2, mode 0 linear / 1 natural cubic, and smooth flags are 0/1. The shared
`state.coordinate_map` handles endpoint easing; `segment.value` evaluates the
natural cubic, with the analytic middle second derivative for three equal knots.
There is no host morph arithmetic, opacity animation, geometry readback, or camera
transform in this kernel. Output colors contain two-sided flat diffuse lighting.

| ID | Three states | Geometry |
|---|---|---|
| 0 | Plane, saddle, wave | Open zero-thickness sheet |
| 1 | Plane, half-roll, full roll | Zero-thickness sheet, periodic seam meets at end |
| 2 | Torus, varying tube radius, varying major radius | Closed surface bounding volume |
| 3 | Sphere, x-ellipsoid, y-ellipsoid | Closed surface bounding volume |
| 4 | Plane, half-twist, full-twist | Open zero-thickness helicoid sheet |
| 5 | Disk, dome, disk | Open zero-thickness sheet |

These are correspondence examples, not topology-changing implicit solids or a
claim of area/volume conservation. The sphere endpoint ellipsoid scale products
are one; intermediate cubic vertex interpolation is not volume constrained.
Sphere poles and the disk center include degenerate parameter-grid triangles.

`build_examples.py --library ... --compiler ... --gpu-compiler ... --output ...`
compiles native fixtures and canonical WGSL with provenance. Native verification
checks 55,296 packets across six examples, both interpolation modes, all four
endpoint easing settings and nine coordinates, plus cubic equivalence to the
shared state interpolator. Emission alone is not browser or hardware acceptance.
The bounded compiler currently assigns the kernel packet width to array-returning
helpers, so internal point/vertex arrays also use 21 slots (only xyz are read).
