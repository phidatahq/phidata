# Copied from pydantic 1.9.2 (the latest version to support python 3.6.)
# https://github.com/pydantic/pydantic/blob/v1.9.2/pydantic/typing.py
# mypy: ignore-errors

import sys
from os import PathLike
from typing import (
    TYPE_CHECKING,
    AbstractSet,
    Any,
    ClassVar,
    Dict,
    Generator,
    List,
    Mapping,
    NewType,
    Optional,
    Sequence,
    Set,
    Tuple,
    Type,
    Union,
    _eval_type,
    cast,
    get_type_hints,
)

from typing_extensions import Annotated, Literal

try:
    from typing import _TypingBase as typing_base  # type: ignore
except ImportError:
    from typing import _Final as typing_base  # type: ignore

try:
    from typing import GenericAlias as TypingGenericAlias  # type: ignore
except ImportError:
    # python < 3.9 does not have GenericAlias (list[int], tuple[str, ...] and so on)
    TypingGenericAlias = ()

try:
    from types import UnionType as TypesUnionType  # type: ignore
except ImportError:
    # python < 3.10 does not have UnionType (str | int, byte | bool and so on)
    TypesUnionType = ()


if sys.version_info < (3, 7):
    if TYPE_CHECKING:

        class ForwardRef:
            def __init__(self, arg: Any):
                pass

            def _eval_type(self, globalns: Any, localns: Any) -> Any:
                pass

    else:
        from typing import _ForwardRef as ForwardRef
else:
    from typing import ForwardRef


if sys.version_info < (3, 7):

    def evaluate_forwardref(type_: ForwardRef, globalns: Any, localns: Any) -> Any:
        return type_._eval_type(globalns, localns)

elif sys.version_info < (3, 9):

    def evaluate_forwardref(type_: ForwardRef, globalns: Any, localns: Any) -> Any:
        return type_._evaluate(globalns, localns)

else:

    def evaluate_forwardref(type_: ForwardRef, globalns: Any, localns: Any) -> Any:
        # Even though it is the right signature for python 3.9, mypy complains with
        # `error: Too many arguments for "_evaluate" of "ForwardRef"` hence the cast...
        return cast(Any, type_)._evaluate(globalns, localns, set())


if sys.version_info < (3, 9):
    # Ensure we always get all the whole `Annotated` hint, not just the annotated type.
    # For 3.6 to 3.8, `get_type_hints` doesn't recognize `typing_extensions.Annotated`,
    # so it already returns the full annotation
    get_all_type_hints = get_type_hints

else:

    def get_all_type_hints(obj: Any, globalns: Any = None, localns: Any = None) -> Any:
        return get_type_hints(obj, globalns, localns, include_extras=True)


if sys.version_info < (3, 7):
    from typing import Callable as Callable

    AnyCallable = Callable[..., Any]
    NoArgAnyCallable = Callable[[], Any]
else:
    from collections.abc import Callable as Callable
    from typing import Callable as TypingCallable

    AnyCallable = TypingCallable[..., Any]
    NoArgAnyCallable = TypingCallable[[], Any]


# Annotated[...] is implemented by returning an instance of one of these classes, depending on
# python/typing_extensions version.
AnnotatedTypeNames = {"AnnotatedMeta", "_AnnotatedAlias"}


if sys.version_info < (3, 8):

    def get_origin(t: Type[Any]) -> Optional[Type[Any]]:
        if type(t).__name__ in AnnotatedTypeNames:
            return cast(
                Type[Any], Annotated
            )  # mypy complains about _SpecialForm in py3.6
        return getattr(t, "__origin__", None)

else:
    from typing import get_origin as _typing_get_origin

    def get_origin(tp: Type[Any]) -> Optional[Type[Any]]:
        """
        We can't directly use `typing.get_origin` since we need a fallback to support
        custom generic classes like `ConstrainedList`
        It should be useless once https://github.com/cython/cython/issues/3537 is
        solved and https://github.com/samuelcolvin/pydantic/pull/1753 is merged.
        """
        if type(tp).__name__ in AnnotatedTypeNames:
            return cast(Type[Any], Annotated)  # mypy complains about _SpecialForm
        return _typing_get_origin(tp) or getattr(tp, "__origin__", None)


