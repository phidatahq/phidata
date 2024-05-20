"""
psycopg copy support
"""

# Copyright (C) 2020 The Psycopg Team

import re
import queue
import struct
import asyncio
import threading
from abc import ABC, abstractmethod
from types import TracebackType
from typing import Any, AsyncIterator, Dict, Generic, Iterator, List, Match, IO
from typing import Optional, Sequence, Tuple, Type, Union, TYPE_CHECKING

from . import pq
from . import adapt
from . import errors as e
from .abc import Buffer, ConnectionType, PQGen, Transformer
from ._compat import create_task, Self
from .pq.misc import connection_summary
from ._cmodule import _psycopg
from ._encodings import pgconn_encoding
from .generators import copy_from, copy_to, copy_end

if TYPE_CHECKING:
    from .cursor import BaseCursor, Cursor
    from .cursor_async import AsyncCursor
    from .connection import Connection  # noqa: F401
    from .connection_async import AsyncConnection  # noqa: F401

PY_TEXT = adapt.PyFormat.TEXT
PY_BINARY = adapt.PyFormat.BINARY

TEXT = pq.Format.TEXT
BINARY = pq.Format.BINARY

COPY_IN = pq.ExecStatus.COPY_IN
COPY_OUT = pq.ExecStatus.COPY_OUT

ACTIVE = pq.TransactionStatus.ACTIVE

# Size of data to accumulate before sending it down the network. We fill a
# buffer this size field by field, and when it passes the threshold size
# we ship it, so it may end up being bigger than this.
BUFFER_SIZE = 32 * 1024

# Maximum data size we want to queue to send to the libpq copy. Sending a
# buffer too big to be handled can cause an infinite loop in the libpq
# (#255) so we want to split it in more digestable chunks.
MAX_BUFFER_SIZE = 4 * BUFFER_SIZE
# Note: making this buffer too large, e.g.
# MAX_BUFFER_SIZE = 1024 * 1024
# makes operations *way* slower! Probably triggering some quadraticity
# in the libpq memory management and data sending.

# Max size of the write queue of buffers. More than that copy will block
# Each buffer should be around BUFFER_SIZE size.
QUEUE_SIZE = 1024


