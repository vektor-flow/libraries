# Local carrier geometry prototype

`dispatch.carrier_mesh_packet` clips each carrier's interpolated local signed
field using the existing parallel triangle clipper. For the text profile with
join=0, the union of these positive regions is the canonical max-field zero set.
It emits xyzRGBA rendering data; z encodes positive material field for a renderer
depth winner, not a physical body/depth. No triangle becomes an authorable object.

The native075 unit compares the offset clip packet to the original clipper and
checks positions/attributes. This is an internal prototype only: active global
measure, renderer and Interp routes are unchanged. GPU rendering, area, endpoint
fidelity and component-count qualification are pending.

The initial84-float entry calling a72-float array-return helper is rejected by
the current GPU emitter (`cannot convert array:72 to array:84`). The prototype now
reuses the existing scalar polygon-count/coordinate helpers with an explicit
field offset. It preserves the same clip crossings and packet order and emits
one84-float output directly. No IR or generated shader edits are used.
