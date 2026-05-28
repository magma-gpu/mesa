# Copyright 2026 The Magma GPU Project
# SPDX-License-Identifier: MIT

from __future__ import annotations
from pathlib import Path
import typing as T

from gorgonzola.common import (
    CommonGenerator,
    ApiAspectMask,
    ApiObject,
    Struct,
    Constant,
    ConstantArray,
    Enum,
    Command,
)
from gorgonzola.utils import to_snake_case

COMMON_RUST_IMPORTS = """\
#![allow(non_camel_case_types)]
#![allow(non_snake_case)]
#![allow(unused_imports)]
#![allow(unused_variables)]

use std::boxed::Box;
use std::convert::TryInto;
use std::ffi::CStr;
use std::os::raw::{c_char, c_void};
use std::panic::{catch_unwind, AssertUnwindSafe};
use std::ptr::null_mut;
use std::slice::{from_raw_parts, from_raw_parts_mut};
use std::sync::Mutex;

use libc::{EINVAL, ESRCH};
use log::error;
"""

RETURN_RESULT_FN = """\
fn return_result<T, E: std::fmt::Display>(result: std::result::Result<T, E>) -> i32 {
    match result {
        Ok(_) => NO_ERROR,
        Err(e) => {
            error!("An error occurred: {}", e);
            -EINVAL
        }
    }
}
"""

RETURN_ON_ERROR_MACRO = """\
macro_rules! return_on_error {
    ($result:expr) => {
        match $result {
            Ok(t) => t,
            Err(e) => {
                error!("An error occurred: {}", e);
                return -EINVAL;
            }
        }
    };
}
"""

ASSIGN_FFI_TYPE = """\
#[allow(non_camel_case_types)]
pub type {ffi_name} = {rust_name};
"""

FFI_FUNCTION = """\
#[no_mangle]
pub unsafe extern "C" fn {name}(
    {args}
) -> {ret} {{
    catch_unwind(AssertUnwindSafe(|| {{
{body}    }}))
    .{unwrap_expr}
}}
"""

UNWRAP_OR_ESRCH = 'unwrap_or(-ESRCH)'

DESTROY_MUT_OBJECT = """\
        if !(*{param_var}).is_null() {{
            let _ = unsafe {{ Box::from_raw(*{param_var}) }};
            *{param_var} = null_mut();
        }}
        NO_ERROR
"""

DESTROY_CONST_OBJECT = """\
        let _ = unsafe {{ Box::from_raw({param_var} as *mut _) }};
        NO_ERROR
"""

INVOKE_STATIC_FUNCTION = """\
        let result = {call_target};
        let items = return_on_error!(result);
        *{count_var} = items.len().try_into().unwrap();
        if *{count_var} > {max_len} {{
            return -EINVAL;
        }}

        let out_slice = from_raw_parts_mut({arr_var}, {max_len} as usize);
        for (i, item) in items.into_iter().enumerate() {{
            out_slice[i] = Box::into_raw(Box::new(item)) as _;
        }}

        NO_ERROR
"""

INVOKE_DISPATCHABLE = """\
        let result = {dispatchable}.{method_name}({args});
        let res = return_on_error!(result);
        *{out_var} = Box::into_raw(Box::new(res)) as _;
        NO_ERROR
"""

INVOKE_METHOD_WITH_OUT_VAR = """\
        let result = {recv_var}.{method_name}({args});
        *{out_var} = return_on_error!(result);
        NO_ERROR
"""

INVOKE_METHOD = """\
        let result = {recv_var}.{method_name}({args});
        return_result(result)
"""


