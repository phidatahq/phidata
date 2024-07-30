"""
psycopg async cursor objects
"""

# Copyright (C) 2020 The Psycopg Team

from types import TracebackType
from typing import Any, AsyncIterator, Iterable, List
from typing import Optional, Type, TYPE_CHECKING, overload
from contextlib import asynccontextmanager

from . import pq
from . import errors as e
from .abc import Query, Params
from .copy import AsyncCopy, AsyncWriter as AsyncCopyWriter
from .rows import Row, RowMaker, AsyncRowFactory
from .cursor import BaseCursor
from ._compat import Self
from ._pipeline import Pipeline

if TYPE_CHECKING:
    from .connection_async import AsyncConnection

ACTIVE = pq.TransactionStatus.ACTIVE


class AsyncCursor(BaseCursor["AsyncConnection[Any]", Row]):
    __module__ = "psycopg"
    __slots__ = ()

    @overload
    def __init__(self, connection: "AsyncConnection[Row]"): ...

    @overload
    def __init__(
        self, connection: "AsyncConnection[Any]", *, row_factory: AsyncRowFactory[Row]
    ): ...

    def __init__(
        self,
        connection: "AsyncConnection[Any]",
        *,
        row_factory: Optional[AsyncRowFactory[Row]] = None,
    ):
        super().__init__(connection)
        self._row_factory = row_factory or connection.row_factory

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        await self.close()

    async def close(self) -> None:
        self._close()

    @property
    def row_factory(self) -> AsyncRowFactory[Row]:
        return self._row_factory

    @row_factory.setter
    def row_factory(self, row_factory: AsyncRowFactory[Row]) -> None:
        self._row_factory = row_factory
        if self.pgresult:
            self._make_row = row_factory(self)

    def _make_row_maker(self) -> RowMaker[Row]:
        return self._row_factory(self)

    async def execute(
        self,
        query: Query,
        params: Optional[Params] = None,
        *,
        prepare: Optional[bool] = None,
        binary: Optional[bool] = None,
    ) -> Self:
        try:
            async with self._conn.lock:
                await self._conn.wait(
                    self._execute_gen(query, params, prepare=prepare, binary=binary)
                )
        except e._NO_TRACEBACK as ex:
            raise ex.with_traceback(None)
        return self

    async def executemany(
        self,
        query: Query,
        params_seq: Iterable[Params],
        *,
        returning: bool = False,
    ) -> None:
        try:
            if Pipeline.is_supported():
                # If there is already a pipeline, ride it, in order to avoid
                # sending unnecessary Sync.
                async with self._conn.lock:
                    p = self._conn._pipeline
                    if p:
                        await self._conn.wait(
                            self._executemany_gen_pipeline(query, params_seq, returning)
                        )
                # Otherwise, make a new one
                if not p:
                    async with self._conn.pipeline(), self._conn.lock:
                        await self._conn.wait(
                            self._executemany_gen_pipeline(query, params_seq, returning)
                        )
            else:
                async with self._conn.lock:
                    await self._conn.wait(
                        self._executemany_gen_no_pipeline(query, params_seq, returning)
                    )
        except e._NO_TRACEBACK as ex:
            raise ex.with_traceback(None)

    async def stream(
        self,
        query: Query,
        params: Optional[Params] = None,
        *,
        binary: Optional[bool] = None,
    ) -> AsyncIterator[Row]:
        if self._pgconn.pipeline_status:
            raise e.ProgrammingError("stream() cannot be used in pipeline mode")

        async with self._conn.lock:
            try:
                await self._conn.wait(
                    self._stream_send_gen(query, params, binary=binary)
                )
                first = True
                while await self._conn.wait(self._stream_fetchone_gen(first)):
                    # We know that, if we got a result, it has a single row.
                    rec: Row = self._tx.load_row(0, self._make_row)  # type: ignore
                    yield rec
                    first = False

            except e._NO_TRACEBACK as ex:
                raise ex.with_traceback(None)

            finally:
                if self._pgconn.transaction_status == ACTIVE:
                    # Try to cancel the query, then consume the results
                    # already received.
                    self._conn.cancel()
                    try:
                        while await self._conn.wait(
                            self._stream_fetchone_gen(first=False)
                        ):
                            pass
                    except Exception:
                        pass

                    # Try to get out of ACTIVE state. Just do a single attempt, which
                    # should work to recover from an error or query cancelled.
                    try:
                        await self._conn.wait(self._stream_fetchone_gen(first=False))
                    except Exception:
                        pass

    async def fetchone(self) -> Optional[Row]:
        await self._fetch_pipeline()
        self._check_result_for_fetch()
        record = self._tx.load_row(self._pos, self._make_row)
        if record is not None:
            self._pos += 1
        return record

    async def fetchmany(self, size: int = 0) -> List[Row]:
        await self._fetch_pipeline()
        self._check_result_for_fetch()
        assert self.pgresult

        if not size:
            size = self.arraysize
        records = self._tx.load_rows(
            self._pos,
            min(self._pos + size, self.pgresult.ntuples),
            self._make_row,
        )
        self._pos += len(records)
        return records

    async def fetchall(self) -> List[Row]:
        await self._fetch_pipeline()
        self._check_result_for_fetch()
        assert self.pgresult
        records = self._tx.load_rows(self._pos, self.pgresult.ntuples, self._make_row)
        self._pos = self.pgresult.ntuples
        return records

    async def __aiter__(self) -> AsyncIterator[Row]:
        await self._fetch_pipeline()
        self._check_result_for_fetch()

        def load(pos: int) -> Optional[Row]:
            return self._tx.load_row(pos, self._make_row)

        while True:
            row = load(self._pos)
            if row is None:
                break
            self._pos += 1
            yield row

    async def scroll(self, value: int, mode: str = "relative") -> None:
        await self._fetch_pipeline()
        self._scroll(value, mode)

    @asynccontextmanager
    async def copy(
        self,
        statement: Query,
        params: Optional[Params] = None,
        *,
        writer: Optional[AsyncCopyWriter] = None,
    ) -> AsyncIterator[AsyncCopy]:
        """
        :rtype: AsyncCopy
        """
        try:
            async with self._conn.lock:
                await self._conn.wait(self._start_copy_gen(statement, params))

            async with AsyncCopy(self, writer=writer) as copy:
                yield copy
        except e._NO_TRACEBACK as ex:
            raise ex.with_traceback(None)

        self._select_current_result(0)

    async def _fetch_pipeline(self) -> None:
        if (
            self._execmany_returning is not False
            and not self.pgresult
            and self._conn._pipeline
        ):
            async with self._conn.lock:
                await self._conn.wait(self._conn._pipeline._fetch_gen(flush=True))