class BaseCopy(Generic[ConnectionType]):
    """
    Base implementation for the copy user interface.

    Two subclasses expose real methods with the sync/async differences.

    The difference between the text and binary format is managed by two
    different `Formatter` subclasses.

    Writing (the I/O part) is implemented in the subclasses by a `Writer` or
    `AsyncWriter` instance. Normally writing implies sending copy data to a
    database, but a different writer might be chosen, e.g. to stream data into
    a file for later use.
    """

    formatter: "Formatter"

    def __init__(
        self,
        cursor: "BaseCursor[ConnectionType, Any]",
        *,
        binary: Optional[bool] = None,
    ):
        self.cursor = cursor
        self.connection = cursor.connection
        self._pgconn = self.connection.pgconn

        result = cursor.pgresult
        if result:
            self._direction = result.status
            if self._direction != COPY_IN and self._direction != COPY_OUT:
                raise e.ProgrammingError(
                    "the cursor should have performed a COPY operation;"
                    f" its status is {pq.ExecStatus(self._direction).name} instead"
                )
        else:
            self._direction = COPY_IN

        if binary is None:
            binary = bool(result and result.binary_tuples)

        tx: Transformer = getattr(cursor, "_tx", None) or adapt.Transformer(cursor)
        if binary:
            self.formatter = BinaryFormatter(tx)
        else:
            self.formatter = TextFormatter(tx, encoding=pgconn_encoding(self._pgconn))

        self._finished = False

    def __repr__(self) -> str:
        cls = f"{self.__class__.__module__}.{self.__class__.__qualname__}"
        info = connection_summary(self._pgconn)
        return f"<{cls} {info} at 0x{id(self):x}>"

    def _enter(self) -> None:
        if self._finished:
            raise TypeError("copy blocks can be used only once")

    def set_types(self, types: Sequence[Union[int, str]]) -> None:
        """
        Set the types expected in a COPY operation.

        The types must be specified as a sequence of oid or PostgreSQL type
        names (e.g. ``int4``, ``timestamptz[]``).

        This operation overcomes the lack of metadata returned by PostgreSQL
        when a COPY operation begins:

        - On :sql:`COPY TO`, `!set_types()` allows to specify what types the
          operation returns. If `!set_types()` is not used, the data will be
          returned as unparsed strings or bytes instead of Python objects.

        - On :sql:`COPY FROM`, `!set_types()` allows to choose what type the
          database expects. This is especially useful in binary copy, because
          PostgreSQL will apply no cast rule.

        """
        registry = self.cursor.adapters.types
        oids = [t if isinstance(t, int) else registry.get_oid(t) for t in types]

        if self._direction == COPY_IN:
            self.formatter.transformer.set_dumper_types(oids, self.formatter.format)
        else:
            self.formatter.transformer.set_loader_types(oids, self.formatter.format)

    # High level copy protocol generators (state change of the Copy object)

    def _read_gen(self) -> PQGen[Buffer]:
        if self._finished:
            return memoryview(b"")

        res = yield from copy_from(self._pgconn)
        if isinstance(res, memoryview):
            return res

        # res is the final PGresult
        self._finished = True

        # This result is a COMMAND_OK which has info about the number of rows
        # returned, but not about the columns, which is instead an information
        # that was received on the COPY_OUT result at the beginning of COPY.
        # So, don't replace the results in the cursor, just update the rowcount.
        nrows = res.command_tuples
        self.cursor._rowcount = nrows if nrows is not None else -1
        return memoryview(b"")

    def _read_row_gen(self) -> PQGen[Optional[Tuple[Any, ...]]]:
        data = yield from self._read_gen()
        if not data:
            return None

        row = self.formatter.parse_row(data)
        if row is None:
            # Get the final result to finish the copy operation
            yield from self._read_gen()
            self._finished = True
            return None

        return row

    def _end_copy_out_gen(self, exc: Optional[BaseException]) -> PQGen[None]:
        if not exc:
            return

        if self._pgconn.transaction_status != ACTIVE:
            # The server has already finished to send copy data. The connection
            # is already in a good state.
            return

        # Throw a cancel to the server, then consume the rest of the copy data
        # (which might or might not have been already transferred entirely to
        # the client, so we won't necessary see the exception associated with
        # canceling).
        self.connection.cancel()
        try:
            while (yield from self._read_gen()):
                pass
        except e.QueryCanceled:
            pass


