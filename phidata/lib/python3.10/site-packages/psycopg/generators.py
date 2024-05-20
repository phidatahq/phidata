"""
Generators implementing communication protocols with the libpq

Certain operations (connection, querying) are an interleave of libpq calls and
waiting for the socket to be ready. This module contains the code to execute
the operations, yielding a polling state whenever there is to wait. The
functions in the `waiting` module are the ones who wait more or less
cooperatively for the socket to be ready and make these generators continue.

All these generators yield pairs (fileno, `Wait`) whenever an operation would
block. The generator can be restarted sending the appropriate `Ready` state
when the file descriptor is ready.

"""

# Copyright (C) 2020 The Psycopg Team

import logging
from typing import List, Optional, Union

from . import pq
from . import errors as e
from .abc import Buffer, PipelineCommand, PQGen, PQGenConn
from .pq.abc import PGconn, PGresult
from .waiting import Wait, Ready
from ._compat import Deque
from ._cmodule import _psycopg
from ._encodings import pgconn_encoding, conninfo_encoding

OK = pq.ConnStatus.OK
BAD = pq.ConnStatus.BAD

POLL_OK = pq.PollingStatus.OK
POLL_READING = pq.PollingStatus.READING
POLL_WRITING = pq.PollingStatus.WRITING
POLL_FAILED = pq.PollingStatus.FAILED

COMMAND_OK = pq.ExecStatus.COMMAND_OK
COPY_OUT = pq.ExecStatus.COPY_OUT
COPY_IN = pq.ExecStatus.COPY_IN
COPY_BOTH = pq.ExecStatus.COPY_BOTH
PIPELINE_SYNC = pq.ExecStatus.PIPELINE_SYNC

WAIT_R = Wait.R
WAIT_W = Wait.W
WAIT_RW = Wait.RW
READY_R = Ready.R
READY_W = Ready.W
READY_RW = Ready.RW

logger = logging.getLogger(__name__)


def _connect(conninfo: str) -> PQGenConn[PGconn]:
    """
    Generator to create a database connection without blocking.

    """
    conn = pq.PGconn.connect_start(conninfo.encode())
    while True:
        if conn.status == BAD:
            encoding = conninfo_encoding(conninfo)
            raise e.OperationalError(
                f"connection is bad: {pq.error_message(conn, encoding=encoding)}",
                pgconn=conn,
            )

        status = conn.connect_poll()
        if status == POLL_OK:
            break
        elif status == POLL_READING:
            yield conn.socket, WAIT_R
        elif status == POLL_WRITING:
            yield conn.socket, WAIT_W
        elif status == POLL_FAILED:
            encoding = conninfo_encoding(conninfo)
            raise e.OperationalError(
                f"connection failed: {pq.error_message(conn, encoding=encoding)}",
                pgconn=e.finish_pgconn(conn),
            )
        else:
            raise e.InternalError(
                f"unexpected poll status: {status}", pgconn=e.finish_pgconn(conn)
            )

    conn.nonblocking = 1
    return conn


def _execute(pgconn: PGconn) -> PQGen[List[PGresult]]:
    """
    Generator sending a query and returning results without blocking.

    The query must have already been sent using `pgconn.send_query()` or
    similar. Flush the query and then return the result using nonblocking
    functions.

    Return the list of results returned by the database (whether success
    or error).
    """
    yield from _send(pgconn)
    rv = yield from _fetch_many(pgconn)
    return rv


def _send(pgconn: PGconn) -> PQGen[None]:
    """
    Generator to send a query to the server without blocking.

    The query must have already been sent using `pgconn.send_query()` or
    similar. Flush the query and then return the result using nonblocking
    functions.

    After this generator has finished you may want to cycle using `fetch()`
    to retrieve the results available.
    """
    while True:
        f = pgconn.flush()
        if f == 0:
            break

        ready = yield WAIT_RW
        if ready & READY_R:
            # This call may read notifies: they will be saved in the
            # PGconn buffer and passed to Python later, in `fetch()`.
            pgconn.consume_input()


def _fetch_many(pgconn: PGconn) -> PQGen[List[PGresult]]:
    """
    Generator retrieving results from the database without blocking.

    The query must have already been sent to the server, so pgconn.flush() has
    already returned 0.

    Return the list of results returned by the database (whether success
    or error).
    """
    results: List[PGresult] = []
    while True:
        res = yield from _fetch(pgconn)
        if not res:
            break

        results.append(res)
        status = res.status
        if status == COPY_IN or status == COPY_OUT or status == COPY_BOTH:
            # After entering copy mode the libpq will create a phony result
            # for every request so let's break the endless loop.
            break

        if status == PIPELINE_SYNC:
            # PIPELINE_SYNC is not followed by a NULL, but we return it alone
            # similarly to other result sets.
            assert len(results) == 1, results
            break

    return results


