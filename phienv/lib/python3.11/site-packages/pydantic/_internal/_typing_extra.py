"""Logic for interacting with type annotations, mostly extensions, shims and hacks to wrap python's typing module."""

from __future__ import annotations as _annotations

import dataclasses
import re
import sys
import types
import typing
import warnings
from collections.abc import Callable
from functools import partial
from types import GetSetDescriptorType
from typing import TYPE_CHECKING, Any, Final, Iterable

from typing_extensions import Annotated, Literal, TypeAliasType, TypeGuard, deprecated, get_args, get_origin

if TYPE_CHECKING:
    from ._dataclasses import StandardDataclass

try:
    from typing import _TypingBase  # type: ignore[attr-defined]
except ImportError:
    from typing import _Final as _TypingBase  # type: ignore[attr-defined]

typing_base = _TypingBase


if sys.version_info < (3, 9):
    # python < 3.9 does not have GenericAlias (list[int], tuple[str, ...] and so on)
    TypingGenericAlias = ()
else:
    from typing import GenericAlias as TypingGenericAlias  # type: ignore


if sys.version_info < (3, 11):
    from typing_extensions import NotRequired, Required
else:
    from typing import NotRequired, Required  # noqa: F401


if sys.version_info < (3, 10):

    def origin_is_union(tp: type[Any] | None) -> bool:
        return tp is typing.Union

    WithArgsTypes = (TypingGenericAlias,)

else:

    def origin_is_union(tp: type[Any] | None) -> bool:
        return tp is typing.Union or tp is types.UnionType

    WithArgsTypes = typing._GenericAlias, types.GenericAlias, types.UnionType  # type: ignore[attr-defined]


if sys.version_info < (3, 10):
    NoneType = type(None)
    EllipsisType = type(Ellipsis)
else:
    from types import NoneType as NoneType


LITERAL_TYPES: set[Any] = {Literal}
if hasattr(typing, 'Literal'):
    LITERAL_TYPES.add(typing.Literal)  # type: ignore

# Check if `deprecated` is a type to prevent errors when using typing_extensions < 4.9.0
DEPRECATED_TYPES: tuple[Any, ...] = (deprecated,) if isinstance(deprecated, type) else ()
if hasattr(warnings, 'deprecated'):
    DEPRECATED_TYPES = (*DEPRECATED_TYPES, warnings.deprecated)  # type: ignore

NONE_TYPES: tuple[Any, ...] = (None, NoneType, *(tp[None] for tp in LITERAL_TYPES))


TypeVarType = Any  # since mypy doesn't allow the use of TypeVar as a type


def is_none_type(type_: Any) -> bool:
    return type_ in NONE_TYPES


def is_callable_type(type_: type[Any]) -> bool:
    return type_ is Callable or get_origin(type_) is Callable


def is_literal_type(type_: type[Any]) -> bool:
    return Literal is not None and get_origin(type_) in LITERAL_TYPES


def is_deprecated_instance(instance: Any) -> TypeGuard[deprecated]:
    return isinstance(instance, DEPRECATED_TYPES)


def literal_values(type_: type[Any]) -> tuple[Any, ...]:
    return get_args(type_)


def all_literal_values(type_: type[Any]) -> list[Any]:
    """This method is used to retrieve all Literal values as
    Literal can be used recursively (see https://www.python.org/dev/peps/pep-0586)
    e.g. `Literal[Literal[Literal[1, 2, 3], "foo"], 5, None]`.
    """
    if not is_literal_type(type_):
        return [type_]

    values = literal_values(type_)
    return [x for value in values for x in all_literal_values(value)]


def is_annotated(ann_type: Any) -> bool:
    return get_origin(ann_type) is Annotated


def annotated_type(type_: Any) -> Any | None:
    return get_args(type_)[0] if is_annotated(type_) else None


def is_namedtuple(type_: type[Any]) -> bool:
    """Check if a given class is a named tuple.
    It can be either a `typing.NamedTuple` or `collections.namedtuple`.
    """
    from ._utils import lenient_issubclass

    return lenient_issubclass(type_, tuple) and hasattr(type_, '_fields')