class Copy(BaseCopy["Connection[Any]"]):
    """Manage a :sql:`COPY` operation.

    :param cursor: the cursor where the operation is performed.
    :param binary: if `!True`, write binary format.
    :param writer: the object to write to destination. If not specified, write
        to the `!cursor` connection.

    Choosing `!binary` is not necessary if the cursor has executed a
    :sql:`COPY` operation, because the operation result describes the format
    too. The parameter is useful when a `!Copy` object is created manually and
    no operation is performed on the cursor, such as when using ``writer=``\\
    `~psycopg.copy.FileWriter`.

    """

    __module__ = "psycopg"

    writer: "Writer"

    def __init__(
        self,
        cursor: "Cursor[Any]",
        *,
        binary: Optional[bool] = None,
        writer: Optional["Writer"] = None,
    ):
        super().__init__(cursor, binary=binary)
        if not writer:
            writer = LibpqWriter(cursor)

        self.writer = writer
        self._write = writer.write

    def __enter__(self) -> Self:
        self._enter()
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self.finish(exc_val)

    # End user sync interface

    def __iter__(self) -> Iterator[Buffer]:
        """Implement block-by-block iteration on :sql:`COPY TO`."""
        while True:
            data = self.read()
            if not data:
                break
            yield data

    def read(self) -> Buffer:
        """
        Read an unparsed row after a :sql:`COPY TO` operation.

        Return an empty string when the data is finished.
        """
        return self.connection.wait(self._read_gen())

    def rows(self) -> Iterator[Tuple[Any, ...]]:
        """
        Iterate on the result of a :sql:`COPY TO` operation record by record.

        Note that the records returned will be tuples of unparsed strings or
        bytes, unless data types are specified using `set_types()`.
        """
        while True:
            record = self.read_row()
            if record is None:
                break
            yield record

    def read_row(self) -> Optional[Tuple[Any, ...]]:
        """
        Read a parsed row of data from a table after a :sql:`COPY TO` operation.

        Return `!None` when the data is finished.

        Note that the records returned will be tuples of unparsed strings or
        bytes, unless data types are specified using `set_types()`.
        """
        return self.connection.wait(self._read_row_gen())

    def write(self, buffer: Union[Buffer, str]) -> None:
        """
        Write a block of data to a table after a :sql:`COPY FROM` operation.

        If the :sql:`COPY` is in binary format `!buffer` must be `!bytes`. In
        text mode it can be either `!bytes` or `!str`.
        """
        data = self.formatter.write(buffer)
        if data:
            self._write(data)

    def write_row(self, row: Sequence[Any]) -> None:
        """Write a record to a table after a :sql:`COPY FROM` operation."""
        data = self.formatter.write_row(row)
        if data:
            self._write(data)

    def finish(self, exc: Optional[BaseException]) -> None:
        """Terminate the copy operation and free the resources allocated.

        You shouldn't need to call this function yourself: it is usually called
        by exit. It is available if, despite what is documented, you end up
        using the `Copy` object outside a block.
        """
        if self._direction == COPY_IN:
            data = self.formatter.end()
            if data:
                self._write(data)
            self.writer.finish(exc)
            self._finished = True
        else:
            self.connection.wait(self._end_copy_out_gen(exc))


class Writer(ABC):
    """
    A class to write copy data somewhere.
    """

    @abstractmethod
    def write(self, data: Buffer) -> None:
        """
        Write some data to destination.
        """
        ...

    def finish(self, exc: Optional[BaseException] = None) -> None:
        """
        Called when write operations are finished.

        If operations finished with an error, it will be passed to ``exc``.
        """
        pass


class LibpqWriter(Writer):
    """
    A `Writer` to write copy data to a Postgres database.
    """

    def __init__(self, cursor: "Cursor[Any]"):
        self.cursor = cursor
        self.connection = cursor.connection
        self._pgconn = self.connection.pgconn

    def write(self, data: Buffer) -> None:
        if len(data) <= MAX_BUFFER_SIZE:
            # Most used path: we don't need to split the buffer in smaller
            # bits, so don't make a copy.
            self.connection.wait(copy_to(self._pgconn, data))
        else:
            # Copy a buffer too large in chunks to avoid causing a memory
            # error in the libpq, which may cause an infinite loop (#255).
            for i in range(0, len(data), MAX_BUFFER_SIZE):
                self.connection.wait(
                    copy_to(self._pgconn, data[i : i + MAX_BUFFER_SIZE])
                )

    def finish(self, exc: Optional[BaseException] = None) -> None:
        bmsg: Optional[bytes]
        if exc:
            msg = f"error from Python: {type(exc).__qualname__} - {exc}"
            bmsg = msg.encode(pgconn_encoding(self._pgconn), "replace")
        else:
            bmsg = None

        try:
            res = self.connection.wait(copy_end(self._pgconn, bmsg))
        # The QueryCanceled is expected if we sent an exception message to
        # pgconn.put_copy_end(). The Python exception that generated that
        # cancelling is more important, so don't clobber it.
        except e.QueryCanceled:
            if not bmsg:
                raise
        else:
            self.cursor._results = [res]


