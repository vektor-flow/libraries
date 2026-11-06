# Sparse native event-field preparation

EventFields.prepare(plan, source_count, target_count, given_weights=[]) accepts
one opaque normalized two-endpoint star cohort N→1 or1→N, N<=128. Dimension2,
join0, no internal smoothing, original mode0/1 with zero second derivatives,
stride=8+size² and exact common-side geometry/RGBA duplicates are required.
The shared native coordinate/easing stays outside this factory.

StateEvents supplies the Ward/C1 embedding and native clipped-cell areas supply
default weights on the distinct side. Existing topology.arrival/support and
state.prepare_jets supply all field curves. Splits reverse the SAME embedding
curve, swapping interval endpoint second derivatives without negation. Source
and target RGBA remain separate for canonical global-coordinate interpolation.
Identity means exact N1 field equality only; poses/colours may still change.
Those fields remain original throughout, avoiding artificial support inflation.

Prepared returns chunks:[InputChunk(offset:int,values:[num])], input_width,
controls:StateControls.Descriptor, normalized weights, actual embedding,
original event tree, ascending actual event_coordinates, direction(+1merge,
-1split,0singleton), source_rgba,target_rgba and identity. The uploader allocates
input_width f32 values and copies each native chunk at its exact offset; it does
not synthesize fields. Validate bounds/no-overlap and the shared memory budget.

The unchanged flat GPU address layout is: embedding.values then embedding.second;
per-carrier source blocks[arrival,m0,m1]; per-carrier target blocks[arrival,m0,m1];
shared support; growN; shrinkN; sourceRGBA4N; targetRGBA4N; normalized weightsN.
The eight EventLayout offsets identify these regions. Common immutable blocks
and zero jets are prepared once and reused. Total offsets are preflighted below
2^24 before allocating large fields.

Native finite gate: actual27 physical-font cohort produces62 chunks/697828floats
(2,791,312 f32 bytes),824-byte descriptor,26events. Preparation26.28s on this host;
this is one-time preparation, not frame latency. Authored endpoint clipped
triangle values match exactly. ActualN2 sparse/full native coalescence differs
<=1.12e-16, reversed split<=2.23e-16. Identity fields are exact;8 malformed
cases reject. Factory-only qualification does not prove first contact, rendered
count/area/colour, GPU performance or complete Product presentation behavior.

The initial monolithic candidate trapped near the native configured heap cap.
MONOLITHIC-DIAGNOSTIC.json records the observation. Chunking retained identical
addresses/math and passed under the existing budget; no heap limit was raised.
