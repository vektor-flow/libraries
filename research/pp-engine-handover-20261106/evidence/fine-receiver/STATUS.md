Root FineReceiver handoff — 2026-11-06

Native source23e78ac4b68ddb385cd337234a819f1171b91c92 is pushed to
vektor-flow/libraries branch codex/native-fine-receiver-20261106.
Source SHA37858e435f6aa1ea7709667c214c15b8bb24909b865bf975a5d5d825e163fd1a.

Final runtime loader and four immutable artifacts are ready for the physical
session owner to integrate. LOADER.json verifies the exact committed source pin,
artifact hashes, nested immutable provenance and explicit unavailable-GPU error.
WASM.json/GPU.json/DIAGNOSTIC.json describe the finite tested capture profile and
per-channel numerical limits. No public full-fluid factory or Product update.

Input AoS20 is accepted unwrapped segments. Output AoS25 updates end3..5,
exposure14 and alive16, preserves mass/RGBA/IDs, and adds capture event/time/pixel
metadata. Captured momentum requires the fluid finaliser's old/new-air temporal
sample at the actual capture point. Native emitter/IR are unmodified.

All GPU qualifications now use flock -w60 /tmp/vkf-qualification-gpu.lock to
avoid idle message-based lease waits. No root GPU browser remains active.

Next root task: independently qualify existing native subpixel point-cloud optics
in vf-screen-point-cloud-renderer.mjs (reserved with parent). Parent owns canonical
state event/count preparation; child owns Fluid/session/ink injection/coupling.
Full PP29-view capture remains blocked on those actual runtime integrations.
