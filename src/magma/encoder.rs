// Copyright 2026 The Magma GPU Project
// SPDX-License-Identifier: MIT
//
// Generated via:
//   https://gitlab.freedesktop.org/mesa/mesa/-/tree/main/src/magma/gorgonzola
//
// Submit patches, do not hand-edit.

use crate::protocol::*;
use magma_gpu::util::Writer;

pub struct Encoder<'a> {
    writer: Writer<'a>,
}

impl<'a> Encoder<'a> {
    pub fn new(buf: &'a mut [u8]) -> Self {
        Self {
            writer: Writer::new(buf),
        }
    }

    pub fn from_writer(writer: Writer<'a>) -> Self {
        Self { writer }
    }

    pub fn bytes_written(&self) -> usize {
        self.writer.bytes_written()
    }
    pub fn encode_create_device(&mut self, msg: &CreateDeviceReq) -> std::io::Result<()> {
        self.writer.write_all(zerocopy::IntoBytes::as_bytes(msg))
    }
    pub fn encode_get_memory_properties(&mut self, msg: &GetMemoryPropertiesReq) -> std::io::Result<()> {
        self.writer.write_all(zerocopy::IntoBytes::as_bytes(msg))
    }
    pub fn encode_get_memory_budget(&mut self, msg: &GetMemoryBudgetReq) -> std::io::Result<()> {
        self.writer.write_all(zerocopy::IntoBytes::as_bytes(msg))
    }
    pub fn encode_create_buffer(&mut self, msg: &CreateBufferReq) -> std::io::Result<()> {
        self.writer.write_all(zerocopy::IntoBytes::as_bytes(msg))
    }
    pub fn encode_create_context(&mut self, msg: &CreateContextReq) -> std::io::Result<()> {
        self.writer.write_all(zerocopy::IntoBytes::as_bytes(msg))
    }
    pub fn encode_device_close(&mut self, msg: &DeviceCloseReq) -> std::io::Result<()> {
        self.writer.write_all(zerocopy::IntoBytes::as_bytes(msg))
    }
    pub fn encode_physical_device_close(&mut self, msg: &PhysicalDeviceCloseReq) -> std::io::Result<()> {
        self.writer.write_all(zerocopy::IntoBytes::as_bytes(msg))
    }

    pub fn encode_resp_create_device(&mut self, msg: &CreateDeviceResp) -> std::io::Result<()> {
        self.writer.write_all(zerocopy::IntoBytes::as_bytes(msg))
    }
    pub fn encode_resp_get_memory_properties(&mut self, msg: &GetMemoryPropertiesResp) -> std::io::Result<()> {
        self.writer.write_all(zerocopy::IntoBytes::as_bytes(msg))
    }
    pub fn encode_resp_get_memory_budget(&mut self, msg: &GetMemoryBudgetResp) -> std::io::Result<()> {
        self.writer.write_all(zerocopy::IntoBytes::as_bytes(msg))
    }
    pub fn encode_resp_create_buffer(&mut self, msg: &CreateBufferResp) -> std::io::Result<()> {
        self.writer.write_all(zerocopy::IntoBytes::as_bytes(msg))
    }
    pub fn encode_resp_create_context(&mut self, msg: &CreateContextResp) -> std::io::Result<()> {
        self.writer.write_all(zerocopy::IntoBytes::as_bytes(msg))
    }
    pub fn encode_msg(&mut self, msg: &MagmaProtocol) -> std::io::Result<()> {
        match msg {
            MagmaProtocol::CreateDevice(msg) => self.encode_create_device(msg),
            MagmaProtocol::GetMemoryProperties(msg) => self.encode_get_memory_properties(msg),
            MagmaProtocol::GetMemoryBudget(msg) => self.encode_get_memory_budget(msg),
            MagmaProtocol::CreateBuffer(msg) => self.encode_create_buffer(msg),
            MagmaProtocol::CreateContext(msg) => self.encode_create_context(msg),
            MagmaProtocol::DeviceClose(msg) => self.encode_device_close(msg),
            MagmaProtocol::PhysicalDeviceClose(msg) => self.encode_physical_device_close(msg),

            MagmaProtocol::RespCreateDevice(msg) => self.encode_resp_create_device(msg),
            MagmaProtocol::RespGetMemoryProperties(msg) => self.encode_resp_get_memory_properties(msg),
            MagmaProtocol::RespGetMemoryBudget(msg) => self.encode_resp_get_memory_budget(msg),
            MagmaProtocol::RespCreateBuffer(msg) => self.encode_resp_create_buffer(msg),
            MagmaProtocol::RespCreateContext(msg) => self.encode_resp_create_context(msg),
        }
    }

}