if sys.version_info < (3, 7):  # noqa: C901 (ignore complexity)

    def get_args(t: Type[Any]) -> Tuple[Any, ...]:
        """Simplest get_args compatibility layer possible.

        The Python 3.6 typing module does not have `_GenericAlias` so
        this won't work for everything. In particular this will not
        support the `generics` module (we don't support generic models in
        python 3.6).

        """
        if type(t).__name__ in AnnotatedTypeNames:
            return t.__args__ + t.__metadata__
        return getattr(t, "__args__", ())

elif sys.version_info < (3, 8):  # noqa: C901
    from typing import _GenericAlias

    def get_args(t: Type[Any]) -> Tuple[Any, ...]:
        """Compatibility version of get_args for python 3.7.

        Mostly compatible with the python 3.8 `typing` module version
        and able to handle almost all use cases.
        """
        if type(t).__name__ in AnnotatedTypeNames:
            return t.__args__ + t.__metadata__
        if isinstance(t, _GenericAlias):
            res = t.__args__
            if t.__origin__ is Callable and res and res[0] is not Ellipsis:
                res = (list(res[:-1]), res[-1])
            return res
        return getattr(t, "__args__", ())

else:
    from typing import get_args as _typing_get_args

    def _generic_get_args(tp: Type[Any]) -> Tuple[Any, ...]:
        """
        In python 3.9, `typing.Dict`, `typing.List`, ...
        do have an empty `__args__` by default (instead of the generic ~T for example).
        In order to still support `Dict` for example and consider it as `Dict[Any, Any]`,
        we retrieve the `_nparams` value that tells us how many parameters it needs.
        """
        if hasattr(tp, "_nparams"):
            return (Any,) * tp._nparams
        return ()

    def get_args(tp: Type[Any]) -> Tuple[Any, ...]:
        """Get type arguments with all substitutions performed.

        For unions, basic simplifications used by Union constructor are performed.
        Examples::
            get_args(Dict[str, int]) == (str, int)
            get_args(int) == ()
            get_args(Union[int, Union[T, int], str][int]) == (int, str)
            get_args(Union[int, Tuple[T, int]][str]) == (int, Tuple[str, int])
            get_args(Callable[[], T][int]) == ([], int)
        """
        if type(tp).__name__ in AnnotatedTypeNames:
            return tp.__args__ + tp.__metadata__
        # the fallback is needed for the same reasons as `get_origin` (see above)
        return (
            _typing_get_args(tp) or getattr(tp, "__args__", ()) or _generic_get_args(tp)
        )


if sys.version_info < (3, 9):

    def convert_generics(tp: Type[Any]) -> Type[Any]:
        """Python 3.9 and older only supports generics from `typing` module.
        They convert strings to ForwardRef automatically.

        Examples::
            typing.List['Hero'] == typing.List[ForwardRef('Hero')]
        """
        return tp

else:
    from typing import _UnionGenericAlias  # type: ignore

    from typing_extensions import _AnnotatedAlias

    def convert_generics(tp: Type[Any]) -> Type[Any]:
        """
        Recursively searches for `str` type hints and replaces them with ForwardRef.

        Examples::
            convert_generics(list['Hero']) == list[ForwardRef('Hero')]
            convert_generics(dict['Hero', 'Team']) == dict[ForwardRef('Hero'), ForwardRef('Team')]
            convert_generics(typing.Dict['Hero', 'Team']) == typing.Dict[ForwardRef('Hero'), ForwardRef('Team')]
            convert_generics(list[str | 'Hero'] | int) == list[str | ForwardRef('Hero')] | int
        """
        origin = get_origin(tp)
        if not origin or not hasattr(tp, "__args__"):
            return tp

        args = get_args(tp)

        # typing.Annotated needs special treatment
        if origin is Annotated:
            return _AnnotatedAlias(convert_generics(args[0]), args[1:])

        # recursively replace `str` instances inside of `GenericAlias` with `ForwardRef(arg)`
        converted = tuple(
            ForwardRef(arg)
            if isinstance(arg, str) and isinstance(tp, TypingGenericAlias)
            else convert_generics(arg)
            for arg in args
        )

        if converted == args:
            return tp
        elif isinstance(tp, TypingGenericAlias):
            return TypingGenericAlias(origin, converted)
        elif isinstance(tp, TypesUnionType):
            # recreate types.UnionType (PEP604, Python >= 3.10)
            return _UnionGenericAlias(origin, converted)
        else:
            try:
                setattr(tp, "__args__", converted)  # noqa: B010
            except AttributeError:
                pass
            return tp


