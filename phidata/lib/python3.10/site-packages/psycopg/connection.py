"""
psycopg connection objects
"""

# Copyright (C) 2020 The Psycopg Team

import logging
import threading
from types import TracebackType
from typing import Any, Callable, cast, Generator, Generic, Iterator
from typing import List, NamedTuple, Optional, Type, TypeVar, Tuple, Union
from typing import overload, TYPE_CHECKING
from weakref import ref, ReferenceType
from warnings import warn
from functools import partial
from contextlib import contextmanager
from typing_extensions import TypeAlias

from . import pq
from . import errors as e
from . import waiting
from . import postgres
from .abc import AdaptContext, Params, Query, RV
from .abc import PQGen, PQGenConn
from .sql import Composable, SQL
from ._tpc import Xid
from .rows import Row, RowFactory, tuple_row, TupleRow, args_row
from .adapt import AdaptersMap
from ._enums import IsolationLevel
from .cursor import Cursor
from ._compat import LiteralString, Self
from .pq.misc import connection_summary
from .conninfo import make_conninfo, conninfo_to_dict
from .conninfo import conninfo_attempts, ConnDict, timeout_from_conninfo
from ._pipeline import BasePipeline, Pipeline
from .generators import notifies, connect, execute
from ._encodings import pgconn_encoding
from ._preparing import PrepareManager
from .transaction import Transaction
from .server_cursor import ServerCursor
from ._connection_info import ConnectionInfo

if TYPE_CHECKING:
    from .pq.abc import PGconn, PGresult
    from psycopg_pool.base import BasePool


# Row Type variable for Cursor (when it needs to be distinguished from the
# connection's one)
CursorRow = TypeVar("CursorRow")

TEXT = pq.Format.TEXT
BINARY = pq.Format.BINARY

OK = pq.ConnStatus.OK
BAD = pq.ConnStatus.BAD

COMMAND_OK = pq.ExecStatus.COMMAND_OK
TUPLES_OK = pq.ExecStatus.TUPLES_OK
FATAL_ERROR = pq.ExecStatus.FATAL_ERROR

IDLE = pq.TransactionStatus.IDLE
INTRANS = pq.TransactionStatus.INTRANS

logger = logging.getLogger("psycopg")


class Notify(NamedTuple):
    """An asynchronous notification received from the database."""

    channel: str
    """The name of the channel on which the notification was received."""

    payload: str
    """The message attached to the notification."""

    pid: int
    """The PID of the backend process which sent the notification."""


Notify.__module__ = "psycopg"

NoticeHandler: TypeAlias = Callable[[e.Diagnostic], None]
NotifyHandler: TypeAlias = Callable[[Notify], None]


