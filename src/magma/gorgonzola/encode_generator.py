# Copyright 2026 The Magma GPU Project
# SPDX-License-Identifier: MIT

from __future__ import annotations
from pathlib import Path

from gorgonzola.common import CommonGenerator, ApiAspectMask
from gorgonzola.utils import normalize_command_name, to_pascal_case, to_snake_case

ENCODER_FILE = """\
{license}{imports}
pub struct Encoder<'a> {{
    writer: Writer<'a>,
}}

impl<'a> Encoder<'a> {{
    pub fn new(buf: &'a mut [u8]) -> Self {{
        Self {{
            writer: Writer::new(buf),
        }}
    }}

    pub fn from_writer(writer: Writer<'a>) -> Self {{
        Self {{ writer }}
    }}

    pub fn bytes_written(&self) -> usize {{
        self.writer.bytes_written()
    }}
{methods}
}}
"""

ENCODER_METHOD = """\
    pub fn encode_{name_snake}(&mut self, msg: &{struct_type}) -> std::io::Result<()> {{
        self.writer.write_all(zerocopy::IntoBytes::as_bytes(msg))
    }}
"""

ENCODE_MSG_METHOD = """\
    pub fn encode_msg(&mut self, msg: &{api}Protocol) -> std::io::Result<()> {{
        match msg {{
{arms}        }}
    }}
"""

ENCODE_MSG_ARM = '            {api}Protocol::{variant}(msg) => self.encode_{name_snake}(msg),\n'


class EncodeGenerator(CommonGenerator):
    ASPECT_MASK = ApiAspectMask.IPC | ApiAspectMask.VIRTIO

    def _emit_imports(self) -> str:
        encoder_config = getattr(self.api_data, 'encoder_config', {})
        protocol_import = encoder_config.get('protocol_import', 'use crate::protocol::*;')
        custom_imports = encoder_config.get(
            'custom_imports', ['use crate::util::Reader;', 'use crate::util::Writer;']
        )
        imports = [protocol_import] + list(custom_imports)
        return '\n'.join(imports) + '\n'

    def _emit_impl(self) -> str:
        req_methods = ''
        resp_methods = ''
        req_arms = ''
        resp_arms = ''
        api = to_pascal_case(self.api_name)
        for cmd_name, cmd in self.api_data.commands.items():
            cmd_pascal = normalize_command_name(cmd_name, self.api_name)
            cmd_snake = to_snake_case(cmd_pascal)
            req_methods += ENCODER_METHOD.format(
                name_snake=cmd_snake, struct_type=f'{cmd_pascal}Req'
            )
            req_arms += ENCODE_MSG_ARM.format(api=api, variant=cmd_pascal, name_snake=cmd_snake)

            if cmd.response:
                resp_snake = f'resp_{cmd_snake}'
                resp_variant = f'Resp{cmd_pascal}'
                resp_methods += ENCODER_METHOD.format(
                    name_snake=resp_snake, struct_type=f'{cmd_pascal}Resp'
                )
                resp_arms += ENCODE_MSG_ARM.format(
                    api=api, variant=resp_variant, name_snake=resp_snake
                )

        methods = req_methods + '\n' + resp_methods
        arms = req_arms + '\n' + resp_arms
        methods += ENCODE_MSG_METHOD.format(api=api, arms=arms)
        imports_str = self._emit_imports()
        return ENCODER_FILE.format(license=self._license(), imports=imports_str, methods=methods)
