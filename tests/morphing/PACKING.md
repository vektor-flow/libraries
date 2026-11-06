# Native geometry channel packing

`verify-packing.mjs <canonical075compilerDir>` compiles the current library and
baseline32aceb6f7aa7cece078482c75af7533a51c21f09 with the same current075 client
compiler. It compares complete prepared geometry and appended attribute plans,
including every value and natural-cubic second coefficient, in2D/3D, modes0/1,
and attribute widths1/4/64. A27-carrier65² two-state case independently checks
every geometry and RGBA slot against its original state-local owner.

The change uses supported zero-based dynamic comprehensions and flat native
concatenation to assemble one carrier chunk at a time. Ownership, ordering,
validation, field sampling, interpolation and the call to state.prepare remain
unchanged. It removes one large-array indexed assignment per channel. It is a
library packing optimization, not an inferred general compiler defect or a new
geometry method.

`packing-qualification.json` records the exact source/compiler hash and measured
client WASM times, including value marshaling and decoding. The prior actual
Product27-carrier diagnostic measured geometry34363.7ms and attributes210812.4ms
(`/tmp/vkf-state-colors-diagnostic.log`); this historical comparison uses a real
physical-glyph field and is not the identical synthetic input benchmark.
The exact baseline comparison itself uses small native plans to avoid repeating
the several-minute large baseline. No GPU performance claim follows from these
CPU timings. Parent separately qualifies actual authored mixed-color rendering.
