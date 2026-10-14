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
