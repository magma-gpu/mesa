// Copyright 2026 Google
// SPDX-License-Identifier: MIT

#![allow(dead_code)]

use std::sync::Arc;

use crate::ioctl_readwrite;

use magma_gpu::util::Error as MagmaGpuError;
use magma_gpu::util::Handle as MagmaGpuHandle;
use magma_gpu::util::MappedRegion;
use magma_gpu::util::Result as MagmaGpuResult;

use crate::traits::Buffer;
use crate::traits::Context;
use crate::traits::Device;
use crate::traits::GenericBuffer;
use crate::traits::GenericDevice;
use crate::traits::PhysicalDevice;

use crate::encoder::Encoder;
use crate::magma_defines::MagmaCreateBufferInfo;
use crate::magma_defines::MagmaHeapBudget;
use crate::magma_defines::MagmaImportHandleInfo;
use crate::magma_defines::MagmaMappedMemoryRange;
use crate::magma_defines::MagmaMemoryProperties;
use crate::protocol::*;

use crate::sys::linux::bindings::drm_bindings::DRM_COMMAND_BASE;
use crate::sys::linux::bindings::drm_bindings::DRM_IOCTL_BASE;
use crate::sys::linux::bindings::virtgpu_bindings::*;
use crate::sys::linux::PlatformDevice;

ioctl_readwrite!(
    drm_ioctl_virtgpu_map,
    DRM_IOCTL_BASE,
    DRM_COMMAND_BASE + DRM_VIRTGPU_MAP,
    drm_virtgpu_map
);

ioctl_readwrite!(
    drm_ioctl_virtgpu_execbuffer,
    DRM_IOCTL_BASE,
    DRM_COMMAND_BASE + DRM_VIRTGPU_EXECBUFFER,
    drm_virtgpu_execbuffer
);

ioctl_readwrite!(
    drm_ioctl_virtgpu_resource_create,
    DRM_IOCTL_BASE,
    DRM_COMMAND_BASE + DRM_VIRTGPU_RESOURCE_CREATE,
    drm_virtgpu_resource_create
);

ioctl_readwrite!(
    drm_ioctl_virtgpu_resource_create_blob,
    DRM_IOCTL_BASE,
    DRM_COMMAND_BASE + DRM_VIRTGPU_RESOURCE_CREATE_BLOB,
    drm_virtgpu_resource_create_blob
);

ioctl_readwrite!(
    drm_ioctl_virtgpu_context_init,
    DRM_IOCTL_BASE,
    DRM_COMMAND_BASE + DRM_VIRTGPU_CONTEXT_INIT,
    drm_virtgpu_context_init
);

struct VirtGpuContext {
    _physical_device: Arc<dyn PhysicalDevice>,
}

impl Context for VirtGpuContext {}

struct VirtGpuBuffer {
    physical_device: Arc<dyn PhysicalDevice>,
    gem_handle: u32,
    size: usize,
}

impl GenericBuffer for VirtGpuBuffer {
    fn map(&self, _buffer: &Arc<dyn Buffer>) -> MagmaGpuResult<Arc<dyn MappedRegion>> {
        let mut map_arg = drm_virtgpu_map {
            handle: self.gem_handle,
            ..Default::default()
        };
        let offset = unsafe {
            drm_ioctl_virtgpu_map(self.physical_device.as_fd().unwrap(), &mut map_arg)?;
            map_arg.offset
        };
        let mapping = self.physical_device.cpu_map(offset, self.size)?;
        Ok(Arc::new(mapping))
    }

    fn export(&self) -> MagmaGpuResult<MagmaGpuHandle> {
        self.physical_device.export(self.gem_handle)
    }

    fn invalidate(
        &self,
        _sync_flags: u64,
        _ranges: &[MagmaMappedMemoryRange],
    ) -> MagmaGpuResult<()> {
        Ok(())
    }

    fn flush(&self, _sync_flags: u64, _ranges: &[MagmaMappedMemoryRange]) -> MagmaGpuResult<()> {
        Ok(())
    }
}

impl Buffer for VirtGpuBuffer {}

pub struct VirtGpu {
    physical_device: Arc<dyn PhysicalDevice>,
}

impl VirtGpu {
    pub fn new(physical_device: Arc<dyn PhysicalDevice>) -> MagmaGpuResult<VirtGpu> {
        Ok(VirtGpu { physical_device })
    }

    fn submit_encoded_cmd(&self, cmd: &[u8]) -> MagmaGpuResult<()> {
        let mut execbuf = drm_virtgpu_execbuffer {
            flags: 0,
            size: cmd.len() as u32,
            command: cmd.as_ptr() as u64,
            ..Default::default()
        };
        unsafe {
            drm_ioctl_virtgpu_execbuffer(self.physical_device.as_fd().unwrap(), &mut execbuf)?;
        }
        Ok(())
    }
}

impl GenericDevice for VirtGpu {
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

        Ok(Arc::new(VirtGpuContext {
            _physical_device: self.physical_device.clone(),
        }))
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

        let mut res = drm_virtgpu_resource_create {
            target: 2,
            format: 1,
            bind: 0,
            width: create_info.size as u32,
            height: 1,
            depth: 1,
            array_size: 1,
            ..Default::default()
        };

        unsafe {
            drm_ioctl_virtgpu_resource_create(self.physical_device.as_fd().unwrap(), &mut res)?;
        }

        Ok(Arc::new(VirtGpuBuffer {
            physical_device: self.physical_device.clone(),
            gem_handle: res.bo_handle,
            size: create_info.size.try_into()?,
        }))
    }

    fn import(
        &self,
        _device: &Arc<dyn Device>,
        _info: MagmaImportHandleInfo,
    ) -> MagmaGpuResult<Arc<dyn Buffer>> {
        Err(MagmaGpuError::Unsupported)
    }
}

impl PlatformDevice for VirtGpu {}
impl Device for VirtGpu {}

unsafe impl Send for VirtGpu {}
unsafe impl Sync for VirtGpu {}
unsafe impl Send for VirtGpuContext {}
unsafe impl Sync for VirtGpuContext {}
unsafe impl Send for VirtGpuBuffer {}
unsafe impl Sync for VirtGpuBuffer {}
