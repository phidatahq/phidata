"""
Adapters for the enum type.
"""

from enum import Enum
from typing import Dict, Generic, Optional, Mapping, Sequence
from typing import Tuple, Type, TypeVar, Union, cast
from typing_extensions import TypeAlias

from .. import postgres
from .. import errors as e
from ..pq import Format
from ..abc import AdaptContext
from ..adapt import Buffer, Dumper, Loader
from .._compat import cache
from .._encodings import conn_encoding
from .._typeinfo import EnumInfo as EnumInfo  # exported here

E = TypeVar("E", bound=Enum)

EnumDumpMap: TypeAlias = Dict[E, bytes]
EnumLoadMap: TypeAlias = Dict[bytes, E]
EnumMapping: TypeAlias = Union[Mapping[E, str], Sequence[Tuple[E, str]], None]

# Hashable versions
_HEnumDumpMap: TypeAlias = Tuple[Tuple[E, bytes], ...]
_HEnumLoadMap: TypeAlias = Tuple[Tuple[bytes, E], ...]

TEXT = Format.TEXT
BINARY = Format.BINARY


class _BaseEnumLoader(Loader, Generic[E]):
    """
    Loader for a specific Enum class
    """

    enum: Type[E]
    _load_map: EnumLoadMap[E]

    def load(self, data: Buffer) -> E:
        if not isinstance(data, bytes):
            data = bytes(data)

        try:
            return self._load_map[data]
        except KeyError:
            enc = conn_encoding(self.connection)
            label = data.decode(enc, "replace")
            raise e.DataError(
                f"bad member for enum {self.enum.__qualname__}: {label!r}"
            )


class _BaseEnumDumper(Dumper, Generic[E]):
    """
    Dumper for a specific Enum class
    """

    enum: Type[E]
    _dump_map: EnumDumpMap[E]

    def dump(self, value: E) -> Buffer:
        return self._dump_map[value]


class EnumDumper(Dumper):
    """
    Dumper for a generic Enum class
    """

    def __init__(self, cls: type, context: Optional[AdaptContext] = None):
        super().__init__(cls, context)
        self._encoding = conn_encoding(self.connection)

    def dump(self, value: E) -> Buffer:
        return value.name.encode(self._encoding)


class EnumBinaryDumper(EnumDumper):
    format = BINARY


def register_enum(
    info: EnumInfo,
    context: Optional[AdaptContext] = None,
    enum: Optional[Type[E]] = None,
    *,
    mapping: EnumMapping[E] = None,
) -> None:
    """Register the adapters to load and dump a enum type.

    :param info: The object with the information about the enum to register.
    :param context: The context where to register the adapters. If `!None`,
        register it globally.
    :param enum: Python enum type matching to the PostgreSQL one. If `!None`,
        a new enum will be generated and exposed as `EnumInfo.enum`.
    :param mapping: Override the mapping between `!enum` members and `!info`
        labels.
    """

    if not info:
        raise TypeError("no info passed. Is the requested enum available?")

    if enum is None:
        enum = cast(Type[E], _make_enum(info.name, tuple(info.labels)))

    info.enum = enum
    adapters = context.adapters if context else postgres.adapters
    info.register(context)

    load_map = _make_load_map(info, enum, mapping, context)

    loader = _make_loader(info.name, info.enum, load_map)
    adapters.register_loader(info.oid, loader)

    loader = _make_binary_loader(info.name, info.enum, load_map)
    adapters.register_loader(info.oid, loader)

    dump_map = _make_dump_map(info, enum, mapping, context)

    dumper = _make_dumper(info.enum, info.oid, dump_map)
    adapters.register_dumper(info.enum, dumper)

    dumper = _make_binary_dumper(info.enum, info.oid, dump_map)
    adapters.register_dumper(info.enum, dumper)


# Cache all dynamically-generated types to avoid leaks in case the types
# cannot be GC'd.


@cache
def _make_enum(name: str, labels: Tuple[str, ...]) -> Enum:
    return Enum(name.title(), labels, module=__name__)


@cache
def _make_loader(
    name: str, enum: Type[Enum], load_map: _HEnumLoadMap[E]
) -> Type[_BaseEnumLoader[E]]:
    attribs = {"enum": enum, "_load_map": dict(load_map)}
    return type(f"{name.title()}Loader", (_BaseEnumLoader,), attribs)


@cache
def _make_binary_loader(
    name: str, enum: Type[Enum], load_map: _HEnumLoadMap[E]
) -> Type[_BaseEnumLoader[E]]:
    attribs = {"enum": enum, "_load_map": dict(load_map), "format": BINARY}
    return type(f"{name.title()}BinaryLoader", (_BaseEnumLoader,), attribs)


@cache
def _make_dumper(
    enum: Type[Enum], oid: int, dump_map: _HEnumDumpMap[E]
) -> Type[_BaseEnumDumper[E]]:
    attribs = {"enum": enum, "oid": oid, "_dump_map": dict(dump_map)}
    return type(f"{enum.__name__}Dumper", (_BaseEnumDumper,), attribs)


@cache
def _make_binary_dumper(
    enum: Type[Enum], oid: int, dump_map: _HEnumDumpMap[E]
) -> Type[_BaseEnumDumper[E]]:
    attribs = {"enum": enum, "oid": oid, "_dump_map": dict(dump_map), "format": BINARY}
    return type(f"{enum.__name__}BinaryDumper", (_BaseEnumDumper,), attribs)


def _make_load_map(
    info: EnumInfo,
    enum: Type[E],
    mapping: EnumMapping[E],
    context: Optional[AdaptContext],
) -> _HEnumLoadMap[E]:
    enc = conn_encoding(context.connection if context else None)
    rv = []
    for label in info.labels:
        try:
            member = enum[label]
        except KeyError:
            # tolerate a missing enum, assuming it won't be used. If it is we
            # will get a DataError on fetch.
            pass
        else:
            rv.append((label.encode(enc), member))

    if mapping:
        if isinstance(mapping, Mapping):
            mapping = list(mapping.items())

        for member, label in mapping:
            rv.append((label.encode(enc), member))

    return tuple(rv)


def _make_dump_map(
    info: EnumInfo,
    enum: Type[E],
    mapping: EnumMapping[E],
    context: Optional[AdaptContext],
) -> _HEnumDumpMap[E]:
    enc = conn_encoding(context.connection if context else None)
    rv = []
    for member in enum:
        rv.append((member, member.name.encode(enc)))

    if mapping:
        if isinstance(mapping, Mapping):
            mapping = list(mapping.items())

        for member, label in mapping:
            rv.append((member, label.encode(enc)))

    return tuple(rv)


def register_default_adapters(context: AdaptContext) -> None:
    context.adapters.register_dumper(Enum, EnumBinaryDumper)
    context.adapters.register_dumper(Enum, EnumDumper)
