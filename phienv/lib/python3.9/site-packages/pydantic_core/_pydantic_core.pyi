from __future__ import annotations

import decimal
import sys
from typing import Any, Callable, Generic, Type, TypeVar

from pydantic_core import ErrorDetails, ErrorTypeInfo, InitErrorDetails, MultiHostHost
from pydantic_core.core_schema import CoreConfig, CoreSchema, ErrorType

if sys.version_info < (3, 8):
    from typing_extensions import final
else:
    from typing import final

if sys.version_info < (3, 11):
    from typing_extensions import Literal, LiteralString, Self, TypeAlias
else:
    from typing import Literal, LiteralString, Self, TypeAlias

from _typeshed import SupportsAllComparisons

__all__ = [
    '__version__',
    'build_profile',
    'ArgsKwargs',
    'SchemaValidator',
    'SchemaSerializer',
    'Url',
    'MultiHostUrl',
    'SchemaError',
    'ValidationError',
    'PydanticCustomError',
    'PydanticKnownError',
    'PydanticOmit',
    'PydanticUseDefault',
    'PydanticSerializationError',
    'PydanticSerializationUnexpectedValue',
    'PydanticUndefined',
    'PydanticUndefinedType',
    'Some',
    'to_json',
    'to_jsonable_python',
    'list_all_errors',
]
__version__: str
build_profile: str

_T = TypeVar('_T', default=Any, covariant=True)

@final
class Some(Generic[_T]):
    __match_args__ = ('value',)

    @property
    def value(self) -> _T: ...
    @classmethod
    def __class_getitem__(cls, __item: Any) -> Type[Self]: ...

@final
class SchemaValidator:
    def __init__(self, schema: CoreSchema, config: CoreConfig | None = None) -> None: ...
    @property
    def title(self) -> str: ...
    def validate_python(
        self,
        input: Any,
        *,
        strict: bool | None = None,
        from_attributes: bool | None = None,
        context: Any = None,
        self_instance: Any | None = None,
    ) -> Any: ...
    def isinstance_python(
        self,
        input: Any,
        *,
        strict: bool | None = None,
        from_attributes: bool | None = None,
        context: Any = None,
        self_instance: Any | None = None,
    ) -> bool: ...
    def validate_json(
        self,
        input: str | bytes | bytearray,
        *,
        strict: bool | None = None,
        context: Any = None,
        self_instance: Any | None = None,
    ) -> Any: ...
    def validate_assignment(
        self,
        obj: Any,
        field_name: str,
        field_value: Any,
        *,
        strict: bool | None = None,
        from_attributes: bool | None = None,
        context: Any = None,
    ) -> dict[str, Any]: ...
    def get_default_value(self, *, strict: bool | None = None, context: Any = None) -> Some | None: ...

_IncEx: TypeAlias = set[int] | set[str] | dict[int, _IncEx] | dict[str, _IncEx] | None

@final
class SchemaSerializer:
    def __init__(self, schema: CoreSchema, config: CoreConfig | None = None) -> None: ...
    def to_python(
        self,
        value: Any,
        *,
        mode: str | None = None,
        include: _IncEx = None,
        exclude: _IncEx = None,
        by_alias: bool = True,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        round_trip: bool = False,
        warnings: bool = True,
        fallback: Callable[[Any], Any] | None = None,
    ) -> Any: ...
    def to_json(
        self,
        value: Any,
        *,
        indent: int | None = None,
        include: _IncEx = None,
        exclude: _IncEx = None,
        by_alias: bool = True,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        round_trip: bool = False,
        warnings: bool = True,
        fallback: Callable[[Any], Any] | None = None,
    ) -> bytes: ...

def to_json(
    value: Any,
    *,
    indent: int | None = None,
    include: _IncEx = None,
    exclude: _IncEx = None,
    by_alias: bool = True,
    exclude_none: bool = False,
    round_trip: bool = False,
    timedelta_mode: Literal['iso8601', 'float'] = 'iso8601',
    bytes_mode: Literal['utf8', 'base64'] = 'utf8',
    serialize_unknown: bool = False,
    fallback: Callable[[Any], Any] | None = None,
) -> bytes: ...
def to_jsonable_python(
    value: Any,
    *,
    include: _IncEx = None,
    exclude: _IncEx = None,
    by_alias: bool = True,
    exclude_none: bool = False,
    round_trip: bool = False,
    timedelta_mode: Literal['iso8601', 'float'] = 'iso8601',
    bytes_mode: Literal['utf8', 'base64'] = 'utf8',
    serialize_unknown: bool = False,
    fallback: Callable[[Any], Any] | None = None,
) -> Any: ...

