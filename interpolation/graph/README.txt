NATIVE GRAPH HERMITE SOURCE CONTRACT — 2026-10-31

Status: source preparation only. graph.vkf has NOT been compiled, executed,
tested or rendered in this task. Existing polynomial/patch qualification does
not qualify this module. Root owns Interpolation.vkf integration and tests.
No compiler/runtime/render/experiment admission was requested or consumed.

Exact module record shapes (no extra count fields):
  Graph:(vertices:[num],width:int,starts:[int],ends:[int],lengths:[num],
         targets:[num],weights:[num],fixed:[int],joins:[int],jets:[num])
  Sample:(value:[num],first:[num],second:[num])
Sample has the existing interpolation Sample field shape. There are no module
imports or import aliases, avoiding the earlier caller/facade m alias collision.
Root should use a unique descriptive alias when wiring the public facade.

Native module entry points:
  prepare(vertices:[num],width:int,starts:[int],ends:[int],lengths:[num],
          targets:[num],weights:[num],fixed:[int],joins:[int])->Graph
  default(vertices:[num],width:int,starts:[int],ends:[int])->Graph
  with_joins(plan:Graph,joins:[int])->Graph
  evaluate(plan:Graph,edge:int,coordinate:num)->Sample

Canonical geometry and physical charts
--------------------------------------
vertices is flat point-major. width is the positive vector channel count.
starts[e], ends[e] reference canonical vertex IDs; sharing an ID means sharing
that hard position. Coincident coordinates with different IDs are not joined.
All positions remain hard, including isolated vertices. Empty edge sets are
accepted with empty incidence arrays; sampling them is rejected. Self-loop
edges are permitted, without any promise of nondegeneracy.

Edge e has physical coordinate x in [0,lengths[e]]. Its endpoint incidence IDs
are 2*e (start) and 2*e+1 (finish). targets and resolved jets are incidence-major,
index incidence*width+channel. Both store OUTWARD physical first derivatives:
at x=0, dF/dx=jets[2*e]; at x=h, dF/dx=-jets[2*e+1]. Neither is a Bezier handle.
weights has one positive scalar per incidence; fixed has one int 0/1 per
incidence. fixed=1 protects the entire original target vector as a hard jet.

joins is a flat list of selected incidence pairs [a,b,...]. Every pair must
have distinct incidence IDs attached to the SAME canonical vertex. Each pair
imposes J_a+J_b=0. The default is sharp C0: there are no join equalities unless
selected. A sharp policy allows a crease; it need not produce a nonzero angle.
No all-pair smoothing is inferred at a branch. Duplicate/reversed pairs are
allowed and add no new mathematical condition.

Projection and ownership
------------------------
The real-arithmetic target minimizes
  sum_i weights[i] * ||J_i-targets[i]||^2
subject to all selected signed equalities and all marked hard jet anchors.
CSR adjacency and BFS assign signs s_i in each connected join component.
For a bipartite component J_i=s_i*z. Without hard anchors,
  z = sum_i weights[i]*s_i*targets[i] / sum_i weights[i].
With hard anchors, z is the first signed anchor; every other signed hard scalar
must compare exactly equal. Conflicts are rejected, with no epsilon relaxation.
An odd cycle imposes z=0, and any nonzero hard scalar in it is rejected.
Unjoined incidence proposals remain unchanged. Nonzero soft proposals may be
discarded when an odd component forces zero. This does not ensure immersion.

The floating mean is confined to the component's signed proposal min/max range,
an identity for the exact positive weighted mean. No hard anchor is clipped or
averaged. Original hard values are copied directly to resolved jets.
Input arrays are elementwise copied into every returned Graph; resolved jets
are separately allocated. with_joins reconstructs from stored ORIGINAL targets,
weights and anchors, never from plan.jets. Removing joins therefore recovers
original proposals rather than preserving a previous projection's history.
Treat returned records as immutable; externally editing a Graph is unsupported.
evaluate guards its accessed layout, geometry, span and selected jets; it does
not re-solve or revalidate all unrelated constraint metadata on every query.

Direct Hermite evaluation
-------------------------
Let p,q be original endpoint vectors, a=J_start, b=J_finish (outward), h>0,
u=x/h. The represented real polynomial is
  F = p + h*a*u + A*u^2 + B*u^3,
  A = 3*(q-p) - h*(2*a-b),
  B = -2*(q-p) + h*(a-b).
This is direct Hermite basis evaluation in local-origin form, without conversion
to rounded Bezier controls. Near the finish the same expression is evaluated in
the reversed local chart v=(h-x)/h, swapping p/q and a/b. first and second are
derivatives with respect to physical x, with second divided by h twice.
At exact x=0 or x=h, value returns the original vertex components and first
returns the resolved physical derivative directly. The second derivative is
the edge's own cubic second derivative, even at endpoints.