if sys.version_info < (3, 10):

    def is_union(tp: Optional[Type[Any]]) -> bool:
        return tp is Union

    WithArgsTypes = (TypingGenericAlias,)

else:
    import types
    import typing

    def is_union(tp: Optional[Type[Any]]) -> bool:
        return tp is Union or tp is types.UnionType  # noqa: E721

    WithArgsTypes = (typing._GenericAlias, types.GenericAlias, types.UnionType)


if sys.version_info < (3, 9):
    StrPath = Union[str, PathLike]
else:
    StrPath = Union[str, PathLike]
    # TODO: Once we switch to Cython 3 to handle generics properly
    #  (https://github.com/cython/cython/issues/2753), use following lines instead
    #  of the one above
    # # os.PathLike only becomes subscriptable from Python 3.9 onwards
    # StrPath = Union[str, PathLike[str]]


if TYPE_CHECKING:
    # Only in Pydantic
    # from .fields import ModelField

    TupleGenerator = Generator[Tuple[str, Any], None, None]
    DictStrAny = Dict[str, Any]
    DictAny = Dict[Any, Any]
    SetStr = Set[str]
    ListStr = List[str]
    IntStr = Union[int, str]
    AbstractSetIntStr = AbstractSet[IntStr]
    DictIntStrAny = Dict[IntStr, Any]
    MappingIntStrAny = Mapping[IntStr, Any]
    CallableGenerator = Generator[AnyCallable, None, None]
    ReprArgs = Sequence[Tuple[Optional[str], Any]]
    AnyClassMethod = classmethod[Any]

__all__ = (
    "ForwardRef",
    "Callable",
    "AnyCallable",
    "NoArgAnyCallable",
    "NoneType",
    "is_none_type",
    "display_as_type",
    "resolve_annotations",
    "is_callable_type",
    "is_literal_type",
    "all_literal_values",
    "is_namedtuple",
    "is_typeddict",
    "is_new_type",
    "new_type_supertype",
    "is_classvar",
    "update_field_forward_refs",
    "update_model_forward_refs",
    "TupleGenerator",
    "DictStrAny",
    "DictAny",
    "SetStr",
    "ListStr",
    "IntStr",
    "AbstractSetIntStr",
    "DictIntStrAny",
    "CallableGenerator",
    "ReprArgs",
    "AnyClassMethod",
    "CallableGenerator",
    "WithArgsTypes",
    "get_args",
    "get_origin",
    "get_sub_types",
    "typing_base",
    "get_all_type_hints",
    "is_union",
    "StrPath",
)


NoneType = None.__class__


NONE_TYPES: Tuple[Any, Any, Any] = (None, NoneType, Literal[None])


if sys.version_info < (3, 8):
    # Even though this implementation is slower, we need it for python 3.6/3.7:
    # In python 3.6/3.7 "Literal" is not a builtin type and uses a different
    # mechanism.
    # for this reason `Literal[None] is Literal[None]` evaluates to `False`,
    # breaking the faster implementation used for the other python versions.

    def is_none_type(type_: Any) -> bool:
        return type_ in NONE_TYPES