class QueuedLibpqWriter(LibpqWriter):
    """
    A writer using a buffer to queue data to write to a Postgres database.

    `write()` returns immediately, so that the main thread can be CPU-bound
    formatting messages, while a worker thread can be IO-bound waiting to write
    on the connection.
    """

    def __init__(self, cursor: "Cursor[Any]"):
        super().__init__(cursor)

        self._queue: queue.Queue[Buffer] = queue.Queue(maxsize=QUEUE_SIZE)
        self._worker: Optional[threading.Thread] = None
        self._worker_error: Optional[BaseException] = None

    def worker(self) -> None:
        """Push data to the server when available from the copy queue.

        Terminate reading when the queue receives a false-y value, or in case
        of error.

        The function is designed to be run in a separate thread.
        """
        try:
            while True:
                data = self._queue.get(block=True, timeout=24 * 60 * 60)
                if not data:
                    break
                self.connection.wait(copy_to(self._pgconn, data))
        except BaseException as ex:
            # Propagate the error to the main thread.
            self._worker_error = ex

    def write(self, data: Buffer) -> None:
        if not self._worker:
            # warning: reference loop, broken by _write_end
            self._worker = threading.Thread(target=self.worker)
            self._worker.daemon = True
            self._worker.start()

        # If the worker thread raies an exception, re-raise it to the caller.
        if self._worker_error:
            raise self._worker_error

        if len(data) <= MAX_BUFFER_SIZE:
            # Most used path: we don't need to split the buffer in smaller
            # bits, so don't make a copy.
            self._queue.put(data)
        else:
            # Copy a buffer too large in chunks to avoid causing a memory
            # error in the libpq, which may cause an infinite loop (#255).
            for i in range(0, len(data), MAX_BUFFER_SIZE):
                self._queue.put(data[i : i + MAX_BUFFER_SIZE])

    def finish(self, exc: Optional[BaseException] = None) -> None:
        self._queue.put(b"")

        if self._worker:
            self._worker.join()
            self._worker = None  # break the loop

        # Check if the worker thread raised any exception before terminating.
        if self._worker_error:
            raise self._worker_error

        super().finish(exc)


class FileWriter(Writer):
    """
    A `Writer` to write copy data to a file-like object.

    :param file: the file where to write copy data. It must be open for writing
        in binary mode.
    """

    def __init__(self, file: IO[bytes]):
        self.file = file

    def write(self, data: Buffer) -> None:
        self.file.write(data)


class AsyncCopy(BaseCopy["AsyncConnection[Any]"]):
    """Manage an asynchronous :sql:`COPY` operation."""

    __module__ = "psycopg"

    writer: "AsyncWriter"

    def __init__(
        self,
        cursor: "AsyncCursor[Any]",
        *,
        binary: Optional[bool] = None,
        writer: Optional["AsyncWriter"] = None,
    ):
        super().__init__(cursor, binary=binary)

        if not writer:
            writer = AsyncLibpqWriter(cursor)

        self.writer = writer
        self._write = writer.write

    async def __aenter__(self) -> Self:
        self._enter()
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        await self.finish(exc_val)

    async def __aiter__(self) -> AsyncIterator[Buffer]:
        while True:
            data = await self.read()
            if not data:
                break
            yield data

    async def read(self) -> Buffer:
        return await self.connection.wait(self._read_gen())

    async def rows(self) -> AsyncIterator[Tuple[Any, ...]]:
        while True:
            record = await self.read_row()
            if record is None:
                break
            yield record

    async def read_row(self) -> Optional[Tuple[Any, ...]]:
        return await self.connection.wait(self._read_row_gen())

    async def write(self, buffer: Union[Buffer, str]) -> None:
        data = self.formatter.write(buffer)
        if data:
            await self._write(data)

    async def write_row(self, row: Sequence[Any]) -> None:
        data = self.formatter.write_row(row)
        if data:
            await self._write(data)

    async def finish(self, exc: Optional[BaseException]) -> None:
        if self._direction == COPY_IN:
            data = self.formatter.end()
            if data:
                await self._write(data)
            await self.writer.finish(exc)
            self._finished = True
        else:
            await self.connection.wait(self._end_copy_out_gen(exc))


