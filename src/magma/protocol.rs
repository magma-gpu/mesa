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
#![allow(dead_code)]

use zerocopy::{FromBytes, IntoBytes, Immutable};

pub const MAGMA_OPCODE_CREATE_DEVICE: u32 = 2;
pub const MAGMA_OPCODE_GET_MEMORY_PROPERTIES: u32 = 3;
pub const MAGMA_OPCODE_GET_MEMORY_BUDGET: u32 = 4;
pub const MAGMA_OPCODE_CREATE_BUFFER: u32 = 5;
pub const MAGMA_OPCODE_CREATE_CONTEXT: u32 = 6;
pub const MAGMA_OPCODE_DEVICE_CLOSE: u32 = 7;
pub const MAGMA_OPCODE_PHYSICAL_DEVICE_CLOSE: u32 = 8;

pub const MAGMA_OPCODE_RESP_CREATE_DEVICE: u32 = 0x8000_0002;
pub const MAGMA_OPCODE_RESP_GET_MEMORY_PROPERTIES: u32 = 0x8000_0003;
pub const MAGMA_OPCODE_RESP_GET_MEMORY_BUDGET: u32 = 0x8000_0004;
pub const MAGMA_OPCODE_RESP_CREATE_BUFFER: u32 = 0x8000_0005;
pub const MAGMA_OPCODE_RESP_CREATE_CONTEXT: u32 = 0x8000_0006;

pub const MAGMA_MAX_PHYSICAL_DEVICES: u32 = 8;
pub const MAGMA_MAX_MEMORY_HEAPS: usize = 32;
pub const MAGMA_MAX_MEMORY_TYPES: usize = 16;

#[derive(Debug, Default, Clone, Copy, PartialEq, Eq)]
#[repr(u16)]
pub enum MagmaVendorId {
    #[default]
    AMD = 0x1002,
    ARM = 0x13B5,
    Intel = 0x8086,
    Qualcomm = 0x5413,
}

#[derive(Debug, Default, Clone, Copy, PartialEq, Eq)]
#[repr(i32)]
pub enum MagmaStatus {
    #[default]
    Success = 0,
    InternalError = -1,
    InvalidArgs = -2,
    AccessDenied = -3,
    MemoryError = -4,
    ContextKilled = -5,
    TimedOut = -6,
    Unimplemented = -7,
}

pub const MAGMA_MEMORY_PROPERTY_DEVICE_LOCAL_BIT: u32 = 0x00000001;
pub const MAGMA_MEMORY_PROPERTY_HOST_VISIBLE_BIT: u32 = 0x00000002;
pub const MAGMA_MEMORY_PROPERTY_HOST_COHERENT_BIT: u32 = 0x00000004;
pub const MAGMA_MEMORY_PROPERTY_HOST_CACHED_BIT: u32 = 0x00000008;
pub const MAGMA_MEMORY_PROPERTY_LAZILY_ALLOCATED_BIT: u32 = 0x00000010;
pub const MAGMA_MEMORY_PROPERTY_PROTECTED_BIT: u32 = 0x00000020;

#[derive(Debug, Default, Clone, Copy, FromBytes, IntoBytes, Immutable)]
#[repr(C)]
pub struct MagmaMemoryType {
    pub property_flags: u32,
    pub heap_idx: u32,
}

#[derive(Debug, Default, Clone, Copy, FromBytes, IntoBytes, Immutable)]
#[repr(C)]
pub struct MagmaHeap {
    pub heap_size: u64,
    pub heap_flags: u64,
}

#[derive(Debug, Default, Clone, Copy, FromBytes, IntoBytes, Immutable)]
#[repr(C)]
pub struct MagmaMemoryProperties {
    pub memory_type_count: u32,
    pub memory_heap_count: u32,
    pub memory_types: [MagmaMemoryType; MAGMA_MAX_MEMORY_TYPES],
    pub memory_heaps: [MagmaHeap; MAGMA_MAX_MEMORY_HEAPS],
}

#[derive(Debug, Default, Clone, Copy, FromBytes, IntoBytes, Immutable)]
#[repr(C)]
pub struct MagmaHeapBudget {
    pub budget: u64,
    pub usage: u64,
}

#[derive(Debug, Default, Clone, Copy, PartialEq, Eq)]
#[repr(u32)]
pub enum MagmaStructureType {
    #[default]
    CreateBufferInfo = 0x00000001,
}

#[derive(Debug, Default, Clone, Copy, FromBytes, IntoBytes, Immutable)]
#[repr(C)]
pub struct MagmaStructureTypeHeader {
    pub stype: u32,
    pub size: u32,
}

