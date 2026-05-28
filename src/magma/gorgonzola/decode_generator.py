# Copyright 2026 The Magma GPU Project
# SPDX-License-Identifier: MIT

from __future__ import annotations
from pathlib import Path

from gorgonzola.common import CommonGenerator, ApiAspectMask
from gorgonzola.utils import normalize_command_name, to_pascal_case, to_snake_case

DECODER_FILE = """\
{license}{imports}
pub fn decode(reader: &mut Reader) -> Option<{api}Protocol> {{
    if reader.available_bytes() < std::mem::size_of::<{api}CommandHeader>() {{
        return None;
    }}
    let header = reader.peek_obj::<{api}CommandHeader>().ok()?;
    match header.opcode {{
{arms}        _ => None,
    }}
}}
"""

DECODER_ARM = """\
        {opcode_const} => {{
            Some({api}Protocol::{name}(reader.read_obj().ok()?))
        }}
"""


class DecodeGenerator(CommonGenerator):
    ASPECT_MASK = ApiAspectMask.IPC | ApiAspectMask.VIRTIO

    def _emit_imports(self) -> str:
        decoder_config = getattr(
            self.api_data, 'decoder_config', getattr(self.api_data, 'encoder_config', {})
        )
        protocol_import = decoder_config.get('protocol_import', 'use crate::protocol::*;')
        custom_imports = decoder_config.get(
            'custom_imports', ['use crate::util::Reader;', 'use crate::util::Writer;']
        )
        imports = [protocol_import] + list(custom_imports)
        return '\n'.join(imports) + '\n'

    def _emit_impl(self) -> str:
        api = to_pascal_case(self.api_name)
        api_upper = self.api_name.upper()
        req_arms = ''
        resp_arms = ''
        for cmd_name, cmd in self.api_data.commands.items():
            cmd_pascal = normalize_command_name(cmd_name, self.api_name)
            cmd_snake = to_snake_case(cmd_pascal).upper()
            opcode_const = f'{api_upper}_OPCODE_{cmd_snake}'
            req_arms += DECODER_ARM.format(opcode_const=opcode_const, api=api, name=cmd_pascal)
            if cmd.response:
                resp_opcode_const = f'{api_upper}_OPCODE_RESP_{cmd_snake}'
                resp_name = f'Resp{cmd_pascal}'
                resp_arms += DECODER_ARM.format(
                    opcode_const=resp_opcode_const, api=api, name=resp_name
                )

        arms = req_arms + '\n' + resp_arms
        imports_str = self._emit_imports()
        return DECODER_FILE.format(license=self._license(), imports=imports_str, api=api, arms=arms)
