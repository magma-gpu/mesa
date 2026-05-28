# Copyright 2026 The Magma GPU Project
# SPDX-License-Identifier: MIT

from __future__ import annotations
from abc import ABC, abstractmethod
import os
from pathlib import Path
import typing as T
from dataclasses import dataclass, field
from enum import Enum as PyEnum, IntFlag

from gorgonzola.utils import create_c_type, to_snake_case

LICENSE = """\
// Copyright {year} {holder}
// SPDX-License-Identifier: {spdx}
//
// Generated via:
//   https://gitlab.freedesktop.org/mesa/mesa/-/tree/main/src/magma/gorgonzola
//
// Submit patches, do not hand-edit.

"""

MAX_LINE_LENGTH = 100


class OutputType(str, PyEnum):
    CLIENT = 'client'
    SERVER = 'server'


class Direction(str, PyEnum):
    IN = 'in'
    INOUT = 'inout'


class ApiAspectMask(IntFlag):
    UNKNOWN = 0
    FFI_HEADER = 1
    FFI = 2
    RUST = 4
    IPC = 8
    VIRTIO = 16
    COMMON = 31


API_ASPECT_MAP: T.Dict[str, ApiAspectMask] = {
    'unknown': ApiAspectMask.UNKNOWN,
    'ffi_header': ApiAspectMask.FFI_HEADER,
    'ffi': ApiAspectMask.FFI,
    'rust': ApiAspectMask.RUST,
    'ipc': ApiAspectMask.IPC,
    'virtio': ApiAspectMask.VIRTIO,
    'common': ApiAspectMask.COMMON,
}


@dataclass
class ApiInfo:
    name: str = ''
    major_version: int = 0
    minor_version: int = 0
    patch_version: int = 0


@dataclass
class CopyrightInfo:
    spdx: str = ''
    holder: str = ''
    year: int = 0


class GorgonzolaTypeInstance(ABC):
    api_data: T.Optional[ApiData] = None

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def get_size(self, api_data: ApiData) -> T.Optional[int]:
        pass

    @abstractmethod
    def get_dependencies(self) -> T.List[str]:
        pass

    def to_c_type(self) -> str:
        return 'void'

    def to_c_arg(self, name: str, is_const: bool) -> str:
        if is_const:
            return f'const {self.to_c_type()}* {name}'
        return f'{self.to_c_type()}* {name}'

    def to_c_struct_field(self, name: str) -> str:
        return f'{self.to_c_type()} {name};'

    def to_c_def(self) -> str:
        return ''

    def to_rust_ffi_type(self) -> str:
        return '()'

    def to_rust_ffi_arg(self, name: str, is_const: bool) -> str:
        if is_const:
            return f'{name}: &{self.to_rust_ffi_type()}'
        return f'{name}: &mut {self.to_rust_ffi_type()}'

    def to_rust_protocol_type(self) -> str:
        return self.name

    def get_protocol_size(self, api_data: ApiData) -> T.Optional[int]:
        return self.get_size(api_data)

    def get_protocol_align(self, api_data: ApiData) -> int:
        return 4


@dataclass
class BaseRustTypeInfo(GorgonzolaTypeInstance):
    rust_name: str
    num_bytes: int
    c_ffi_type: str

    @property
    def name(self) -> str:
        return self.rust_name

    def get_size(self, api_data: ApiData) -> T.Optional[int]:
        return self.num_bytes

    def get_protocol_align(self, api_data: ApiData) -> int:
        return min(self.num_bytes, 8)

    def get_dependencies(self) -> T.List[str]:
        return []

    def to_c_type(self) -> str:
        return self.c_ffi_type

    def to_c_arg(self, name: str, is_const: bool) -> str:
        if is_const:
            return f'{self.c_ffi_type} {name}'
        return f'{self.c_ffi_type}* {name}'

    def to_rust_ffi_type(self) -> str:
        if self.rust_name == 'void':
            return '()'
        return self.rust_name

    def to_rust_ffi_arg(self, name: str, is_const: bool) -> str:
        if is_const:
            return f'{name}: {self.rust_name}'
        return f'{name}: &mut {self.rust_name}'

    def to_rust_protocol_type(self) -> str:
        if self.rust_name == 'void':
            return '()'
        return self.rust_name


