from __future__ import annotations

import inspect
import typing as t
from weakref import ref
from weakref import WeakMethod

T = t.TypeVar("T")


class Symbol:
    """A constant symbol, nicer than ``object()``. Repeated calls return the
    same instance.

    >>> Symbol('foo') is Symbol('foo')
    True
    >>> Symbol('foo')
    foo
    """

    symbols: t.ClassVar[dict[str, Symbol]] = {}

    def __new__(cls, name: str) -> Symbol:
        if name in cls.symbols:
            return cls.symbols[name]

        obj = super().__new__(cls)
        cls.symbols[name] = obj
        return obj

    def __init__(self, name: str) -> None:
        self.name = name

    def __repr__(self) -> str:
        return self.name

    def __getnewargs__(self) -> tuple[t.Any]:
        return (self.name,)


def make_id(obj: object) -> t.Hashable:
    if inspect.ismethod(obj):
        return id(obj.__func__), id(obj.__self__)

    return id(obj)


def make_ref(obj: T, callback: t.Callable[[ref[T]], None] | None = None) -> ref[T]:
    if inspect.ismethod(obj):
        return WeakMethod(obj, callback)  # type: ignore[arg-type, return-value]

    return ref(obj, callback)
