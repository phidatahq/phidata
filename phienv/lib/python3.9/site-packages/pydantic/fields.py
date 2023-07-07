"""Defining fields on models."""
from __future__ import annotations as _annotations

import dataclasses
import inspect
import sys
import typing
from copy import copy
from dataclasses import Field as DataclassField
from typing import Any, ClassVar
from warnings import warn

import annotated_types
import typing_extensions
from pydantic_core import PydanticUndefined
from typing_extensions import Unpack

from . import types
from ._internal import _decorators, _fields, _generics, _internal_dataclass, _repr, _typing_extra, _utils
from .errors import PydanticUserError
from .warnings import PydanticDeprecatedSince20

if typing.TYPE_CHECKING:
    from ._internal._repr import ReprArgs
else:
    # See PyCharm issues https://youtrack.jetbrains.com/issue/PY-21915
    # and https://youtrack.jetbrains.com/issue/PY-51428
    DeprecationWarning = PydanticDeprecatedSince20


_Unset: Any = PydanticUndefined


class _FromFieldInfoInputs(typing_extensions.TypedDict, total=False):
    """This class exists solely to add type checking for the `**kwargs` in `FieldInfo.from_field`."""

    annotation: type[Any] | None
    default_factory: typing.Callable[[], Any] | None
    alias: str | None
    alias_priority: int | None
    validation_alias: str | AliasPath | AliasChoices | None
    serialization_alias: str | None
    title: str | None
    description: str | None
    examples: list[Any] | None
    exclude: bool | None
    include: bool | None
    gt: float | None
    ge: float | None
    lt: float | None
    le: float | None
    multiple_of: float | None
    strict: bool | None
    min_length: int | None
    max_length: int | None
    pattern: str | None
    allow_inf_nan: bool | None
    max_digits: int | None
    decimal_places: int | None
    discriminator: str | None
    json_schema_extra: dict[str, Any] | None
    frozen: bool | None
    validate_default: bool | None
    repr: bool
    init_var: bool | None
    kw_only: bool | None


class _FieldInfoInputs(_FromFieldInfoInputs, total=False):
    """This class exists solely to add type checking for the `**kwargs` in `FieldInfo.__init__`."""

    default: Any