#[derive(Debug, Default, Clone, Copy, FromBytes, IntoBytes, Immutable)]
#[repr(C)]
pub struct MagmaCreateBufferInfo {
    pub header: MagmaStructureTypeHeader,
    pub memory_type_idx: u32,
    pub alignment: u32,
    pub common_flags: u32,
    pub vendor_flags: u32,
    pub size: u64,
}

#[repr(C)]
#[derive(Debug, Default, Copy, Clone, FromBytes, IntoBytes, Immutable)]
pub struct MagmaCommandHeader {
    pub opcode: u32,
    pub size: u32,
}

#[repr(C)]
#[derive(Debug, Default, Copy, Clone, FromBytes, IntoBytes, Immutable)]
pub struct CreateDeviceReq {
    pub header: MagmaCommandHeader,
    pub physical_device: u32,
    pub padding: u32,
}

#[repr(C)]
#[derive(Debug, Default, Copy, Clone, FromBytes, IntoBytes, Immutable)]
pub struct CreateDeviceResp {
    pub header: MagmaCommandHeader,
    pub device: u32,
    pub padding: u32,
}

#[repr(C)]
#[derive(Debug, Default, Copy, Clone, FromBytes, IntoBytes, Immutable)]
pub struct GetMemoryPropertiesReq {
    pub header: MagmaCommandHeader,
    pub device: u32,
    pub padding: u32,
}

#[repr(C)]
#[derive(Debug, Default, Copy, Clone, FromBytes, IntoBytes, Immutable)]
pub struct GetMemoryPropertiesResp {
    pub header: MagmaCommandHeader,
    pub mem_props: MagmaMemoryProperties,
}

#[repr(C)]
#[derive(Debug, Default, Copy, Clone, FromBytes, IntoBytes, Immutable)]
pub struct GetMemoryBudgetReq {
    pub header: MagmaCommandHeader,
    pub device: u32,
    pub heap_idx: u32,
}

#[repr(C)]
#[derive(Debug, Default, Copy, Clone, FromBytes, IntoBytes, Immutable)]
pub struct GetMemoryBudgetResp {
    pub header: MagmaCommandHeader,
    pub budget: MagmaHeapBudget,
}

#[repr(C)]
#[derive(Debug, Default, Copy, Clone, FromBytes, IntoBytes, Immutable)]
pub struct CreateBufferReq {
    pub header: MagmaCommandHeader,
    pub device: u32,
    pub _pad0: u32,
    pub info: MagmaCreateBufferInfo,
}

#[repr(C)]
#[derive(Debug, Default, Copy, Clone, FromBytes, IntoBytes, Immutable)]
pub struct CreateBufferResp {
    pub header: MagmaCommandHeader,
    pub buffer_out: u32,
    pub padding: u32,
}

#[repr(C)]
#[derive(Debug, Default, Copy, Clone, FromBytes, IntoBytes, Immutable)]
pub struct CreateContextReq {
    pub header: MagmaCommandHeader,
    pub device: u32,
    pub padding: u32,
}

#[repr(C)]
#[derive(Debug, Default, Copy, Clone, FromBytes, IntoBytes, Immutable)]
pub struct CreateContextResp {
    pub header: MagmaCommandHeader,
    pub context: u32,
    pub padding: u32,
}

#[repr(C)]
#[derive(Debug, Default, Copy, Clone, FromBytes, IntoBytes, Immutable)]
pub struct DeviceCloseReq {
    pub header: MagmaCommandHeader,

}

#[repr(C)]
#[derive(Debug, Default, Copy, Clone, FromBytes, IntoBytes, Immutable)]
pub struct PhysicalDeviceCloseReq {
    pub header: MagmaCommandHeader,

}

#[derive(Debug)]
pub enum MagmaProtocol {
    CreateDevice(CreateDeviceReq),
    GetMemoryProperties(GetMemoryPropertiesReq),
    GetMemoryBudget(GetMemoryBudgetReq),
    CreateBuffer(CreateBufferReq),
    CreateContext(CreateContextReq),
    DeviceClose(DeviceCloseReq),
    PhysicalDeviceClose(PhysicalDeviceCloseReq),

    RespCreateDevice(CreateDeviceResp),
    RespGetMemoryProperties(GetMemoryPropertiesResp),
    RespGetMemoryBudget(GetMemoryBudgetResp),
    RespCreateBuffer(CreateBufferResp),
    RespCreateContext(CreateContextResp),
}
