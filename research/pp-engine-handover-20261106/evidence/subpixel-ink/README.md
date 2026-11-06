# Native world-space subpixel ink

`setWorldInkCarriers(records, projection)` accepts Float32 XYZ, device-pixel footprint and straight RGBA (eight values per carrier). The existing native vertex projection and analytic pixel-overlap shader render it. No host trajectory, minimum one-pixel clamp or alternate renderer is introduced. Zero-alpha captured carriers remain invisible; the physical caller owns their capture and motion.

GPU.json records 30 checks: world/screen pixel parity including device densities 1, 2 and 3; six subpixel sizes at four offsets; viewport-edge coverage; matching source/render density; inactive visibility; invalid inputs; and mode-switch replay. These ran in a software GPU browser, not on a physical phone.

Coverage uses source-over composition. Overlapping subpixel footprints do not conserve optical area: the deliberate four-footprint test measures 0.6863 alpha against geometric area 1. Physical material mass remains a separate native ledger. This change does not qualify fluid physics, suction, text formation or the full Product presentation.