class FieldInfo(_repr.Representation):
    """This class holds information about a field.

    `FieldInfo` is used for any field definition regardless of whether the `Field()` function is explicitly used.

    Attributes:
        annotation: The type annotation of the field.
        default: The default value of the field.
        default_factory: The factory function used to construct the default for the field.
        alias: The alias name of the field.
        alias_priority: The priority of the field's alias.
        validation_alias: The validation alias name of the field.
        serialization_alias: The serialization alias name of the field.
        title: The title of the field.
        description: The description of the field.
        examples: List of examples of the field.
        exclude: Whether to exclude the field from the model schema.
        include: Whether to include the field in the model schema.
        discriminator: Field name for discriminating the type in a tagged union.
        json_schema_extra: Dictionary of extra JSON schema properties.
        frozen: Whether the field is frozen.
        validate_default: Whether to validate the default value of the field.
        repr: Whether to include the field in representation of the model.
        init_var: Whether the field should be included in the constructor of the dataclass.
        kw_only: Whether the field should be a keyword-only argument in the constructor of the dataclass.
        metadata: List of metadata constraints.
    """

    annotation: type[Any] | None
    default: Any
    default_factory: typing.Callable[[], Any] | None
    alias: str | None
    alias_priority: int | None
    validation_alias: str | AliasPath | AliasChoices | None
    serialization_alias: str | None
    title: str | None
    description: str | None
    examples: list[Any] | None
    exclude: bool | None
    include: bool | None
    discriminator: str | None
    json_schema_extra: dict[str, Any] | None
    frozen: bool | None
    validate_default: bool | None
    repr: bool
    init_var: bool | None
    kw_only: bool | None
    metadata: list[Any]

    __slots__ = (
        'annotation',
        'default',
        'default_factory',
        'alias',
        'alias_priority',
        'validation_alias',
        'serialization_alias',
        'title',
        'description',
        'examples',
        'exclude',
        'include',
        'discriminator',
        'json_schema_extra',
        'frozen',
        'validate_default',
        'repr',
        'init_var',
        'kw_only',
        'metadata',
        '_attributes_set',
    )

    # used to convert kwargs to metadata/constraints,
    # None has a special meaning - these items are collected into a `PydanticGeneralMetadata`
    metadata_lookup: ClassVar[dict[str, typing.Callable[[Any], Any] | None]] = {
        'strict': types.Strict,
        'gt': annotated_types.Gt,
        'ge': annotated_types.Ge,
        'lt': annotated_types.Lt,
        'le': annotated_types.Le,
        'multiple_of': annotated_types.MultipleOf,
        'min_length': annotated_types.MinLen,
        'max_length': annotated_types.MaxLen,
        'pattern': None,
        'allow_inf_nan': None,
        'max_digits': None,
        'decimal_places': None,
    }

    def __init__(self, **kwargs: Unpack[_FieldInfoInputs]) -> None:
        """This class should generally not be initialized directly; instead, use the `pydantic.fields.Field` function
        or one of the constructor classmethods.

        See the signature of `pydantic.fields.Field` for more details about the expected arguments.
        """
        self._attributes_set = {k: v for k, v in kwargs.items() if v is not _Unset}
        kwargs = {k: _DefaultValues.get(k) if v is _Unset else v for k, v in kwargs.items()}  # type: ignore
        self.annotation, annotation_metadata = self._extract_metadata(kwargs.get('annotation'))

        default = kwargs.pop('default', PydanticUndefined)
        if default is Ellipsis:
            self.default = PydanticUndefined
        else:
            self.default = default

        self.default_factory = kwargs.pop('default_factory', None)

        if self.default is not PydanticUndefined and self.default_factory is not None:
            raise TypeError('cannot specify both default and default_factory')

        self.title = kwargs.pop('title', None)
        self.alias = kwargs.pop('alias', None)
        self.validation_alias = kwargs.pop('validation_alias', None)
        self.serialization_alias = kwargs.pop('serialization_alias', None)
        alias_is_set = any(alias is not None for alias in (self.alias, self.validation_alias, self.serialization_alias))
        self.alias_priority = kwargs.pop('alias_priority', None) or 2 if alias_is_set else None
        self.description = kwargs.pop('description', None)
        self.examples = kwargs.pop('examples', None)
        self.exclude = kwargs.pop('exclude', None)
        self.include = kwargs.pop('include', None)
        self.discriminator = kwargs.pop('discriminator', None)
        self.repr = kwargs.pop('repr', True)
        self.json_schema_extra = kwargs.pop('json_schema_extra', None)
        self.validate_default = kwargs.pop('validate_default', None)
        self.frozen = kwargs.pop('frozen', None)
        # currently only used on dataclasses
        self.init_var = kwargs.pop('init_var', None)
        self.kw_only = kwargs.pop('kw_only', None)

        self.metadata = self._collect_metadata(kwargs) + annotation_metadata  # type: ignore

    @classmethod
    def from_field(
        cls, default: Any = PydanticUndefined, **kwargs: Unpack[_FromFieldInfoInputs]
    ) -> typing_extensions.Self:
        """Create a new `FieldInfo` object with the `Field` function.

        Args:
            default: The default value for the field. Defaults to Undefined.
            **kwargs: Additional arguments dictionary.

        Raises:
            TypeError: If 'annotation' is passed as a keyword argument.

        Returns:
            A new FieldInfo object with the given parameters.

        Example:
            This is how you can create a field with default value like this:

            ```python
            import pydantic

            class MyModel(pydantic.BaseModel):
                foo: int = pydantic.Field(4, ...)
            ```
        """
        if 'annotation' in kwargs:
            raise TypeError('"annotation" is not permitted as a Field keyword argument')
        return cls(default=default, **kwargs)

    @classmethod
    def from_annotation(cls, annotation: type[Any]) -> typing_extensions.Self:
        """Creates a `FieldInfo` instance from a bare annotation.

        Args:
            annotation: An annotation object.

        Returns:
            An instance of the field metadata.

        Example:
            This is how you can create a field from a bare annotation like this:

            ```python
            import pydantic
            class MyModel(pydantic.BaseModel):
                foo: int  # <-- like this
            ```

            We also account for the case where the annotation can be an instance of `Annotated` and where
            one of the (not first) arguments in `Annotated` are an instance of `FieldInfo`, e.g.:

            ```python
            import pydantic, annotated_types, typing

            class MyModel(pydantic.BaseModel):
                foo: typing.Annotated[int, annotated_types.Gt(42)]
                bar: typing.Annotated[int, Field(gt=42)]
            ```

        """
        final = False
        if _typing_extra.is_finalvar(annotation):
            final = True
            if annotation is not typing_extensions.Final:
                annotation = typing_extensions.get_args(annotation)[0]

        if _typing_extra.is_annotated(annotation):
            first_arg, *extra_args = typing_extensions.get_args(annotation)
            if _typing_extra.is_finalvar(first_arg):
                final = True
            field_info = cls._find_field_info_arg(extra_args)
            if field_info:
                new_field_info = copy(field_info)
                new_field_info.annotation = first_arg
                new_field_info.frozen = final or field_info.frozen
                new_field_info.metadata += [a for a in extra_args if not isinstance(a, FieldInfo)]
                return new_field_info

        return cls(annotation=annotation, frozen=final or None)

    @classmethod
    def from_annotated_attribute(cls, annotation: type[Any], default: Any) -> typing_extensions.Self:
        """Create `FieldInfo` from an annotation with a default value.

        Args:
            annotation: The type annotation of the field.
            default: The default value of the field.

        Returns:
            A field object with the passed values.

        Example:
            ```python
            import pydantic, annotated_types, typing

            class MyModel(pydantic.BaseModel):
                foo: int = 4  # <-- like this
                bar: typing.Annotated[int, annotated_types.Gt(4)] = 4  # <-- or this
                spam: typing.Annotated[int, pydantic.Field(gt=4)] = 4  # <-- or this
            ```
        """
        final = False
        if _typing_extra.is_finalvar(annotation):
            final = True
            if annotation is not typing_extensions.Final:
                annotation = typing_extensions.get_args(annotation)[0]

        if isinstance(default, cls):
            default.annotation, annotation_metadata = cls._extract_metadata(annotation)
            default.metadata += annotation_metadata
            default.frozen = final or default.frozen
            return default
        elif isinstance(default, dataclasses.Field):
            init_var = False
            if annotation is dataclasses.InitVar:
                if sys.version_info < (3, 8):
                    raise RuntimeError('InitVar is not supported in Python 3.7 as type information is lost')

                init_var = True
                annotation = Any
            elif isinstance(annotation, dataclasses.InitVar):
                init_var = True
                annotation = annotation.type
            pydantic_field = cls._from_dataclass_field(default)
            pydantic_field.annotation, annotation_metadata = cls._extract_metadata(annotation)
            pydantic_field.metadata += annotation_metadata
            pydantic_field.frozen = final or pydantic_field.frozen
            pydantic_field.init_var = init_var
            pydantic_field.kw_only = getattr(default, 'kw_only', None)
            return pydantic_field
        else:
            if _typing_extra.is_annotated(annotation):
                first_arg, *extra_args = typing_extensions.get_args(annotation)
                field_infos = [a for a in extra_args if isinstance(a, FieldInfo)]
                field_info = cls.merge_field_infos(*field_infos, annotation=first_arg, default=default)
                field_info.metadata += [a for a in extra_args if not isinstance(a, FieldInfo)]
                return field_info

            return cls(annotation=annotation, default=default, frozen=final or None)

    @staticmethod
    def merge_field_infos(*field_infos: FieldInfo, **overrides: Any) -> FieldInfo:
        """Merge `FieldInfo` instances keeping only explicitly set attributes.

        Returns:
            FieldInfo: A merged FieldInfo instance.
        """
        new_kwargs: dict[str, Any] = {}
        for field_info in field_infos:
            new_kwargs.update(field_info._attributes_set)
        new_kwargs.update(overrides)
        return FieldInfo(**new_kwargs)

    @classmethod
    def _from_dataclass_field(cls, dc_field: DataclassField[Any]) -> typing_extensions.Self:
        """Return a new `FieldInfo` instance from a `dataclasses.Field` instance.

        Args:
            dc_field: The `dataclasses.Field` instance to convert.

        Returns:
            The corresponding `FieldInfo` instance.

        Raises:
            TypeError: If any of the `FieldInfo` kwargs does not match the `dataclass.Field` kwargs.
        """
        default = dc_field.default
        if default is dataclasses.MISSING:
            default = PydanticUndefined

        if dc_field.default_factory is dataclasses.MISSING:
            default_factory: typing.Callable[[], Any] | None = None
        else:
            default_factory = dc_field.default_factory

        # use the `Field` function so in correct kwargs raise the correct `TypeError`
        field = Field(default=default, default_factory=default_factory, repr=dc_field.repr, **dc_field.metadata)

        field.annotation, annotation_metadata = cls._extract_metadata(dc_field.type)
        field.metadata += annotation_metadata
        return field

    @classmethod
    def _extract_metadata(cls, annotation: type[Any] | None) -> tuple[type[Any] | None, list[Any]]:
        """Tries to extract metadata/constraints from an annotation if it uses `Annotated`.

        Args:
            annotation: The type hint annotation for which metadata has to be extracted.

        Returns:
            A tuple containing the extracted metadata type and the list of extra arguments.
        """
        if annotation is not None:
            if _typing_extra.is_annotated(annotation):
                first_arg, *extra_args = typing_extensions.get_args(annotation)
                return first_arg, list(extra_args)

        return annotation, []

    @staticmethod
    def _find_field_info_arg(args: Any) -> FieldInfo | None:
        """Find an instance of `FieldInfo` in the provided arguments.

        Args:
            args: The argument list to search for `FieldInfo`.

        Returns:
            An instance of `FieldInfo` if found, otherwise `None`.
        """
        return next((a for a in args if isinstance(a, FieldInfo)), None)

    @classmethod
    def _collect_metadata(cls, kwargs: dict[str, Any]) -> list[Any]:
        """Collect annotations from kwargs.

        The return type is actually `annotated_types.BaseMetadata | PydanticMetadata`,
        but it gets combined with `list[Any]` from `Annotated[T, ...]`, hence types.

        Args:
            kwargs: Keyword arguments passed to the function.

        Returns:
            A list of metadata objects - a combination of `annotated_types.BaseMetadata` and
                `PydanticMetadata`.
        """
        metadata: list[Any] = []
        general_metadata = {}
        for key, value in list(kwargs.items()):
            try:
                marker = cls.metadata_lookup[key]
            except KeyError:
                continue

            del kwargs[key]
            if value is not None:
                if marker is None:
                    general_metadata[key] = value
                else:
                    metadata.append(marker(value))
        if general_metadata:
            metadata.append(_fields.PydanticGeneralMetadata(**general_metadata))
        return metadata

    def get_default(self, *, call_default_factory: bool = False) -> Any:
        """Get the default value.

        We expose an option for whether to call the default_factory (if present), as calling it may
        result in side effects that we want to avoid. However, there are times when it really should
        be called (namely, when instantiating a model via `model_construct`).

        Args:
            call_default_factory: Whether to call the default_factory or not. Defaults to `False`.

        Returns:
            The default value, calling the default factory if requested or `None` if not set.
        """
        if self.default_factory is None:
            return _utils.smart_deepcopy(self.default)
        elif call_default_factory:
            return self.default_factory()
        else:
            return None

    def is_required(self) -> bool:
        """Check if the argument is required.

        Returns:
            `True` if the argument is required, `False` otherwise.
        """
        return self.default is PydanticUndefined and self.default_factory is None

    def rebuild_annotation(self) -> Any:
        """Rebuilds the original annotation for use in function signatures.

        If metadata is present, it adds it to the original annotation using an
        `AnnotatedAlias`. Otherwise, it returns the original annotation as is.

        Returns:
            The rebuilt annotation.
        """
        if not self.metadata:
            return self.annotation
        else:
            # Annotated arguments must be a tuple
            return typing_extensions.Annotated[(self.annotation, *self.metadata)]  # type: ignore

    def apply_typevars_map(self, typevars_map: dict[Any, Any] | None, types_namespace: dict[str, Any] | None) -> None:
        """Apply a `typevars_map` to the annotation.

        This method is used when analyzing parametrized generic types to replace typevars with their concrete types.

        This method applies the `typevars_map` to the annotation in place.

        Args:
            typevars_map: A dictionary mapping type variables to their concrete types.
            types_namespace (dict | None): A dictionary containing related types to the annotated type.

        See Also:
            pydantic._internal._generics.replace_types is used for replacing the typevars with
                their concrete types.
        """
        annotation = _typing_extra.eval_type_lenient(self.annotation, types_namespace, None)
        self.annotation = _generics.replace_types(annotation, typevars_map)

    def __repr_args__(self) -> ReprArgs:
        yield 'annotation', _repr.PlainRepr(_repr.display_as_type(self.annotation))
        yield 'required', self.is_required()

        for s in self.__slots__:
            if s == '_attributes_set':
                continue
            if s == 'annotation':
                continue
            elif s == 'metadata' and not self.metadata:
                continue
            elif s == 'repr' and self.repr is True:
                continue
            if s == 'frozen' and self.frozen is False:
                continue
            if s == 'validation_alias' and self.validation_alias == self.alias:
                continue
            if s == 'serialization_alias' and self.serialization_alias == self.alias:
                continue
            if s == 'default_factory' and self.default_factory is not None:
                yield 'default_factory', _repr.PlainRepr(_repr.display_as_type(self.default_factory))
            else:
                value = getattr(self, s)
                if value is not None and value is not PydanticUndefined:
                    yield s, value