RUST_TYPE_INFO_MAP: T.Dict[str, BaseRustTypeInfo] = {
    'u8': BaseRustTypeInfo('u8', 1, 'uint8_t'),
    'i8': BaseRustTypeInfo('i8', 1, 'int8_t'),
    'u16': BaseRustTypeInfo('u16', 2, 'uint16_t'),
    'i16': BaseRustTypeInfo('i16', 2, 'int16_t'),
    'u32': BaseRustTypeInfo('u32', 4, 'uint32_t'),
    'i32': BaseRustTypeInfo('i32', 4, 'int32_t'),
    'u64': BaseRustTypeInfo('u64', 8, 'uint64_t'),
    'i64': BaseRustTypeInfo('i64', 8, 'int64_t'),
    'f64': BaseRustTypeInfo('f64', 8, 'double'),
    'usize': BaseRustTypeInfo('usize', 8, 'uintptr_t'),
    'c_void': BaseRustTypeInfo('c_void', 8, 'void*'),
    'uint8_t': BaseRustTypeInfo('u8', 1, 'uint8_t'),
    'int8_t': BaseRustTypeInfo('i8', 1, 'int8_t'),
    'uint16_t': BaseRustTypeInfo('u16', 2, 'uint16_t'),
    'int16_t': BaseRustTypeInfo('i16', 2, 'int16_t'),
    'uint32_t': BaseRustTypeInfo('u32', 4, 'uint32_t'),
    'int32_t': BaseRustTypeInfo('i32', 4, 'int32_t'),
    'uint64_t': BaseRustTypeInfo('u64', 8, 'uint64_t'),
    'int64_t': BaseRustTypeInfo('i64', 8, 'int64_t'),
    'double': BaseRustTypeInfo('f64', 8, 'double'),
    'uintptr_t': BaseRustTypeInfo('usize', 8, 'uintptr_t'),
    'void*': BaseRustTypeInfo('c_void', 8, 'void*'),
}


class Constant(GorgonzolaTypeInstance):
    def __init__(self, name: str, type_name: str, value: str) -> None:
        self._name = name
        self.type_name = type_name
        self.value = value

    @property
    def name(self) -> str:
        return self._name

    def get_size(self, api_data: ApiData) -> T.Optional[int]:
        return api_data.get_type_size(self.type_name)

    def get_dependencies(self) -> T.List[str]:
        return [self.type_name]

    def to_c_def(self) -> str:
        return f'#define {self.name} {self.value}\n'


@dataclass
class EnumEntry:
    name: str
    value: str


class BaseEnum(GorgonzolaTypeInstance):
    def __init__(self, name: str, type_info: BaseRustTypeInfo, entries: T.List[EnumEntry]) -> None:
        self._name = name
        self.type_info = type_info
        self.entries = entries

    @property
    def name(self) -> str:
        return self._name

    def get_size(self, api_data: ApiData) -> T.Optional[int]:
        return self.type_info.num_bytes

    def get_protocol_align(self, api_data: ApiData) -> int:
        return min(self.type_info.num_bytes, 8)

    def get_dependencies(self) -> T.List[str]:
        return []

    def to_c_type(self) -> str:
        return create_c_type(self.name)

    def to_c_arg(self, name: str, is_const: bool) -> str:
        c_type = self.to_c_type()
        if is_const:
            return f'{c_type} {name}'
        return f'{c_type}* {name}'

    def to_c_def(self) -> str:
        prefix = to_snake_case(self.name).upper()
        enum_str: str = ''
        for e in self.entries:
            entry_name = to_snake_case(e.name).upper()
            enum_str += f'    {prefix}_{entry_name} = {e.value},\n'
        return f'typedef enum {{\n{enum_str}}} {self.to_c_type()};\n'

    def to_rust_ffi_type(self) -> str:
        return to_snake_case(self.name)

    def to_rust_ffi_arg(self, name: str, is_const: bool) -> str:
        rust_type = self.to_rust_ffi_type()
        if is_const:
            return f'{name}: {rust_type}'
        return f'{name}: *mut {rust_type}'

    def to_rust_protocol_type(self) -> str:
        return self.name


class Enum(BaseEnum):
    pass


class Flag(BaseEnum):
    pass


