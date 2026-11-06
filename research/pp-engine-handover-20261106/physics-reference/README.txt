Research-only numerical reference; never import into the Product runtime.
Physics: PHYSICS.txt. Native glyph coupling: SDF_COUPLING.txt.
Install: python3 -m pip install -r research/physical-smoke/requirements.txt
Test: python3 -m unittest discover -s research/physical-smoke -p 'test_*.py'
Generate owner-requested case: python3 research/physical-smoke/make_visual_proof.py --fluid-only
Run the existing Vite development server; visit /research/physical-smoke/visual-proof.html?case=fluid-only
The viewer uses current pinned native VKF points/text/media capture. No custom plotting.
Generated binary frames are ignored; configuration, seeds, source and evidence are tracked.
Watch: https://staging.platonicplay.com/_expo/static/proof/navier-stokes-20261106/fluid-only.mp4
The published clip is 361 native frames at30fps, codec/range conversion only.
This case disables collector, buoyancy, SGS and stochastic probe displacement.
Its continuous low-frequency initial field is pressure-projected once, then evolves
under the nonlinear viscous Navier-Stokes equations without continuing forcing.
Other collector/LES cases and their tests are numerical references, not native integration.

Three-view recorded presentation reference (2026-11-06):
python3 research/physical-smoke/make_presentation.py
Visit /research/physical-smoke/presentation-reference.html on the local Vite server.
fluid-presentation.vkf was authored/exported with real PP text/list/copy-view controls.
The research player reuses native VKF text waves, points, compositor and encoder.
18 seconds, 433 frames at24fps. The physical clock continues across all3views.
16,384 probes: final12,689 captured at their actual absorption locations,3,695 gas.
Only live gas probes are drawn. Absorbed material enters the collector reservoir;
it is not shown as frozen smoke. This reference has no glyph reconstruction.
The collector is balanced by return air, moves after12s, and is enabled after6s.
Probe+continuum mass balance is checked everyframe. No artificial deletion or fade.
This is recorded CPU-f64 research, NOT an installed VKF GPU fluid solver or Product
fluid component. Binary generated frames are ignored. Native port remains pending.

Receiver bookkeeping reference: receiver_reference.py subclasses the existing
solver only to integrate spatial sink*c at the accepted SSPRK3 stages. It does
not change velocity/concentration evolution. Integral spatial uptake equals the
existing deposited-species ledger; gas remains gas until actual absorption.
Three tests cover analytical ramp uptake, moving collector parity and complete
receiver-history handover. No glyph-mask/stroke-formation/thermal claim follows.
The earlier 18s video is REJECTED by the owner: it was not the full presentation
and incorrectly visualized captured probes as frozen smoke. Its historical proof
records that rejection. The corrected generator draws only live gas.

Finite release reference: material_transfer_reference.py adds held solid-density
fields and one-shot source identities to the SAME accepted fluid. Explicit
release transfers all held source mass to gas at the current boundary time, with
no air-velocity change. This is a declared initial-condition jump, not a thermal
phase-change law or normal impulse. Source+gas+captured mass and handover history
are tested. Native glyph sampling, receiver masks and stroke formation remain
unqualified; these bookkeeping tests cannot establish their correctness.

Actual glyph-mask mapping/interception qualification (research only):
1. Open /research/physical-smoke/glyph-mask-reference.html on the local Vite
   server and capture native masks. Save the binary to this directory. The JSON
   receipt binds actual PP views19/23, native source/receiver specs and data hash.
2. python3 research/physical-smoke/qualify_glyph_grid.py
3. python3 research/physical-smoke/qualify_fine_receiver.py
Conservative native8bit-alpha→MAC cell averages preserve area, but a uniform
coarse-cell sink is RED: at24x16x8 it overpredicts frozen-position capture by
8–11times on these actual letters despite a small sink-only60HzCFL.
fine_receiver_reference.py integrates exposure along accepted linear probe
segments at pixel boundaries. Captures occur only inside native occupied pixels,
and optionally inside an affine moving front band. Crossing a thin stroke cannot
be missed by a midpoint sample. Periodic wrapping, source→gas→received mass and
view/time partition checks pass; unabsorbed gas always moves to its advected end.
Uniform velocity is an exact unforced NS test solution used ONLY to isolate this
reaction operator; it is not a replacement for the turbulent fluid presentation.
A bounded hazard, not a fixed flow rate, is gated by the wave front. Its effective
flux varies with occupied band area and is zero across spaces. No infinite rate
is introduced at an empty band. This does not guarantee first-row completion on
a deadline. Fine air-flow, nonlinear/shape-changing fronts, GPU integration and
captured-stock→native stroke formation remain unqualified.
