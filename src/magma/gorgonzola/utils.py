# Copyright 2026 The Magma GPU Project
# SPDX-License-Identifier: MIT

import re


# gl_create_texture -> GlCreateTexture
def to_pascal_case(s: str) -> str:
    return ''.join(word.capitalize() for word in s.split('_'))


# GlCreateTexture -> gl_create_texture, AMD -> amd
def to_snake_case(s: str) -> str:
    s = re.sub(r'(?<=[a-z0-9])([A-Z])', r'_\1', s)
    s = re.sub(r'(?<=[A-Z])([A-Z][a-z])', r'_\1', s)
    return s.lower()


def create_c_type(s: str) -> str:
    return to_snake_case(s) + '_t'


def normalize_command_name(cmd_name: str, api_name: str) -> str:
    snake = to_snake_case(cmd_name)
    prefix = api_name.lower() + '_'
    if snake.startswith(prefix):
        snake = snake[len(prefix) :]
    return to_pascal_case(snake)