class ApiObject(GorgonzolaTypeInstance):
    def __init__(self, name: str) -> None:
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def get_size(self, api_data: ApiData) -> T.Optional[int]:
        return 8

    def get_protocol_size(self, api_data: ApiData) -> T.Optional[int]:
        return 4

    def get_protocol_align(self, api_data: ApiData) -> int:
        return 4

    def get_dependencies(self) -> T.List[str]:
        return []

    def to_c_type(self) -> str:
        return create_c_type(self.name)

    def to_c_arg(self, name: str, is_const: bool) -> str:
        c_type = self.to_c_type()
        if is_const:
            return f'{c_type} {name}'
        return f'{c_type}* {name}'

    def to_c_def(self) -> str:
        snake = to_snake_case(self.name)
        return f'struct {snake};\ntypedef struct {snake}* {self.to_c_type()};\n'

    def to_rust_ffi_type(self) -> str:
        return to_snake_case(self.name)

    def to_rust_ffi_arg(self, name: str, is_const: bool) -> str:
        rust_type = self.to_rust_ffi_type()
        if is_const:
            return f'{name}: &mut {rust_type}'
        return f'{name}: &mut *mut {rust_type}'

    def to_rust_protocol_type(self) -> str:
        return 'u32'


class ConstantArray(GorgonzolaTypeInstance):
    def __init__(
        self, name: str, element_type: GorgonzolaTypeInstance, array_size_name: str
    ) -> None:
        self._name = name
        self.element_type = element_type
        self.array_size_name = array_size_name

    @property
    def name(self) -> str:
        return self._name

    def get_size(self, api_data: ApiData) -> T.Optional[int]:
        element_size = self.element_type.get_size(api_data)
        array_size = api_data.resolve_constant_to_int(self.array_size_name)
        if element_size is not None and array_size is not None:
            return element_size * array_size
        return None

    def get_protocol_size(self, api_data: ApiData) -> T.Optional[int]:
        element_size = self.element_type.get_protocol_size(api_data)
        array_size = api_data.resolve_constant_to_int(self.array_size_name)
        if element_size is not None and array_size is not None:
            return element_size * array_size
        return None

    def get_protocol_align(self, api_data: ApiData) -> int:
        return self.element_type.get_protocol_align(api_data)

    def get_dependencies(self) -> T.List[str]:
        deps = [self.element_type.name]
        if not self.array_size_name.isdigit():
            deps.append(self.array_size_name)
        return deps

    def to_c_type(self) -> str:
        return self.element_type.to_c_type() + '*'

    def to_c_arg(self, name: str, is_const: bool) -> str:
        if is_const:
            return f'const {self.element_type.to_c_type()} {name}[{self.array_size_name}]'
        return f'{self.element_type.to_c_type()} {name}[{self.array_size_name}]'

    def to_c_struct_field(self, name: str) -> str:
        return f'{self.element_type.to_c_type()} {name}[{self.array_size_name}];'

    def to_rust_ffi_type(self) -> str:
        return self.element_type.to_rust_ffi_type()

    def to_rust_ffi_arg(self, name: str, is_const: bool) -> str:
        if isinstance(self.element_type, ApiObject):
            element_ffi = self.element_type.to_rust_ffi_type()
            if is_const:
                return f'{name}: &mut *const {element_ffi}'
            return f'{name}: &mut *mut {element_ffi}'
        element_ffi = self.element_type.to_rust_ffi_type()
        if is_const:
            return f'{name}: &[{element_ffi}; {self.array_size_name}]'
        return f'{name}: &mut [{element_ffi}; {self.array_size_name}]'

    def to_rust_protocol_type(self) -> str:
        elem_str = self.element_type.to_rust_protocol_type()
        return f'[{elem_str}; {self.array_size_name}]'


@dataclass
class StructMember:
    name: str
    type: GorgonzolaTypeInstance
    direction: T.Optional[Direction] = None

    def to_c_struct_field(self) -> str:
        return self.type.to_c_struct_field(self.name)

    def to_c_arg(self, is_const: T.Optional[bool] = None) -> str:
        if is_const is None:
            is_const = self.direction == Direction.IN
        return self.type.to_c_arg(self.name, is_const)

    def to_rust_ffi_arg(self, is_const: T.Optional[bool] = None) -> str:
        if is_const is None:
            is_const = self.direction == Direction.IN
        return self.type.to_rust_ffi_arg(self.name, is_const)

    def to_rust_protocol_field(self) -> str:
        return f'    pub {self.name}: {self.type.to_rust_protocol_type()},'


