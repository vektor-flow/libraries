This candidate runs installed tools; it does not vendor their engines or fonts.
Source and generated-field receipts preserve the identities of used tools,
packages, font maps, TeX metrics and Type1 outlines. Generated artwork and field
textures are separate ignored research artifacts.

- msdfgen: https://github.com/Chlumsky/msdfgen at
  `84f183a6c8137c42abc5728b29ed274bab3edeb0`, MIT. Shader reconstruction follows
  its documented median/derivative method. See accompanying MSDFGEN-LICENSE.txt.
- LaTeX2e/amsmath/amsfonts and Computer Modern fonts: supplied by installed TeX Live.
  Package/font licenses remain with the installation; no font binaries are included
  in this source candidate. Pin and review those notices if distributing a bundled
  engine/fonts later.
- dvisvgm 3.6: https://dvisvgm.de, GPL-3.0-or-later; external conversion executable.
- fontTools 4.66.1: https://github.com/fonttools/fonttools, MIT.
- Pillow 12.3.0: https://github.com/python-pillow/Pillow, HPND.

The earlier KaTeX font experiment and its source are preserved separately under
Cuvami staging/artifacts/gpu-math/20261014/katex-exploration-source. It is not a
runtime dependency or the reference for the current direct-LaTeX candidate.