@_internal_dataclass.slots_dataclass
class AliasPath:
    """usage docs: https://docs.pydantic.dev/dev-v2/usage/fields#aliaspath-and-aliaschoices

    A data class used by `validation_alias` as a convenience to create aliases.

    Attributes:
        path: A list of string or integer aliases.
    """

    path: list[int | str]

    def __init__(self, first_arg: str, *args: str | int) -> None:
        self.path = [first_arg] + list(args)

    def convert_to_aliases(self) -> list[str | int]:
        """Converts arguments to a list of string or integer aliases.

        Returns:
            The list of aliases.
        """
        return self.path


@_internal_dataclass.slots_dataclass
class AliasChoices:
    """usage docs: https://docs.pydantic.dev/dev-v2/usage/fields#aliaspath-and-aliaschoices

    A data class used by `validation_alias` as a convenience to create aliases.

    Attributes:
        choices: A list containing a string or `AliasPath`.
    """

    choices: list[str | AliasPath]

    def __init__(self, first_choice: str | AliasPath, *choices: str | AliasPath) -> None:
        self.choices = [first_choice] + list(choices)

    def convert_to_aliases(self) -> list[list[str | int]]:
        """Converts arguments to a list of lists containing string or integer aliases.

        Returns:
            The list of aliases.
        """
        aliases: list[list[str | int]] = []
        for c in self.choices:
            if isinstance(c, AliasPath):
                aliases.append(c.convert_to_aliases())
            else:
                aliases.append([c])
        return aliases


