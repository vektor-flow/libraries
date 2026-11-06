# Native attached-material ownership

Source: libraries commit c288e285f334a09254c72966f2e95decd14474bd, MaterialStock.vkf, importing unchanged qualified Fluid.sample_component. SOURCE_CLOSURE.json binds committed source hashes to the unmodified compiler/emitter output. FineReceiver.capture remains unchanged.

`createNativeMaterialStockKernels(device)` authenticates artifacts and returns `reemit`, `owners`, and `captureOwner` compiled-field bind adapters. The shared device is caller-owned. The caller must clear/check every native error summary and accept all related result buffers in one transaction; these pure operators never mutate input air or stock.

For reemit/owners: params are flow24 ++ [count, ownerKey]; values are accepted7N ++ records20C ++ ownersC ++ persistedNewThresholdsC. Only inactive records matching the owner are released. Positions, mass, RGBA and identities are preserved; velocity samples the current accepted staggered air, exposure resets, the persisted fresh threshold replaces the old one, alive becomes1, accepted dt becomes0. Non-selected moving gas and other stock remain unchanged. Owners returns -1 for selected stock and preserves every other tag. Keys are exact integers0..16777215; -1 denotes unowned/gas.

For captureOwner: params are [count, receiverKey]; values are previousOwnersC ++ FineReceiver25C. A newly captured event transfers ownership; older attached stock remains attached to its existing owner. A claimed capture cannot remain live gas.

WASM and software-GPU gates cover varied mass/colour/IDs, periodic current-air sampling, exact non-selected preservation, readonly input, repeat release selecting zero, capture ownership, same-device replay and eight malformed-input cases. GPU velocity differs from the independent f64 reference by at most9.22e-9. Selected/released mass is exactly1.875 in the finite fixture. Runtime loading also rejects missing GPU and corrupt artifact bytes.

These checks qualify operators. They do not prove source-to-first-row formation, suction, session rollback, thermal phase change, two-way momentum exchange, optical mass conservation or the full Product presentation.
