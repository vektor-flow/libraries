# Varied GPU math and geometry film — 2026-10-14

The current study uses **GPU math**, the independent typesetting runtime and its
native scalar distance atlas. Its source/assets are pinned at
8352880e0c7a37c1794892521bc5c73abfb22104. The other chat's worktree is read-only.
Historical terminology and evidence below are retained for provenance.

New endpoint-only research adapters:

- `affine_transport.py` infers a positive-determinant affine map by enumerating
  cyclic boundary alignments. Polar rotation/log-stretch interpolation preserves
  the affine shape throughout. It requires compatible boundary sampling; this
  is not a general affine recognizer for independently resampled images.
- `registered_transport.py` infers rotation from boundary distance and hole
  positions before contour interpolation. Rotation and residual deformation
  happen concurrently. This fixes the two-hole infinity-to-eight candidate;
  validation is still required for arbitrary shapes.
- `replica_transport.py` handles bounded split/merge cases between approximately
  axis-affine-equivalent, hole-free outlines. Geometry eligibility precedes
  spatial assignment; small sampling differences must not outweigh travel.
  Curved central contact necks, smooth field unions and continuous area calibration operate concurrently with
  movement. Fields are reconstructed from native zero contours at 4x sampling;
  they are not direct atlas-alpha interpolation. Reverse playback gives merges.
  It rejects unrelated cohort overlap and unsupported geometry. Component count
  must be checked over time; monotonicity is not guaranteed for arbitrary inputs.
- `plan_transport.py` selects these bounded candidates from anonymous endpoint
  geometry: count change, affine equivalence, hole count and body count.
  `render_variety.py` validates the result. No formula strings, glyph identities,
  supplied correspondences or example planner labels enter inference. Selection
  can still return a candidate that fails validation; no fallback is hidden.

Evidence is in Cuvami `staging/artifacts/embedding-transport/mixed-transformations`.
The input contains rotation/translation, shear/stretch, GPU math symbol division,
symbol merging, a ten-body fraction rearrangement, ring-to-Delta with one hole,
infinity-to-eight with two holes, and a one-to-three geometric division.
The symbol changes are visual demonstrations, not algebraic equivalence claims.
The film uses one evolving state at a time, six seconds per case, 60 fps and
linear-light color interpolation. There are no start/end overlays or crossfades
between unrelated endpoint images.

Twenty focused tests pass, including geometric affine inference with reversed
boundary indexing, endpoint ramp behavior, rotation of two-hole geometry,
near-identical repeated bars, generated split shapes and reversed trajectories.
Independent bilinear atlas sampling validates all ten basic math endpoint layouts
at greater than 0.992 silhouette IoU, with matching component/hole counts.
This does not establish the other runtime's cropped/extended glyphs, viewport
wrapping or browser integration. The three branching cases also pass 933 half-frame samples; their calibrated
coverage-area errors stay below 0.0002 square pixels. Full frame/codec receipts
accompany the film. Ordinary 4:2:0 encoding damaged near-contact seams even at
lossless quantization and was rejected. The final film uses lossless RGB H.264;
players must support its High 4:4:4 Predictive profile. This is a codec limitation,
not a relaxation of the geometry/decoded-frame checks.

Reproduce in a fresh output directory:

    python -m unittest discover -s examples/field-transport -p 'test_*.py'
    python examples/field-transport/render_variety.py INPUT_JSON OUTPUT_DIRECTORY

Preserve failed first trials: bar assignment caused overlap, and unregistered
infinity-to-eight crossed a hole. The shared fixes address geometric families;
no per-formula trajectories were added. Distribution, collection, factorization
and cancellation remain unresolved in the existing benchmark. This is an offline
CPU reference using GPU math field data, not GPU playback, a complete arbitrary
morphology solver, or a claim of global optimality/continuous collision proof.

---

# Scalar-field contours with preserved holes

The earlier coalescence movie passed component-count checks but lost the hole in
ring→D for 37 of 312 motion frames. Its earlier acceptance did not establish
topology preservation. This isolated replacement focuses on equal topology.

`Atlas` consumes the completed GPU-math renderer's `typing-data.json` and
`atlas.rgba.gz`. Alpha is signed distance with the metadata's texel range, not
opacity. RGB median is not used as a Euclidean transport field. The pinned input
snapshot/provenance and font notices live beside the movie evidence; the other
chat's worktree is read-only. Native math atlas source at capture:
9bf84283b24028c11f7628970c843f28ef4c919e.

