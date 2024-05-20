"""
The Column object in Cursor.description
"""

# Copyright (C) 2020 The Psycopg Team

from typing import Any, NamedTuple, Optional, Sequence, TYPE_CHECKING
from operator import attrgetter

if TYPE_CHECKING:
    from .cursor import BaseCursor


class ColumnData(NamedTuple):
    ftype: int
    fmod: int
    fsize: int


class Column(Sequence[Any]):
    __module__ = "psycopg"

    def __init__(self, cursor: "BaseCursor[Any, Any]", index: int):
        res = cursor.pgresult
        assert res

        fname = res.fname(index)
        if fname:
            self._name = fname.decode(cursor._encoding)
        else:
            # COPY_OUT results have columns but no name
            self._name = f"column_{index + 1}"

        self._data = ColumnData(
            ftype=res.ftype(index),
            fmod=res.fmod(index),
            fsize=res.fsize(index),
        )
        self._type = cursor.adapters.types.get(self._data.ftype)

    _attrs = tuple(
        attrgetter(attr)
        for attr in """
            name type_code display_size internal_size precision scale null_ok
            """.split()
    )

    def __repr__(self) -> str:
        return (
            f"<Column {self.name!r},"
            f" type: {self._type_display()} (oid: {self.type_code})>"
        )

    def __len__(self) -> int:
        return 7

    def _type_display(self) -> str:
        parts = []
        parts.append(self._type.name if self._type else str(self.type_code))

        mod1 = self.precision
        if mod1 is None:
            mod1 = self.display_size
        if mod1:
            parts.append(f"({mod1}")
            if self.scale:
                parts.append(f", {self.scale}")
            parts.append(")")

        if self._type and self.type_code == self._type.array_oid:
            parts.append("[]")

        return "".join(parts)

    def __getitem__(self, index: Any) -> Any:
        if isinstance(index, slice):
            return tuple(getter(self) for getter in self._attrs[index])
        else:
            return self._attrs[index](self)

    @property
    def name(self) -> str:
        """The name of the column."""
        return self._name

    @property
    def type_code(self) -> int:
        """The numeric OID of the column."""
        return self._data.ftype

    @property
    def display_size(self) -> Optional[int]:
        """The field size, for :sql:`varchar(n)`, None otherwise."""
        if not self._type:
            return None

        if self._type.name in ("varchar", "char"):
            fmod = self._data.fmod
            if fmod >= 0:
                return fmod - 4

        return None

    @property
    def internal_size(self) -> Optional[int]:
        """The internal field size for fixed-size types, None otherwise."""
        fsize = self._data.fsize
        return fsize if fsize >= 0 else None

    @property
    def precision(self) -> Optional[int]:
        """The number of digits for fixed precision types."""
        if not self._type:
            return None

        dttypes = ("time", "timetz", "timestamp", "timestamptz", "interval")
        if self._type.name == "numeric":
            fmod = self._data.fmod
            if fmod >= 0:
                return fmod >> 16

        elif self._type.name in dttypes:
            fmod = self._data.fmod
            if fmod >= 0:
                return fmod & 0xFFFF

        return None

    @property
    def scale(self) -> Optional[int]:
        """The number of digits after the decimal point if available."""
        if self._type and self._type.name == "numeric":
            fmod = self._data.fmod - 4
            if fmod >= 0:
                return fmod & 0xFFFF

        return None

    @property
    def null_ok(self) -> Optional[bool]:
        """Always `!None`"""
        return None
