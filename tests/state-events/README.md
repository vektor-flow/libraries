# Native laminar embedding events

StateEvents.prepare(source4N, positiveWeightsN, commonTarget4) builds a bounded
N-to-one Ward tree and the existing native C1 state Curve. N is1..128; source
and target extents must be positive. Ward cost uses XY centroids only. Pair
iteration uses ascending node IDs and keeps the first exact tie. Leaf nodes are
0..N-1; internal nodes are N+j; parent[root]=-1. Each internal event coordinate
is (j+1)/N, leaving the last interval to settle into the common target. Singleton
metadata uses .5 for field support while its embedding follows the straight path.

For each parent cutoff t, an existing cubic segment takes offset factor1 to0,
with initial derivative-1 and terminal derivative0. A leaf's embedding is the
root's straight weighted-mean path plus its ancestor centroid offsets times
these factors. This is prepared once through morphing.state.prepare_jets;
playback uses the same state interpolation backend. No easing is applied here.

Before each cutoff,0<=f_child<=f_parent<=1-q; afterwards that factor is0.
Telescoping ancestor centroids therefore gives nonnegative convex coefficients,
so positive extents stay positive. Weighted offsets cancel. Once descendants
share a parent cutoff, their remaining paths and first jets are identical and
never separate. These are embedding properties. They do not establish first
geometric contact, overlap topology, rendered connected-component count, ink
area, colour, optical conservation or physical momentum.

Run `node tests/state-events/qualify.mjs <canonical075Directory>`. The test builds
with the current native compiler and an independent test-only Ward oracle.
Five finite fixtures include the actual current07527-glyph source/target
embeddings with explicitly uniform test weights (not claimed ink-mass weights),
a weighted synthetic27, exact ties, singleton and extreme positive extents.
QUALIFICATION.json records endpoint, weighted-mean, first-jet, coincidence,
replay and malformed-input checks. No GPU/raster or Product readiness claim.
