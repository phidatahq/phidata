"""
Code concerned with waiting in different contexts (blocking, async, etc).

These functions are designed to consume the generators returned by the
`generators` module function and to return their final value.

"""

# Copyright (C) 2020 The Psycopg Team


import os
import sys
import select
import logging
import selectors
from typing import Optional
from asyncio import get_event_loop, wait_for, Event, TimeoutError
from selectors import DefaultSelector

from . import errors as e
from .abc import RV, PQGen, PQGenConn, WaitFunc
from ._enums import Wait as Wait, Ready as Ready  # re-exported
from ._cmodule import _psycopg

WAIT_R = Wait.R
WAIT_W = Wait.W
WAIT_RW = Wait.RW
READY_R = Ready.R
READY_W = Ready.W
READY_RW = Ready.RW

logger = logging.getLogger(__name__)


def wait_selector(gen: PQGen[RV], fileno: int, timeout: Optional[float] = None) -> RV:
    """
    Wait for a generator using the best strategy available.

    :param gen: a generator performing database operations and yielding
        `Ready` values when it would block.
    :param fileno: the file descriptor to wait on.
    :param timeout: timeout (in seconds) to check for other interrupt, e.g.
        to allow Ctrl-C.
    :type timeout: float
    :return: whatever `!gen` returns on completion.

    Consume `!gen`, scheduling `fileno` for completion when it is reported to
    block. Once ready again send the ready state back to `!gen`.
    """
    try:
        s = next(gen)
        with DefaultSelector() as sel:
            while True:
                sel.register(fileno, s)
                rlist = None
                while not rlist:
                    rlist = sel.select(timeout=timeout)
                sel.unregister(fileno)
                # note: this line should require a cast, but mypy doesn't complain
                ready: Ready = rlist[0][1]
                assert s & ready
                s = gen.send(ready)

    except StopIteration as ex:
        rv: RV = ex.args[0] if ex.args else None
        return rv


def wait_conn(gen: PQGenConn[RV], timeout: Optional[float] = None) -> RV:
    """
    Wait for a connection generator using the best strategy available.

    :param gen: a generator performing database operations and yielding
        (fd, `Ready`) pairs when it would block.
    :param timeout: timeout (in seconds) to check for other interrupt, e.g.
        to allow Ctrl-C. If zero or None, wait indefinitely.
    :type timeout: float
    :return: whatever `!gen` returns on completion.

    Behave like in `wait()`, but take the fileno to wait from the generator
    itself, which might change during processing.
    """
    try:
        fileno, s = next(gen)
        if not timeout:
            timeout = None
        with DefaultSelector() as sel:
            while True:
                sel.register(fileno, s)
                rlist = sel.select(timeout=timeout)
                sel.unregister(fileno)
                if not rlist:
                    raise e.ConnectionTimeout("connection timeout expired")
                ready: Ready = rlist[0][1]  # type: ignore[assignment]
                fileno, s = gen.send(ready)

    except StopIteration as ex:
        rv: RV = ex.args[0] if ex.args else None
        return rv


async def wait_async(
    gen: PQGen[RV], fileno: int, timeout: Optional[float] = None
) -> RV:
    """
    Coroutine waiting for a generator to complete.

    :param gen: a generator performing database operations and yielding
        `Ready` values when it would block.
    :param fileno: the file descriptor to wait on.
    :return: whatever `!gen` returns on completion.

    Behave like in `wait()`, but exposing an `asyncio` interface.
    """
    # Use an event to block and restart after the fd state changes.
    # Not sure this is the best implementation but it's a start.
    ev = Event()
    loop = get_event_loop()
    ready: Ready
    s: Wait

    def wakeup(state: Ready) -> None:
        nonlocal ready
        ready |= state  # type: ignore[assignment]
        ev.set()

    try:
        s = next(gen)
        while True:
            reader = s & WAIT_R
            writer = s & WAIT_W
            if not reader and not writer:
                raise e.InternalError(f"bad poll status: {s}")
            ev.clear()
            ready = 0  # type: ignore[assignment]
            if reader:
                loop.add_reader(fileno, wakeup, READY_R)
            if writer:
                loop.add_writer(fileno, wakeup, READY_W)
            try:
                if timeout is None:
                    await ev.wait()
                else:
                    try:
                        await wait_for(ev.wait(), timeout)
                    except TimeoutError:
                        pass
            finally:
                if reader:
                    loop.remove_reader(fileno)
                if writer:
                    loop.remove_writer(fileno)
            s = gen.send(ready)

    except StopIteration as ex:
        rv: RV = ex.args[0] if ex.args else None
        return rv