class FFIGenerator(CommonGenerator):
    ASPECT_MASK = ApiAspectMask.FFI

    def _generate_ffi_body(self, cmd_name: str, cmd: Command, ret_type: str) -> str:
        body = self._generate_ffi_body_impl(cmd_name, cmd)
        if ret_type == '()' and body.rstrip().endswith('NO_ERROR'):
            lines = body.rstrip().split('\n')
            if lines[-1].strip() == 'NO_ERROR':
                body = '\n'.join(lines[:-1]) + '\n' if len(lines) > 1 else ''
        return body

    def _generate_ffi_body_impl(self, cmd_name: str, cmd: Command) -> str:
        # Case 1: Destructor / Close / Free commands
        if cmd.is_destructor:
            return self._generate_destructor_body(cmd)

        # Case 2: Enumeration / Static function (no object receiver)
        if len(cmd.inputs_const) == 0 or not isinstance(cmd.inputs_const[0].type, ApiObject):
            return self._generate_static_function_body(cmd_name, cmd)

        # Case 3 & 4: Method call on an ApiObject receiver
        if len(cmd.inputs_const) >= 1 and isinstance(cmd.inputs_const[0].type, ApiObject):
            if len(cmd.inputs_mut) == 1 and isinstance(cmd.inputs_mut[0].type, ApiObject):
                return self._generate_object_creation_body(cmd_name, cmd)
            else:
                return self._generate_method_call_body(cmd_name, cmd)

        return '        NO_ERROR\n'

    def _generate_destructor_body(self, cmd: Command) -> str:
        all_inputs = cmd.inputs_mut + cmd.inputs_const
        if all_inputs:
            param = all_inputs[0]
            if param in cmd.inputs_mut:
                return DESTROY_MUT_OBJECT.format(param_var=param.name)
            else:
                return DESTROY_CONST_OBJECT.format(param_var=param.name)
        return '        NO_ERROR\n'

    def _generate_static_function_body(self, cmd_name: str, cmd: Command) -> str:
        if len(cmd.inputs_mut) >= 2:
            arr_param = cmd.inputs_mut[0]
            count_param = cmd.inputs_mut[1]
            if getattr(cmd, 'target', None):
                call_target = f'{cmd.target}()'
            else:
                call_target = f'{to_snake_case(cmd_name)}()'
            max_len = getattr(arr_param.type, 'array_size_name', '8')
            return INVOKE_STATIC_FUNCTION.format(
                call_target=call_target,
                count_var=count_param.name,
                max_len=max_len,
                arr_var=arr_param.name,
            )
        return '        NO_ERROR\n'

    def _resolve_method_invocation(self, cmd_name: str, cmd: Command) -> T.Tuple[str, str, str]:
        recv_var = cmd.inputs_const[0].name
        recv_type_snake = to_snake_case(cmd.inputs_const[0].type.name)

        if getattr(cmd, 'target', None):
            method_name = cmd.target
        else:
            method_name = to_snake_case(cmd_name)
            api_prefix = f'{self.api_name.lower()}_'
            if method_name.startswith(api_prefix):
                method_name = method_name[len(api_prefix) :]
            if method_name.startswith(f'{recv_type_snake}_'):
                method_name = method_name[len(recv_type_snake) + 1 :]

        args = ', '.join(p.name for p in cmd.inputs_const[1:])
        return recv_var, method_name, args

    def _generate_object_creation_body(self, cmd_name: str, cmd: Command) -> str:
        dispatchable, method_name, args = self._resolve_method_invocation(cmd_name, cmd)
        out_var = cmd.inputs_mut[0].name
        return INVOKE_DISPATCHABLE.format(
            dispatchable=dispatchable, method_name=method_name, args=args, out_var=out_var
        )

    def _generate_method_call_body(self, cmd_name: str, cmd: Command) -> str:
        recv_var, method_name, args = self._resolve_method_invocation(cmd_name, cmd)
        if len(cmd.inputs_mut) >= 1:
            out_var = cmd.inputs_mut[0].name
            return INVOKE_METHOD_WITH_OUT_VAR.format(
                recv_var=recv_var, method_name=method_name, args=args, out_var=out_var
            )
        else:
            return INVOKE_METHOD.format(recv_var=recv_var, method_name=method_name, args=args)

    def _emit_imports(self) -> str:
        ffi_config = getattr(self.api_data, 'ffi_config', {})
        crate_name = ffi_config.get('crate_name', self.api_name.lower())
        custom_imports = ffi_config.get('custom_imports', [])
        exclude_imports = set(ffi_config.get('exclude_imports', []))

        imports: T.List[str] = list(custom_imports)
        for name in sorted(self.api_data.api_objects.keys()):
            if name not in exclude_imports:
                imports.append(f'use {crate_name}::{name};')
        for name in sorted(self.api_data.structs.keys()):
            if name not in exclude_imports:
                imports.append(f'use {crate_name}::{name};')
        for name in sorted(self.api_data.enums.keys()):
            if name not in exclude_imports:
                imports.append(f'use {crate_name}::{name};')
        return '\n'.join(imports)

    def _emit_constants(self, items: T.Dict[str, Constant], used_text: str) -> str:
        res = ''
        if 'NO_ERROR' in used_text:
            res += 'const NO_ERROR: i32 = 0;\n'
        for name, const in items.items():
            if name in used_text:
                rust_type = self.api_data.resolve_type_name(const.type_name).to_rust_protocol_type()
                res += f'const {name}: {rust_type} = {const.value};\n'
        return res

    def _emit_type_aliases(self, items: T.Dict[str, T.Any], exclude_imports: T.Set[str]) -> str:
        aliases = []
        for name in sorted(items.keys()):
            if name in exclude_imports:
                continue
            ffi_name = to_snake_case(name)
            if ffi_name != name:
                aliases.append(ASSIGN_FFI_TYPE.format(rust_name=name, ffi_name=ffi_name).strip())
        return '\n\n'.join(aliases)

    def _emit_commands(self, items: T.Dict[str, Command]) -> str:
        ffi_config = getattr(self.api_data, 'ffi_config', {})
        status_types = set(ffi_config.get('status_types', []))

        funcs = []
        for cmd_name, cmd in items.items():
            args = [p.to_rust_ffi_arg() for p in cmd.inputs]

            ret_type = cmd.ret.to_rust_ffi_type()
            if (
                isinstance(cmd.ret, Enum)
                or cmd.ret.name in status_types
                or ret_type in status_types
            ):
                ret_type = 'i32'

            body = self._generate_ffi_body(cmd_name, cmd, ret_type)

            func_name = to_snake_case(cmd_name)
            funcs.append(
                FFI_FUNCTION.format(
                    name=func_name,
                    args=',\n    '.join(args),
                    ret=ret_type,
                    body=body,
                    unwrap_expr=UNWRAP_OR_ESRCH,
                ).strip()
            )
        return '\n\n'.join(funcs)

    def _emit_impl(self) -> str:
        ffi_config = getattr(self.api_data, 'ffi_config', {})
        exclude_imports = set(ffi_config.get('exclude_imports', []))

        commands_str = (
            self._emit_commands(self.api_data.commands).strip() if self.api_data.commands else ''
        )
        all_types: T.Dict[str, T.Any] = {}
        if self.api_data.api_objects:
            all_types.update(self.api_data.api_objects)
        if self.api_data.structs:
            all_types.update(self.api_data.structs)
        if self.api_data.enums:
            all_types.update(self.api_data.enums)
        aliases_str = (
            self._emit_type_aliases(all_types, exclude_imports).strip() if all_types else ''
        )

        helpers_list = []
        if 'return_result(' in commands_str:
            helpers_list.append(RETURN_RESULT_FN.strip())
        if 'return_on_error!' in commands_str:
            helpers_list.append(RETURN_ON_ERROR_MACRO.strip())
        helpers_str = '\n\n'.join(helpers_list)

        used_text = commands_str + '\n' + aliases_str + '\n' + helpers_str
        constants_str = self._emit_constants(self.api_data.constants, used_text).strip()

        rust_ffi_file = self._license()
        rust_ffi_file += COMMON_RUST_IMPORTS.strip()

        imports_str = self._emit_imports().strip()
        if imports_str:
            rust_ffi_file += '\n\n' + imports_str

        if constants_str:
            rust_ffi_file += '\n\n' + constants_str

        if helpers_str:
            rust_ffi_file += '\n\n' + helpers_str

        if aliases_str:
            rust_ffi_file += '\n\n' + aliases_str

        if commands_str:
            rust_ffi_file += '\n\n' + commands_str

        return rust_ffi_file + '\n'
