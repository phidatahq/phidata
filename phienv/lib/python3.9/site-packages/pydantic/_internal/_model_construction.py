"""Private logic for creating models."""
from __future__ import annotations as _annotations

import typing
import warnings
from abc import ABCMeta
from functools import partial
from types import FunctionType
from typing import Any, Callable, Generic, Mapping

from pydantic_core import PydanticUndefined, SchemaSerializer, SchemaValidator
from typing_extensions import dataclass_transform, deprecated

from ..errors import PydanticUndefinedAnnotation, PydanticUserError
from ..fields import Field, FieldInfo, ModelPrivateAttr, PrivateAttr
from ..warnings import PydanticDeprecatedSince20
from ._config import ConfigWrapper
from ._core_utils import collect_invalid_schemas, flatten_schema_defs, inline_schema_defs
from ._decorators import ComputedFieldInfo, DecoratorInfos, PydanticDescriptorProxy
from ._discriminated_union import apply_discriminators
from ._fields import collect_model_fields, is_valid_field_name, is_valid_privateattr_name
from ._generate_schema import GenerateSchema
from ._generics import PydanticGenericMetadata, get_model_typevars_map
from ._mock_validator import set_basemodel_mock_validator
from ._schema_generation_shared import CallbackGetCoreSchemaHandler
from ._typing_extra import get_cls_types_namespace, is_classvar, parent_frame_namespace
from ._utils import ClassAttribute, is_valid_identifier

if typing.TYPE_CHECKING:
    from inspect import Signature

    from ..main import BaseModel
else:
    # See PyCharm issues https://youtrack.jetbrains.com/issue/PY-21915
    # and https://youtrack.jetbrains.com/issue/PY-51428
    DeprecationWarning = PydanticDeprecatedSince20


IGNORED_TYPES: tuple[Any, ...] = (
    FunctionType,
    property,
    classmethod,
    staticmethod,
    PydanticDescriptorProxy,
    ComputedFieldInfo,
)
object_setattr = object.__setattr__


class _ModelNamespaceDict(dict):  # type: ignore[type-arg]
    """A dictionary subclass that intercepts attribute setting on model classes and
    warns about overriding of decorators.
    """

    def __setitem__(self, k: str, v: object) -> None:
        existing: Any = self.get(k, None)
        if existing and v is not existing and isinstance(existing, PydanticDescriptorProxy):
            warnings.warn(f'`{k}` overrides an existing Pydantic `{existing.decorator_info.decorator_repr}` decorator')

        return super().__setitem__(k, v)