class _EmptyKwargs(typing_extensions.TypedDict):
    """This class exists solely to ensure that type checking warns about passing `**extra` in `Field`."""


_DefaultValues = dict(
    default=...,
    default_factory=None,
    alias=None,
    alias_priority=None,
    validation_alias=None,
    serialization_alias=None,
    title=None,
    description=None,
    examples=None,
    exclude=None,
    include=None,
    discriminator=None,
    json_schema_extra=None,
    frozen=None,
    validate_default=None,
    repr=True,
    init_var=None,
    kw_only=None,
    pattern=None,
    strict=None,
    gt=None,
    ge=None,
    lt=None,
    le=None,
    multiple_of=None,
    allow_inf_nan=None,
    max_digits=None,
    decimal_places=None,
    min_length=None,
    max_length=None,
)


def Field(  # noqa: C901
    default: Any = PydanticUndefined,
    *,
    default_factory: typing.Callable[[], Any] | None = _Unset,
    alias: str | None = _Unset,
    alias_priority: int | None = _Unset,
    validation_alias: str | AliasPath | AliasChoices | None = _Unset,
    serialization_alias: str | None = _Unset,
    title: str | None = _Unset,
    description: str | None = _Unset,
    examples: list[Any] | None = _Unset,
    exclude: bool | None = _Unset,
    include: bool | None = _Unset,
    discriminator: str | None = _Unset,
    json_schema_extra: dict[str, Any] | None = _Unset,
    frozen: bool | None = _Unset,
    validate_default: bool | None = _Unset,
    repr: bool = _Unset,
    init_var: bool | None = _Unset,
    kw_only: bool | None = _Unset,
    pattern: str | None = _Unset,
    strict: bool | None = _Unset,
    gt: float | None = _Unset,
    ge: float | None = _Unset,
    lt: float | None = _Unset,
    le: float | None = _Unset,
    multiple_of: float | None = _Unset,
    allow_inf_nan: bool | None = _Unset,
    max_digits: int | None = _Unset,
    decimal_places: int | None = _Unset,
    min_length: int | None = _Unset,
    max_length: int | None = _Unset,
    **extra: Unpack[_EmptyKwargs],
) -> Any:
    """Create a field for objects that can be configured.

    Used to provide extra information about a field, either for the model schema or complex validation. Some arguments
    apply only to number fields (`int`, `float`, `Decimal`) and some apply only to `str`.

    Args:
        default: Default value if the field is not set.
        default_factory: A callable to generate the default value, such as :func:`~datetime.utcnow`.
        alias: An alternative name for the attribute.
        alias_priority: Priority of the alias. This affects whether an alias generator is used.
        validation_alias: 'Whitelist' validation step. The field will be the single one allowed by the alias or set of
            aliases defined.
        serialization_alias: 'Blacklist' validation step. The vanilla field will be the single one of the alias' or set
            of aliases' fields and all the other fields will be ignored at serialization time.
        title: Human-readable title.
        description: Human-readable description.
        examples: Example values for this field.
        exclude: Whether to exclude the field from the model schema.
        include: Whether to include the field in the model schema.
        discriminator: Field name for discriminating the type in a tagged union.
        json_schema_extra: Any additional JSON schema data for the schema property.
        frozen: Whether the field is frozen.
        validate_default: Run validation that isn't only checking existence of defaults. `True` by default.
        repr: A boolean indicating whether to include the field in the `__repr__` output.
        init_var: Whether the field should be included in the constructor of the dataclass.
        kw_only: Whether the field should be a keyword-only argument in the constructor of the dataclass.
        strict: If `True`, strict validation is applied to the field.
            See [Strict Mode](../usage/strict_mode.md) for details.
        gt: Greater than. If set, value must be greater than this. Only applicable to numbers.
        ge: Greater than or equal. If set, value must be greater than or equal to this. Only applicable to numbers.
        lt: Less than. If set, value must be less than this. Only applicable to numbers.
        le: Less than or equal. If set, value must be less than or equal to this. Only applicable to numbers.
        multiple_of: Value must be a multiple of this. Only applicable to numbers.
        min_length: Minimum length for strings.
        max_length: Maximum length for strings.
        pattern: Pattern for strings.
        allow_inf_nan: Allow `inf`, `-inf`, `nan`. Only applicable to numbers.
        max_digits: Maximum number of allow digits for strings.
        decimal_places: Maximum number of decimal places allowed for numbers.
        extra: Include extra fields used by the JSON schema.

            !!! warning Deprecated
                The `extra` kwargs is deprecated. Use `json_schema_extra` instead.

    Returns:
        The generated `FieldInfo` object
    """
    # Check deprecated and removed params from V1. This logic should eventually be removed.
    const = extra.pop('const', None)  # type: ignore
    if const is not None:
        raise PydanticUserError('`const` is removed, use `Literal` instead', code='removed-kwargs')

    min_items = extra.pop('min_items', None)  # type: ignore
    if min_items is not None:
        warn('`min_items` is deprecated and will be removed, use `min_length` instead', DeprecationWarning)
        if min_length in (None, _Unset):
            min_length = min_items  # type: ignore

    max_items = extra.pop('max_items', None)  # type: ignore
    if max_items is not None:
        warn('`max_items` is deprecated and will be removed, use `max_length` instead', DeprecationWarning)
        if max_length in (None, _Unset):
            max_length = max_items  # type: ignore

    unique_items = extra.pop('unique_items', None)  # type: ignore
    if unique_items is not None:
        raise PydanticUserError(
            (
                '`unique_items` is removed, use `Set` instead'
                '(this feature is discussed in https://github.com/pydantic/pydantic-core/issues/296)'
            ),
            code='removed-kwargs',
        )

    allow_mutation = extra.pop('allow_mutation', None)  # type: ignore
    if allow_mutation is not None:
        warn('`allow_mutation` is deprecated and will be removed. use `frozen` instead', DeprecationWarning)
        if allow_mutation is False:
            frozen = True

    regex = extra.pop('regex', None)  # type: ignore
    if regex is not None:
        raise PydanticUserError('`regex` is removed. use `pattern` instead', code='removed-kwargs')

    if extra:
        warn(
            'Extra keyword arguments on `Field` is deprecated and will be removed. use `json_schema_extra` instead',
            DeprecationWarning,
        )
        if not json_schema_extra or json_schema_extra is _Unset:
            json_schema_extra = extra  # type: ignore

    if (
        validation_alias
        and validation_alias is not _Unset
        and not isinstance(validation_alias, (str, AliasChoices, AliasPath))
    ):
        raise TypeError('Invalid `validation_alias` type. it should be `str`, `AliasChoices`, or `AliasPath`')

    if serialization_alias in (_Unset, None) and isinstance(alias, str):
        serialization_alias = alias

    if validation_alias in (_Unset, None):
        validation_alias = alias

    return FieldInfo.from_field(
        default,
        default_factory=default_factory,
        alias=alias,
        alias_priority=alias_priority,
        validation_alias=validation_alias,
        serialization_alias=serialization_alias,
        title=title,
        description=description,
        examples=examples,
        exclude=exclude,
        include=include,
        discriminator=discriminator,
        json_schema_extra=json_schema_extra,
        frozen=frozen,
        pattern=pattern,
        validate_default=validate_default,
        repr=repr,
        init_var=init_var,
        kw_only=kw_only,
        strict=strict,
        gt=gt,
        ge=ge,
        lt=lt,
        le=le,
        multiple_of=multiple_of,
        min_length=min_length,
        max_length=max_length,
        allow_inf_nan=allow_inf_nan,
        max_digits=max_digits,
        decimal_places=decimal_places,
    )


