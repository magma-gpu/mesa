# Copyright 2026 The Magma GPU Project
# SPDX-License-Identifier: MIT

from __future__ import annotations
from pathlib import Path
import typing as T

from gorgonzola.common import CommonGenerator, ApiAspectMask, Enum, Flag, Struct
from gorgonzola.utils import normalize_command_name, to_pascal_case, to_snake_case

COMMON_RUST_IMPORTS = """\
#![allow(non_camel_case_types)]
#![allow(non_snake_case)]
#![allow(unused_imports)]
#![allow(dead_code)]

use zerocopy::{FromBytes, IntoBytes, Immutable};
"""

ENUM = """\
#[derive(Debug, Default, Clone, Copy, PartialEq, Eq)]
#[repr({type_name})]
pub enum {name} {{
{entries}
}}

"""

STRUCT = """\
#[derive(Debug, Default, Clone, Copy, FromBytes, IntoBytes, Immutable)]
#[repr(C)]
pub struct {name} {{
{members}
}}

"""

EXTENSIBLE_STYPE_ENUM = """\
#[derive(Debug, Default, Clone, Copy, PartialEq, Eq)]
#[repr(u32)]
pub enum {api}StructureType {{
{entries}
}}

"""

EXTENSIBLE_HEADER = """\
#[derive(Debug, Default, Clone, Copy, FromBytes, IntoBytes, Immutable)]
#[repr(C)]
pub struct {api}StructureTypeHeader {{
    pub stype: u32,
    pub size: u32,
}}

"""

EXTENSIBLE_STRUCT = """\
#[derive(Debug, Default, Clone, Copy, FromBytes, IntoBytes, Immutable)]
#[repr(C)]
pub struct {name} {{
    pub header: {api}StructureTypeHeader,
{members}
}}

"""

PROTOCOL_ENUM = """\
#[derive(Debug)]
pub enum {api}Protocol {{
{variants}
}}

"""

COMMAND_HEADER = """\
#[repr(C)]
#[derive(Debug, Default, Copy, Clone, FromBytes, IntoBytes, Immutable)]
pub struct {api}CommandHeader {{
    pub opcode: u32,
    pub size: u32,
}}

"""

PROTOCOL_COMMAND_STRUCT = """\
#[repr(C)]
#[derive(Debug, Default, Copy, Clone, FromBytes, IntoBytes, Immutable)]
pub struct {name}{suffix} {{
    pub header: {api}CommandHeader,
{members}
}}

"""


