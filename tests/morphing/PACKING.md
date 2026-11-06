# Native geometry channel packing

Active source 86d5841 restores the exact d429453 carrier-chunk packer. Each state/
carrier contributes one native chunk, appended once to the prepared channel
array. Ownership, order, validation and the original state.prepare are unchanged.
No source or interpolation algorithm was replaced.

The whole-output comprehension candidate 571a16a is rejected and removed from
active source. Small 2D/3D parity and a synthetic 1→27 benchmark passed, but the
actual 27→1 native glyph input returned corrupted value tag 65538 on a fresh
current075 instance. With the identical actual inputs, the restored full d429453
kernel prepared geometry in 4.55s and actual white/mint→gold RGBA in 5.78s with
all channels exact. That is correctness evidence for the restored implementation,
not permission to reuse the rejected candidate or its 0.7s timings.

`verify-packing.mjs <canonical075compilerDir>` compares complete native plans
against source 32aceb6 in 2D/3D, modes 0/1, and attribute widths 1/4/64. It tests BOTH
27-carrier 65² directions using distinct fields and RGBA per object, plus actual
physical native glyph 27→1 geometry and width 4 attributes. The compressed actual
fixture preserves the failed candidate's input and the qualified chunk kernel's
exact full-plan hashes. No host layout, glyph approximation or runtime numerical
implementation is added by these tests.

`packing-gc-fixture.json` separately preserves an actual contour call followed
by actual seven-to-one geometry. On one shared pinned075 instance this triggers
a native GC allocation-header assertion; geometry alone passes, and existing
native reset between calls does not repair it. The qualifier records that shared
arena RED explicitly. Detached native instances of the SAME cached module preserve
exact output. This ownership scope changes no retained-program/handle APIs.
Renderer docs/state-colors/NATIVE_ARENA_GAP.md and KERNEL_OWNERSHIP.json record
the bounded 216-operation history, creation cost and resident/external memory.
No source-only packing qualification claims to repair the shared native GC path.

`packing-qualification.json` records source/compiler hashes and measured WASM
costs including marshaling/decoding. Historical actual source 32 diagnostics
measured geometry 34.36s and attributes 210.81s, on physical fields different from
the synthetic benchmark. Native GPU/color rendering and full 29-view resource,
pixel and seek qualification are separate parent-owned integration gates. No
low-memory-device, 3D browser rendering, optical mixing or Navier–Stokes claim
follows from these tests.