class ModelPrivateAttr(_repr.Representation):
    """A descriptor for private attributes in class models.

    Attributes:
        default: The default value of the attribute if not provided.
        default_factory: A callable function that generates the default value of the
            attribute if not provided.
    """

    __slots__ = 'default', 'default_factory'

    def __init__(
        self, default: Any = PydanticUndefined, *, default_factory: typing.Callable[[], Any] | None = None
    ) -> None:
        self.default = default
        self.default_factory = default_factory

    def __getattr__(self, item: str) -> Any:
        """This function improves compatibility with custom descriptors by ensuring delegation happens
        as expected when the default value of a private attribute is a descriptor.
        """
        if item in {'__get__', '__set__', '__delete__'}:
            if hasattr(self.default, item):
                return getattr(self.default, item)
        raise AttributeError(f'{type(self).__name__!r} object has no attribute {item!r}')

    def __set_name__(self, cls: type[Any], name: str) -> None:
        """Preserve `__set_name__` protocol defined in https://peps.python.org/pep-0487."""
        if self.default is PydanticUndefined:
            return
        if not hasattr(self.default, '__set_name__'):
            return
        set_name = self.default.__set_name__
        if callable(set_name):
            set_name(cls, name)

    def get_default(self) -> Any:
        """Retrieve the default value of the object.

        If `self.default_factory` is `None`, the method will return a deep copy of the `self.default` object.

        If `self.default_factory` is not `None`, it will call `self.default_factory` and return the value returned.

        Returns:
            The default value of the object.
        """
        return _utils.smart_deepcopy(self.default) if self.default_factory is None else self.default_factory()

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, self.__class__) and (self.default, self.default_factory) == (
            other.default,
            other.default_factory,
        )