elif sys.version_info[:2] == (3, 8):
    # We can use the fast implementation for 3.8 but there is a very weird bug
    # where it can fail for `Literal[None]`.
    # We just need to redefine a useless `Literal[None]` inside the function body to fix this

    def is_none_type(type_: Any) -> bool:
        Literal[None]  # fix edge case
        for none_type in NONE_TYPES:
            if type_ is none_type:
                return True
        return False

else:

    def is_none_type(type_: Any) -> bool:
        for none_type in NONE_TYPES:
            if type_ is none_type:
                return True
        return False


def display_as_type(v: Type[Any]) -> str:
    if (
        not isinstance(v, typing_base)
        and not isinstance(v, WithArgsTypes)
        and not isinstance(v, type)
    ):
        v = v.__class__

    if is_union(get_origin(v)):
        return f'Union[{", ".join(map(display_as_type, get_args(v)))}]'

    if isinstance(v, WithArgsTypes):
        # Generic alias are constructs like `list[int]`
        return str(v).replace("typing.", "")

    try:
        return v.__name__
    except AttributeError:
        # happens with typing objects
        return str(v).replace("typing.", "")


def resolve_annotations(
    raw_annotations: Dict[str, Type[Any]], module_name: Optional[str]
) -> Dict[str, Type[Any]]:
    """
    Partially taken from typing.get_type_hints.

    Resolve string or ForwardRef annotations into type objects if possible.
    """
    base_globals: Optional[Dict[str, Any]] = None
    if module_name:
        try:
            module = sys.modules[module_name]
        except KeyError:
            # happens occasionally, see https://github.com/samuelcolvin/pydantic/issues/2363
            pass
        else:
            base_globals = module.__dict__

    annotations = {}
    for name, value in raw_annotations.items():
        if isinstance(value, str):
            if (3, 10) > sys.version_info >= (3, 9, 8) or sys.version_info >= (
                3,
                10,
                1,
            ):
                value = ForwardRef(value, is_argument=False, is_class=True)
            elif sys.version_info >= (3, 7):
                value = ForwardRef(value, is_argument=False)
            else:
                value = ForwardRef(value)
        try:
            value = _eval_type(value, base_globals, None)
        except NameError:
            # this is ok, it can be fixed with update_forward_refs
            pass
        annotations[name] = value
    return annotations


def is_callable_type(type_: Type[Any]) -> bool:
    return type_ is Callable or get_origin(type_) is Callable


if sys.version_info >= (3, 7):

    def is_literal_type(type_: Type[Any]) -> bool:
        return Literal is not None and get_origin(type_) is Literal

    def literal_values(type_: Type[Any]) -> Tuple[Any, ...]:
        return get_args(type_)

else:

    def is_literal_type(type_: Type[Any]) -> bool:
        return (
            Literal is not None
            and hasattr(type_, "__values__")
            and type_ == Literal[type_.__values__]
        )

    def literal_values(type_: Type[Any]) -> Tuple[Any, ...]:
        return type_.__values__


def all_literal_values(type_: Type[Any]) -> Tuple[Any, ...]:
    """
    This method is used to retrieve all Literal values as
    Literal can be used recursively (see https://www.python.org/dev/peps/pep-0586)
    e.g. `Literal[Literal[Literal[1, 2, 3], "foo"], 5, None]`
    """
    if not is_literal_type(type_):
        return (type_,)

    values = literal_values(type_)
    return tuple(x for value in values for x in all_literal_values(value))


def is_namedtuple(type_: Type[Any]) -> bool:
    """
    Check if a given class is a named tuple.
    It can be either a `typing.NamedTuple` or `collections.namedtuple`
    """
    from .utils import lenient_issubclass

    return lenient_issubclass(type_, tuple) and hasattr(type_, "_fields")


def is_typeddict(type_: Type[Any]) -> bool:
    """
    Check if a given class is a typed dict (from `typing` or `typing_extensions`)
    In 3.10, there will be a public method (https://docs.python.org/3.10/library/typing.html#typing.is_typeddict)
    """
    from .utils import lenient_issubclass

    return lenient_issubclass(type_, dict) and hasattr(type_, "__total__")