test_new_type = typing.NewType('test_new_type', str)


def is_new_type(type_: type[Any]) -> bool:
    """Check whether type_ was created using typing.NewType.

    Can't use isinstance because it fails <3.10.
    """
    return isinstance(type_, test_new_type.__class__) and hasattr(type_, '__supertype__')  # type: ignore[arg-type]


classvar_re = re.compile(r'(\w+\.)?ClassVar\[')


def _check_classvar(v: type[Any] | None) -> bool:
    return v is not None and v.__class__ is typing.ClassVar.__class__ and getattr(v, '_name', None) == 'ClassVar'


def is_classvar(ann_type: type[Any]) -> bool:
    if _check_classvar(ann_type) or _check_classvar(get_origin(ann_type)):
        return True

    # this is an ugly workaround for class vars that contain forward references and are therefore themselves
    # forward references, see #3679
    if ann_type.__class__ == typing.ForwardRef and classvar_re.match(ann_type.__forward_arg__):
        return True

    return False


def _check_finalvar(v: type[Any] | None) -> bool:
    """Check if a given type is a `typing.Final` type."""
    if v is None:
        return False

    return v.__class__ == Final.__class__ and (sys.version_info < (3, 8) or getattr(v, '_name', None) == 'Final')


def is_finalvar(ann_type: Any) -> bool:
    return _check_finalvar(ann_type) or _check_finalvar(get_origin(ann_type))


def parent_frame_namespace(*, parent_depth: int = 2, force: bool = False) -> dict[str, Any] | None:
    """We allow use of items in parent namespace to get around the issue with `get_type_hints` only looking in the
    global module namespace. See https://github.com/pydantic/pydantic/issues/2678#issuecomment-1008139014 -> Scope
    and suggestion at the end of the next comment by @gvanrossum.

    WARNING 1: it matters exactly where this is called. By default, this function will build a namespace from the
    parent of where it is called.

    WARNING 2: this only looks in the parent namespace, not other parents since (AFAIK) there's no way to collect a
    dict of exactly what's in scope. Using `f_back` would work sometimes but would be very wrong and confusing in many
    other cases. See https://discuss.python.org/t/is-there-a-way-to-access-parent-nested-namespaces/20659.

    There are some cases where we want to force fetching the parent namespace, ex: during a `model_rebuild` call.
    In this case, we want both the namespace of the class' module, if applicable, and the parent namespace of the
    module where the rebuild is called.

    In other cases, like during initial schema build, if a class is defined at the top module level, we don't need to
    fetch that module's namespace, because the class' __module__ attribute can be used to access the parent namespace.
    This is done in `_typing_extra.get_module_ns_of`. Thus, there's no need to cache the parent frame namespace in this case.
    """
    frame = sys._getframe(parent_depth)

    # note, we don't copy frame.f_locals here (or during the last return call), because we don't expect the namespace to be modified down the line
    # if this becomes a problem, we could implement some sort of frozen mapping structure to enforce this
    if force:
        return frame.f_locals

    # if either of the following conditions are true, the class is defined at the top module level
    # to better understand why we need both of these checks, see
    # https://github.com/pydantic/pydantic/pull/10113#discussion_r1714981531
    if frame.f_back is None or frame.f_code.co_name == '<module>':
        return None

    return frame.f_locals


def get_module_ns_of(obj: Any) -> dict[str, Any]:
    """Get the namespace of the module where the object is defined.

    Caution: this function does not return a copy of the module namespace, so it should not be mutated.
    The burden of enforcing this is on the caller.
    """
    module_name = getattr(obj, '__module__', None)
    if module_name:
        try:
            return sys.modules[module_name].__dict__
        except KeyError:
            # happens occasionally, see https://github.com/pydantic/pydantic/issues/2363
            return {}
    return {}


def merge_cls_and_parent_ns(cls: type[Any], parent_namespace: dict[str, Any] | None = None) -> dict[str, Any]:
    ns = get_module_ns_of(cls).copy()
    if parent_namespace is not None:
        ns.update(parent_namespace)
    ns[cls.__name__] = cls
    return ns