def PrivateAttr(
    default: Any = PydanticUndefined,
    *,
    default_factory: typing.Callable[[], Any] | None = None,
) -> Any:
    """Indicates that attribute is only used internally and never mixed with regular fields.

    Private attributes are not checked by Pydantic, so it's up to you to maintain their accuracy.

    Private attributes are stored in `__private_attributes__` on the model.

    Args:
        default: The attribute's default value. Defaults to Undefined.
        default_factory: Callable that will be
            called when a default value is needed for this attribute.
            If both `default` and `default_factory` are set, an error will be raised.

    Returns:
        An instance of `ModelPrivateAttr` class.

    Raises:
        ValueError: If both `default` and `default_factory` are set.
    """
    if default is not PydanticUndefined and default_factory is not None:
        raise TypeError('cannot specify both default and default_factory')

    return ModelPrivateAttr(
        default,
        default_factory=default_factory,
    )


@_internal_dataclass.slots_dataclass
class ComputedFieldInfo:
    """A container for data from `@computed_field` so that we can access it while building the pydantic-core schema.

    Attributes:
        decorator_repr: A class variable representing the decorator string, '@computed_field'.
        wrapped_property: The wrapped computed field property.
        return_type: The type of the computed field property's return value.
        alias: The alias of the property to be used during encoding and decoding.
        alias_priority: priority of the alias. This affects whether an alias generator is used
        title: Title of the computed field as in OpenAPI document, should be a short summary.
        description: Description of the computed field as in OpenAPI document.
        repr: A boolean indicating whether or not to include the field in the __repr__ output.
    """

    decorator_repr: ClassVar[str] = '@computed_field'
    wrapped_property: property
    return_type: type[Any]
    alias: str | None
    alias_priority: int | None
    title: str | None
    description: str | None
    repr: bool


