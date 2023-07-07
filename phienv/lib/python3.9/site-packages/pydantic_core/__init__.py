from __future__ import annotations

import sys as _sys
from typing import Any as _Any

from ._pydantic_core import (
    ArgsKwargs,
    MultiHostUrl,
    PydanticCustomError,
    PydanticKnownError,
    PydanticOmit,
    PydanticSerializationError,
    PydanticSerializationUnexpectedValue,
    PydanticUndefined,
    PydanticUndefinedType,
    PydanticUseDefault,
    SchemaError,
    SchemaSerializer,
    SchemaValidator,
    Some,
    Url,
    ValidationError,
    __version__,
    to_json,
    to_jsonable_python,
)
from .core_schema import CoreConfig, CoreSchema, CoreSchemaType, ErrorType

if _sys.version_info < (3, 11):
    from typing_extensions import NotRequired as _NotRequired
else:
    from typing import NotRequired as _NotRequired

if _sys.version_info < (3, 9):
    from typing_extensions import TypedDict as _TypedDict
else:
    from typing import TypedDict as _TypedDict

__all__ = [
    '__version__',
    'CoreConfig',
    'CoreSchema',
    'CoreSchemaType',
    'SchemaValidator',
    'SchemaSerializer',
    'Some',
    'Url',
    'MultiHostUrl',
    'ArgsKwargs',
    'PydanticUndefined',
    'PydanticUndefinedType',
    'SchemaError',
    'ErrorDetails',
    'InitErrorDetails',
    'ValidationError',
    'PydanticCustomError',
    'PydanticKnownError',
    'PydanticOmit',
    'PydanticUseDefault',
    'PydanticSerializationError',
    'PydanticSerializationUnexpectedValue',
    'to_json',
    'to_jsonable_python',
]


class ErrorDetails(_TypedDict):
    type: str
    loc: tuple[int | str, ...]
    msg: str
    input: _Any
    ctx: _NotRequired[dict[str, str | int | float]]


class InitErrorDetails(_TypedDict):
    type: str | PydanticCustomError
    loc: _NotRequired[tuple[int | str, ...]]
    input: _Any
    ctx: _NotRequired[dict[str, str | int | float]]


class ErrorTypeInfo(_TypedDict):
    type: ErrorType
    message_template_python: str
    example_message_python: str
    message_template_json: _NotRequired[str]
    example_message_json: _NotRequired[str]
    example_context: dict[str, str | int | float] | None


class MultiHostHost(_TypedDict):
    username: str | None
    password: str | None
    host: str | None
    port: int | None