def get_cls_type_hints_lenient(
    obj: Any, globalns: dict[str, Any] | None = None, mro: Iterable[type[Any]] | None = None
) -> dict[str, Any]:
    """Collect annotations from a class, including those from parent classes.

    Unlike `typing.get_type_hints`, this function will not error if a forward reference is not resolvable.
    """
    hints = {}
    if mro is None:
        mro = reversed(obj.__mro__)
    for base in mro:
        ann = base.__dict__.get('__annotations__')
        localns = dict(vars(base))
        if ann is not None and ann is not GetSetDescriptorType:
            for name, value in ann.items():
                hints[name] = eval_type_lenient(value, globalns, localns)
    return hints


def eval_type_lenient(value: Any, globalns: dict[str, Any] | None = None, localns: dict[str, Any] | None = None) -> Any:
    """Behaves like typing._eval_type, except it won't raise an error if a forward reference can't be resolved."""
    if value is None:
        value = NoneType
    elif isinstance(value, str):
        value = _make_forward_ref(value, is_argument=False, is_class=True)

    try:
        return eval_type_backport(value, globalns, localns)
    except NameError:
        # the point of this function is to be tolerant to this case
        return value


def eval_type_backport(
    value: Any,
    globalns: dict[str, Any] | None = None,
    localns: dict[str, Any] | None = None,
    type_params: tuple[Any] | None = None,
) -> Any:
    """An enhanced version of `typing._eval_type` which will fall back to using the `eval_type_backport`
    package if it's installed to let older Python versions use newer typing constructs.

    Specifically, this transforms `X | Y` into `typing.Union[X, Y]` and `list[X]` into `typing.List[X]`
    (as well as all the types made generic in PEP 585) if the original syntax is not supported in the
    current Python version.

    This function will also display a helpful error if the value passed fails to evaluate.
    """
    try:
        return _eval_type_backport(value, globalns, localns, type_params)
    except TypeError as e:
        if 'Unable to evaluate type annotation' in str(e):
            raise

        # If it is a `TypeError` and value isn't a `ForwardRef`, it would have failed during annotation definition.
        # Thus we assert here for type checking purposes:
        assert isinstance(value, typing.ForwardRef)

        message = f'Unable to evaluate type annotation {value.__forward_arg__!r}.'
        if sys.version_info >= (3, 11):
            e.add_note(message)
            raise
        else:
            raise TypeError(message) from e


def _eval_type_backport(
    value: Any,
    globalns: dict[str, Any] | None = None,
    localns: dict[str, Any] | None = None,
    type_params: tuple[Any] | None = None,
) -> Any:
    try:
        return _eval_type(value, globalns, localns, type_params)
    except TypeError as e:
        if not (isinstance(value, typing.ForwardRef) and is_backport_fixable_error(e)):
            raise

        try:
            from eval_type_backport import eval_type_backport
        except ImportError:
            raise TypeError(
                f'Unable to evaluate type annotation {value.__forward_arg__!r}. If you are making use '
                'of the new typing syntax (unions using `|` since Python 3.10 or builtins subscripting '
                'since Python 3.9), you should either replace the use of new syntax with the existing '
                '`typing` constructs or install the `eval_type_backport` package.'
            ) from e

        return eval_type_backport(value, globalns, localns, try_default=False)


def _eval_type(
    value: Any,
    globalns: dict[str, Any] | None = None,
    localns: dict[str, Any] | None = None,
    type_params: tuple[Any] | None = None,
) -> Any:
    if sys.version_info >= (3, 13):
        return typing._eval_type(  # type: ignore
            value, globalns, localns, type_params=type_params
        )
    else:
        return typing._eval_type(  # type: ignore
            value, globalns, localns
        )


def is_backport_fixable_error(e: TypeError) -> bool:
    msg = str(e)

    return (
        sys.version_info < (3, 10)
        and msg.startswith('unsupported operand type(s) for |: ')
        or sys.version_info < (3, 9)
        and "' object is not subscriptable" in msg
    )


