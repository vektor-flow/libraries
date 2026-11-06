# Native geometry channel packing

`verify-packing.mjs <canonical075compilerDir>` compiles this library and baseline
32aceb6f7aa7cece078482c75af7533a51c21f09 using the same current075 client compiler.
It compares every prepared value, natural-cubic second coefficient and metadata
field in 2D/3D, modes 0/1, with attribute widths 1/4/64. A 27-carrier 65² two-state
case independently checks all 228366 geometry values and appended RGBA channels
against the original state-local owner.

One output-sized native comprehension reads the original state/carrier/channel
order through scalar helpers. Ownership, validation, field sampling, interpolation
and the original state.prepare call remain unchanged. No indexed mutation per
channel or growing-prefix concatenation remains. It is an exact library packing
optimization, not a new geometry method or an inferred general language defect.

The first optimization d429453 used one concatenated chunk per carrier. Its
standalone 27-carrier benchmark passed but actual browser view 7 exposed a native
shared-arena GC trap. The whole-output builder is faster and preserves exact
plans, but does not independently repair that trap. Do not cite source-only
packing qualification as a working shared-arena integration.

`packing-gc-fixture.json` preserves the actual genuine native-outline contour
call followed by the actual seven-to-one geometry call. On the pinned075
runtime, sharing a kernel produces a native GC allocation-header assertion;
geometry alone passes, and existing native reset between calls does not repair
it. The qualifier records this shared-arena RED explicitly and requires exact
geometry under separate detached native instances of the same cached module.
That ownership boundary preserves value-only calls; retained program/handle APIs
remain a separate responsibility. See renderer docs/state-colors/NATIVE_ARENA_GAP.md
and KERNEL_OWNERSHIP.json for 216 applicable actual native operations, exact field/
plan comparisons, creation cost, and resident versus external memory measurements.

`packing-qualification.json` records the exact source/compiler hashes and measured
client WASM times, including marshaling/decoding. The historical actual Product
27-carrier diagnostic measured geometry 34363.7ms and attributes 210812.4ms;
its physical-glyph fields differ from the synthetic large benchmark. Exact
baseline plan comparisons use small native plans to avoid repeating that
several-minute large baseline. No GPU, low-memory-device or Navier–Stokes claim
follows from these CPU measurements. Parent separately qualifies the actual
29-view authored mixed-color rendering and capture path.