def _fetch(pgconn: PGconn) -> PQGen[Optional[PGresult]]:
    """
    Generator retrieving a single result from the database without blocking.

    The query must have already been sent to the server, so pgconn.flush() has
    already returned 0.

    Return a result from the database (whether success or error).
    """
    if pgconn.is_busy():
        yield WAIT_R
        while True:
            pgconn.consume_input()
            if not pgconn.is_busy():
                break
            yield WAIT_R

    _consume_notifies(pgconn)

    return pgconn.get_result()


def _pipeline_communicate(
    pgconn: PGconn, commands: Deque[PipelineCommand]
) -> PQGen[List[List[PGresult]]]:
    """Generator to send queries from a connection in pipeline mode while also
    receiving results.

    Return a list results, including single PIPELINE_SYNC elements.
    """
    results = []

    while True:
        ready = yield WAIT_RW

        if ready & READY_R:
            pgconn.consume_input()
            _consume_notifies(pgconn)

            res: List[PGresult] = []
            while not pgconn.is_busy():
                r = pgconn.get_result()
                if r is None:
                    if not res:
                        break
                    results.append(res)
                    res = []
                else:
                    status = r.status
                    if status == PIPELINE_SYNC:
                        assert not res
                        results.append([r])
                    elif status == COPY_IN or status == COPY_OUT or status == COPY_BOTH:
                        # This shouldn't happen, but insisting hard enough, it will.
                        # For instance, in test_executemany_badquery(), with the COPY
                        # statement and the AsyncClientCursor, which disables
                        # prepared statements).
                        # Bail out from the resulting infinite loop.
                        raise e.NotSupportedError(
                            "COPY cannot be used in pipeline mode"
                        )
                    else:
                        res.append(r)

        if ready & READY_W:
            pgconn.flush()
            if not commands:
                break
            commands.popleft()()

    return results


def _consume_notifies(pgconn: PGconn) -> None:
    # Consume notifies
    while True:
        n = pgconn.notifies()
        if not n:
            break
        if pgconn.notify_handler:
            pgconn.notify_handler(n)


def notifies(pgconn: PGconn) -> PQGen[List[pq.PGnotify]]:
    yield WAIT_R
    pgconn.consume_input()

    ns = []
    while True:
        n = pgconn.notifies()
        if n:
            ns.append(n)
        else:
            break

    return ns


def copy_from(pgconn: PGconn) -> PQGen[Union[memoryview, PGresult]]:
    while True:
        nbytes, data = pgconn.get_copy_data(1)
        if nbytes != 0:
            break

        # would block
        yield WAIT_R
        pgconn.consume_input()

    if nbytes > 0:
        # some data
        return data

    # Retrieve the final result of copy
    results = yield from _fetch_many(pgconn)
    if len(results) > 1:
        # TODO: too brutal? Copy worked.
        raise e.ProgrammingError("you cannot mix COPY with other operations")
    result = results[0]
    if result.status != COMMAND_OK:
        encoding = pgconn_encoding(pgconn)
        raise e.error_from_result(result, encoding=encoding)

    return result


def copy_to(pgconn: PGconn, buffer: Buffer) -> PQGen[None]:
    # Retry enqueuing data until successful.
    #
    # WARNING! This can cause an infinite loop if the buffer is too large. (see
    # ticket #255). We avoid it in the Copy object by splitting a large buffer
    # into smaller ones. We prefer to do it there instead of here in order to
    # do it upstream the queue decoupling the writer task from the producer one.
    while pgconn.put_copy_data(buffer) == 0:
        yield WAIT_W


def copy_end(pgconn: PGconn, error: Optional[bytes]) -> PQGen[PGresult]:
    # Retry enqueuing end copy message until successful
    while pgconn.put_copy_end(error) == 0:
        yield WAIT_W

    # Repeat until it the message is flushed to the server
    while True:
        yield WAIT_W
        f = pgconn.flush()
        if f == 0:
            break

    # Retrieve the final result of copy
    (result,) = yield from _fetch_many(pgconn)
    if result.status != COMMAND_OK:
        encoding = pgconn_encoding(pgconn)
        raise e.error_from_result(result, encoding=encoding)

    return result


# Override functions with fast versions if available
if _psycopg:
    connect = _psycopg.connect
    execute = _psycopg.execute
    send = _psycopg.send
    fetch_many = _psycopg.fetch_many
    fetch = _psycopg.fetch
    pipeline_communicate = _psycopg.pipeline_communicate

else:
    connect = _connect
    execute = _execute
    send = _send
    fetch_many = _fetch_many
    fetch = _fetch
    pipeline_communicate = _pipeline_communicate
