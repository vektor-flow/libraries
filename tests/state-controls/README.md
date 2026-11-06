# Native small state-control descriptor

StateControls.prepare accepts CurveLayout, GeometryLayout, optional density and
zero/one EventLayout. It retains knots and scalar layout only, never SDF values,
curve values/curvatures or per-glyph field arrays. sample returns the agreed
52-slot canonical GPU control packet. The caller supplies the already-mapped
native coordinate; this module applies no easing or interpolation law.

Slots0..35 preserve the existing native renderer-adapter ink controls. Mode2
encodes negative curve count; field width is geometry.width. Slot16 is caller
tolerance,17 is1e-6. Slots36..40 describe density, optional events, reserved0,
embedding width and coordinate. Slots41..48 contain event offsets;49..51 carry
optional positive CSS viewport dimensions. Lattice0 derives2*resolution-1.

The native WASM gate checks56 dense/event, linear/cubic/first-jet, NDC/viewport
and coordinate cases against an independent test-only packet oracle. Every
slot matches exactly. Default arguments and17 malformed layout/sample rejection
cases pass. Event descriptor is824 JSON bytes for the27-carrier fixture; no
large field payload is supplied per sample. This is not a measured frame-rate,
GPU raster, first-contact or full Product qualification.