@dataclass_transform(kw_only_default=True, field_specifiers=(Field,))
class ModelMetaclass(ABCMeta):
    def __new__(
        mcs,
        cls_name: str,
        bases: tuple[type[Any], ...],
        namespace: dict[str, Any],
        __pydantic_generic_metadata__: PydanticGenericMetadata | None = None,
        __pydantic_reset_parent_namespace__: bool = True,
        **kwargs: Any,
    ) -> type:
        """Metaclass for creating Pydantic models.

        Args:
            cls_name: The name of the class to be created.
            bases: The base classes of the class to be created.
            namespace: The attribute dictionary of the class to be created.
            __pydantic_generic_metadata__: Metadata for generic models.
            __pydantic_reset_parent_namespace__: Reset parent namespace.
            **kwargs: Catch-all for any other keyword arguments.

        Returns:
            The new class created by the metaclass.
        """
        # Note `ModelMetaclass` refers to `BaseModel`, but is also used to *create* `BaseModel`, so we rely on the fact
        # that `BaseModel` itself won't have any bases, but any subclass of it will, to determine whether the `__new__`
        # call we're in the middle of is for the `BaseModel` class.
        if bases:
            base_field_names, class_vars, base_private_attributes = mcs._collect_bases_data(bases)

            config_wrapper = ConfigWrapper.for_model(bases, namespace, kwargs)
            namespace['model_config'] = config_wrapper.config_dict
            private_attributes = inspect_namespace(
                namespace, config_wrapper.ignored_types, class_vars, base_field_names
            )
            if private_attributes:
                if 'model_post_init' in namespace:
                    # if there are private_attributes and a model_post_init function, we handle both
                    original_model_post_init = namespace['model_post_init']

                    def wrapped_model_post_init(self: BaseModel, __context: Any) -> None:
                        """We need to both initialize private attributes and call the user-defined model_post_init
                        method.
                        """
                        init_private_attributes(self, __context)
                        original_model_post_init(self, __context)

                    namespace['model_post_init'] = wrapped_model_post_init
                else:
                    namespace['model_post_init'] = init_private_attributes

            namespace['__class_vars__'] = class_vars
            namespace['__private_attributes__'] = {**base_private_attributes, **private_attributes}

            if '__hash__' not in namespace and config_wrapper.frozen:

                def hash_func(self: Any) -> int:
                    return hash(self.__class__) + hash(tuple(self.__dict__.values()))

                namespace['__hash__'] = hash_func

            cls: type[BaseModel] = super().__new__(mcs, cls_name, bases, namespace, **kwargs)  # type: ignore

            from ..main import BaseModel

            cls.__pydantic_custom_init__ = not getattr(cls.__init__, '__pydantic_base_init__', False)
            cls.__pydantic_post_init__ = None if cls.model_post_init is BaseModel.model_post_init else 'model_post_init'

            cls.__pydantic_decorators__ = DecoratorInfos.build(cls)

            # Use the getattr below to grab the __parameters__ from the `typing.Generic` parent class
            if __pydantic_generic_metadata__:
                cls.__pydantic_generic_metadata__ = __pydantic_generic_metadata__
            else:
                parameters = getattr(cls, '__parameters__', ())
                parent_parameters = getattr(cls, '__pydantic_generic_metadata__', {}).get('parameters', ())
                if parameters and parent_parameters and not all(x in parameters for x in parent_parameters):
                    combined_parameters = parent_parameters + tuple(x for x in parameters if x not in parent_parameters)
                    parameters_str = ', '.join([str(x) for x in combined_parameters])
                    error_message = (
                        f'All parameters must be present on typing.Generic;'
                        f' you should inherit from typing.Generic[{parameters_str}]'
                    )
                    if Generic not in bases:  # pragma: no cover
                        # This branch will only be hit if I have misunderstood how `__parameters__` works.
                        # If that is the case, and a user hits this, I could imagine it being very helpful
                        # to have this extra detail in the reported traceback.
                        error_message += f' (bases={bases})'
                    raise TypeError(error_message)

                cls.__pydantic_generic_metadata__ = {
                    'origin': None,
                    'args': (),
                    'parameters': parameters,
                }

            cls.__pydantic_complete__ = False  # Ensure this specific class gets completed

            # preserve `__set_name__` protocol defined in https://peps.python.org/pep-0487
            # for attributes not in `new_namespace` (e.g. private attributes)
            for name, obj in private_attributes.items():
                obj.__set_name__(cls, name)

            if __pydantic_reset_parent_namespace__:
                cls.__pydantic_parent_namespace__ = parent_frame_namespace()
            parent_namespace = getattr(cls, '__pydantic_parent_namespace__', None)

            types_namespace = get_cls_types_namespace(cls, parent_namespace)
            set_model_fields(cls, bases, config_wrapper, types_namespace)
            complete_model_class(
                cls,
                cls_name,
                config_wrapper,
                raise_errors=False,
                types_namespace=types_namespace,
            )
            # using super(cls, cls) on the next line ensures we only call the parent class's __pydantic_init_subclass__
            # I believe the `type: ignore` is only necessary because mypy doesn't realize that this code branch is
            # only hit for _proper_ subclasses of BaseModel
            super(cls, cls).__pydantic_init_subclass__(**kwargs)  # type: ignore[misc]
            return cls
        else:
            # this is the BaseModel class itself being created, no logic required
            return super().__new__(mcs, cls_name, bases, namespace, **kwargs)

    def __getattr__(self, item: str) -> Any:
        """This is necessary to keep attribute access working for class attribute access."""
        private_attributes = self.__dict__.get('__private_attributes__')
        if private_attributes and item in private_attributes:
            return private_attributes[item]
        raise AttributeError(item)

    @classmethod
    def __prepare__(cls, *args: Any, **kwargs: Any) -> Mapping[str, object]:
        return _ModelNamespaceDict()

    def __instancecheck__(self, instance: Any) -> bool:
        """Avoid calling ABC _abc_subclasscheck unless we're pretty sure.

        See #3829 and python/cpython#92810
        """
        return hasattr(instance, '__pydantic_validator__') and super().__instancecheck__(instance)

    @staticmethod
    def _collect_bases_data(bases: tuple[type[Any], ...]) -> tuple[set[str], set[str], dict[str, ModelPrivateAttr]]:
        from ..main import BaseModel

        field_names: set[str] = set()
        class_vars: set[str] = set()
        private_attributes: dict[str, ModelPrivateAttr] = {}
        for base in bases:
            if issubclass(base, BaseModel) and base is not BaseModel:
                # model_fields might not be defined yet in the case of generics, so we use getattr here:
                field_names.update(getattr(base, 'model_fields', {}).keys())
                class_vars.update(base.__class_vars__)
                private_attributes.update(base.__private_attributes__)
        return field_names, class_vars, private_attributes

    @property
    @deprecated(
        'The `__fields__` attribute is deprecated, use `model_fields` instead.', category=PydanticDeprecatedSince20
    )
    def __fields__(self) -> dict[str, FieldInfo]:
        warnings.warn('The `__fields__` attribute is deprecated, use `model_fields` instead.', DeprecationWarning)
        return self.model_fields