Over real arithmetic this gives C0 at every shared vertex and C1 along the
selected physical crossing paths. Binary64 execution, endpoint behavior and
error require separate native qualification. There is no physical C2 claim,
immersion/injectivity/topology solve, smoothing of unselected pairs, surface
seam solve, curvature prescription, or curve/surface curvature role assignment.

First numeric and resource domain
---------------------------------
Every input position component and outward target jet satisfies abs(value)<1e100.
All inputs must be finite. weights are in [1e-100,1e100]; physical spans are in
[1e-50,1e50]. Samples require finite x in [0,h]. Explicit comparisons reject
NaN/infinity under the intended numeric semantics; native injection is untested.
Resolved means are constrained to signed input ranges; exact hard anchors are
retained. default uses h=1, straight secant outward jets, weights=1, fixed=0,
and no joins. It rejects a derived secant outside the same target-jet bound,
even when both original positions are individually in range.

The finite implementation caps width and each input array at 1,000,000 slots,
and edges at 500,000. Products are checked via division/layout bounds first.
One CSR offset array has incidences+1 slots. These bounds limit arithmetic
intermediates but do not guarantee memory availability, practical performance,
accuracy under cancellation, or an unlimited-allocation/resource capability.
Preparation uses O(incidences+join_pairs) adjacency/BFS work plus linear vector
copy/projection work O(vertices.length+incidences*width), and matching storage.
evaluate currently validates all vertex positions/edge IDs before O(width)
sampling; it is not claimed constant time in total graph size.

Preregistered next qualification scope — NOT execution authorization
------------------------------------------------------------------
Root must obtain NEW resource-coordinator admission before any actual compiler,
runtime, render or experiment call. Do not reuse an earlier consumed grant.
Retain source/compiler hashes, command/argv, native output, comparison rules,
admission receipt, all failures and previous artifacts. Keep research identities,
native numeric evidence, and rendered views distinguishable. Do not replace
native evaluation with Python or another runtime surrogate.

Before starting a native batch, root should freeze exact fixtures and oracles
covering: default straight edges; physical spans other than one; selected paths
with unselected branches; reversed incidence ordering; weighted signed means;
consistent hard anchors; scalar hard conflicts; even/odd cycles (soft, zero hard,
nonzero hard); duplicate joins; source-array copy isolation; history-free join
replacement/removal; exact endpoint positions/jets at disparate scales; output
widths; malformed layouts/IDs/joins/flags; zero/nonfinite/out-of-domain inputs;
input magnitude/resource boundaries. For example, joined scalar proposals 2,6
with weights 1,3 resolve to -4,+4 in real arithmetic, not the unsigned mean.
Use independent exact-rational Hermite identities for reference; binary64
interior comparisons need preregistered finite bounds, not continuity proofs.

Requested concave/convex curve and genuine sheet visuals: deferred specifications
-------------------------------------------------------------------------------
No visual is generated or claimed here. Root's separately admitted native
sampling/render work can use these explicitly different dimensional objects:

1. Convex scalar graph F(x)=(x,x^2), x in [0,1]: vertices [0,0,1,1], width=2,
   starts=[0], ends=[1], h=[1], outward targets=[1,0,-1,-2].
2. Concave scalar graph G(x)=(x,2*x-x^2), same endpoints/domain, targets
   [1,2,-1,0]. Both use weights=[1,1], fixed=[0,0], joins=[]. These are planar
   curves with scalar graph second derivative +2 and -2 respectively, not a
   claim about arbitrary vector-curve curvature or automatic shape preservation.
3. Genuine two-parameter sheets S_sigma(u,v)=(u,v,
   sigma*((u-1/2)^2+(v-1/2)^2)), sigma=+1 and -1, u,v in [0,1]. Use the
   existing tensor patch module, independently of graph.vkf. A degree-(2,2)
   tensor Bezier net is specified by a,b in {0,1,2}:
     C[a,b]=(a/2,b/2,sigma*(c[a]+c[b])), c=[1/4,-1/4,1/4].
   Flatten v-major with u fastest, width=3, u_count=v_count=3. This is a real
   two-dimensional sheet, not a thickened curve. du=(1,0,sigma*(2*u-1)),
   dv=(0,1,sigma*(2*v-1)); the cross product has third component 1 everywhere.
   Hessian of the scalar height is diag(2*sigma,2*sigma), mixed derivative zero.
   These analytic specifications are not native/runtime/render evidence.

Before executing the visual batch, freeze sample grids, native exports, rendering
commands and axis conventions in root's preregistration. Render only saved
native coordinates, label curve versus sheet and convex versus concave height,
and retain provenance. No Python-computed surrogate geometry or GPU/browser is
authorized by this source task. Source samples do not establish continuum error
bounds, general seam policy, or arbitrary-topology smoothability.
