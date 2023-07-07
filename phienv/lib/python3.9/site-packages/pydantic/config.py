"""Configuration for Pydantic models."""
from __future__ import annotations as _annotations

from typing import TYPE_CHECKING, Any, Callable, overload
from warnings import warn

from typing_extensions import Literal, Protocol, TypedDict

from ._migration import getattr_migration
from .deprecated.config import BaseConfig
from .warnings import PydanticDeprecatedSince20

if not TYPE_CHECKING:
    # See PyCharm issues https://youtrack.jetbrains.com/issue/PY-21915
    # and https://youtrack.jetbrains.com/issue/PY-51428
    DeprecationWarning = PydanticDeprecatedSince20

__all__ = 'BaseConfig', 'ConfigDict', 'Extra'


class JsonSchemaExtraCallable(Protocol):
    @overload
    def __call__(self, schema: dict[str, Any]) -> None:
        pass

    @overload
    def __call__(self, schema: dict[str, Any], model_class: type[Any]) -> None:
        pass


class _Extra:
    allow: Literal['allow'] = 'allow'
    ignore: Literal['ignore'] = 'ignore'
    forbid: Literal['forbid'] = 'forbid'

    def __getattribute__(self, __name: str) -> Any:
        warn(
            '`pydantic.config.Extra` is deprecated, use literal values instead' " (e.g. `extra='allow'`)",
            DeprecationWarning,
            stacklevel=2,
        )
        return super().__getattribute__(__name)


Extra = _Extra()

ExtraValues = Literal['allow', 'ignore', 'forbid']


