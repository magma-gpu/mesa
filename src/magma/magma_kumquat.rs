// Copyright 2025 Android Open Source Project
// SPDX-License-Identifier: MIT

use std::sync::Arc;
use std::sync::Mutex;

use magma_gpu::util::Error as MagmaGpuError;
use magma_gpu::util::Result as MagmaGpuResult;
use magma_gpu::virtgpu_kumquat::VirtGpuKumquat;

use crate::magma::MagmaPhysicalDevice;
use crate::magma_defines::MagmaCreateBufferInfo;
use crate::magma_defines::MagmaHeapBudget;
use crate::magma_defines::MagmaImportHandleInfo;
use crate::magma_defines::MagmaMemoryProperties;
use crate::magma_defines::MagmaPciBusInfo;
use crate::magma_defines::MagmaPciInfo;
use crate::sys::platform::PlatformPhysicalDevice;
use crate::traits::AsVirtGpu;
use crate::traits::Buffer;
use crate::traits::Context;
use crate::traits::Device;
use crate::traits::GenericDevice;
use crate::traits::GenericPhysicalDevice;
use crate::traits::PhysicalDevice;

use crate::encoder::Encoder;
use crate::protocol::*;

pub struct MagmaKumquat {
    virtgpu: Mutex<VirtGpuKumquat>,
}

impl MagmaKumquat {
    pub fn new() -> MagmaGpuResult<MagmaKumquat> {
        Ok(MagmaKumquat {
            virtgpu: Mutex::new(VirtGpuKumquat::new("/tmp/kumquat-gpu-0")?),
        })
    }

    fn submit_encoded_cmd(&self, cmd: &[u8]) -> MagmaGpuResult<()> {
        let mut raw_desc = -1;
        let mut virtgpu = self
            .virtgpu
            .lock()
            .map_err(|_| MagmaGpuError::WithContext("lock failed"))?;
        virtgpu.submit_command(0, &[], cmd, 0, &[], &mut raw_desc)
    }
}

impl AsVirtGpu for MagmaKumquat {
    fn as_virtgpu(&self) -> Option<&Mutex<VirtGpuKumquat>> {
        Some(&self.virtgpu)
    }
}

impl PlatformPhysicalDevice for MagmaKumquat {}
impl PhysicalDevice for MagmaKumquat {}

impl GenericPhysicalDevice for MagmaKumquat {
    fn create_device(
        &self,
        physical_device: &Arc<dyn PhysicalDevice>,
        _pci_info: &MagmaPciInfo,
    ) -> MagmaGpuResult<Arc<dyn Device>> {
        let _virtgpu = physical_device.as_virtgpu().unwrap();
        let mut buf = [0u8; 256];
        let mut encoder = Encoder::new(&mut buf);
        let req = CreateDeviceReq {
            header: MagmaCommandHeader {
                opcode: MAGMA_OPCODE_CREATE_DEVICE,
                size: std::mem::size_of::<CreateDeviceReq>() as u32,
            },
            ..Default::default()
        };
        encoder.encode_create_device(&req)?;
        let len = encoder.bytes_written();
        self.submit_encoded_cmd(&buf[..len])?;
        Err(MagmaGpuError::Unsupported)
    }
}

impl GenericDevice for MagmaKumquat {
    fn get_memory_properties(&self) -> MagmaGpuResult<MagmaMemoryProperties> {
        let mut buf = [0u8; 256];
        let mut encoder = Encoder::new(&mut buf);
        let req = GetMemoryPropertiesReq {
            header: MagmaCommandHeader {
                opcode: MAGMA_OPCODE_GET_MEMORY_PROPERTIES,
                size: std::mem::size_of::<GetMemoryPropertiesReq>() as u32,
            },
            device: 0,
            ..Default::default()
        };
        encoder.encode_get_memory_properties(&req)?;
        let len = encoder.bytes_written();
        self.submit_encoded_cmd(&buf[..len])?;
        Err(MagmaGpuError::Unsupported)
    }

    fn get_memory_budget(&self, heap_idx: u32) -> MagmaGpuResult<MagmaHeapBudget> {
        let mut buf = [0u8; 256];
        let mut encoder = Encoder::new(&mut buf);
        let req = GetMemoryBudgetReq {
            header: MagmaCommandHeader {
                opcode: MAGMA_OPCODE_GET_MEMORY_BUDGET,
                size: std::mem::size_of::<GetMemoryBudgetReq>() as u32,
            },
            device: 0,
            heap_idx,
            ..Default::default()
        };
        encoder.encode_get_memory_budget(&req)?;
        let len = encoder.bytes_written();
        self.submit_encoded_cmd(&buf[..len])?;
        Err(MagmaGpuError::Unsupported)
    }

    fn create_context(&self, _device: &Arc<dyn Device>) -> MagmaGpuResult<Arc<dyn Context>> {
        let mut buf = [0u8; 256];
        let mut encoder = Encoder::new(&mut buf);
        let req = CreateContextReq {
            header: MagmaCommandHeader {
                opcode: MAGMA_OPCODE_CREATE_CONTEXT,
                size: std::mem::size_of::<CreateContextReq>() as u32,
            },
            device: 0,
            ..Default::default()
        };
        encoder.encode_create_context(&req)?;
        let len = encoder.bytes_written();
        self.submit_encoded_cmd(&buf[..len])?;
        Err(MagmaGpuError::Unsupported)
    }

    fn create_buffer(
        &self,
        _device: &Arc<dyn Device>,
        create_info: &MagmaCreateBufferInfo,
    ) -> MagmaGpuResult<Arc<dyn Buffer>> {
        let mut buf = [0u8; 512];
        let mut encoder = Encoder::new(&mut buf);
        let req = CreateBufferReq {
            header: MagmaCommandHeader {
                opcode: MAGMA_OPCODE_CREATE_BUFFER,
                size: std::mem::size_of::<CreateBufferReq>() as u32,
            },
            device: 0,
            info: create_info.clone(),
            ..Default::default()
        };
        encoder.encode_create_buffer(&req)?;
        let len = encoder.bytes_written();
        self.submit_encoded_cmd(&buf[..len])?;
        Err(MagmaGpuError::Unsupported)
    }

    fn import(
        &self,
        _device: &Arc<dyn Device>,
        _info: MagmaImportHandleInfo,
    ) -> MagmaGpuResult<Arc<dyn Buffer>> {
        Err(MagmaGpuError::Unsupported)
    }
}

pub fn enumerate_devices() -> MagmaGpuResult<Vec<MagmaPhysicalDevice>> {
    let pci_info: MagmaPciInfo = Default::default();
    let pci_bus_info: MagmaPciBusInfo = Default::default();
    let mut devices: Vec<MagmaPhysicalDevice> = Vec::new();

    let enc = MagmaKumquat::new()?;
    // TODO): Get data from the server

    devices.push(MagmaPhysicalDevice::new(
        Arc::new(enc),
        pci_info,
        pci_bus_info,
    ));

    Ok(devices)
}