def get_function_type_hints(
    function: Callable[..., Any], *, include_keys: set[str] | None = None, types_namespace: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Like `typing.get_type_hints`, but doesn't convert `X` to `Optional[X]` if the default value is `None`, also
    copes with `partial`.
    """
    try:
        if isinstance(function, partial):
            annotations = function.func.__annotations__
        else:
            annotations = function.__annotations__
    except AttributeError:
        type_hints = get_type_hints(function)
        if isinstance(function, type):
            # `type[...]` is a callable, which returns an instance of itself.
            # At some point, we might even look into the return type of `__new__`
            # if it returns something else.
            type_hints.setdefault('return', function)
        return type_hints

    globalns = get_module_ns_of(function)
    type_hints = {}
    type_params: tuple[Any] = getattr(function, '__type_params__', ())  # type: ignore
    for name, value in annotations.items():
        if include_keys is not None and name not in include_keys:
            continue
        if value is None:
            value = NoneType
        elif isinstance(value, str):
            value = _make_forward_ref(value)

        type_hints[name] = eval_type_backport(value, globalns, types_namespace, type_params)

    return type_hints


if sys.version_info < (3, 9, 8) or (3, 10) <= sys.version_info < (3, 10, 1):

    def _make_forward_ref(
        arg: Any,
        is_argument: bool = True,
        *,
        is_class: bool = False,
    ) -> typing.ForwardRef:
        """Wrapper for ForwardRef that accounts for the `is_class` argument missing in older versions.
        The `module` argument is omitted as it breaks <3.9.8, =3.10.0 and isn't used in the calls below.

        See https://github.com/python/cpython/pull/28560 for some background.
        The backport happened on 3.9.8, see:
        https://github.com/pydantic/pydantic/discussions/6244#discussioncomment-6275458,
        and on 3.10.1 for the 3.10 branch, see:
        https://github.com/pydantic/pydantic/issues/6912

        Implemented as EAFP with memory.
        """
        return typing.ForwardRef(arg, is_argument)

else:
    _make_forward_ref = typing.ForwardRef


if sys.version_info >= (3, 10):
    get_type_hints = typing.get_type_hints

else:
    """
    For older versions of python, we have a custom implementation of `get_type_hints` which is a close as possible to
    the implementation in CPython 3.10.8.
    """

    @typing.no_type_check
    def get_type_hints(  # noqa: C901
        obj: Any,
        globalns: dict[str, Any] | None = None,
        localns: dict[str, Any] | None = None,
        include_extras: bool = False,
    ) -> dict[str, Any]:  # pragma: no cover
        """Taken verbatim from python 3.10.8 unchanged, except:
        * type annotations of the function definition above.
        * prefixing `typing.` where appropriate
        * Use `_make_forward_ref` instead of `typing.ForwardRef` to handle the `is_class` argument.

        https://github.com/python/cpython/blob/aaaf5174241496afca7ce4d4584570190ff972fe/Lib/typing.py#L1773-L1875

        DO NOT CHANGE THIS METHOD UNLESS ABSOLUTELY NECESSARY.
        ======================================================

        Return type hints for an object.

        This is often the same as obj.__annotations__, but it handles
        forward references encoded as string literals, adds Optional[t] if a
        default value equal to None is set and recursively replaces all
        'Annotated[T, ...]' with 'T' (unless 'include_extras=True').

        The argument may be a module, class, method, or function. The annotations
        are returned as a dictionary. For classes, annotations include also
        inherited members.

        TypeError is raised if the argument is not of a type that can contain
        annotations, and an empty dictionary is returned if no annotations are
        present.

        BEWARE -- the behavior of globalns and localns is counterintuitive
        (unless you are familiar with how eval() and exec() work).  The
        search order is locals first, then globals.

        - If no dict arguments are passed, an attempt is made to use the
          globals from obj (or the respective module's globals for classes),
          and these are also used as the locals.  If the object does not appear
          to have globals, an empty dictionary is used.  For classes, the search
          order is globals first then locals.

        - If one dict argument is passed, it is used for both globals and
          locals.

        - If two dict arguments are passed, they specify globals and
          locals, respectively.
        """
        if getattr(obj, '__no_type_check__', None):
            return {}
        # Classes require a special treatment.
        if isinstance(obj, type):
            hints = {}
            for base in reversed(obj.__mro__):
                if globalns is None:
                    base_globals = getattr(sys.modules.get(base.__module__, None), '__dict__', {})
                else:
                    base_globals = globalns
                ann = base.__dict__.get('__annotations__', {})
                if isinstance(ann, types.GetSetDescriptorType):
                    ann = {}
                base_locals = dict(vars(base)) if localns is None else localns
                if localns is None and globalns is None:
                    # This is surprising, but required.  Before Python 3.10,
                    # get_type_hints only evaluated the globalns of
                    # a class.  To maintain backwards compatibility, we reverse
                    # the globalns and localns order so that eval() looks into
                    # *base_globals* first rather than *base_locals*.
                    # This only affects ForwardRefs.
                    base_globals, base_locals = base_locals, base_globals
                for name, value in ann.items():
                    if value is None:
                        value = type(None)
                    if isinstance(value, str):
                        value = _make_forward_ref(value, is_argument=False, is_class=True)

                    value = eval_type_backport(value, base_globals, base_locals)
                    hints[name] = value
            if not include_extras and hasattr(typing, '_strip_annotations'):
                return {
                    k: typing._strip_annotations(t)  # type: ignore
                    for k, t in hints.items()
                }
            else:
                return hints

        if globalns is None:
            if isinstance(obj, types.ModuleType):
                globalns = obj.__dict__
            else:
                nsobj = obj
                # Find globalns for the unwrapped object.
                while hasattr(nsobj, '__wrapped__'):
                    nsobj = nsobj.__wrapped__
                globalns = getattr(nsobj, '__globals__', {})
            if localns is None:
                localns = globalns
        elif localns is None:
            localns = globalns
        hints = getattr(obj, '__annotations__', None)
        if hints is None:
            # Return empty annotations for something that _could_ have them.
            if isinstance(obj, typing._allowed_types):  # type: ignore
                return {}
            else:
                raise TypeError(f'{obj!r} is not a module, class, method, ' 'or function.')
        defaults = typing._get_defaults(obj)  # type: ignore
        hints = dict(hints)
        for name, value in hints.items():
            if value is None:
                value = type(None)
            if isinstance(value, str):
                # class-level forward refs were handled above, this must be either
                # a module-level annotation or a function argument annotation

                value = _make_forward_ref(
                    value,
                    is_argument=not isinstance(obj, types.ModuleType),
                    is_class=False,
                )
            value = eval_type_backport(value, globalns, localns)
            if name in defaults and defaults[name] is None:
                value = typing.Optional[value]
            hints[name] = value
        return hints if include_extras else {k: typing._strip_annotations(t) for k, t in hints.items()}  # type: ignore


def is_dataclass(_cls: type[Any]) -> TypeGuard[type[StandardDataclass]]:
    # The dataclasses.is_dataclass function doesn't seem to provide TypeGuard functionality,
    # so I created this convenience function
    return dataclasses.is_dataclass(_cls)


def origin_is_type_alias_type(origin: Any) -> TypeGuard[TypeAliasType]:
    return isinstance(origin, TypeAliasType)


if sys.version_info >= (3, 10):

    def is_generic_alias(type_: type[Any]) -> bool:
        return isinstance(type_, (types.GenericAlias, typing._GenericAlias))  # type: ignore[attr-defined]

else:

    def is_generic_alias(type_: type[Any]) -> bool:
        return isinstance(type_, typing._GenericAlias)  # type: ignore


def is_self_type(tp: Any) -> bool:
    """Check if a given class is a Self type (from `typing` or `typing_extensions`)"""
    return isinstance(tp, typing_base) and getattr(tp, '_name', None) == 'Self'


if sys.version_info >= (3, 9):
    from zoneinfo import ZoneInfo

    def is_zoneinfo_type(tp: Any) -> bool:
        """Check if a give class is a zone_info.ZoneInfo type"""
        return tp is ZoneInfo

else:

    def is_zoneinfo_type(tp: Any) -> bool:
        return False