test_type = NewType("test_type", str)


def is_new_type(type_: Type[Any]) -> bool:
    """
    Check whether type_ was created using typing.NewType
    """
    return isinstance(type_, test_type.__class__) and hasattr(type_, "__supertype__")  # type: ignore


def new_type_supertype(type_: Type[Any]) -> Type[Any]:
    while hasattr(type_, "__supertype__"):
        type_ = type_.__supertype__
    return type_


def _check_classvar(v: Optional[Type[Any]]) -> bool:
    if v is None:
        return False

    return v.__class__ == ClassVar.__class__ and (
        sys.version_info < (3, 7) or getattr(v, "_name", None) == "ClassVar"
    )


def is_classvar(ann_type: Type[Any]) -> bool:
    if _check_classvar(ann_type) or _check_classvar(get_origin(ann_type)):
        return True

    # this is an ugly workaround for class vars that contain forward references and are therefore themselves
    # forward references, see #3679
    if ann_type.__class__ == ForwardRef and ann_type.__forward_arg__.startswith(
        "ClassVar["
    ):
        return True

    return False


# Only in Pydantic
# def update_field_forward_refs(field: "ModelField", globalns: Any, localns: Any) -> None:
#     """
#     Try to update ForwardRefs on fields based on this ModelField, globalns and localns.
#     """
#     if field.type_.__class__ == ForwardRef:
#         field.type_ = evaluate_forwardref(field.type_, globalns, localns or None)
#         field.prepare()

#     if field.sub_fields:
#         for sub_f in field.sub_fields:
#             update_field_forward_refs(sub_f, globalns=globalns, localns=localns)

#     if field.discriminator_key is not None:
#         field.prepare_discriminated_union_sub_fields()


# Only in Pydantic
# def update_model_forward_refs(
#     model: Type[Any],
#     fields: Iterable["ModelField"],
#     json_encoders: Dict[Union[Type[Any], str], AnyCallable],
#     localns: "DictStrAny",
#     exc_to_suppress: Tuple[Type[BaseException], ...] = (),
# ) -> None:
#     """
#     Try to update model fields ForwardRefs based on model and localns.
#     """
#     if model.__module__ in sys.modules:
#         globalns = sys.modules[model.__module__].__dict__.copy()
#     else:
#         globalns = {}

#     globalns.setdefault(model.__name__, model)

#     for f in fields:
#         try:
#             update_field_forward_refs(f, globalns=globalns, localns=localns)
#         except exc_to_suppress:
#             pass

#     for key in set(json_encoders.keys()):
#         if isinstance(key, str):
#             fr: ForwardRef = ForwardRef(key)
#         elif isinstance(key, ForwardRef):
#             fr = key
#         else:
#             continue

#         try:
#             new_key = evaluate_forwardref(fr, globalns, localns or None)
#         except exc_to_suppress:  # pragma: no cover
#             continue

#         json_encoders[new_key] = json_encoders.pop(key)


def get_class(type_: Type[Any]) -> Union[None, bool, Type[Any]]:
    """
    Tries to get the class of a Type[T] annotation. Returns True if Type is used
    without brackets. Otherwise returns None.
    """
    try:
        origin = get_origin(type_)
        if origin is None:  # Python 3.6
            origin = type_
        if issubclass(origin, Type):  # type: ignore
            if not get_args(type_) or not isinstance(get_args(type_)[0], type):
                return True
            return get_args(type_)[0]
    except (AttributeError, TypeError):
        pass
    return None


def get_sub_types(tp: Any) -> List[Any]:
    """
    Return all the types that are allowed by type `tp`
    `tp` can be a `Union` of allowed types or an `Annotated` type
    """
    origin = get_origin(tp)
    if origin is Annotated:
        return get_sub_types(get_args(tp)[0])
    elif is_union(origin):
        return [x for t in get_args(tp) for x in get_sub_types(t)]
    else:
        return [tp]