def init_private_attributes(self: BaseModel, __context: Any) -> None:
    """This function is meant to behave like a BaseModel method to initialise private attributes.

    It takes context as an argument since that's what pydantic-core passes when calling it.

    Args:
        self: The BaseModel instance.
        __context: The context.
    """
    pydantic_private = {}
    for name, private_attr in self.__private_attributes__.items():
        default = private_attr.get_default()
        if default is not PydanticUndefined:
            pydantic_private[name] = default
    object_setattr(self, '__pydantic_private__', pydantic_private)


def inspect_namespace(  # noqa C901
    namespace: dict[str, Any],
    ignored_types: tuple[type[Any], ...],
    base_class_vars: set[str],
    base_class_fields: set[str],
) -> dict[str, ModelPrivateAttr]:
    """Iterate over the namespace and:
    * gather private attributes
    * check for items which look like fields but are not (e.g. have no annotation) and warn.

    Args:
        namespace: The attribute dictionary of the class to be created.
        ignored_types: A tuple of ignore types.
        base_class_vars: A set of base class class variables.
        base_class_fields: A set of base class fields.

    Returns:
        A dict contains private attributes info.

    Raises:
        TypeError: If there is a `__root__` field in model.
        NameError: If private attribute name is invalid.
        PydanticUserError:
            - If a field does not have a type annotation.
            - If a field on base class was overridden by a non-annotated attribute.
    """
    all_ignored_types = ignored_types + IGNORED_TYPES

    private_attributes: dict[str, ModelPrivateAttr] = {}
    raw_annotations = namespace.get('__annotations__', {})

    if '__root__' in raw_annotations or '__root__' in namespace:
        raise TypeError("To define root models, use `pydantic.RootModel` rather than a field called '__root__'")

    ignored_names: set[str] = set()
    for var_name, value in list(namespace.items()):
        if var_name == 'model_config':
            continue
        elif (
            isinstance(value, type)
            and value.__module__ == namespace['__module__']
            and value.__qualname__.startswith(namespace['__qualname__'])
        ):
            # `value` is a nested type defined in this namespace; don't error
            continue
        elif isinstance(value, all_ignored_types) or value.__class__.__module__ == 'functools':
            ignored_names.add(var_name)
            continue
        elif isinstance(value, ModelPrivateAttr):
            if var_name.startswith('__'):
                raise NameError(
                    f'Private attributes "{var_name}" must not have dunder names; '
                    'use a single underscore prefix instead.'
                )
            elif is_valid_field_name(var_name):
                raise NameError(
                    f'Private attributes "{var_name}" must not be a valid field name; '
                    f'use sunder names, e.g. "_{var_name}"'
                )
            private_attributes[var_name] = value
            del namespace[var_name]
        elif var_name.startswith('__'):
            continue
        elif is_valid_privateattr_name(var_name):
            if var_name not in raw_annotations or not is_classvar(raw_annotations[var_name]):
                private_attributes[var_name] = PrivateAttr(default=value)
                del namespace[var_name]
        elif var_name in base_class_vars:
            continue
        elif var_name not in raw_annotations:
            if var_name in base_class_fields:
                raise PydanticUserError(
                    f'Field {var_name!r} defined on a base class was overridden by a non-annotated attribute. '
                    f'All field definitions, including overrides, require a type annotation.',
                    code='model-field-overridden',
                )
            elif isinstance(value, FieldInfo):
                raise PydanticUserError(
                    f'Field {var_name!r} requires a type annotation', code='model-field-missing-annotation'
                )
            else:
                raise PydanticUserError(
                    f"A non-annotated attribute was detected: `{var_name} = {value!r}`. All model fields require a "
                    f"type annotation; if `{var_name}` is not meant to be a field, you may be able to resolve this "
                    f"error by annotating it as a `ClassVar` or updating `model_config['ignored_types']`.",
                    code='model-field-missing-annotation',
                )

    for ann_name, ann_type in raw_annotations.items():
        if (
            is_valid_privateattr_name(ann_name)
            and ann_name not in private_attributes
            and ann_name not in ignored_names
            and not is_classvar(ann_type)
            and ann_type not in all_ignored_types
            and getattr(ann_type, '__module__', None) != 'functools'
        ):
            private_attributes[ann_name] = PrivateAttr()

    return private_attributes