class ConfigDict(TypedDict, total=False):
    """A dictionary-like class for configuring Pydantic models.

    Attributes:
        title: The title for the generated JSON schema. Defaults to `None`.
        str_to_lower: Whether to convert all characters to lowercase for str & bytes types. Defaults to `False`.
        str_to_upper: Whether to convert all characters to uppercase for str & bytes types. Defaults to `False`.
        str_strip_whitespace: Whether to strip leading and trailing whitespace for str & bytes types.
            Defaults to `False`.
        str_min_length: The minimum length for str & bytes types. Defaults to `None`.
        str_max_length: The maximum length for str & bytes types. Defaults to `None`.
        extra: Whether to ignore, allow, or forbid extra attributes during model initialization.
            Accepts the string values of `'ignore'`, `'allow'`, or `'forbid'`. Defaults to `'ignore'`.

            - `'forbid'` will cause validation to fail if extra attributes are included.
            - `'ignore'` will silently ignore any extra attributes.
            - `'allow'` will assign the attributes to the model.

            See [Extra Attributes](../usage/model_config.md#extra-attributes) for details.
        frozen: Whether or not models are faux-immutable, i.e. whether `__setattr__` is allowed, and also generates
            a `__hash__()` method for the model. This makes instances of the model potentially hashable if all the
            attributes are hashable. Defaults to `False`.

            !!! note
                On V1, this setting was called `allow_mutation`, and was `True` by default.
        populate_by_name: Whether an aliased field may be populated by its name as given by the model
            attribute, as well as the alias. Defaults to `False`.

            !!! note
                The name of this configuration setting was changed in **v2.0** from
                `allow_population_by_alias` to `populate_by_name`.
        use_enum_values: Whether to populate models with the `value` property of enums, rather than the raw enum.
            This may be useful if you want to serialize `model.model_dump()` later. Defaults to `False`.
        validate_assignment: Whether to perform validation on *assignment* to attributes. Defaults to `False`.
        arbitrary_types_allowed: Whether to allow arbitrary user types for fields (they are validated simply by
            checking if the value is an instance of the type). If `False`, `RuntimeError` will be raised on model
            declaration. Defaults to `False`.

            See [Arbitrary Types Allowed](../usage/model_config.md#arbitrary-types-allowed) for details.
        from_attributes: Whether to allow model creation from object attributes. Defaults to `False`.

            !!! note
                The name of this configuration setting was changed in **v2.0** from `orm_mode` to `from_attributes`.
        loc_by_alias: Whether to use the alias for error `loc`s. Defaults to `True`.
        alias_generator: a callable that takes a field name and returns an alias for it.

            See [Alias Generator](../usage/model_config.md#alias-generator) for details.
        ignored_types: A tuple of types that may occur as values of class attributes without annotations. This is
            typically used for custom descriptors (classes that behave like `property`). If an attribute is set on a
            class without an annotation and has a type that is not in this tuple (or otherwise recognized by
            _pydantic_), an error will be raised. Defaults to `()`.
        allow_inf_nan: Whether to allow infinity (`+inf` an `-inf`) and NaN values to float fields. Defaults to `True`.
        json_schema_extra: A dict or callable to provide extra JSON schema properties. Defaults to `None`.
        strict: If `True`, strict validation is applied to all fields on the model.
            See [Strict Mode](../usage/strict_mode.md) for details.
        revalidate_instances: When and how to revalidate models and dataclasses during validation. Accepts the string
            values of `'never'`, `'always'` and `'subclass-instances'`. Defaults to `'never'`.

            - `'never'` will not revalidate models and dataclasses during validation
            - `'always'` will revalidate models and dataclasses during validation
            - `'subclass-instances'` will revalidate models and dataclasses during validation if the instance is a
                subclass of the model or dataclass

            See [Revalidate Instances](../usage/model_config.md#revalidate-instances) for details.
        ser_json_timedelta: The format of JSON serialized timedeltas. Accepts the string values of `'iso8601'` and
            `'float'`. Defaults to `'iso8601'`.

            - `'iso8601'` will serialize timedeltas to ISO 8601 durations.
            - `'float'` will serialize timedeltas to the total number of seconds.
        ser_json_bytes: The encoding of JSON serialized bytes. Accepts the string values of `'utf8'` and `'base64'`.
            Defaults to `'utf8'`.

            - `'utf8'` will serialize bytes to UTF-8 strings.
            - `'base64'` will serialize bytes to base64 strings.
        validate_default: Whether to validate default values during validation. Defaults to `False`.
        protected_namespaces: A `tuple` of strings that prevent model to have field which conflict with them.
            Defaults to `('model_', )`).

            See [Protected Namespaces](../usage/model_config.md#protected-namespaces) for details.
        hide_input_in_errors: Whether to hide inputs when printing errors. Defaults to `False`.

            See [Hide Input in Errors](../usage/model_config.md#hide-input-in-errors).
    """

    title: str | None
    str_to_lower: bool
    str_to_upper: bool
    str_strip_whitespace: bool
    str_min_length: int
    str_max_length: int | None
    extra: ExtraValues | None
    frozen: bool
    populate_by_name: bool
    use_enum_values: bool
    validate_assignment: bool
    arbitrary_types_allowed: bool
    from_attributes: bool
    # whether to use the used alias (or first alias for "field required" errors) instead of field_names
    # to construct error `loc`s, default True
    loc_by_alias: bool
    alias_generator: Callable[[str], str] | None
    ignored_types: tuple[type, ...]
    allow_inf_nan: bool
    json_schema_extra: dict[str, object] | JsonSchemaExtraCallable | None

    # new in V2
    strict: bool
    # whether instances of models and dataclasses (including subclass instances) should re-validate, default 'never'
    revalidate_instances: Literal['always', 'never', 'subclass-instances']
    ser_json_timedelta: Literal['iso8601', 'float']
    ser_json_bytes: Literal['utf8', 'base64']
    # whether to validate default values during validation, default False
    validate_default: bool
    # whether to validate the return value from call validator
    validate_return: bool
    protected_namespaces: tuple[str, ...]
    hide_input_in_errors: bool


__getattr__ = getattr_migration(__name__)
