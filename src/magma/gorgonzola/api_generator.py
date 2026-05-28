# Copyright 2026 The Magma GPU Project
# SPDX-License-Identifier: MIT

from __future__ import annotations
import tomllib
from pathlib import Path
import typing as T

from gorgonzola.common import (
    OutputType,
    ApiInfo,
    CopyrightInfo,
    ApiData,
    Constant,
    EnumEntry,
    Enum,
    Flag,
    ApiObject,
    ConstantArray,
    Struct,
    Command,
    RUST_TYPE_INFO_MAP,
    BaseRustTypeInfo,
    ApiAspectMask,
    API_ASPECT_MAP,
    CommonGenerator,
    StructMember,
    GorgonzolaTypeInstance,
    Direction,
)

from gorgonzola.ffi_generator import FFIGenerator
from gorgonzola.header_generator import HeaderGenerator
from gorgonzola.protocol_generator import ProtocolGenerator
from gorgonzola.encode_generator import EncodeGenerator
from gorgonzola.decode_generator import DecodeGenerator


class ApiSection(T.TypedDict, total=False):
    name: str
    major_version: int
    minor_version: int
    patch_version: int


class CopyrightSection(T.TypedDict, total=False):
    spdx: str
    holder: str
    year: int


class ClientOutDir(T.TypedDict, total=False):
    ffi: str
    header: str
    protocol: str
    encoder: str


class ServerOutDir(T.TypedDict, total=False):
    protocol: str
    encoder: str


class OutDirInfoSection(T.TypedDict, total=False):
    client: ClientOutDir
    server: ServerOutDir


ApiToml = T.TypedDict(
    'ApiToml',
    {'api': ApiSection, 'copyright': CopyrightSection, 'out-dir-info': OutDirInfoSection},
    total=False,
)


class ConstantTyped(T.TypedDict, total=False):
    name: str
    type: str
    value: T.Union[str, int]


class EnumEntryTyped(T.TypedDict, total=False):
    name: str
    value: T.Union[str, int]


class EnumTyped(T.TypedDict, total=False):
    name: str
    type: str
    entries: T.Union[T.Dict[str, T.Union[str, int]], T.List[EnumEntryTyped]]


class DefinitionsToml(T.TypedDict, total=False):
    api_objects: T.List[str]
    constants: T.List[ConstantTyped]
    enums: T.Union[T.List[EnumTyped], T.Dict[str, EnumTyped]]
    flags: T.Union[T.List[EnumTyped], T.Dict[str, EnumTyped]]


class StructMemberTyped(T.TypedDict, total=False):
    name: str
    type: str
    array_size: T.Union[str, int]


class StypeTyped(T.TypedDict, total=False):
    name: str
    value: T.Union[str, int]


class StructTyped(T.TypedDict, total=False):
    name: str
    members: T.List[StructMemberTyped]
    stype: StypeTyped


class StructsToml(T.TypedDict, total=False):
    structs: T.List[StructTyped]
    extensible_structs: T.List[StructTyped]


class CommandInput(T.TypedDict, total=False):
    name: str
    type: str
    array_size: T.Union[str, int]
    direction: str


CommandTyped = T.TypedDict(
    'CommandTyped',
    {
        'name': str,
        'command_name': str,
        'inputs': T.List[CommandInput],
        'output': str,
        'return': str,
        'aspects': T.List[str],
        'destructor': bool,
        'is_destructor': bool,
        'response': bool,
    },
    total=False,
)


class CommandsToml(T.TypedDict, total=False):
    commands: T.List[CommandTyped]


def open_api_toml(file: Path) -> ApiToml:
    with file.open(mode='rb') as f:
        return T.cast(ApiToml, tomllib.load(f))


def open_definitions_toml(file: Path) -> DefinitionsToml:
    with file.open(mode='rb') as f:
        return T.cast(DefinitionsToml, tomllib.load(f))


def open_structs_toml(file: Path) -> StructsToml:
    with file.open(mode='rb') as f:
        return T.cast(StructsToml, tomllib.load(f))