The adapter extracts closed zero contours from the scalar field, retaining an
outer boundary and its holes. Equal topology is required. Geometry-only matching
pairs holes and chooses cyclic boundary correspondence. Quintic progress moves
all boundaries, with periodic curve smoothing that vanishes continuously at the
endpoints. Per-contour area calibration follows the eased endpoint areas; this
makes polygon filled area monotone in these tests. It is not physical mass or
pixel-coverage conservation. Unlike the old union/blend, the model does not fill
a hole and then recreate it. No semantic glyph labels enter `Transport`.

The study renders ring→D, O→D, 8→B and 0→D as four sequential six-second clips,
24 seconds total at 60 fps (the owner's twice-speed rate). Sixfold supersampling
reduces raster contour stair steps. The final font's own corners remain at the
endpoint; smoothing applies to the evolving curves rather than blurring coverage.

    python -m pip install -r examples/field-transport/requirements.txt
    python examples/field-transport/render_study.py /path/to/atlas /path/to/fresh-output
    python examples/field-transport/verify_native_endpoints.py /path/to/atlas /path/to/endpoint-check.json
    python examples/field-transport/verify_subframes.py /path/to/atlas /path/to/subframe-check.json
    python -m unittest discover -s examples/field-transport -p 'test_*.py'

Five tests cover alpha-channel interpretation/units, hole preservation, geometric
area, endpoint motion ramps, crossing detection and rejecting topology changes.
The study checks all 1,248 motion frames for components, holes and boundary/self
crossings, and all 1,440 decoded frames for component/hole counts and held endpoint
silhouettes. Another 1,244 half-frame samples check holes and crossings, with
boundary second differences recorded. 8→B must retain two holes, all other cases one. Receipts retain exact
atlas hashes and movie hashes. Direct bilinear field sampling independently checks
endpoint silhouettes; contour extraction/rasterization is approximate, not exact
analytic-font reconstruction.

This is CPU contour transport using the real renderer's field data, not a new
GPU solver or native compiler integration. Supported inputs are one exterior with
disjoint holes and unchanged topology. Split/merge routing, arbitrary topology,
many-object collision planning and a general affine-first solution are not solved
here. Finite frame/intersection tests are not a continuous-time proof, and scalar
atlas quantization/range remain limitations. Earlier movies and failures remain
preserved; no deployment, production, paid-plan or other-chat source changes.

Endpoint tolerances are explicit: the encoded YUV420 silhouette must exceed
0.995 IoU against the contour raster. Direct native-scalar sampling versus the
contour raster exceeds 0.99 (observed 0.993095–0.994924). These are not pixel-exact
native outlines. The first sixfold exports rejected 8→B under a 0.999 encoded
threshold (0.998069 observed); those movies/logs remain in final/ and final-v2/.
RGB export now rounds instead of truncating. The delivered verified/ run uses
the documented codec tolerance, without weakening hole/component/crossing checks.
The earlier threefold study also remains preserved. Subframe checks additionally
bound the separation between contour segments from nearest-vertex distances and
half-edge lengths; every bound must stay positive.

## Color blends

`render_colors.py VERIFIED_FOLDER FRESH_OUTPUT_FOLDER` reuses the accepted shape
frames and blends distinct endpoint colors in linear-light RGB using the same
quintic clock. Coverage compositing also takes place in linear light. Cyan→coral,
pink→gold, blue→green and purple→turquoise show intermediate colors, with zero
endpoint color velocity/acceleration. The four clips retain six seconds each at
60 fps. This is color interpolation, not spatial pigment/material mixing.

The encoder decodes every frame, compares decoded luma with the known half-coverage blend luminance (avoiding
chroma-subsampling bias in RGB-vector projection), and checks components, holes and
silhouette IoU >0.99. Solid-interior median color must stay within four sRGB code
values of the expected blend. Receipts hash the unchanged input shape arrays.
The earlier monochrome movie remains preserved.

## Larger colored scenes and bounded division/fusion studies

`prepare_scenes.mjs RUNTIME_MODULE ATLAS_JSON OUTPUT_JSON` captures real native
math/text layout packets. The exact layout module snapshot and atlas hashes are
part of the evidence; another chat's working files are read only and are not
misrepresented as a committed runtime release. `scene_transport.py` converts the
packets to anonymous placed scalar-field contours, separates exteriors/holes and
matches bodies by geometry, location and hole count. Glyph keys/text do not enter
assignment. Inferred rigid similarities bypass morphology; incompatible body
counts/hole distributions fail closed. Unrelated-body overlap and topology changes
are checked in the rasterized scene, with self/hole crossings checked for morphs.

The selected scenes are a curved baseline for “These shapes move.” (all sixteen
components translate rigidly), O²+2O+1 → D²+2D+1, (8+O)/(0+O) → (B+D)/(O+D),
and x + analytic ring → x + D. The formulas demonstrate geometric changes, not
algebraic identities. The initially tried sentence-content changes and more general
variable morphs failed crossing/topology checks and remain rejected. Factorization
ab+ac → a(b+c) and x+x+x → 3x require a general branching planner and remain rejected.

`division_field.py` adds a deliberately bounded analytic two-disc fixture. It
combines the discs' signed fields with a rounded maximum, continuously changes
separation/radius and calibrates antialiased area to the eased endpoint areas.
The reverse trajectory supplies fusion. Both are checked for direction-monotone
component counts and no holes. This is not a general split/merge solver, inferred
arbitrary-object correspondence or physical material/color transport.

    python examples/field-transport/render_scene_study.py ATLAS_FOLDER LAYOUT_JSON OUTPUT_FOLDER
    python examples/field-transport/verify_scene_movies.py OUTPUT_FOLDER

Each case lasts six seconds at60fps. Source geometry/topology receipts and cached
frames support replay. Eight tests cover the prior contour slice plus rigid
translation, rejecting body-count mismatch and bounded division topology/area.
Decoded verification uses exact component/hole counts and at most one boundary
pixel displacement. IoU is also reported, but a fixed relative-area cutoff is
unsuitable for comparing tiny text strokes with the earlier giant glyphs. The
initial0.99/0.97-gate failures remain recorded; the one-pixel check applies uniformly
to all cases. Preserve the initial layout/probe/serialization/codec trials.

## Actual math benchmark and fixed-shape routing

The larger-math request is now tracked with five distinct endpoint operations:
reorder x²+y²+z² → z²+x²+y²; distribute a(b+c+d) → ab+ac+ad;
collect x+x+x+y+y → 3x+2y; factor x²+2x+1 → (x+1)²; and cancel
(x²−1)/(x−1) → x+1. `prepare_math_scenes.mjs` takes the same runtime/atlas/output
arguments as the previous generator. It does not send symbol names to matching.
`verify_math_cases.py ATLAS LAYOUTS REPORT` retains unsuccessful operations in
its report and exits unsuccessfully if any remain unsolved. Reordering passes;
the other four still need validated nonrigid/branching correspondence. They are
not replaced with more O→D demonstrations.

`rigid_routes.py` is a separate fixed-shape candidate. Exact geometry matches
outrank proximity in its assignment, fixing the prior preference for a nearby
wrong shape over a farther identical one. Anonymous silhouette correlations
construct pairwise collision obstacles. A time/vertical-offset lattice finds
passing corridors; bounded quadratic smoothing penalizes travel and acceleration
inside those corridors. C2 cubic paths use the existing quintic clock, preserving
zero endpoint velocity and acceleration. All parts retain their geometry, area,
and holes; no shrinking, rotation, fading, or contour deformation is introduced
to evade obstacles. This is prioritized bounded routing, not a global optimum or
complete planar planner. Large detours can remain. Dense sampled raster checks
remain mandatory; the planning grid alone is not an acceptance check.

    python examples/field-transport/render_scene_study.py ATLAS LAYOUTS FRESH_OUTPUT --cases reorder --routed

The six-second colored polynomial movie passes all312 source frames and360
decoded frames; another623-state check includes half-frame positions. The decoded
silhouette stays within the existing one-boundary-pixel tolerance. Minimum IoU
is0.979114. Ten focused tests pass, including unchanged-shape matching across a
large exchange and collision-free routing of two holed bodies. Quadratic path
smoothing reduced peak sampled transverse second difference from1.7053 to0.3975
pixels/frame²; this is a numerical comparison, not perceptual acceptance.

Earlier contour/color behavior stays on its original path: exact-first matching
is opt-in for the routing candidate. The previous four scene layouts reproduce
identical contour arrays at21 sample times each. Original movies, initial failed
single-arc routing attempts, raster failures and the first unsmoothed route movie
remain in Cuvami staging/artifacts/embedding-transport/field-real-math. No compiler,
GPU, other-chat worktree, staging deployment or registry changes.

## Generated routing regressions

The owner requires improvements to the shared algorithm, without formula-specific
exceptions. `RoutedScene` accepts only anonymous endpoint contours. It has no
formula identifier, symbol name, seed, target-list identity, or authored trajectory.
`stress_transport.py` independently generates permutations of two to seven
bodies, holes, concave outlines, rotated layouts, common scale/translation changes
and reversed endpoints. A focused regression also scrambles target-list order.
These are fixed-shape translation problems; rotating an entire input layout is
not a test of object rotation between endpoints. This distinction matters.

The original vertical-detour search failed two of sixteen generated layouts.
Both-axis search fixed those, but the additional seeds exposed crossings for
which neither one-axis corridor connected the endpoints. The shared algorithm
now searches geometry-derived priority orders and, when needed, a full planar
offset lattice. Feasible one-axis candidates are compared by detour/motion cost.
The full planar fallback smooths both coordinates inside conservative rectangular
corridors. All candidates undergo a denser 1,001-sample collision-obstacle and
viewport check after smoothing; independent raster/topology checks still apply.
Endpoint overlap is rejected before planning. No collision/topology tolerance was
relaxed, no symbol is shrunk, and failed candidates are not rendered as successes.

    python examples/field-transport/stress_transport.py BASE_REPORT
    python examples/field-transport/stress_transport.py ADDITIONAL_REPORT --start-seed 100 --seeds 12 --varied

The corpus seeds and generator hash are recorded with the denominator and every
failure. Preserve the baseline, intermediate both-axis/priority failures, and
final planar reports in Cuvami staging/artifacts/embedding-transport/generalization.
The existing polynomial movie's plan remains exactly unchanged: identical offset
knots and identical contour arrays at31 checked times.

This remains a bounded prioritized routing algorithm with sampled verification,
not a complete solver or proof of continuous collision freedom. Passing this
corpus does not establish arbitrary affine matching, morphology, hole creation,
or split/merge transport. The four unsolved algebra operations remain visible in
the separate math benchmark and must not be counted as covered by routing tests.

Final generated result:40/40 cases,3,240 independently raster-checked states;
14 focused tests pass. This denominator covers translation/permutation families
only. It does not include the four currently unsolved algebra transformations.

## Routing demonstration video

The requested30-second60fps video joins the verified native-field polynomial
rearrangement with four nonrepeated generated routing cases: five-body vertical
layout, four-body full-planar crossing, seven-body full-planar crossing, and
six-body oblique layout. One evolving scene appears at a time. Existing six-second
clip timing and linear-light color blends are retained. This demonstrates routing,
not the unfinished algebraic split/merge transformations.

`render_scene_study.py` also accepts layout entries with `geometry:[start,end]`,
where each side contains bodies of closed contour point arrays. This is a data
adapter; the solver receives no scene identifiers. All1,248 new source frames and
1,440 new decoded frames passed the unchanged topology/overlap/silhouette gates.
The combined1,800 decoded frames match the five verified source clips byte for
byte in decoded-frame hashes. Existing movies and all migration evidence remain.

Movie and reproducible join/verification script:
Cuvami staging/artifacts/embedding-transport/generalization-video/
cuvami-routing-demonstration.mp4 and join_and_verify.py.
SHA256:5ba6ddcf6583b6ef7d7a9436a2aa888d0d7a9d125e12c20a4e09faf9dcdfbf6e.

## Combined graph, geometry and GPU math scenes (2026-10-15)

`prepare_combined.mjs SNAPSHOT OUTPUT_LAYOUTS` uses the pinned independent GPU
math runtime. `build_combined_inputs.py OUTPUT_DIRECTORY SNAPSHOT` constructs
six pairs of endpoint scenes (7–10 glyphs each), including quadratic/cubic and
cubic/quintic graph changes with simultaneous label changes. Formula strings
remain provider metadata; `CombinedScene` receives only anonymous boundaries.
Reference axes/grid are explicit background context, not inferred foreground.

`render_combined.py INPUTS OUTPUT_DIRECTORY` produces three-second,60fps clips:
156 motion frames and twelve extra holds at either end. This is twice the prior
six-second pace. Multiple transform families operate concurrently within each
scene. Native affine matches take precedence; thin x-monotone ribbons get
profile correspondence; open strokes use endpoint-inferred medial tangent angles
and widths, with scalar endpoint-detail residuals and eased area calibration.
The latter is a bounded candidate for mostly unbranched strokes, not an arbitrary
shape solver. Rigid bodies whose translation exposes coarse raster artifacts use
higher supersampling and a fixed0.7-pixel antialiasing kernel throughout their
trajectory. The kernel conserves coverage mass and stays fixed in time. Sampled topology/overlap gates
remain mandatory; supersampling does not exempt a frame from those checks.

Foreground frames are checked for monotone object count, preserved holes, no
unrelated overlap and endpoint agreement within one boundary pixel. Lossless RGB
clips are decoded and compared exactly to all rendered frames. A separate phone
viewing transcode must retain the research originals and their checks. Continuous
collision proofs, arbitrary topology changes, foreground/background inference and
the previously unresolved algebraic operations remain outside acceptance.

## Morphology benchmark and affine-hole correction (2026-10-15)

`benchmark_morphology.py FRESH_OUTPUT` audits twelve generated cases: eight
same-map affine shapes with one/two holes, a non-affine ribbon, replica split and
merge, and unsupported hole creation. Supply `--combined INPUTS_JSON` to include
the six existing native combined scenes. Supply both `--atlas ATLAS_DIRECTORY`
and `--math-layouts LAYOUTS_JSON` to retain the five actual algebra operations.
`--samples 157` includes endpoints and midpoint; `--solver-dir DIRECTORY` runs
the exact same corpus against a separate solver checkout. `--cases ID ...`
selects cases explicitly and rejects unknown IDs.

Every report retains all failures, input/solver hashes, accepted state counts,
frame hashes, topology/count/foreground-overlap checks and one-boundary-pixel
endpoint checks. Preparation and image+validation wall times are separate. The
command completing successfully means the **audit completed**, not that all
cases passed. Consult `passed`, `total` and the per-case errors in `report.json`.
The initial concurrent screening times are diagnostic only; serial repeated
measurements are separate evidence. This is CPU research, not GPU or phone timing,
and finite raster samples do not establish continuous geometric validity.

The affine candidate previously selected its lowest-cost exterior map before
checking holes. Symmetric exteriors can admit multiple maps; the selected one
can disagree with holes even when a valid alternative exists. Hole enumeration
also carries no correspondence. Affine inference now searches exterior candidates
in the original preference order and accepts the first with a geometry-inferred
bijection of holes under that **same map**. Hole winding/phase and enumeration
may differ, and distinct holes may have different sample counts. Each matched
boundary must still have equal sampling and maximum error <=1e-6. No non-affine
input is promoted by a looser fitting threshold.

The initial identical 23-case screening recognizes all eight exact affine cases
(previously zero), replacing contour/registered fallbacks. Overall sampled raster
acceptance remains18/23, including the expected unsupported hole event. The four
algebra failures remain: distribution has no same-hole primary assignment,
collection develops invalid body topology, factorization has unrelated foreground
overlap, and cancellation needs unsupported branching. Existing accepted cases
retain identical screening frame hashes. This correction improves transform
selection, not algebraic branching coverage or GPU integration.

`render_morphology_review.py INPUTS_JSON NEW_MOVIE --label TEXT --cases ID ...`
replays selected cases at60fps, three seconds each. `--solver-dir` allows a
baseline clip; both clips use the same fixed crop and scale. Every lossless RGB
frame is decoded and checked exactly. The review joins four baseline/updated
comparisons vertically in a720x1280 H.264 phone-format movie. This is a focused
shape-transform review, separate from the earlier multi-glyph combined film.
Evidence and reproduction helpers live in Cuvami staging artifacts under
`morphology-review-20261015`; the public player is unchanged.

Final denser audit retains18/23 at157 samples per case:2,826 states across fully
passing cases, plus56 valid states before the two runtime-rejected algebra cases.
A held-out seeded set of24 affine scenes plus reversed endpoints passes48/48:
1,584 additional states check self/inter-contour crossings and raster topology.
All29 focused Python tests pass. Six existing native combined scenes and all
other non-affine screening cases retain their exact previous frame hashes.
The720-frame comparison transcode preserves both panels' topology, stays within
one boundary pixel, and has minimum silhouette IoU0.9987615. Lossless source clips
are decoded exactly. No hosted or physical-phone result is claimed.

## Experimental branch morphs and changing-cohort routes (2026-10-15)

`ValidatedCombinedScene` in `validated_transport.py` is an opt-in offline candidate.
The existing `CombinedScene` remains the default. Invoke the audit with
`--planner validated`; `--inputs CORPUS_JSON` replays a complete anonymous geometry
corpus instead of regenerating it. The default generated corpus now also includes
a nonrigid two-body exchange with a persistent hole (13 generated cases). Case
names and parent-reduction metadata never enter body matching or planning.

The tree candidate extends the open-stroke study with significant side branches
inferred from the endpoint skeletons. Branches attach to the inferred main path;
unmatched branches grow from or contract into their attachment. Local tangent
frames carry their shape during deformation. A bounded choice of fixed frame
weights is sampled and validated; these are algorithm candidates, not authored
correspondences. Existing contour plans are kept when their screening checks pass.
A failed hole-free contour may try the tree candidate; unsupported inputs remain
explicit failures.

Merely changing the boundary phase or branch frame left brief holes in native
reductions. The new tree field therefore fills enclosed scalar valleys by grayscale
morphological reconstruction **before** coverage-area calibration. This changes
the modeled geometry at every field level; it is not a binary repair applied to
accepted frames. The result is a scalar shape field, not an exact Euclidean signed
distance field or material-conserving simulation. This candidate intentionally
supports hole-free trees only. It does not infer arbitrary hole creation/deletion.
The calibrated area tolerance remains0.01 square pixels before quantization.
Tree selection checks305 distinct states (257 uniform times plus inverse-quintic
planning phases), endpoints and the existing raster topology criteria. This is
still sampled validation, not a guarantee at every possible time.

`cohort_routes.py` adds a bounded prioritized routing candidate for changing
silhouettes. It samples actual cohort masks at51 uniform progress values, max-pools
at4 pixels, and builds silhouette-correlation obstacles. Dynamic programming tries
one-axis corridors and geometry-derived priorities; constrained smoothing and
cubic splines retain stationary endpoint motion under the quintic clock. A proposed
route must pass257 full-resolution scene states, including topology, unrelated
foreground separation, component-count direction and viewport checks. Route offsets
move whole cohorts; they do not alter matching, merge unrelated cohorts, or permit
fragmented bodies. Bilinear coverage translation is explicit and revalidated; it
is not a new native field renderer. General full-planar/nonrigid coordination and
continuous collision proofs remain open.

The expanded evidence corpus has28 cases: the original23, four isolated native
contour reductions from collection/factorization, and the new nonrigid exchange.
Keep reduction outcomes separate from acceptance of their parent algebra scenes.
An additional seeded routing set rotates/scales/translates the layouts and shuffles
target order. Tests also use independently checked changing-radius circles, branch
attachment growth, area, endpoint ramps, unsupported holes and rejected routes.
Preparation includes expensive selection/replay validation. No realtime, GPU,
physical-phone or performance-improvement claim is made for this candidate.

The review renderer accepts `--planner validated`. Its explicit `--diagnostic`
flag renders rejected baseline frames with validation disabled and records that
fact in the receipt; candidate rendering keeps validation enabled. The new phone
movie compares two isolated glyphs and the nonrigid exchange, with the same fixed
zoom on both sides. This is not a movie of solved algebra transformations.
Lossless clips and rejected exports remain beside all benchmark results under
Cuvami staging artifacts `morphology-branching-20261015`. Public players and the
physical NVIDIA STOP remain unchanged.

Final comparison at157 states per case: **19/28 → 23/28**, with no regressions.
The gains are `algebra-collect-outline-0`, `algebra-collect-outline-1`,
`algebra-factor-outline-4` and `nonrigid-hole-crossing`. All19 previously passing
cases retain identical dense frame hashes. The original23-case subset remains
18/23; none of the four failed parent algebra operations is counted as solved.
36 focused tests and four held-out routes (260 states) pass. Default-solver
regression is exact for all28 cases at17 states. The candidate passes3611 states
in fully passing cases; failed cases remain in the denominator.

The final phone-format movie is `morphology-branching-review-v3.mp4`:9seconds,
540frames, High-profile H.264/yuv420p. Candidate decoded topology is exact,
minimum silhouette IoU is0.998545 and boundaries stay within one pixel. Verification
compares actual luma with the exact pre-encode YUV420 conversion; RGB/chroma edge
projection is not used as a coverage proxy. The first RGB-mean export and second
4:4:4-reference export failed the unchanged0.995 codec IoU gate and remain in the
evidence. The accepted third export uses explicit BT.601 conversion andQP1;
lossless originals and rejected diagnostic frames remain preserved. No physical
phone compatibility or playback test is claimed.
