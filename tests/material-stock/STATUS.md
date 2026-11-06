2026-11-06 — Native MaterialStock.vkf: WASM gate passes.

Three operators: reemit, owners, capture_owner. Readonly accepted air plus
AoS20 material and explicit ownership/threshold arrays. Re-emission selects
inactive matching-owner stock only, preserving positions/mass/RGBA/identity,
sampling current accepted MAC velocity and resetting hazard/liveness/timestep.
Owners clear only selected stock. Newly captured events claim receiver ownership.

Independent 8-record finite oracle: three selected; mass exact; all other gas
and stock unchanged; retry selects zero; five malformed controls/material cases
reject; sample velocity error0 against f64 trilinear reference. GPU qualification
and integration pending. Fluid/FineReceiver sources unchanged. No suction,
formation, thermal or two-way momentum claim.
