// Copyright 2026 The ChromiumOS Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

use std::boxed::Box;
use std::panic::catch_unwind;
use std::panic::AssertUnwindSafe;
use std::slice::from_raw_parts_mut;

use libc::EINVAL;
use libc::ESRCH;
use log::error;

use magma_gpu_magma::magma_enumerate_devices as enumerate_devices;
use magma_gpu_magma::MagmaPhysicalDevice;

const NO_ERROR: i32 = 0;
const MAGMA_MAX_PHYSICAL_DEVICES: u32 = 8;

macro_rules! return_on_error {
    ($result:expr) => {
        match $result {
            Ok(t) => t,
            Err(e) => {
                error!("An error occurred: {}", e);
                return -EINVAL;
            }
        }
    };
}

#[allow(non_camel_case_types)]
type magma_physical_device = MagmaPhysicalDevice;

// The following structs (in define.rs) must be ABI-compatible with FFI header
// (magma.h).

#[no_mangle]
pub unsafe extern "C" fn magma_enumerate_physical_devices(
    physical_devices: &mut *mut magma_physical_device,
    num_devices: &mut u32,
) -> i32 {
    catch_unwind(AssertUnwindSafe(|| {
        let result = enumerate_devices();
        let phys_devs = return_on_error!(result);
        *num_devices = phys_devs.len().try_into().unwrap();
        if *num_devices > MAGMA_MAX_PHYSICAL_DEVICES {
            return -EINVAL;
        }

        let physical_devices =
            from_raw_parts_mut(physical_devices, MAGMA_MAX_PHYSICAL_DEVICES as usize);
        for (i, phys_dev) in phys_devs.into_iter().enumerate() {
            physical_devices[i] = Box::into_raw(Box::new(phys_dev)) as _;
        }

        NO_ERROR
    }))
    .unwrap_or(-ESRCH)
}