class AsyncWriter(ABC):
    """
    A class to write copy data somewhere (for async connections).
    """

    @abstractmethod
    async def write(self, data: Buffer) -> None: ...

    async def finish(self, exc: Optional[BaseException] = None) -> None:
        pass


class AsyncLibpqWriter(AsyncWriter):
    """
    An `AsyncWriter` to write copy data to a Postgres database.
    """

    def __init__(self, cursor: "AsyncCursor[Any]"):
        self.cursor = cursor
        self.connection = cursor.connection
        self._pgconn = self.connection.pgconn

    async def write(self, data: Buffer) -> None:
        if len(data) <= MAX_BUFFER_SIZE:
            # Most used path: we don't need to split the buffer in smaller
            # bits, so don't make a copy.
            await self.connection.wait(copy_to(self._pgconn, data))
        else:
            # Copy a buffer too large in chunks to avoid causing a memory
            # error in the libpq, which may cause an infinite loop (#255).
            for i in range(0, len(data), MAX_BUFFER_SIZE):
                await self.connection.wait(
                    copy_to(self._pgconn, data[i : i + MAX_BUFFER_SIZE])
                )

    async def finish(self, exc: Optional[BaseException] = None) -> None:
        bmsg: Optional[bytes]
        if exc:
            msg = f"error from Python: {type(exc).__qualname__} - {exc}"
            bmsg = msg.encode(pgconn_encoding(self._pgconn), "replace")
        else:
            bmsg = None

        try:
            res = await self.connection.wait(copy_end(self._pgconn, bmsg))
        # The QueryCanceled is expected if we sent an exception message to
        # pgconn.put_copy_end(). The Python exception that generated that
        # cancelling is more important, so don't clobber it.
        except e.QueryCanceled:
            if not bmsg:
                raise
        else:
            self.cursor._results = [res]


class AsyncQueuedLibpqWriter(AsyncLibpqWriter):
    """
    An `AsyncWriter` using a buffer to queue data to write.

    `write()` returns immediately, so that the main thread can be CPU-bound
    formatting messages, while a worker thread can be IO-bound waiting to write
    on the connection.
    """

    def __init__(self, cursor: "AsyncCursor[Any]"):
        super().__init__(cursor)

        self._queue: asyncio.Queue[Buffer] = asyncio.Queue(maxsize=QUEUE_SIZE)
        self._worker: Optional[asyncio.Future[None]] = None

    async def worker(self) -> None:
        """Push data to the server when available from the copy queue.

        Terminate reading when the queue receives a false-y value.

        The function is designed to be run in a separate task.
        """
        while True:
            data = await self._queue.get()
            if not data:
                break
            await self.connection.wait(copy_to(self._pgconn, data))

    async def write(self, data: Buffer) -> None:
        if not self._worker:
            self._worker = create_task(self.worker())

        if len(data) <= MAX_BUFFER_SIZE:
            # Most used path: we don't need to split the buffer in smaller
            # bits, so don't make a copy.
            await self._queue.put(data)
        else:
            # Copy a buffer too large in chunks to avoid causing a memory
            # error in the libpq, which may cause an infinite loop (#255).
            for i in range(0, len(data), MAX_BUFFER_SIZE):
                await self._queue.put(data[i : i + MAX_BUFFER_SIZE])

    async def finish(self, exc: Optional[BaseException] = None) -> None:
        await self._queue.put(b"")

        if self._worker:
            await asyncio.gather(self._worker)
            self._worker = None  # break reference loops if any

        await super().finish(exc)