class Struct(GorgonzolaTypeInstance):
    def __init__(
        self,
        name: str,
        members: T.List[StructMember],
        stype: T.Optional[str] = None,
        stype_value: T.Optional[str] = None,
    ) -> None:
        self._name = name
        self.members = members
        self.stype = stype
        self.stype_value = stype_value

    @property
    def padding(self) -> T.Optional[StructMember]:
        if not self.api_data:
            return None
        size = self.get_size(self.api_data)
        if size is None:
            return None
        return self.api_data._calculate_padding(size)

    @property
    def name(self) -> str:
        return self._name

    def get_size(self, api_data: ApiData) -> T.Optional[int]:
        size = 0
        if self.stype:
            size += 8

        for m in self.members:
            m_size = m.type.get_size(api_data)
            if m_size is None:
                return None
            size += m_size
        return size

    def get_protocol_size(self, api_data: ApiData) -> T.Optional[int]:
        size = 8 if self.stype else 0
        for m in self.members:
            align = m.type.get_protocol_align(api_data)
            m_size = m.type.get_protocol_size(api_data)
            if m_size is None:
                return None
            if size % align != 0:
                size += (align - (size % align)) % align
            size += m_size
        if size % 8 != 0:
            size += (8 - (size % 8)) % 8
        return size

    def get_protocol_align(self, api_data: ApiData) -> int:
        max_align = 8 if self.stype else 4
        for m in self.members:
            max_align = max(max_align, m.type.get_protocol_align(api_data))
        return min(max_align, 8)

    def get_dependencies(self) -> T.List[str]:
        return [m.type.name for m in self.members if not isinstance(m.type, BaseRustTypeInfo)]

    def to_c_type(self) -> str:
        return f'struct {to_snake_case(self.name)}'

    def to_c_arg(self, name: str, is_const: bool) -> str:
        c_type = self.to_c_type()
        if is_const:
            return f'const {c_type}* {name}'
        return f'{c_type}* {name}'

    def to_c_def(self) -> str:
        members_str: str = ''
        for member in self.members:
            members_str += f'    {member.to_c_struct_field()}\n'
        return f'{self.to_c_type()} {{\n{members_str}}};\n'

    def to_rust_ffi_type(self) -> str:
        return to_snake_case(self.name)

    def to_rust_protocol_type(self) -> str:
        return self.name


class Command(GorgonzolaTypeInstance):
    def __init__(
        self,
        name: str,
        ret: GorgonzolaTypeInstance,
        inputs: T.List[StructMember],
        opcode: int = 0,
        target: T.Optional[str] = None,
        is_destructor: bool = False,
        response: bool = False,
    ) -> None:
        self._name = name
        self.ret = ret
        self.inputs = inputs
        self.opcode = opcode
        self.target = target
        self.is_destructor = is_destructor
        self.destructor = is_destructor
        self.response = response
        self.has_response = response

    @property
    def inputs_const(self) -> T.List[StructMember]:
        return [p for p in self.inputs if p.direction == Direction.IN]

    @property
    def inputs_mut(self) -> T.List[StructMember]:
        return [p for p in self.inputs if p.direction == Direction.INOUT]

    def _get_fields_padding(self, fields: T.List[StructMember]) -> T.Optional[StructMember]:
        if not self.api_data:
            return None
        size = 8
        for p in fields:
            p_size = p.type.get_size(self.api_data)
            if p_size is not None:
                size += p_size
        return self.api_data._calculate_padding(size)

    @property
    def req_padding(self) -> T.Optional[StructMember]:
        return self._get_fields_padding(self.inputs_const)

    @property
    def resp_padding(self) -> T.Optional[StructMember]:
        if not self.response:
            return None
        return self._get_fields_padding(self.inputs_mut)

    @property
    def name(self) -> str:
        return self._name

    def get_size(self, api_data: ApiData) -> T.Optional[int]:
        return None

    def get_dependencies(self) -> T.List[str]:
        deps: T.List[str] = []
        if not isinstance(self.ret, BaseRustTypeInfo):
            deps.append(self.ret.name)
        for p in self.inputs:
            if not isinstance(p.type, BaseRustTypeInfo):
                deps.append(p.type.name)
        return deps

    def to_c_def(self) -> str:
        args: T.List[str] = [m.to_c_arg() for m in self.inputs]

        prefix: str = f'{self.ret.to_c_type()} {to_snake_case(self.name)}('
        indent_len: int = len(prefix)
        indent: str = ' ' * indent_len
        if not args:
            return prefix + 'void);\n'

        tokens = []
        for arg in args[:-1]:
            tokens.append(arg + ',')

        tokens.append(args[-1] + ');')

        res = prefix
        curr_line_len = indent_len

        for i, token in enumerate(tokens):
            if i == 0:
                # Always attach directly to '(', no space, no newline to first argument.
                res += token
                curr_line_len += len(token)
            else:
                if curr_line_len + 1 + len(token) > MAX_LINE_LENGTH:
                    res += '\n' + indent
                    curr_line_len = indent_len
                else:
                    res += ' '
                    curr_line_len += 1

                res += token
                curr_line_len += len(token)

        return res + '\n'


