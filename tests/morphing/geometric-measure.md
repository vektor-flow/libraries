# Native clipped-cell geometric measure prototype

This adds only internal helpers to morphing/parallel.vkf. Active biological.raster,
dispatch.sample_field, calibration and all browser assets remain unchanged.
The previous soft-coverage measure is still unqualified as geometric area.

Contracts:

- triangle_fraction(a,b,c) returns the area fraction where a triangle's linearly
  interpolated finite signed field is nonnegative. One-inside uses the product
  of its two native edge crossing ratios. Two-inside uses u+v-u*v, avoiding the
  subtraction of nearly equal unit areas. The result is bounded to [0,1].
- cell_fraction(a,b,c,d) uses row-major corners and the SAME a--d diagonal as
  existing parallel.corner/cell_triangles. It averages the two triangle fractions.
- cell_area(values,size,extent_x,extent_y,cell) integrates that nodal cell over a
  rectangular domain. Grid values may have trailing attributes after size² nodes.
  Storage, positive extents, size and cell-index guards reject malformed input.

The helper measures the existing piecewise-linear rendering model. It does not
claim the true area of a bilinear interpolant, an exact curved outline, a union
of separately rendered carriers, or an antialiased pixel mask. Nonnegative zero
plateaus are filled, matching current contour clipping; a zero edge with negative
remaining interior has zero area. All-zero triangles therefore count as filled,
and their complements also count as filled. Do not infer a complement identity
on a positive-measure zero plateau.

Run with the exact current075 canonical compiler directory:

```sh
node tests/morphing/geometric-measure.mjs /path/to/current075/canonical
```

The native test checks 125 triples, all 6 vertex permutations, positive field
rescaling by 1e-8/1e-4/1/1e4/1e8, 625 corner configurations against area integrated
from EXISTING native cell_triangles packets, the saddle diagonal, rectangular
scaling and invalid cell guards. All numerical oracle work executes in native
VKF. Packet comparisons use 1e-12 absolute tolerance in current075 WASM, not a
claim of bit-identical floating arithmetic. Qualification includes source and
compiler hashes. GPU real-f32 and active calibration integration are separate
checks owned by the parent task.

No tetrahedron/3D volume helper is added: robust mixed-sign tetrahedron clipping
and its renderer agreement require a separate bounded qualification. No active
measure, public facade, renderer, font resource or PP source changes here.