class Formatter(ABC):
    """
    A class which understand a copy format (text, binary).
    """

    format: pq.Format

    def __init__(self, transformer: Transformer):
        self.transformer = transformer
        self._write_buffer = bytearray()
        self._row_mode = False  # true if the user is using write_row()

    @abstractmethod
    def parse_row(self, data: Buffer) -> Optional[Tuple[Any, ...]]: ...

    @abstractmethod
    def write(self, buffer: Union[Buffer, str]) -> Buffer: ...

    @abstractmethod
    def write_row(self, row: Sequence[Any]) -> Buffer: ...

    @abstractmethod
    def end(self) -> Buffer: ...


class TextFormatter(Formatter):
    format = TEXT

    def __init__(self, transformer: Transformer, encoding: str = "utf-8"):
        super().__init__(transformer)
        self._encoding = encoding

    def parse_row(self, data: Buffer) -> Optional[Tuple[Any, ...]]:
        if data:
            return parse_row_text(data, self.transformer)
        else:
            return None

    def write(self, buffer: Union[Buffer, str]) -> Buffer:
        data = self._ensure_bytes(buffer)
        self._signature_sent = True
        return data

    def write_row(self, row: Sequence[Any]) -> Buffer:
        # Note down that we are writing in row mode: it means we will have
        # to take care of the end-of-copy marker too
        self._row_mode = True

        format_row_text(row, self.transformer, self._write_buffer)
        if len(self._write_buffer) > BUFFER_SIZE:
            buffer, self._write_buffer = self._write_buffer, bytearray()
            return buffer
        else:
            return b""

    def end(self) -> Buffer:
        buffer, self._write_buffer = self._write_buffer, bytearray()
        return buffer

    def _ensure_bytes(self, data: Union[Buffer, str]) -> Buffer:
        if isinstance(data, str):
            return data.encode(self._encoding)
        else:
            # Assume, for simplicity, that the user is not passing stupid
            # things to the write function. If that's the case, things
            # will fail downstream.
            return data


class BinaryFormatter(Formatter):
    format = BINARY

    def __init__(self, transformer: Transformer):
        super().__init__(transformer)
        self._signature_sent = False

    def parse_row(self, data: Buffer) -> Optional[Tuple[Any, ...]]:
        if not self._signature_sent:
            if data[: len(_binary_signature)] != _binary_signature:
                raise e.DataError(
                    "binary copy doesn't start with the expected signature"
                )
            self._signature_sent = True
            data = data[len(_binary_signature) :]

        elif data == _binary_trailer:
            return None

        return parse_row_binary(data, self.transformer)

    def write(self, buffer: Union[Buffer, str]) -> Buffer:
        data = self._ensure_bytes(buffer)
        self._signature_sent = True
        return data

    def write_row(self, row: Sequence[Any]) -> Buffer:
        # Note down that we are writing in row mode: it means we will have
        # to take care of the end-of-copy marker too
        self._row_mode = True

        if not self._signature_sent:
            self._write_buffer += _binary_signature
            self._signature_sent = True

        format_row_binary(row, self.transformer, self._write_buffer)
        if len(self._write_buffer) > BUFFER_SIZE:
            buffer, self._write_buffer = self._write_buffer, bytearray()
            return buffer
        else:
            return b""

    def end(self) -> Buffer:
        # If we have sent no data we need to send the signature
        # and the trailer
        if not self._signature_sent:
            self._write_buffer += _binary_signature
            self._write_buffer += _binary_trailer

        elif self._row_mode:
            # if we have sent data already, we have sent the signature
            # too (either with the first row, or we assume that in
            # block mode the signature is included).
            # Write the trailer only if we are sending rows (with the
            # assumption that who is copying binary data is sending the
            # whole format).
            self._write_buffer += _binary_trailer

        buffer, self._write_buffer = self._write_buffer, bytearray()
        return buffer

    def _ensure_bytes(self, data: Union[Buffer, str]) -> Buffer:
        if isinstance(data, str):
            raise TypeError("cannot copy str data in binary mode: use bytes instead")
        else:
            # Assume, for simplicity, that the user is not passing stupid
            # things to the write function. If that's the case, things
            # will fail downstream.
            return data