async def wait_conn_async(gen: PQGenConn[RV], timeout: Optional[float] = None) -> RV:
    """
    Coroutine waiting for a connection generator to complete.

    :param gen: a generator performing database operations and yielding
        (fd, `Ready`) pairs when it would block.
    :param timeout: timeout (in seconds) to check for other interrupt, e.g.
        to allow Ctrl-C. If zero or None, wait indefinitely.
    :return: whatever `!gen` returns on completion.

    Behave like in `wait()`, but take the fileno to wait from the generator
    itself, which might change during processing.
    """
    # Use an event to block and restart after the fd state changes.
    # Not sure this is the best implementation but it's a start.
    ev = Event()
    loop = get_event_loop()
    ready: Ready
    s: Wait

    def wakeup(state: Ready) -> None:
        nonlocal ready
        ready = state
        ev.set()

    try:
        fileno, s = next(gen)
        if not timeout:
            timeout = None
        while True:
            reader = s & WAIT_R
            writer = s & WAIT_W
            if not reader and not writer:
                raise e.InternalError(f"bad poll status: {s}")
            ev.clear()
            ready = 0  # type: ignore[assignment]
            if reader:
                loop.add_reader(fileno, wakeup, READY_R)
            if writer:
                loop.add_writer(fileno, wakeup, READY_W)
            try:
                await wait_for(ev.wait(), timeout)
            finally:
                if reader:
                    loop.remove_reader(fileno)
                if writer:
                    loop.remove_writer(fileno)
            fileno, s = gen.send(ready)

    except TimeoutError:
        raise e.ConnectionTimeout("connection timeout expired")

    except StopIteration as ex:
        rv: RV = ex.args[0] if ex.args else None
        return rv


# Specialised implementation of wait functions.


def wait_select(gen: PQGen[RV], fileno: int, timeout: Optional[float] = None) -> RV:
    """
    Wait for a generator using select where supported.

    BUG: on Linux, can't select on FD >= 1024. On Windows it's fine.
    """
    try:
        s = next(gen)

        empty = ()
        fnlist = (fileno,)
        while True:
            rl, wl, xl = select.select(
                fnlist if s & WAIT_R else empty,
                fnlist if s & WAIT_W else empty,
                fnlist,
                timeout,
            )
            ready = 0
            if rl:
                ready = READY_R
            if wl:
                ready |= READY_W
            if not ready:
                continue
            # assert s & ready
            s = gen.send(ready)  # type: ignore

    except StopIteration as ex:
        rv: RV = ex.args[0] if ex.args else None
        return rv


if hasattr(selectors, "EpollSelector"):
    _epoll_evmasks = {
        WAIT_R: select.EPOLLONESHOT | select.EPOLLIN | select.EPOLLERR,
        WAIT_W: select.EPOLLONESHOT | select.EPOLLOUT | select.EPOLLERR,
        WAIT_RW: select.EPOLLONESHOT
        | (select.EPOLLIN | select.EPOLLOUT | select.EPOLLERR),
    }
else:
    _epoll_evmasks = {}


