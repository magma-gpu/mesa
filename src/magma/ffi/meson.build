# Copyright © 2025 Google
# SPDX-License-Identifier: MIT

libmesa_magma = static_library(
  'mesa3d_magma_ffi',
  'lib.rs',
  gnu_symbol_visibility : 'hidden',
  rust_abi : 'c',
  link_with: [libmesa_magma, libmagma_gpu_rs],
  dependencies: [dep_magma_gpu_rs, dep_log]
)