def _format_row_text(
    row: Sequence[Any], tx: Transformer, out: Optional[bytearray] = None
) -> bytearray:
    """Convert a row of objects to the data to send for copy."""
    if out is None:
        out = bytearray()

    if not row:
        out += b"\n"
        return out

    for item in row:
        if item is not None:
            dumper = tx.get_dumper(item, PY_TEXT)
            b = dumper.dump(item)
            out += _dump_re.sub(_dump_sub, b)
        else:
            out += rb"\N"
        out += b"\t"

    out[-1:] = b"\n"
    return out


def _format_row_binary(
    row: Sequence[Any], tx: Transformer, out: Optional[bytearray] = None
) -> bytearray:
    """Convert a row of objects to the data to send for binary copy."""
    if out is None:
        out = bytearray()

    out += _pack_int2(len(row))
    adapted = tx.dump_sequence(row, [PY_BINARY] * len(row))
    for b in adapted:
        if b is not None:
            out += _pack_int4(len(b))
            out += b
        else:
            out += _binary_null

    return out


def _parse_row_text(data: Buffer, tx: Transformer) -> Tuple[Any, ...]:
    if not isinstance(data, bytes):
        data = bytes(data)
    fields = data.split(b"\t")
    fields[-1] = fields[-1][:-1]  # drop \n
    row = [None if f == b"\\N" else _load_re.sub(_load_sub, f) for f in fields]
    return tx.load_sequence(row)


def _parse_row_binary(data: Buffer, tx: Transformer) -> Tuple[Any, ...]:
    row: List[Optional[Buffer]] = []
    nfields = _unpack_int2(data, 0)[0]
    pos = 2
    for i in range(nfields):
        length = _unpack_int4(data, pos)[0]
        pos += 4
        if length >= 0:
            row.append(data[pos : pos + length])
            pos += length
        else:
            row.append(None)

    return tx.load_sequence(row)


_pack_int2 = struct.Struct("!h").pack
_pack_int4 = struct.Struct("!i").pack
_unpack_int2 = struct.Struct("!h").unpack_from
_unpack_int4 = struct.Struct("!i").unpack_from

_binary_signature = (
    b"PGCOPY\n\xff\r\n\0"  # Signature
    b"\x00\x00\x00\x00"  # flags
    b"\x00\x00\x00\x00"  # extra length
)
_binary_trailer = b"\xff\xff"
_binary_null = b"\xff\xff\xff\xff"

_dump_re = re.compile(b"[\b\t\n\v\f\r\\\\]")
_dump_repl = {
    b"\b": b"\\b",
    b"\t": b"\\t",
    b"\n": b"\\n",
    b"\v": b"\\v",
    b"\f": b"\\f",
    b"\r": b"\\r",
    b"\\": b"\\\\",
}


def _dump_sub(m: Match[bytes], __map: Dict[bytes, bytes] = _dump_repl) -> bytes:
    return __map[m.group(0)]


_load_re = re.compile(b"\\\\[btnvfr\\\\]")
_load_repl = {v: k for k, v in _dump_repl.items()}


def _load_sub(m: Match[bytes], __map: Dict[bytes, bytes] = _load_repl) -> bytes:
    return __map[m.group(0)]


# Override functions with fast versions if available
if _psycopg:
    format_row_text = _psycopg.format_row_text
    format_row_binary = _psycopg.format_row_binary
    parse_row_text = _psycopg.parse_row_text
    parse_row_binary = _psycopg.parse_row_binary

else:
    format_row_text = _format_row_text
    format_row_binary = _format_row_binary
    parse_row_text = _parse_row_text
    parse_row_binary = _parse_row_binary