class BaseConnection(Generic[Row]):
    """
    Base class for different types of connections.

    Share common functionalities such as access to the wrapped PGconn, but
    allow different interfaces (sync/async).
    """

    # DBAPI2 exposed exceptions
    Warning = e.Warning
    Error = e.Error
    InterfaceError = e.InterfaceError
    DatabaseError = e.DatabaseError
    DataError = e.DataError
    OperationalError = e.OperationalError
    IntegrityError = e.IntegrityError
    InternalError = e.InternalError
    ProgrammingError = e.ProgrammingError
    NotSupportedError = e.NotSupportedError

    # Enums useful for the connection
    ConnStatus = pq.ConnStatus
    TransactionStatus = pq.TransactionStatus

    def __init__(self, pgconn: "PGconn"):
        self.pgconn = pgconn
        self._autocommit = False

        # None, but set to a copy of the global adapters map as soon as requested.
        self._adapters: Optional[AdaptersMap] = None

        self._notice_handlers: List[NoticeHandler] = []
        self._notify_handlers: List[NotifyHandler] = []

        # Number of transaction blocks currently entered
        self._num_transactions = 0

        self._closed = False  # closed by an explicit close()
        self._prepared: PrepareManager = PrepareManager()
        self._tpc: Optional[Tuple[Xid, bool]] = None  # xid, prepared

        wself = ref(self)
        pgconn.notice_handler = partial(BaseConnection._notice_handler, wself)
        pgconn.notify_handler = partial(BaseConnection._notify_handler, wself)

        # Attribute is only set if the connection is from a pool so we can tell
        # apart a connection in the pool too (when _pool = None)
        self._pool: Optional["BasePool[Any]"]

        self._pipeline: Optional[BasePipeline] = None

        # Time after which the connection should be closed
        self._expire_at: float

        self._isolation_level: Optional[IsolationLevel] = None
        self._read_only: Optional[bool] = None
        self._deferrable: Optional[bool] = None
        self._begin_statement = b""

    def __del__(self) -> None:
        # If fails on connection we might not have this attribute yet
        if not hasattr(self, "pgconn"):
            return

        # Connection correctly closed
        if self.closed:
            return

        # Connection in a pool so terminating with the program is normal
        if hasattr(self, "_pool"):
            return

        warn(
            f"connection {self} was deleted while still open."
            " Please use 'with' or '.close()' to close the connection",
            ResourceWarning,
        )

    def __repr__(self) -> str:
        cls = f"{self.__class__.__module__}.{self.__class__.__qualname__}"
        info = connection_summary(self.pgconn)
        return f"<{cls} {info} at 0x{id(self):x}>"

    @property
    def closed(self) -> bool:
        """`!True` if the connection is closed."""
        return self.pgconn.status == BAD

    @property
    def broken(self) -> bool:
        """
        `!True` if the connection was interrupted.

        A broken connection is always `closed`, but wasn't closed in a clean
        way, such as using `close()` or a `!with` block.
        """
        return self.pgconn.status == BAD and not self._closed

    @property
    def autocommit(self) -> bool:
        """The autocommit state of the connection."""
        return self._autocommit

    @autocommit.setter
    def autocommit(self, value: bool) -> None:
        self._set_autocommit(value)

    def _set_autocommit(self, value: bool) -> None:
        raise NotImplementedError

    def _set_autocommit_gen(self, value: bool) -> PQGen[None]:
        yield from self._check_intrans_gen("autocommit")
        self._autocommit = bool(value)

    @property
    def isolation_level(self) -> Optional[IsolationLevel]:
        """
        The isolation level of the new transactions started on the connection.
        """
        return self._isolation_level

    @isolation_level.setter
    def isolation_level(self, value: Optional[IsolationLevel]) -> None:
        self._set_isolation_level(value)

    def _set_isolation_level(self, value: Optional[IsolationLevel]) -> None:
        raise NotImplementedError

    def _set_isolation_level_gen(self, value: Optional[IsolationLevel]) -> PQGen[None]:
        yield from self._check_intrans_gen("isolation_level")
        self._isolation_level = IsolationLevel(value) if value is not None else None
        self._begin_statement = b""

    @property
    def read_only(self) -> Optional[bool]:
        """
        The read-only state of the new transactions started on the connection.
        """
        return self._read_only

    @read_only.setter
    def read_only(self, value: Optional[bool]) -> None:
        self._set_read_only(value)

    def _set_read_only(self, value: Optional[bool]) -> None:
        raise NotImplementedError

    def _set_read_only_gen(self, value: Optional[bool]) -> PQGen[None]:
        yield from self._check_intrans_gen("read_only")
        self._read_only = bool(value) if value is not None else None
        self._begin_statement = b""

    @property
    def deferrable(self) -> Optional[bool]:
        """
        The deferrable state of the new transactions started on the connection.
        """
        return self._deferrable

    @deferrable.setter
    def deferrable(self, value: Optional[bool]) -> None:
        self._set_deferrable(value)

    def _set_deferrable(self, value: Optional[bool]) -> None:
        raise NotImplementedError

    def _set_deferrable_gen(self, value: Optional[bool]) -> PQGen[None]:
        yield from self._check_intrans_gen("deferrable")
        self._deferrable = bool(value) if value is not None else None
        self._begin_statement = b""

    def _check_intrans_gen(self, attribute: str) -> PQGen[None]:
        # Raise an exception if we are in a transaction
        status = self.pgconn.transaction_status
        if status == IDLE and self._pipeline:
            yield from self._pipeline._sync_gen()
            status = self.pgconn.transaction_status
        if status != IDLE:
            if self._num_transactions:
                raise e.ProgrammingError(
                    f"can't change {attribute!r} now: "
                    "connection.transaction() context in progress"
                )
            else:
                raise e.ProgrammingError(
                    f"can't change {attribute!r} now: "
                    "connection in transaction status "
                    f"{pq.TransactionStatus(status).name}"
                )

    @property
    def info(self) -> ConnectionInfo:
        """A `ConnectionInfo` attribute to inspect connection properties."""
        return ConnectionInfo(self.pgconn)

    @property
    def adapters(self) -> AdaptersMap:
        if not self._adapters:
            self._adapters = AdaptersMap(postgres.adapters)

        return self._adapters

    @property
    def connection(self) -> "BaseConnection[Row]":
        # implement the AdaptContext protocol
        return self

    def fileno(self) -> int:
        """Return the file descriptor of the connection.

        This function allows to use the connection as file-like object in
        functions waiting for readiness, such as the ones defined in the
        `selectors` module.
        """
        return self.pgconn.socket

    def cancel(self) -> None:
        """Cancel the current operation on the connection."""
        # No-op if the connection is closed
        # this allows to use the method as callback handler without caring
        # about its life.
        if self.closed:
            return

        if self._tpc and self._tpc[1]:
            raise e.ProgrammingError(
                "cancel() cannot be used with a prepared two-phase transaction"
            )

        self._try_cancel(self.pgconn)

    @classmethod
    def _try_cancel(cls, pgconn: "PGconn") -> None:
        try:
            # Can fail if the connection is closed
            c = pgconn.get_cancel()
        except Exception as ex:
            logger.warning("couldn't try to cancel query: %s", ex)
        else:
            c.cancel()

    def add_notice_handler(self, callback: NoticeHandler) -> None:
        """
        Register a callable to be invoked when a notice message is received.

        :param callback: the callback to call upon message received.
        :type callback: Callable[[~psycopg.errors.Diagnostic], None]
        """
        self._notice_handlers.append(callback)

    def remove_notice_handler(self, callback: NoticeHandler) -> None:
        """
        Unregister a notice message callable previously registered.

        :param callback: the callback to remove.
        :type callback: Callable[[~psycopg.errors.Diagnostic], None]
        """
        self._notice_handlers.remove(callback)

    @staticmethod
    def _notice_handler(
        wself: "ReferenceType[BaseConnection[Row]]", res: "PGresult"
    ) -> None:
        self = wself()
        if not (self and self._notice_handlers):
            return

        diag = e.Diagnostic(res, pgconn_encoding(self.pgconn))
        for cb in self._notice_handlers:
            try:
                cb(diag)
            except Exception as ex:
                logger.exception("error processing notice callback '%s': %s", cb, ex)

    def add_notify_handler(self, callback: NotifyHandler) -> None:
        """
        Register a callable to be invoked whenever a notification is received.

        :param callback: the callback to call upon notification received.
        :type callback: Callable[[~psycopg.Notify], None]
        """
        self._notify_handlers.append(callback)

    def remove_notify_handler(self, callback: NotifyHandler) -> None:
        """
        Unregister a notification callable previously registered.

        :param callback: the callback to remove.
        :type callback: Callable[[~psycopg.Notify], None]
        """
        self._notify_handlers.remove(callback)

    @staticmethod
    def _notify_handler(
        wself: "ReferenceType[BaseConnection[Row]]", pgn: pq.PGnotify
    ) -> None:
        self = wself()
        if not (self and self._notify_handlers):
            return

        enc = pgconn_encoding(self.pgconn)
        n = Notify(pgn.relname.decode(enc), pgn.extra.decode(enc), pgn.be_pid)
        for cb in self._notify_handlers:
            cb(n)

    @property
    def prepare_threshold(self) -> Optional[int]:
        """
        Number of times a query is executed before it is prepared.

        - If it is set to 0, every query is prepared the first time it is
          executed.
        - If it is set to `!None`, prepared statements are disabled on the
          connection.

        Default value: 5
        """
        return self._prepared.prepare_threshold

    @prepare_threshold.setter
    def prepare_threshold(self, value: Optional[int]) -> None:
        self._prepared.prepare_threshold = value

    @property
    def prepared_max(self) -> int:
        """
        Maximum number of prepared statements on the connection.

        Default value: 100
        """
        return self._prepared.prepared_max

    @prepared_max.setter
    def prepared_max(self, value: int) -> None:
        self._prepared.prepared_max = value

    # Generators to perform high-level operations on the connection
    #
    # These operations are expressed in terms of non-blocking generators
    # and the task of waiting when needed (when the generators yield) is left
    # to the connections subclass, which might wait either in blocking mode
    # or through asyncio.
    #
    # All these generators assume exclusive access to the connection: subclasses
    # should have a lock and hold it before calling and consuming them.

    @classmethod
    def _connect_gen(cls, conninfo: str = "") -> PQGenConn[Self]:
        """Generator to connect to the database and create a new instance."""
        pgconn = yield from connect(conninfo)
        conn = cls(pgconn)
        return conn

    def _exec_command(
        self, command: Query, result_format: pq.Format = TEXT
    ) -> PQGen[Optional["PGresult"]]:
        """
        Generator to send a command and receive the result to the backend.

        Only used to implement internal commands such as "commit", with eventual
        arguments bound client-side. The cursor can do more complex stuff.
        """
        self._check_connection_ok()

        if isinstance(command, str):
            command = command.encode(pgconn_encoding(self.pgconn))
        elif isinstance(command, Composable):
            command = command.as_bytes(self)

        if self._pipeline:
            cmd = partial(
                self.pgconn.send_query_params,
                command,
                None,
                result_format=result_format,
            )
            self._pipeline.command_queue.append(cmd)
            self._pipeline.result_queue.append(None)
            return None

        self.pgconn.send_query_params(command, None, result_format=result_format)

        result = (yield from execute(self.pgconn))[-1]
        if result.status != COMMAND_OK and result.status != TUPLES_OK:
            if result.status == FATAL_ERROR:
                raise e.error_from_result(result, encoding=pgconn_encoding(self.pgconn))
            else:
                raise e.InterfaceError(
                    f"unexpected result {pq.ExecStatus(result.status).name}"
                    f" from command {command.decode()!r}"
                )
        return result

    def _check_connection_ok(self) -> None:
        if self.pgconn.status == OK:
            return

        if self.pgconn.status == BAD:
            raise e.OperationalError("the connection is closed")
        raise e.InterfaceError(
            "cannot execute operations: the connection is"
            f" in status {self.pgconn.status}"
        )

    def _start_query(self) -> PQGen[None]:
        """Generator to start a transaction if necessary."""
        if self._autocommit:
            return

        if self.pgconn.transaction_status != IDLE:
            return

        yield from self._exec_command(self._get_tx_start_command())
        if self._pipeline:
            yield from self._pipeline._sync_gen()

    def _get_tx_start_command(self) -> bytes:
        if self._begin_statement:
            return self._begin_statement

        parts = [b"BEGIN"]

        if self.isolation_level is not None:
            val = IsolationLevel(self.isolation_level)
            parts.append(b"ISOLATION LEVEL")
            parts.append(val.name.replace("_", " ").encode())

        if self.read_only is not None:
            parts.append(b"READ ONLY" if self.read_only else b"READ WRITE")

        if self.deferrable is not None:
            parts.append(b"DEFERRABLE" if self.deferrable else b"NOT DEFERRABLE")

        self._begin_statement = b" ".join(parts)
        return self._begin_statement

    def _commit_gen(self) -> PQGen[None]:
        """Generator implementing `Connection.commit()`."""
        if self._num_transactions:
            raise e.ProgrammingError(
                "Explicit commit() forbidden within a Transaction "
                "context. (Transaction will be automatically committed "
                "on successful exit from context.)"
            )
        if self._tpc:
            raise e.ProgrammingError(
                "commit() cannot be used during a two-phase transaction"
            )
        if self.pgconn.transaction_status == IDLE:
            return

        yield from self._exec_command(b"COMMIT")

        if self._pipeline:
            yield from self._pipeline._sync_gen()

    def _rollback_gen(self) -> PQGen[None]:
        """Generator implementing `Connection.rollback()`."""
        if self._num_transactions:
            raise e.ProgrammingError(
                "Explicit rollback() forbidden within a Transaction "
                "context. (Either raise Rollback() or allow "
                "an exception to propagate out of the context.)"
            )
        if self._tpc:
            raise e.ProgrammingError(
                "rollback() cannot be used during a two-phase transaction"
            )

        # Get out of a "pipeline aborted" state
        if self._pipeline:
            yield from self._pipeline._sync_gen()

        if self.pgconn.transaction_status == IDLE:
            return

        yield from self._exec_command(b"ROLLBACK")
        self._prepared.clear()
        for cmd in self._prepared.get_maintenance_commands():
            yield from self._exec_command(cmd)

        if self._pipeline:
            yield from self._pipeline._sync_gen()

    def xid(self, format_id: int, gtrid: str, bqual: str) -> Xid:
        """
        Returns a `Xid` to pass to the `!tpc_*()` methods of this connection.

        The argument types and constraints are explained in
        :ref:`two-phase-commit`.

        The values passed to the method will be available on the returned
        object as the members `~Xid.format_id`, `~Xid.gtrid`, `~Xid.bqual`.
        """
        self._check_tpc()
        return Xid.from_parts(format_id, gtrid, bqual)

    def _tpc_begin_gen(self, xid: Union[Xid, str]) -> PQGen[None]:
        self._check_tpc()

        if not isinstance(xid, Xid):
            xid = Xid.from_string(xid)

        if self.pgconn.transaction_status != IDLE:
            raise e.ProgrammingError(
                "can't start two-phase transaction: connection in status"
                f" {pq.TransactionStatus(self.pgconn.transaction_status).name}"
            )

        if self._autocommit:
            raise e.ProgrammingError(
                "can't use two-phase transactions in autocommit mode"
            )

        self._tpc = (xid, False)
        yield from self._exec_command(self._get_tx_start_command())

    def _tpc_prepare_gen(self) -> PQGen[None]:
        if not self._tpc:
            raise e.ProgrammingError(
                "'tpc_prepare()' must be called inside a two-phase transaction"
            )
        if self._tpc[1]:
            raise e.ProgrammingError(
                "'tpc_prepare()' cannot be used during a prepared two-phase transaction"
            )
        xid = self._tpc[0]
        self._tpc = (xid, True)
        yield from self._exec_command(SQL("PREPARE TRANSACTION {}").format(str(xid)))
        if self._pipeline:
            yield from self._pipeline._sync_gen()

    def _tpc_finish_gen(
        self, action: LiteralString, xid: Union[Xid, str, None]
    ) -> PQGen[None]:
        fname = f"tpc_{action.lower()}()"
        if xid is None:
            if not self._tpc:
                raise e.ProgrammingError(
                    f"{fname} without xid must must be"
                    " called inside a two-phase transaction"
                )
            xid = self._tpc[0]
        else:
            if self._tpc:
                raise e.ProgrammingError(
                    f"{fname} with xid must must be called"
                    " outside a two-phase transaction"
                )
            if not isinstance(xid, Xid):
                xid = Xid.from_string(xid)

        if self._tpc and not self._tpc[1]:
            meth: Callable[[], PQGen[None]]
            meth = getattr(self, f"_{action.lower()}_gen")
            self._tpc = None
            yield from meth()
        else:
            yield from self._exec_command(
                SQL("{} PREPARED {}").format(SQL(action), str(xid))
            )
            self._tpc = None

    def _check_tpc(self) -> None:
        """Raise NotSupportedError if TPC is not supported."""
        # TPC supported on every supported PostgreSQL version.
        pass