# this should really be `property[T], cached_proprety[T]` but property is not generic unlike cached_property
# See https://github.com/python/typing/issues/985 and linked issues
PropertyT = typing.TypeVar('PropertyT')


@typing.overload
def computed_field(
    *,
    return_type: Any = None,
    alias: str | None = None,
    alias_priority: int | None = None,
    title: str | None = None,
    description: str | None = None,
    repr: bool = True,
) -> typing.Callable[[PropertyT], PropertyT]:
    ...


@typing.overload
def computed_field(__func: PropertyT) -> PropertyT:
    ...


def computed_field(
    __f: PropertyT | None = None,
    *,
    alias: str | None = None,
    alias_priority: int | None = None,
    title: str | None = None,
    description: str | None = None,
    repr: bool = True,
    return_type: Any = None,
) -> PropertyT | typing.Callable[[PropertyT], PropertyT]:
    """Decorator to include `property` and `cached_property` when serializing models.

    If applied to functions not yet decorated with `@property` or `@cached_property`, the function is
    automatically wrapped with `property`.

    See [Computed Fields](../usage/computed_fields.md) for more details.

    Args:
        __f: the function to wrap.
        alias: alias to use when serializing this computed field, only used when `by_alias=True`
        alias_priority: priority of the alias. This affects whether an alias generator is used
        title: Title to used when including this computed field in JSON Schema, currently unused waiting for #4697
        description: Description to used when including this computed field in JSON Schema, defaults to the functions
            docstring, currently unused waiting for #4697
        repr: whether to include this computed field in model repr
        return_type: optional return for serialization logic to expect when serializing to JSON, if included
            this must be correct, otherwise a `TypeError` is raised.
            If you don't include a return type Any is used, which does runtime introspection to handle arbitrary
            objects.

    Returns:
        A proxy wrapper for the property.
    """

    def dec(f: Any) -> Any:
        nonlocal description, return_type, alias_priority
        if description is None and f.__doc__:
            description = inspect.cleandoc(f.__doc__)

        return_type = _decorators.get_function_return_type(f, return_type)
        if return_type is None:
            raise PydanticUserError(
                'Computed field is missing return type annotation or specifying `return_type`'
                ' to the `@computed_field` decorator (e.g. `@computed_field(return_type=int|str)`)',
                code='model-field-missing-annotation',
            )

        # if the function isn't already decorated with `@property` (or another descriptor), then we wrap it now
        f = _decorators.ensure_property(f)
        alias_priority = (alias_priority or 2) if alias is not None else None
        dec_info = ComputedFieldInfo(f, return_type, alias, alias_priority, title, description, repr)
        return _decorators.PydanticDescriptorProxy(f, dec_info)

    if __f is None:
        return dec
    else:
        return dec(__f)