def set_model_fields(
    cls: type[BaseModel], bases: tuple[type[Any], ...], config_wrapper: ConfigWrapper, types_namespace: dict[str, Any]
) -> None:
    """Collect and set `cls.model_fields` and `cls.__class_vars__`.

    Args:
        cls: BaseModel or dataclass.
        bases: Parents of the class, generally `cls.__bases__`.
        config_wrapper: The config wrapper instance.
        types_namespace: Optional extra namespace to look for types in.
    """
    typevars_map = get_model_typevars_map(cls)
    fields, class_vars = collect_model_fields(cls, bases, config_wrapper, types_namespace, typevars_map=typevars_map)

    cls.model_fields = fields
    cls.__class_vars__.update(class_vars)

    for k in class_vars:
        # Class vars should not be private attributes
        #     We remove them _here_ and not earlier because we rely on inspecting the class to determine its classvars,
        #     but private attributes are determined by inspecting the namespace _prior_ to class creation.
        #     In the case that a classvar with a leading-'_' is defined via a ForwardRef (e.g., when using
        #     `__future__.annotations`), we want to remove the private attribute which was detected _before_ we knew it
        #     evaluated to a classvar

        value = cls.__private_attributes__.pop(k, None)
        if value is not None and value.default is not PydanticUndefined:
            setattr(cls, k, value.default)