def wait_epoll(gen: PQGen[RV], fileno: int, timeout: Optional[float] = None) -> RV:
    """
    Wait for a generator using epoll where supported.

    Parameters are like for `wait()`. If it is detected that the best selector
    strategy is `epoll` then this function will be used instead of `wait`.

    See also: https://linux.die.net/man/2/epoll_ctl

    BUG: if the connection FD is closed, `epoll.poll()` hangs. Same for
    EpollSelector. For this reason, wait_poll() is currently preferable.
    To reproduce the bug:

        export PSYCOPG_WAIT_FUNC=wait_epoll
        pytest tests/test_concurrency.py::test_concurrent_close
    """
    try:
        s = next(gen)

        if timeout is None or timeout < 0:
            timeout = 0
        else:
            timeout = int(timeout * 1000.0)

        with select.epoll() as epoll:
            evmask = _epoll_evmasks[s]
            epoll.register(fileno, evmask)
            while True:
                fileevs = None
                while not fileevs:
                    fileevs = epoll.poll(timeout)
                ev = fileevs[0][1]
                ready = 0
                if ev & ~select.EPOLLOUT:
                    ready = READY_R
                if ev & ~select.EPOLLIN:
                    ready |= READY_W
                # assert s & ready
                s = gen.send(ready)
                evmask = _epoll_evmasks[s]
                epoll.modify(fileno, evmask)

    except StopIteration as ex:
        rv: RV = ex.args[0] if ex.args else None
        return rv


if hasattr(selectors, "PollSelector"):
    _poll_evmasks = {
        WAIT_R: select.POLLIN,
        WAIT_W: select.POLLOUT,
        WAIT_RW: select.POLLIN | select.POLLOUT,
    }
else:
    _poll_evmasks = {}


def wait_poll(gen: PQGen[RV], fileno: int, timeout: Optional[float] = None) -> RV:
    """
    Wait for a generator using poll where supported.

    Parameters are like for `wait()`.
    """
    try:
        s = next(gen)

        if timeout is None or timeout < 0:
            timeout = 0
        else:
            timeout = int(timeout * 1000.0)

        poll = select.poll()
        evmask = _poll_evmasks[s]
        poll.register(fileno, evmask)
        while True:
            fileevs = None
            while not fileevs:
                fileevs = poll.poll(timeout)
            ev = fileevs[0][1]
            ready = 0
            if ev & ~select.POLLOUT:
                ready = READY_R
            if ev & ~select.POLLIN:
                ready |= READY_W
            # assert s & ready
            s = gen.send(ready)
            evmask = _poll_evmasks[s]
            poll.modify(fileno, evmask)

    except StopIteration as ex:
        rv: RV = ex.args[0] if ex.args else None
        return rv


def _is_select_patched() -> bool:
    """
    Detect if some greenlet library has patched the select library.

    If this is the case, avoid to use the wait_c function as it doesn't behave
    in a collaborative way.

    Currently supported: gevent.
    """
    # If not imported, don't import it.
    m = sys.modules.get("gevent.monkey")
    if m:
        try:
            if m.is_module_patched("select"):
                return True
        except Exception as ex:
            logger.warning("failed to detect gevent monkey-patching: %s", ex)

    return False


if _psycopg:
    wait_c = _psycopg.wait_c


# Choose the best wait strategy for the platform.
#
# the selectors objects have a generic interface but come with some overhead,
# so we also offer more finely tuned implementations.

wait: WaitFunc

# Allow the user to choose a specific function for testing
if "PSYCOPG_WAIT_FUNC" in os.environ:
    fname = os.environ["PSYCOPG_WAIT_FUNC"]
    if not fname.startswith("wait_") or fname not in globals():
        raise ImportError(
            "PSYCOPG_WAIT_FUNC should be the name of an available wait function;"
            f" got {fname!r}"
        )
    wait = globals()[fname]

# On Windows, for the moment, avoid using wait_c, because it was reported to
# use excessive CPU (see #645).
# TODO: investigate why.
elif _psycopg and sys.platform != "win32" and not _is_select_patched():
    wait = wait_c

elif selectors.DefaultSelector is getattr(selectors, "SelectSelector", None):
    # On Windows, SelectSelector should be the default.
    wait = wait_select

elif hasattr(selectors, "PollSelector"):
    # On linux, EpollSelector is the default. However, it hangs if the fd is
    # closed while polling.
    wait = wait_poll

else:
    wait = wait_selector