class Url(SupportsAllComparisons):
    def __init__(self, url: str) -> None: ...
    @property
    def scheme(self) -> str: ...
    @property
    def username(self) -> str | None: ...
    @property
    def password(self) -> str | None: ...
    @property
    def host(self) -> str | None: ...
    @property
    def port(self) -> int | None: ...
    @property
    def path(self) -> str | None: ...
    @property
    def query(self) -> str | None: ...
    @property
    def fragment(self) -> str | None: ...
    def unicode_host(self) -> str | None: ...
    def query_params(self) -> list[tuple[str, str]]: ...
    def unicode_string(self) -> str: ...
    def __repr__(self) -> str: ...
    def __str__(self) -> str: ...
    def __deepcopy__(self, memo: dict) -> str: ...

class MultiHostUrl(SupportsAllComparisons):
    def __init__(self, url: str) -> None: ...
    @property
    def scheme(self) -> str: ...
    @property
    def path(self) -> str | None: ...
    @property
    def query(self) -> str | None: ...
    @property
    def fragment(self) -> str | None: ...
    def hosts(self) -> list[MultiHostHost]: ...
    def query_params(self) -> list[tuple[str, str]]: ...
    def unicode_string(self) -> str: ...
    def __repr__(self) -> str: ...
    def __str__(self) -> str: ...
    def __deepcopy__(self, memo: dict) -> Self: ...

@final
class SchemaError(Exception):
    def error_count(self) -> int: ...
    def errors(self) -> list[ErrorDetails]: ...

@final
class ValidationError(ValueError):
    @staticmethod
    def from_exception_data(
        title: str,
        line_errors: list[InitErrorDetails],
        error_mode: Literal['python', 'json'] = 'python',
        hide_input: bool = False,
    ) -> ValidationError:
        """
        Provisory constructor for a Validation Error.
        This API will probably change and be deprecated in the the future; we will make it easier and more
        powerful to construct and use ValidationErrors, but we cannot do that before our initial Pydantic V2 release.
        So if you use this method please be aware that it may change or be removed before Pydantic V3.
        """
    @property
    def title(self) -> str: ...
    def error_count(self) -> int: ...
    def errors(self, *, include_url: bool = True, include_context: bool = True) -> list[ErrorDetails]: ...
    def json(self, *, indent: int | None = None, include_url: bool = True, include_context: bool = True) -> str: ...

@final
class PydanticCustomError(ValueError):
    def __init__(
        self, error_type: LiteralString, message_template: LiteralString, context: dict[str, Any] | None = None
    ) -> None: ...
    @property
    def context(self) -> dict[str, Any] | None: ...
    @property
    def type(self) -> str: ...
    @property
    def message_template(self) -> str: ...
    def message(self) -> str: ...

@final
class PydanticKnownError(ValueError):
    def __init__(
        self, error_type: ErrorType, context: dict[str, str | int | float | decimal.Decimal] | None = None
    ) -> None: ...
    @property
    def context(self) -> dict[str, str | int | float] | None: ...
    @property
    def type(self) -> ErrorType: ...
    @property
    def message_template(self) -> str: ...
    def message(self) -> str: ...

@final
class PydanticOmit(Exception):
    def __new__(self) -> PydanticOmit: ...

@final
class PydanticUseDefault(Exception):
    def __new__(self) -> PydanticUseDefault: ...

@final
class PydanticSerializationError(ValueError):
    def __init__(self, message: str) -> None: ...

@final
class PydanticSerializationUnexpectedValue(ValueError):
    def __init__(self, message: str | None = None) -> None: ...

@final
class ArgsKwargs:
    def __init__(self, args: tuple[Any, ...], kwargs: dict[str, Any] | None = None) -> None: ...
    @property
    def args(self) -> tuple[Any, ...]: ...
    @property
    def kwargs(self) -> dict[str, Any] | None: ...

@final
class PydanticUndefinedType:
    def __copy__(self) -> Self: ...
    def __deepcopy__(self, memo: Any) -> Self: ...

PydanticUndefined: PydanticUndefinedType

def list_all_errors() -> list[ErrorTypeInfo]:
    """
    Get information about all built-in errors.
    """