class ProtocolGenerator(CommonGenerator):
    ASPECT_MASK = ApiAspectMask.IPC | ApiAspectMask.VIRTIO

    @property
    def api_pascal(self) -> str:
        return to_pascal_case(self.api_name)

    def _emit_constants(self, items: T.Dict[str, Constant]) -> str:
        constants_list = []
        for name, const in items.items():
            rust_type = self.api_data.resolve_type_name(const.type_name).to_rust_protocol_type()
            constants_list.append(f'pub const {name}: {rust_type} = {const.value};')
        return '\n'.join(constants_list)

    def _emit_enums_and_flags(self, enums: T.Dict[str, Enum], flags: T.Dict[str, Flag]) -> str:
        enums_list = []
        for name, enum_obj in enums.items():
            enums_list.append(self._emit_rust_enum(name, enum_obj).strip())
        for name, flag_obj in flags.items():
            enums_list.append(self._emit_rust_flag(name, flag_obj).strip())
        return '\n\n'.join(enums_list)

    def _emit_structs(self, items: T.Dict[str, Struct]) -> str:
        structs_list = []
        for name, struct_obj in items.items():
            if not struct_obj.stype:
                structs_list.append(self._emit_rust_struct(name, struct_obj).strip())
        return '\n\n'.join(structs_list)

    def _emit_extensible_structs(self, items: T.Dict[str, Struct]) -> str:
        stype_entries = []
        extensible_list = []
        for name, struct_obj in items.items():
            if struct_obj.stype:
                if not stype_entries:
                    stype_entries.append(
                        f'    #[default]\n    {struct_obj.stype} = {struct_obj.stype_value},'
                    )
                else:
                    stype_entries.append(f'    {struct_obj.stype} = {struct_obj.stype_value},')
                extensible_list.append(self._emit_rust_struct(name, struct_obj).strip())

        if not extensible_list and not stype_entries:
            return ''

        stype_enum = EXTENSIBLE_STYPE_ENUM.format(
            api=self.api_pascal, entries='\n'.join(stype_entries)
        ).strip()
        header_str = EXTENSIBLE_HEADER.format(api=self.api_pascal).strip()
        structs_str = '\n\n'.join(extensible_list)
        return f'{stype_enum}\n\n{header_str}\n\n{structs_str}'

    def _emit_opcodes(self, items: T.Dict[str, Command]) -> str:
        if not items:
            return ''

        req_opcodes = []
        resp_opcodes = []
        api_upper = self.api_name.upper()
        for cmd_name, cmd in items.items():
            cmd_pascal = normalize_command_name(cmd_name, self.api_name)
            cmd_snake = to_snake_case(cmd_pascal).upper()
            req_opcodes.append(f'pub const {api_upper}_OPCODE_{cmd_snake}: u32 = {cmd.opcode};')
            if cmd.response:
                val = 0x80000000 | int(cmd.opcode)
                hex_str = f'{val:08x}'
                resp_opcode = f'0x{hex_str[:4]}_{hex_str[4:]}'
                resp_opcodes.append(
                    f'pub const {api_upper}_OPCODE_RESP_{cmd_snake}: u32 = {resp_opcode};'
                )

        return '\n'.join(req_opcodes + [''] + resp_opcodes)

    def _emit_commands(self, items: T.Dict[str, Command]) -> str:
        if not items:
            return ''

        req_variants = []
        resp_variants = []
        command_structs = []

        for cmd_name, cmd in items.items():
            cmd_pascal = normalize_command_name(cmd_name, self.api_name)
            req_variants.append(f'    {cmd_pascal}({cmd_pascal}Req),')
            if cmd.response:
                resp_variants.append(f'    Resp{cmd_pascal}({cmd_pascal}Resp),')

            # Req struct
            req_members_str = self._layout_struct_members(cmd.inputs_const, start_offset=8)

            command_structs.append(
                PROTOCOL_COMMAND_STRUCT.format(
                    api=self.api_pascal, name=cmd_pascal, suffix='Req', members=req_members_str
                ).strip()
            )

            # Resp struct
            if cmd.response:
                resp_members_str = self._layout_struct_members(cmd.inputs_mut, start_offset=8)

                command_structs.append(
                    PROTOCOL_COMMAND_STRUCT.format(
                        api=self.api_pascal,
                        name=cmd_pascal,
                        suffix='Resp',
                        members=resp_members_str,
                    ).strip()
                )

        cmd_header = COMMAND_HEADER.format(api=self.api_pascal).strip()
        structs_str = '\n\n'.join(command_structs)
        variants_str = '\n'.join(req_variants + [''] + resp_variants)
        protocol_enum = PROTOCOL_ENUM.format(api=self.api_pascal, variants=variants_str).strip()
        return f'{cmd_header}\n\n{structs_str}\n\n{protocol_enum}'

    def _emit_impl(self) -> str:
        rust_protocol_file = self._license()
        rust_protocol_file += COMMON_RUST_IMPORTS.strip()

        if self.api_data.commands:
            opcodes_str = self._emit_opcodes(self.api_data.commands).strip()
            if opcodes_str:
                rust_protocol_file += '\n\n' + opcodes_str

        if self.api_data.constants:
            rust_protocol_file += '\n\n' + self._emit_constants(self.api_data.constants).strip()

        if self.api_data.enums or self.api_data.flags:
            rust_protocol_file += (
                '\n\n'
                + self._emit_enums_and_flags(self.api_data.enums, self.api_data.flags).strip()
            )

        if self.api_data.structs:
            structs_str = self._emit_structs(self.api_data.structs).strip()
            if structs_str:
                rust_protocol_file += '\n\n' + structs_str

            extensible_str = self._emit_extensible_structs(self.api_data.structs).strip()
            if extensible_str:
                rust_protocol_file += '\n\n' + extensible_str

        if self.api_data.commands:
            rust_protocol_file += '\n\n' + self._emit_commands(self.api_data.commands).strip()

        return rust_protocol_file + '\n'

    def _emit_rust_enum(self, name: str, enum_obj: T.Union[Enum, Flag]) -> str:
        lines = []
        for i, e in enumerate(enum_obj.entries):
            if i == 0:
                lines.append(f'    #[default]\n    {e.name} = {e.value},')
            else:
                lines.append(f'    {e.name} = {e.value},')
        entries_str = '\n'.join(lines)
        rust_type = enum_obj.type_info.rust_name
        return ENUM.format(name=name, type_name=rust_type, entries=entries_str)

    def _emit_rust_flag(self, name: str, flag_obj: Flag) -> str:
        prefix = to_snake_case(name).upper()
        rust_type = flag_obj.type_info.rust_name
        lines = []
        for e in flag_obj.entries:
            entry_name = to_snake_case(e.name).upper()
            lines.append(f'pub const {prefix}_{entry_name}: {rust_type} = {e.value};')
        return '\n'.join(lines)

    def _layout_struct_members(self, fields: T.List[StructMember], start_offset: int = 0) -> str:
        members_list = []
        curr_offset = start_offset
        pad_idx = 0
        for f in fields:
            align = f.type.get_protocol_align(self.api_data)
            size = f.type.get_protocol_size(self.api_data) or 4
            if curr_offset % align != 0:
                pad_size = (align - (curr_offset % align)) % align
                if pad_size == 4:
                    members_list.append(f'    pub _pad{pad_idx}: u32,')
                    pad_idx += 1
                    curr_offset += 4
                elif pad_size > 0:
                    members_list.append(f'    pub _pad{pad_idx}: [u8; {pad_size}],')
                    pad_idx += 1
                    curr_offset += pad_size
            members_list.append(f.to_rust_protocol_field().rstrip())
            curr_offset += size

        if curr_offset % 8 != 0:
            trail_pad = (8 - (curr_offset % 8)) % 8
            if trail_pad == 4:
                members_list.append('    pub padding: u32,')
            elif trail_pad > 0:
                members_list.append(f'    pub padding: [u8; {trail_pad}],')
        return '\n'.join(members_list)

    def _emit_rust_struct(self, name: str, struct_obj: Struct) -> str:
        start_offset = 8 if struct_obj.stype else 0
        members_val = self._layout_struct_members(struct_obj.members, start_offset=start_offset)

        if struct_obj.stype:
            return EXTENSIBLE_STRUCT.format(api=self.api_pascal, name=name, members=members_val)
        else:
            return STRUCT.format(name=name, members=members_val)
