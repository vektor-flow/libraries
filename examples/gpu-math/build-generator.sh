#!/usr/bin/env bash
set -euo pipefail
export PATH=/home/viktor/.local/bin:$PATH
# Requires existing CMake/C++, FreeType, libpng and tinyxml2 development packages.
# CPU source/build only. No root, driver changes, GPU sessions or vcpkg.
math_tool_dir="${1:?Provide a fresh external build directory}"
git clone https://github.com/Chlumsky/msdfgen.git "$math_tool_dir"
git -C "$math_tool_dir" checkout --detach 84f183a6c8137c42abc5728b29ed274bab3edeb0
cmake -S "$math_tool_dir" -B "$math_tool_dir/build" -DCMAKE_BUILD_TYPE=Release \
  -DMSDFGEN_USE_VCPKG=OFF -DMSDFGEN_USE_SKIA=OFF -DMSDFGEN_BUILD_STANDALONE=ON
cmake --build "$math_tool_dir/build" -j 4
