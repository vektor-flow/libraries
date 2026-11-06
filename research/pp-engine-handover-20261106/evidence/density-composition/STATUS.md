2026-11-06 — Active native density raster transport implementation.

Owner root, branch codex/native-density-composition-20261106, renderer base
c3c91aecefc87501283332bcadc7fb8697611124. Parent owns native density law,
compiled accumulation/resolve artifacts and state event preparation. Child owns
continuous NS/material session. This worktree owns only resident renderer
composition and bounded tests/docs.

The new profile rasterizes each native rhoRGB/rho lineage to one reusable
RGBA16float MSAA4 layer, keeps a persistent MSAA4 MAX coverage union, gathers
channels into native f32 accumulation, then native resolve. It never adds an
interpolation or colour law in the host. Every dispatch summary is retained and
checked before displaying output. Shared device is caller-owned. Explicit
resource bound includes staging and errors; default/max 256 MiB.

GPU qualification passes: mixture, order/seek parity, clear, aspect, offset,
resource rejection, plus native numerical-error rejection preserving last accepted
image. The latter required a retained accepted GPU result buffer: invalid candidate
results never overwrite snapshots. Every native dispatch summary is checked. Not an intake or
readiness claim; the full Product movie remains pending.