@dataclass
class ApiData:
    constants: T.Dict[str, Constant] = field(default_factory=dict)
    api_objects: T.Dict[str, ApiObject] = field(default_factory=dict)
    enums: T.Dict[str, Enum] = field(default_factory=dict)
    flags: T.Dict[str, Flag] = field(default_factory=dict)
    structs: T.Dict[str, Struct] = field(default_factory=dict)
    arrays: T.Dict[str, ConstantArray] = field(default_factory=dict)
    commands: T.Dict[str, Command] = field(default_factory=dict)
    ffi_config: T.Dict[str, T.Any] = field(default_factory=dict)
    encoder_config: T.Dict[str, T.Any] = field(default_factory=dict)
    decoder_config: T.Dict[str, T.Any] = field(default_factory=dict)

    def add_type(self, obj: GorgonzolaTypeInstance) -> None:
        obj.api_data = self
        if isinstance(obj, Constant):
            self.constants[obj.name] = obj
        elif isinstance(obj, ApiObject):
            self.api_objects[obj.name] = obj
        elif isinstance(obj, Enum):
            self.enums[obj.name] = obj
        elif isinstance(obj, Flag):
            self.flags[obj.name] = obj
        elif isinstance(obj, Struct):
            self.structs[obj.name] = obj
        elif isinstance(obj, ConstantArray):
            self.arrays[obj.name] = obj
        elif isinstance(obj, Command):
            self.commands[obj.name] = obj

    def _calculate_padding(self, current_size: int) -> T.Optional[StructMember]:
        padding = (8 - (current_size % 8)) % 8
        if padding == 4:
            return StructMember(name='padding', type=RUST_TYPE_INFO_MAP['u32'])
        elif padding > 0:
            arr_name = f'[u8; {padding}]'
            if arr_name not in self.arrays:
                array_type = ConstantArray(arr_name, RUST_TYPE_INFO_MAP['u8'], str(padding))
                self.add_type(array_type)
            return StructMember(name='padding', type=self.arrays[arr_name])
        return None

    def all_types(self) -> T.Iterator[GorgonzolaTypeInstance]:
        yield from self.constants.values()
        yield from self.api_objects.values()
        yield from self.enums.values()
        yield from self.flags.values()
        yield from self.structs.values()
        yield from self.arrays.values()
        yield from self.commands.values()

    def resolve_type_name(self, name: str) -> GorgonzolaTypeInstance:
        if name == 'void':
            return BaseRustTypeInfo('void', 0, 'void')
        if name in RUST_TYPE_INFO_MAP:
            return RUST_TYPE_INFO_MAP[name]

        if name in self.structs:
            return self.structs[name]
        if name in self.api_objects:
            return self.api_objects[name]
        if name in self.enums:
            return self.enums[name]
        if name in self.flags:
            return self.flags[name]
        if name in self.arrays:
            return self.arrays[name]
        if name in self.constants:
            return self.constants[name]
        if name in self.commands:
            return self.commands[name]

        raise ValueError(f'Unable to resolve type name: {name}')

    def find_by_name(self, name: str) -> T.Optional[GorgonzolaTypeInstance]:
        try:
            return self.resolve_type_name(name)
        except ValueError:
            return None

    def get_type_size(self, type_name: str) -> T.Optional[int]:
        obj = self.find_by_name(type_name)
        if obj:
            return obj.get_size(self)
        return None

    def resolve_constant_to_int(self, const_name: str) -> T.Optional[int]:
        if const_name.isdigit():
            return int(const_name)

        if const_name in self.constants:
            const_obj = self.constants[const_name]
            val_str = const_obj.value
            try:
                return int(val_str, 0)
            except ValueError:
                return self.resolve_constant_to_int(val_str)
        return None


class CommonGenerator(ABC):
    ASPECT_MASK: ApiAspectMask = ApiAspectMask.UNKNOWN

    def __init__(self, full_path: Path, copyright_info: CopyrightInfo, api_name: str) -> None:
        self.full_path = full_path
        self.copyright_info = copyright_info
        self.api_name = api_name
        self.api_data = ApiData()

    def emit(self) -> None:
        os.makedirs(self.full_path.parent, exist_ok=True)

        content = self._emit_impl()

        with open(self.full_path, 'w') as f:
            f.write(content)

    @abstractmethod
    def _emit_impl(self) -> str:
        pass

    def _license(self) -> str:
        c = self.copyright_info
        return LICENSE.format(year=c.year, holder=c.holder, spdx=c.spdx)