def complete_model_class(
    cls: type[BaseModel],
    cls_name: str,
    config_wrapper: ConfigWrapper,
    *,
    raise_errors: bool = True,
    types_namespace: dict[str, Any] | None,
) -> bool:
    """Finish building a model class.

    This logic must be called after class has been created since validation functions must be bound
    and `get_type_hints` requires a class object.

    Args:
        cls: BaseModel or dataclass.
        cls_name: The model or dataclass name.
        config_wrapper: The config wrapper instance.
        raise_errors: Whether to raise errors.
        types_namespace: Optional extra namespace to look for types in.

    Returns:
        `True` if the model is successfully completed, else `False`.

    Raises:
        PydanticUndefinedAnnotation: If `PydanticUndefinedAnnotation` occurs in`__get_pydantic_core_schema__`
            and `raise_errors=True`.
    """
    typevars_map = get_model_typevars_map(cls)
    gen_schema = GenerateSchema(
        config_wrapper,
        types_namespace,
        typevars_map,
    )

    handler = CallbackGetCoreSchemaHandler(
        partial(gen_schema.generate_schema, from_dunder_get_core_schema=False),
        gen_schema,
        ref_mode='unpack',
    )

    try:
        schema = cls.__get_pydantic_core_schema__(cls, handler)
    except PydanticUndefinedAnnotation as e:
        if raise_errors:
            raise
        set_basemodel_mock_validator(cls, cls_name, f'`{e.name}`')
        return False

    core_config = config_wrapper.core_config(cls)

    schema = gen_schema.collect_definitions(schema)
    schema = apply_discriminators(flatten_schema_defs(schema))
    if collect_invalid_schemas(schema):
        set_basemodel_mock_validator(cls, cls_name, 'all referenced types')
        return False

    # debug(schema)
    cls.__pydantic_core_schema__ = schema
    simplified_core_schema = inline_schema_defs(schema)
    cls.__pydantic_validator__ = SchemaValidator(simplified_core_schema, core_config)
    cls.__pydantic_serializer__ = SchemaSerializer(simplified_core_schema, core_config)
    cls.__pydantic_complete__ = True

    # set __signature__ attr only for model class, but not for its instances
    cls.__signature__ = ClassAttribute(
        '__signature__', generate_model_signature(cls.__init__, cls.model_fields, config_wrapper)
    )
    return True


def generate_model_signature(
    init: Callable[..., None], fields: dict[str, FieldInfo], config_wrapper: ConfigWrapper
) -> Signature:
    """Generate signature for model based on its fields.

    Args:
        init: The class init.
        fields: The model fields.
        config_wrapper: The config wrapper instance.

    Returns:
        The model signature.
    """
    from inspect import Parameter, Signature, signature
    from itertools import islice

    present_params = signature(init).parameters.values()
    merged_params: dict[str, Parameter] = {}
    var_kw = None
    use_var_kw = False

    for param in islice(present_params, 1, None):  # skip self arg
        # inspect does "clever" things to show annotations as strings because we have
        # `from __future__ import annotations` in main, we don't want that
        if param.annotation == 'Any':
            param = param.replace(annotation=Any)
        if param.kind is param.VAR_KEYWORD:
            var_kw = param
            continue
        merged_params[param.name] = param

    if var_kw:  # if custom init has no var_kw, fields which are not declared in it cannot be passed through
        allow_names = config_wrapper.populate_by_name
        for field_name, field in fields.items():
            # when alias is a str it should be used for signature generation
            if isinstance(field.alias, str):
                param_name = field.alias
            else:
                param_name = field_name

            if field_name in merged_params or param_name in merged_params:
                continue

            if not is_valid_identifier(param_name):
                if allow_names and is_valid_identifier(field_name):
                    param_name = field_name
                else:
                    use_var_kw = True
                    continue

            kwargs = {} if field.is_required() else {'default': field.get_default(call_default_factory=False)}
            merged_params[param_name] = Parameter(
                param_name, Parameter.KEYWORD_ONLY, annotation=field.rebuild_annotation(), **kwargs
            )

    if config_wrapper.extra == 'allow':
        use_var_kw = True

    if var_kw and use_var_kw:
        # Make sure the parameter for extra kwargs
        # does not have the same name as a field
        default_model_signature = [
            ('__pydantic_self__', Parameter.POSITIONAL_OR_KEYWORD),
            ('data', Parameter.VAR_KEYWORD),
        ]
        if [(p.name, p.kind) for p in present_params] == default_model_signature:
            # if this is the standard model signature, use extra_data as the extra args name
            var_kw_name = 'extra_data'
        else:
            # else start from var_kw
            var_kw_name = var_kw.name

        # generate a name that's definitely unique
        while var_kw_name in fields:
            var_kw_name += '_'
        merged_params[var_kw_name] = var_kw.replace(name=var_kw_name)

    return Signature(parameters=list(merged_params.values()), return_annotation=None)
