# Copyright 2026 The Magma GPU Project
# SPDX-License-Identifier: MIT

from __future__ import annotations
from pathlib import Path
import typing as T

from gorgonzola.common import (
    CommonGenerator,
    CopyrightInfo,
    ApiAspectMask,
    Constant,
    Enum,
    Flag,
    ApiObject,
    Struct,
    Command,
)

C_PREPROCESSOR_START = """\
#ifndef {guard}
#define {guard}

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {{
#endif
"""

C_PREPROCESSOR_END = """\
#ifdef __cplusplus
}
#endif

#endif
"""


class HeaderGenerator(CommonGenerator):
    ASPECT_MASK = ApiAspectMask.FFI_HEADER

    def _handle_constants(self, items: T.Dict[str, Constant]) -> str:
        constants: str = ''
        for obj in items.values():
            constants += obj.to_c_def()
        return constants

    def _handle_api_objects(self, items: T.Dict[str, ApiObject]) -> str:
        api_objects: str = ''
        for obj in items.values():
            api_objects += obj.to_c_def() + '\n'
        return api_objects

    def _handle_enums(self, items: T.Dict[str, Enum]) -> str:
        enums: str = ''
        for obj in items.values():
            enums += obj.to_c_def() + '\n'
        return enums

    def _handle_flags(self, items: T.Dict[str, Flag]) -> str:
        flags: str = ''
        for obj in items.values():
            flags += obj.to_c_def() + '\n'
        return flags

    def _handle_structs(self, items: T.Dict[str, Struct]) -> str:
        structs: str = ''
        for obj in items.values():
            structs += obj.to_c_def() + '\n'
        return structs

    def _handle_commands(self, items: T.Dict[str, Command]) -> str:
        commands: str = ''
        for obj in items.values():
            commands += obj.to_c_def() + '\n'
        return commands

    def _emit_impl(self) -> str:
        guard = self.full_path.name.upper().replace('.', '_')
        c_header_file = self._license()
        c_header_file += C_PREPROCESSOR_START.format(guard=guard).strip()

        if self.api_data.constants:
            c_header_file += '\n\n' + self._handle_constants(self.api_data.constants).strip()
        if self.api_data.api_objects:
            c_header_file += '\n\n' + self._handle_api_objects(self.api_data.api_objects).strip()
        if self.api_data.enums:
            c_header_file += '\n\n' + self._handle_enums(self.api_data.enums).strip()
        if self.api_data.flags:
            c_header_file += '\n\n' + self._handle_flags(self.api_data.flags).strip()
        if self.api_data.structs:
            c_header_file += '\n\n' + self._handle_structs(self.api_data.structs).strip()
        if self.api_data.commands:
            c_header_file += '\n\n' + self._handle_commands(self.api_data.commands).strip()

        c_header_file += '\n\n' + C_PREPROCESSOR_END.strip() + '\n'
        return c_header_file