class Connection(BaseConnection[Row]):
    """
    Wrapper for a connection to the database.
    """

    __module__ = "psycopg"

    cursor_factory: Type[Cursor[Row]]
    server_cursor_factory: Type[ServerCursor[Row]]
    row_factory: RowFactory[Row]
    _pipeline: Optional[Pipeline]

    def __init__(
        self,
        pgconn: "PGconn",
        row_factory: RowFactory[Row] = cast(RowFactory[Row], tuple_row),
    ):
        super().__init__(pgconn)
        self.row_factory = row_factory
        self.lock = threading.Lock()
        self.cursor_factory = Cursor
        self.server_cursor_factory = ServerCursor

    @overload
    @classmethod
    def connect(
        cls,
        conninfo: str = "",
        *,
        autocommit: bool = False,
        row_factory: RowFactory[Row],
        prepare_threshold: Optional[int] = 5,
        cursor_factory: Optional[Type[Cursor[Row]]] = None,
        context: Optional[AdaptContext] = None,
        **kwargs: Union[None, int, str],
    ) -> "Connection[Row]":
        # TODO: returned type should be Self. See #308.
        # Unfortunately we cannot use Self[Row] as Self is not parametric.
        # https://peps.python.org/pep-0673/#use-in-generic-classes
        ...

    @overload
    @classmethod
    def connect(
        cls,
        conninfo: str = "",
        *,
        autocommit: bool = False,
        prepare_threshold: Optional[int] = 5,
        cursor_factory: Optional[Type[Cursor[Any]]] = None,
        context: Optional[AdaptContext] = None,
        **kwargs: Union[None, int, str],
    ) -> "Connection[TupleRow]": ...

    @classmethod  # type: ignore[misc] # https://github.com/python/mypy/issues/11004
    def connect(
        cls,
        conninfo: str = "",
        *,
        autocommit: bool = False,
        prepare_threshold: Optional[int] = 5,
        row_factory: Optional[RowFactory[Row]] = None,
        cursor_factory: Optional[Type[Cursor[Row]]] = None,
        context: Optional[AdaptContext] = None,
        **kwargs: Any,
    ) -> Self:
        """
        Connect to a database server and return a new `Connection` instance.
        """
        params = cls._get_connection_params(conninfo, **kwargs)
        timeout = timeout_from_conninfo(params)
        rv = None
        attempts = conninfo_attempts(params)
        for attempt in attempts:
            try:
                conninfo = make_conninfo(**attempt)
                rv = cls._wait_conn(cls._connect_gen(conninfo), timeout=timeout)
                break
            except e._NO_TRACEBACK as ex:
                if len(attempts) > 1:
                    logger.debug(
                        "connection attempt failed on host: %r, port: %r,"
                        " hostaddr: %r: %s",
                        attempt.get("host"),
                        attempt.get("port"),
                        attempt.get("hostaddr"),
                        str(ex),
                    )
                last_ex = ex

        if not rv:
            assert last_ex
            raise last_ex.with_traceback(None)

        rv._autocommit = bool(autocommit)
        if row_factory:
            rv.row_factory = row_factory
        if cursor_factory:
            rv.cursor_factory = cursor_factory
        if context:
            rv._adapters = AdaptersMap(context.adapters)
        rv.prepare_threshold = prepare_threshold
        return rv

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        if self.closed:
            return

        if exc_type:
            # try to rollback, but if there are problems (connection in a bad
            # state) just warn without clobbering the exception bubbling up.
            try:
                self.rollback()
            except Exception as exc2:
                logger.warning(
                    "error ignored in rollback on %s: %s",
                    self,
                    exc2,
                )
        else:
            self.commit()

        # Close the connection only if it doesn't belong to a pool.
        if not getattr(self, "_pool", None):
            self.close()

    @classmethod
    def _get_connection_params(cls, conninfo: str, **kwargs: Any) -> ConnDict:
        """Manipulate connection parameters before connecting.

        :param conninfo: Connection string as received by `~Connection.connect()`.
        :param kwargs: Overriding connection arguments as received by `!connect()`.
        :return: Connection arguments merged and eventually modified, in a
            format similar to `~conninfo.conninfo_to_dict()`.
        """
        return conninfo_to_dict(conninfo, **kwargs)

    def close(self) -> None:
        """Close the database connection."""
        if self.closed:
            return
        self._closed = True

        # TODO: maybe send a cancel on close, if the connection is ACTIVE?

        self.pgconn.finish()

    @overload
    def cursor(self, *, binary: bool = False) -> Cursor[Row]: ...

    @overload
    def cursor(
        self, *, binary: bool = False, row_factory: RowFactory[CursorRow]
    ) -> Cursor[CursorRow]: ...

    @overload
    def cursor(
        self,
        name: str,
        *,
        binary: bool = False,
        scrollable: Optional[bool] = None,
        withhold: bool = False,
    ) -> ServerCursor[Row]: ...

    @overload
    def cursor(
        self,
        name: str,
        *,
        binary: bool = False,
        row_factory: RowFactory[CursorRow],
        scrollable: Optional[bool] = None,
        withhold: bool = False,
    ) -> ServerCursor[CursorRow]: ...

    def cursor(
        self,
        name: str = "",
        *,
        binary: bool = False,
        row_factory: Optional[RowFactory[Any]] = None,
        scrollable: Optional[bool] = None,
        withhold: bool = False,
    ) -> Union[Cursor[Any], ServerCursor[Any]]:
        """
        Return a new cursor to send commands and queries to the connection.
        """
        self._check_connection_ok()

        if not row_factory:
            row_factory = self.row_factory

        cur: Union[Cursor[Any], ServerCursor[Any]]
        if name:
            cur = self.server_cursor_factory(
                self,
                name=name,
                row_factory=row_factory,
                scrollable=scrollable,
                withhold=withhold,
            )
        else:
            cur = self.cursor_factory(self, row_factory=row_factory)

        if binary:
            cur.format = BINARY

        return cur

    def execute(
        self,
        query: Query,
        params: Optional[Params] = None,
        *,
        prepare: Optional[bool] = None,
        binary: bool = False,
    ) -> Cursor[Row]:
        """Execute a query and return a cursor to read its results."""
        try:
            cur = self.cursor()
            if binary:
                cur.format = BINARY

            return cur.execute(query, params, prepare=prepare)

        except e._NO_TRACEBACK as ex:
            raise ex.with_traceback(None)

    def commit(self) -> None:
        """Commit any pending transaction to the database."""
        with self.lock:
            self.wait(self._commit_gen())

    def rollback(self) -> None:
        """Roll back to the start of any pending transaction."""
        with self.lock:
            self.wait(self._rollback_gen())

    @contextmanager
    def transaction(
        self,
        savepoint_name: Optional[str] = None,
        force_rollback: bool = False,
    ) -> Iterator[Transaction]:
        """
        Start a context block with a new transaction or nested transaction.

        :param savepoint_name: Name of the savepoint used to manage a nested
            transaction. If `!None`, one will be chosen automatically.
        :param force_rollback: Roll back the transaction at the end of the
            block even if there were no error (e.g. to try a no-op process).
        :rtype: Transaction
        """
        tx = Transaction(self, savepoint_name, force_rollback)
        if self._pipeline:
            with self.pipeline(), tx, self.pipeline():
                yield tx
        else:
            with tx:
                yield tx

    def notifies(self) -> Generator[Notify, None, None]:
        """
        Yield `Notify` objects as soon as they are received from the database.
        """
        while True:
            with self.lock:
                try:
                    ns = self.wait(notifies(self.pgconn))
                except e._NO_TRACEBACK as ex:
                    raise ex.with_traceback(None)
            enc = pgconn_encoding(self.pgconn)
            for pgn in ns:
                n = Notify(pgn.relname.decode(enc), pgn.extra.decode(enc), pgn.be_pid)
                yield n

    @contextmanager
    def pipeline(self) -> Iterator[Pipeline]:
        """Switch the connection into pipeline mode."""
        with self.lock:
            self._check_connection_ok()

            pipeline = self._pipeline
            if pipeline is None:
                # WARNING: reference loop, broken ahead.
                pipeline = self._pipeline = Pipeline(self)

        try:
            with pipeline:
                yield pipeline
        finally:
            if pipeline.level == 0:
                with self.lock:
                    assert pipeline is self._pipeline
                    self._pipeline = None

    def wait(self, gen: PQGen[RV], timeout: Optional[float] = 0.1) -> RV:
        """
        Consume a generator operating on the connection.

        The function must be used on generators that don't change connection
        fd (i.e. not on connect and reset).
        """
        try:
            return waiting.wait(gen, self.pgconn.socket, timeout=timeout)
        except KeyboardInterrupt:
            # On Ctrl-C, try to cancel the query in the server, otherwise
            # the connection will remain stuck in ACTIVE state.
            self._try_cancel(self.pgconn)
            try:
                waiting.wait(gen, self.pgconn.socket, timeout=timeout)
            except e.QueryCanceled:
                pass  # as expected
            raise

    @classmethod
    def _wait_conn(cls, gen: PQGenConn[RV], timeout: Optional[int]) -> RV:
        """Consume a connection generator."""
        return waiting.wait_conn(gen, timeout=timeout)

    def _set_autocommit(self, value: bool) -> None:
        with self.lock:
            self.wait(self._set_autocommit_gen(value))

    def _set_isolation_level(self, value: Optional[IsolationLevel]) -> None:
        with self.lock:
            self.wait(self._set_isolation_level_gen(value))

    def _set_read_only(self, value: Optional[bool]) -> None:
        with self.lock:
            self.wait(self._set_read_only_gen(value))

    def _set_deferrable(self, value: Optional[bool]) -> None:
        with self.lock:
            self.wait(self._set_deferrable_gen(value))

    def tpc_begin(self, xid: Union[Xid, str]) -> None:
        """
        Begin a TPC transaction with the given transaction ID `!xid`.
        """
        with self.lock:
            self.wait(self._tpc_begin_gen(xid))

    def tpc_prepare(self) -> None:
        """
        Perform the first phase of a transaction started with `tpc_begin()`.
        """
        try:
            with self.lock:
                self.wait(self._tpc_prepare_gen())
        except e.ObjectNotInPrerequisiteState as ex:
            raise e.NotSupportedError(str(ex)) from None

    def tpc_commit(self, xid: Union[Xid, str, None] = None) -> None:
        """
        Commit a prepared two-phase transaction.
        """
        with self.lock:
            self.wait(self._tpc_finish_gen("COMMIT", xid))

    def tpc_rollback(self, xid: Union[Xid, str, None] = None) -> None:
        """
        Roll back a prepared two-phase transaction.
        """
        with self.lock:
            self.wait(self._tpc_finish_gen("ROLLBACK", xid))

    def tpc_recover(self) -> List[Xid]:
        self._check_tpc()
        status = self.info.transaction_status
        with self.cursor(row_factory=args_row(Xid._from_record)) as cur:
            cur.execute(Xid._get_recover_query())
            res = cur.fetchall()

        if status == IDLE and self.info.transaction_status == INTRANS:
            self.rollback()

        return res
