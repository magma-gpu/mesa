// Copyright 2026 The Magma GPU Project
// SPDX-License-Identifier: MIT
//
// Generated via:
//   https://gitlab.freedesktop.org/mesa/mesa/-/tree/main/src/magma/gorgonzola
//
// Submit patches, do not hand-edit.

#![allow(non_camel_case_types)]
#![allow(non_snake_case)]
#![allow(unused_imports)]
#![allow(unused_variables)]

use std::boxed::Box;
use std::convert::TryInto;
use std::ffi::CStr;
use std::os::raw::{c_char, c_void};
use std::panic::{catch_unwind, AssertUnwindSafe};
use std::ptr::null_mut;
use std::slice::{from_raw_parts, from_raw_parts_mut};
use std::sync::Mutex;

use libc::{EINVAL, ESRCH};
use log::error;

use magma_gpu_magma::magma_enumerate_devices as enumerate_devices;
use magma_gpu_magma::MagmaBuffer;
use magma_gpu_magma::MagmaContext;
use magma_gpu_magma::MagmaDevice;
use magma_gpu_magma::MagmaPhysicalDevice;
use magma_gpu_magma::MagmaCreateBufferInfo;
use magma_gpu_magma::MagmaHeap;
use magma_gpu_magma::MagmaHeapBudget;
use magma_gpu_magma::MagmaMemoryProperties;
use magma_gpu_magma::MagmaMemoryType;

const NO_ERROR: i32 = 0;

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
pub type magma_buffer = MagmaBuffer;

#[allow(non_camel_case_types)]
pub type magma_context = MagmaContext;

#[allow(non_camel_case_types)]
pub type magma_create_buffer_info = MagmaCreateBufferInfo;

#[allow(non_camel_case_types)]
pub type magma_device = MagmaDevice;

#[allow(non_camel_case_types)]
pub type magma_heap = MagmaHeap;

#[allow(non_camel_case_types)]
pub type magma_heap_budget = MagmaHeapBudget;

#[allow(non_camel_case_types)]
pub type magma_memory_properties = MagmaMemoryProperties;

#[allow(non_camel_case_types)]
pub type magma_memory_type = MagmaMemoryType;

#[allow(non_camel_case_types)]
pub type magma_physical_device = MagmaPhysicalDevice;

#[no_mangle]
pub unsafe extern "C" fn magma_create_device(
    physical_device: &mut magma_physical_device,
    device: &mut *mut magma_device
) -> i32 {
    catch_unwind(AssertUnwindSafe(|| {
        let result = physical_device.create_device();
        let res = return_on_error!(result);
        *device = Box::into_raw(Box::new(res)) as _;
        NO_ERROR
    }))
    .unwrap_or(-ESRCH)
}

#[no_mangle]
pub unsafe extern "C" fn magma_get_memory_properties(
    device: &mut magma_device,
    mem_props: &mut magma_memory_properties
) -> i32 {
    catch_unwind(AssertUnwindSafe(|| {
        let result = device.get_memory_properties();
        *mem_props = return_on_error!(result);
        NO_ERROR
    }))
    .unwrap_or(-ESRCH)
}

#[no_mangle]
pub unsafe extern "C" fn magma_get_memory_budget(
    device: &mut magma_device,
    heap_idx: u32,
    budget: &mut magma_heap_budget
) -> i32 {
    catch_unwind(AssertUnwindSafe(|| {
        let result = device.get_memory_budget(heap_idx);
        *budget = return_on_error!(result);
        NO_ERROR
    }))
    .unwrap_or(-ESRCH)
}

#[no_mangle]
pub unsafe extern "C" fn magma_create_buffer(
    device: &mut magma_device,
    info: &magma_create_buffer_info,
    buffer_out: &mut *mut magma_buffer
) -> i32 {
    catch_unwind(AssertUnwindSafe(|| {
        let result = device.create_buffer(info);
        let res = return_on_error!(result);
        *buffer_out = Box::into_raw(Box::new(res)) as _;
        NO_ERROR
    }))
    .unwrap_or(-ESRCH)
}

#[no_mangle]
pub unsafe extern "C" fn magma_create_context(
    device: &mut magma_device,
    context: &mut *mut magma_context
) -> i32 {
    catch_unwind(AssertUnwindSafe(|| {
        let result = device.create_context();
        let res = return_on_error!(result);
        *context = Box::into_raw(Box::new(res)) as _;
        NO_ERROR
    }))
    .unwrap_or(-ESRCH)
}

#[no_mangle]
pub unsafe extern "C" fn magma_device_close(
    device: &mut *mut magma_device
) -> i32 {
    catch_unwind(AssertUnwindSafe(|| {
        if !(*device).is_null() {
            let _ = unsafe { Box::from_raw(*device) };
            *device = null_mut();
        }
        NO_ERROR
    }))
    .unwrap_or(-ESRCH)
}

#[no_mangle]
pub unsafe extern "C" fn magma_physical_device_close(
    physical_device: &mut *mut magma_physical_device
) -> i32 {
    catch_unwind(AssertUnwindSafe(|| {
        if !(*physical_device).is_null() {
            let _ = unsafe { Box::from_raw(*physical_device) };
            *physical_device = null_mut();
        }
        NO_ERROR
    }))
    .unwrap_or(-ESRCH)
}