def open_commands_toml(file: Path) -> CommandsToml:
    with file.open(mode='rb') as f:
        return T.cast(CommandsToml, tomllib.load(f))


class ApiGenerator:
    def __init__(self, directory: Path, out_dir: Path, output_type: OutputType) -> None:
        self.directory = directory
        self.out_dir = out_dir
        self.output_type = output_type

        self.api_info = ApiInfo()
        self.copyright_info = CopyrightInfo()

        self.generators: T.List[CommonGenerator] = []
        self.common_api_data = ApiData()
        self.aspects: T.Dict[str, ApiAspectMask] = {}

    def _add_schema_type(
        self, obj: GorgonzolaTypeInstance, aspect: ApiAspectMask = ApiAspectMask.UNKNOWN
    ) -> None:
        self.common_api_data.add_type(obj)
        if obj.name not in self.aspects or aspect != ApiAspectMask.UNKNOWN:
            self.aspects[obj.name] = aspect

    def parse(self) -> T.Optional[ApiGenerator]:
        if not self._parse_api_toml():
            return None

        if not self._parse_definitions_toml():
            return None

        if not self._parse_structs_toml():
            return None

        if not self._parse_commands_toml():
            return None

        self._post_process()
        self._populate_generators()
        return self

    def emit(self) -> None:
        for generator in self.generators:
            generator.emit()

    def _parse_api_toml(self) -> bool:
        api_toml_path = self.directory / 'api.toml'
        data = open_api_toml(api_toml_path)

        if 'api' not in data or 'copyright' not in data or 'out-dir-info' not in data:
            print(f'Error: {api_toml_path} is missing required sections')
            return False

        api_data = data['api']
        copyright_data = data['copyright']
        output_data = data['out-dir-info']

        self.api_info = ApiInfo(
            name=api_data['name'],
            major_version=api_data['major_version'],
            minor_version=api_data['minor_version'],
            patch_version=api_data['patch_version'],
        )

        self.copyright_info = CopyrightInfo(
            spdx=copyright_data['spdx'],
            holder=copyright_data['holder'],
            year=copyright_data['year'],
        )
        self.common_api_data.ffi_config = data.get('ffi', data.get('ffi-info', {}))
        self.common_api_data.encoder_config = data.get('encoder', data.get('encoder-info', {}))
        self.common_api_data.decoder_config = data.get('decoder', data.get('decoder-info', {}))

        if self.output_type == OutputType.CLIENT:
            client_data = output_data.get('client', {})
            if 'ffi' in client_data:
                self.generators.append(
                    FFIGenerator(
                        self.out_dir / Path(client_data['ffi']),
                        self.copyright_info,
                        self.api_info.name,
                    )
                )
            if 'header' in client_data:
                self.generators.append(
                    HeaderGenerator(
                        self.out_dir / Path(client_data['header']),
                        self.copyright_info,
                        self.api_info.name,
                    )
                )
            if 'protocol' in client_data:
                self.generators.append(
                    ProtocolGenerator(
                        self.out_dir / Path(client_data['protocol']),
                        self.copyright_info,
                        self.api_info.name,
                    )
                )
            if 'encoder' in client_data:
                self.generators.append(
                    EncodeGenerator(
                        self.out_dir / Path(client_data['encoder']),
                        self.copyright_info,
                        self.api_info.name,
                    )
                )

        elif self.output_type == OutputType.SERVER:
            server_data = output_data.get('server', {})
            if 'protocol' in server_data:
                self.generators.append(
                    ProtocolGenerator(
                        self.out_dir / Path(server_data['protocol']),
                        self.copyright_info,
                        self.api_info.name,
                    )
                )
            if 'encoder' in server_data:
                self.generators.append(
                    DecodeGenerator(
                        self.out_dir / Path(server_data['encoder']),
                        self.copyright_info,
                        self.api_info.name,
                    )
                )

        return True

    def _parse_enum_entries(
        self, entries_data: T.Union[T.Dict[str, T.Union[str, int]], T.List[EnumEntryTyped]]
    ) -> T.List[EnumEntry]:
        if isinstance(entries_data, dict):
            return [EnumEntry(name=k, value=str(v)) for k, v in entries_data.items()]
        elif isinstance(entries_data, list):
            return [EnumEntry(name=item['name'], value=str(item['value'])) for item in entries_data]
        else:
            raise TypeError('entries must be a dict or a list')

    def _parse_definitions_toml(self) -> bool:
        data = open_definitions_toml(self.directory / 'definitions.toml')

        if 'api_objects' in data:
            for name in data['api_objects']:
                self._add_schema_type(ApiObject(name), ApiAspectMask.COMMON)

        if 'constants' in data:
            for c in data['constants']:
                self._add_schema_type(
                    Constant(c['name'], c['type'], str(c['value'])), ApiAspectMask.COMMON
                )

        if 'enums' in data:
            enums_data = data['enums']
            if isinstance(enums_data, list):
                for e in enums_data:
                    name = e['name']
                    entries = self._parse_enum_entries(e['entries'])
                    type_info = RUST_TYPE_INFO_MAP.get(e['type'])
                    if not type_info:
                        raise ValueError(f'Unknown underlying type {e["type"]} for enum {name}')
                    self._add_schema_type(Enum(name, type_info, entries), ApiAspectMask.COMMON)
            elif isinstance(enums_data, dict):
                for name, e in enums_data.items():
                    entries = self._parse_enum_entries(e['entries'])
                    type_info = RUST_TYPE_INFO_MAP.get(e['type'])
                    if not type_info:
                        raise ValueError(f'Unknown underlying type {e["type"]} for enum {name}')
                    self._add_schema_type(Enum(name, type_info, entries), ApiAspectMask.COMMON)

        if 'flags' in data:
            flags_data = data['flags']
            if isinstance(flags_data, list):
                for f in flags_data:
                    name = f['name']
                    entries = self._parse_enum_entries(f['entries'])
                    type_info = RUST_TYPE_INFO_MAP.get(f['type'])
                    if not type_info:
                        raise ValueError(f'Unknown underlying type {f["type"]} for flag {name}')
                    self._add_schema_type(Flag(name, type_info, entries), ApiAspectMask.COMMON)
            elif isinstance(flags_data, dict):
                for name, f in flags_data.items():
                    entries = self._parse_enum_entries(f['entries'])
                    type_info = RUST_TYPE_INFO_MAP.get(f['type'])
                    if not type_info:
                        raise ValueError(f'Unknown underlying type {f["type"]} for flag {name}')
                    self._add_schema_type(Flag(name, type_info, entries), ApiAspectMask.COMMON)

        return True

    def _parse_structs_toml(self) -> bool:
        data = open_structs_toml(self.directory / 'structs.toml')

        if 'structs' in data:
            for s in data['structs']:
                self._parse_struct(s, extensible=False)

        if 'extensible_structs' in data:
            for s in data['extensible_structs']:
                self._parse_struct(s, extensible=True)
        return True

    def _parse_struct(self, s: StructTyped, extensible: bool) -> None:
        name = s['name']
        members = []
        for m in s['members']:
            type_name = m['type']
            if 'array_size' in m:
                arr_name = f'[{type_name}; {m["array_size"]}]'
                if arr_name not in self.common_api_data.arrays:
                    resolved_elem_type = self.common_api_data.resolve_type_name(type_name)
                    array_type = ConstantArray(arr_name, resolved_elem_type, str(m['array_size']))
                    self._add_schema_type(array_type)
                type_name = arr_name

            resolved_type = self.common_api_data.resolve_type_name(type_name)
            members.append(StructMember(name=m['name'], type=resolved_type))

        stype = None
        stype_value = None
        if extensible:
            stype_data = s['stype']
            stype = stype_data['name']
            stype_value = str(stype_data['value'])

        self._add_schema_type(Struct(name, members, stype, stype_value))

    def _parse_commands_toml(self) -> bool:
        data = open_commands_toml(self.directory / 'commands.toml')
        if 'commands' in data:
            opcode_val = 1
            for command in data['commands']:
                name = command['name']
                aspect_mask = ApiAspectMask.UNKNOWN
                if 'aspects' in command:
                    for aspect in command['aspects']:
                        aspect_mask |= API_ASPECT_MAP[aspect]
                else:
                    aspect_mask = ApiAspectMask.COMMON

                inputs = self._parse_fields(command.get('inputs', []))

                ret_name = command.get('output', command.get('return', 'void'))
                ret = self.common_api_data.resolve_type_name(ret_name)
                target = command.get('target', command.get('rust_target'))
                is_destructor = command.get('destructor', command.get('is_destructor', False))
                response = command.get('response', False)

                self._add_schema_type(
                    Command(
                        name=name,
                        ret=ret,
                        inputs=inputs,
                        opcode=opcode_val,
                        target=target,
                        is_destructor=is_destructor,
                        response=response,
                    ),
                    aspect_mask,
                )
                opcode_val += 1
        return True

    def _parse_fields(self, fields_data: T.List[CommandInput]) -> T.List[StructMember]:
        fields = []
        for f in fields_data:
            type_name = f['type']
            if 'array_size' in f:
                arr_name = f'[{type_name}; {f["array_size"]}]'
                if arr_name not in self.common_api_data.arrays:
                    resolved_elem_type = self.common_api_data.resolve_type_name(type_name)
                    array_type = ConstantArray(arr_name, resolved_elem_type, str(f['array_size']))
                    self._add_schema_type(array_type)
                type_name = arr_name
            resolved_type = self.common_api_data.resolve_type_name(type_name)
            direction_str = f.get('direction')
            if direction_str not in (Direction.IN, Direction.INOUT):
                raise ValueError(
                    f'Invalid direction "{direction_str}" for input "{f.get("name")}". '
                    'Must be "in" or "inout".'
                )
            direction = Direction(direction_str)
            fields.append(StructMember(name=f['name'], type=resolved_type, direction=direction))
        return fields

    def _post_process(self) -> None:
        self._propagate_aspects()

    def _propagate_aspects(self) -> None:
        for type_obj in self.common_api_data.all_types():
            if type_obj.name not in self.aspects:
                self.aspects[type_obj.name] = ApiAspectMask.UNKNOWN

        for cmd_name, cmd in self.common_api_data.commands.items():
            cmd_mask = self.aspects[cmd_name]
            for p in cmd.inputs:
                if not isinstance(p.type, BaseRustTypeInfo):
                    self._add_aspect_to_type(p.type.name, cmd_mask)
            if not isinstance(cmd.ret, BaseRustTypeInfo):
                self._add_aspect_to_type(cmd.ret.name, cmd_mask)

        changed = True
        while changed:
            changed = False
            for type_obj in self.common_api_data.all_types():
                if isinstance(type_obj, Command):
                    continue
                mask = self.aspects.get(type_obj.name, ApiAspectMask.UNKNOWN)
                if mask == ApiAspectMask.UNKNOWN:
                    continue

                for dep_name in type_obj.get_dependencies():
                    if self.common_api_data.find_by_name(dep_name) and self._add_aspect_to_type(
                        dep_name, mask
                    ):
                        changed = True

    def _add_aspect_to_type(self, type_name: str, aspect_mask: ApiAspectMask) -> bool:
        old_mask = self.aspects.get(type_name, ApiAspectMask.UNKNOWN)
        new_mask = old_mask | aspect_mask
        if new_mask != old_mask:
            self.aspects[type_name] = new_mask
            return True
        return False

    def _populate_generators(self) -> None:
        for generator in self.generators:
            generator.api_data.ffi_config = self.common_api_data.ffi_config
            generator.api_data.encoder_config = self.common_api_data.encoder_config
            generator.api_data.decoder_config = self.common_api_data.decoder_config
            for type_obj in self.common_api_data.all_types():
                mask = self.aspects.get(type_obj.name, ApiAspectMask.UNKNOWN)
                if mask & generator.ASPECT_MASK:
                    generator.api_data.add_type(type_obj)
