"""
CockroachDB-specific connections.
"""

# Copyright (C) 2022 The Psycopg Team

import re
from typing import Any, Optional, Type, Union, overload, TYPE_CHECKING

from .. import errors as e
from ..abc import AdaptContext
from ..rows import Row, RowFactory, AsyncRowFactory, TupleRow
from .._compat import Self
from ..connection import Connection
from .._adapters_map import AdaptersMap
from .._connection_info import ConnectionInfo
from ..connection_async import AsyncConnection
from ._types import adapters

if TYPE_CHECKING:
    from ..pq.abc import PGconn
    from ..cursor import Cursor
    from ..cursor_async import AsyncCursor


class _CrdbConnectionMixin:
    _adapters: Optional[AdaptersMap]
    pgconn: "PGconn"

    @classmethod
    def is_crdb(
        cls, conn: Union[Connection[Any], AsyncConnection[Any], "PGconn"]
    ) -> bool:
        """
        Return `!True` if the server connected to `!conn` is CockroachDB.
        """
        if isinstance(conn, (Connection, AsyncConnection)):
            conn = conn.pgconn

        return bool(conn.parameter_status(b"crdb_version"))

    @property
    def adapters(self) -> AdaptersMap:
        if not self._adapters:
            # By default, use CockroachDB adapters map
            self._adapters = AdaptersMap(adapters)

        return self._adapters

    @property
    def info(self) -> "CrdbConnectionInfo":
        return CrdbConnectionInfo(self.pgconn)

    def _check_tpc(self) -> None:
        if self.is_crdb(self.pgconn):
            raise e.NotSupportedError("CockroachDB doesn't support prepared statements")


class CrdbConnection(_CrdbConnectionMixin, Connection[Row]):
    """
    Wrapper for a connection to a CockroachDB database.
    """

    __module__ = "psycopg.crdb"

    # TODO: this method shouldn't require re-definition if the base class
    # implements a generic self.
    # https://github.com/psycopg/psycopg/issues/308
    @overload
    @classmethod
    def connect(
        cls,
        conninfo: str = "",
        *,
        autocommit: bool = False,
        row_factory: RowFactory[Row],
        prepare_threshold: Optional[int] = 5,
        cursor_factory: "Optional[Type[Cursor[Row]]]" = None,
        context: Optional[AdaptContext] = None,
        **kwargs: Union[None, int, str],
    ) -> "CrdbConnection[Row]": ...

    @overload
    @classmethod
    def connect(
        cls,
        conninfo: str = "",
        *,
        autocommit: bool = False,
        prepare_threshold: Optional[int] = 5,
        cursor_factory: "Optional[Type[Cursor[Any]]]" = None,
        context: Optional[AdaptContext] = None,
        **kwargs: Union[None, int, str],
    ) -> "CrdbConnection[TupleRow]": ...

    @classmethod
    def connect(cls, conninfo: str = "", **kwargs: Any) -> Self:
        """
        Connect to a database server and return a new `CrdbConnection` instance.
        """
        return super().connect(conninfo, **kwargs)  # type: ignore[return-value]


class AsyncCrdbConnection(_CrdbConnectionMixin, AsyncConnection[Row]):
    """
    Wrapper for an async connection to a CockroachDB database.
    """

    __module__ = "psycopg.crdb"

    # TODO: this method shouldn't require re-definition if the base class
    # implements a generic self.
    # https://github.com/psycopg/psycopg/issues/308
    @overload
    @classmethod
    async def connect(
        cls,
        conninfo: str = "",
        *,
        autocommit: bool = False,
        prepare_threshold: Optional[int] = 5,
        row_factory: AsyncRowFactory[Row],
        cursor_factory: "Optional[Type[AsyncCursor[Row]]]" = None,
        context: Optional[AdaptContext] = None,
        **kwargs: Union[None, int, str],
    ) -> "AsyncCrdbConnection[Row]": ...

    @overload
    @classmethod
    async def connect(
        cls,
        conninfo: str = "",
        *,
        autocommit: bool = False,
        prepare_threshold: Optional[int] = 5,
        cursor_factory: "Optional[Type[AsyncCursor[Any]]]" = None,
        context: Optional[AdaptContext] = None,
        **kwargs: Union[None, int, str],
    ) -> "AsyncCrdbConnection[TupleRow]": ...

    @classmethod
    async def connect(cls, conninfo: str = "", **kwargs: Any) -> Self:
        return await super().connect(conninfo, **kwargs)  # type: ignore[no-any-return]


class CrdbConnectionInfo(ConnectionInfo):
    """
    `~psycopg.ConnectionInfo` subclass to get info about a CockroachDB database.
    """

    __module__ = "psycopg.crdb"

    @property
    def vendor(self) -> str:
        return "CockroachDB"

    @property
    def server_version(self) -> int:
        """
        Return the CockroachDB server version connected.

        Return a number in the PostgreSQL format (e.g. 21.2.10 -> 210210).
        """
        sver = self.parameter_status("crdb_version")
        if not sver:
            raise e.InternalError("'crdb_version' parameter status not set")

        ver = self.parse_crdb_version(sver)
        if ver is None:
            raise e.InterfaceError(f"couldn't parse CockroachDB version from: {sver!r}")

        return ver

    @classmethod
    def parse_crdb_version(self, sver: str) -> Optional[int]:
        m = re.search(r"\bv(\d+)\.(\d+)\.(\d+)", sver)
        if not m:
            return None

        return int(m.group(1)) * 10000 + int(m.group(2)) * 100 + int(m.group(3))
