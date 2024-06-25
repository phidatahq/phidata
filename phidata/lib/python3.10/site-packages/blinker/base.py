"""Signals and events.

A small implementation of signals, inspired by a snippet of Django signal
API client code seen in a blog post.  Signals are first-class objects and
each manages its own receivers and message emission.

The :func:`signal` function provides singleton behavior for named signals.
"""

from __future__ import annotations

import typing as t
import warnings
import weakref
from collections import defaultdict
from contextlib import contextmanager
from functools import cached_property
from inspect import iscoroutinefunction
from weakref import WeakValueDictionary

from ._utilities import make_id
from ._utilities import make_ref
from ._utilities import Symbol

if t.TYPE_CHECKING:
    import typing_extensions as te

    F = t.TypeVar("F", bound=t.Callable[..., t.Any])
    T = t.TypeVar("T")
    P = te.ParamSpec("P")

    class PAsyncWrapper(t.Protocol):
        def __call__(self, f: t.Callable[P, t.Awaitable[T]]) -> t.Callable[P, T]: ...

    class PSyncWrapper(t.Protocol):
        def __call__(self, f: t.Callable[P, T]) -> t.Callable[P, t.Awaitable[T]]: ...


ANY = Symbol("ANY")
"""Token for "any sender"."""
ANY_ID = 0


class Signal:
    """A notification emitter."""

    #: An :obj:`ANY` convenience synonym, allows ``Signal.ANY``
    #: without an additional import.
    ANY = ANY

    set_class: type[set[t.Any]] = set

    @cached_property
    def receiver_connected(self) -> Signal:
        """Emitted after each :meth:`connect`.

        The signal sender is the signal instance, and the :meth:`connect`
        arguments are passed through: *receiver*, *sender*, and *weak*.

        .. versionadded:: 1.2
        """
        return Signal(doc="Emitted after a receiver connects.")

    @cached_property
    def receiver_disconnected(self) -> Signal:
        """Emitted after :meth:`disconnect`.

        The sender is the signal instance, and the :meth:`disconnect` arguments
        are passed through: *receiver* and *sender*.

        Note, this signal is emitted **only** when :meth:`disconnect` is
        called explicitly.

        The disconnect signal can not be emitted by an automatic disconnect
        (due to a weakly referenced receiver or sender going out of scope),
        as the receiver and/or sender instances are no longer available for
        use at the time this signal would be emitted.

        An alternative approach is available by subscribing to
        :attr:`receiver_connected` and setting up a custom weakref cleanup
        callback on weak receivers and senders.

        .. versionadded:: 1.2
        """
        return Signal(doc="Emitted after a receiver disconnects.")

    def __init__(self, doc: str | None = None) -> None:
        """
        :param doc: Set the instance's ``__doc__`` attribute for documentation.
        """
        if doc:
            self.__doc__ = doc

        #: A mapping of connected receivers.
        #:
        #: The values of this mapping are not meaningful outside of the
        #: internal :class:`Signal` implementation, however the boolean value
        #: of the mapping is useful as an extremely efficient check to see if
        #: any receivers are connected to the signal.
        self.receivers: dict[
            t.Any, weakref.ref[t.Callable[..., t.Any]] | t.Callable[..., t.Any]
        ] = {}
        self.is_muted: bool = False
        self._by_receiver: dict[t.Any, set[t.Any]] = defaultdict(self.set_class)
        self._by_sender: dict[t.Any, set[t.Any]] = defaultdict(self.set_class)
        self._weak_senders: dict[t.Any, weakref.ref[t.Any]] = {}

    def connect(self, receiver: F, sender: t.Any = ANY, weak: bool = True) -> F:
        """Connect *receiver* to signal events sent by *sender*.

        :param receiver: A callable.  Will be invoked by :meth:`send` with
          `sender=` as a single positional argument and any ``kwargs`` that
          were provided to a call to :meth:`send`.

        :param sender: Any object or :obj:`ANY`, defaults to ``ANY``.
          Restricts notifications delivered to *receiver* to only those
          :meth:`send` emissions sent by *sender*.  If ``ANY``, the receiver
          will always be notified.  A *receiver* may be connected to
          multiple *sender* values on the same Signal through multiple calls
          to :meth:`connect`.

        :param weak: If true, the Signal will hold a weakref to *receiver*
          and automatically disconnect when *receiver* goes out of scope or
          is garbage collected.  Defaults to True.
        """
        receiver_id = make_id(receiver)
        sender_id = ANY_ID if sender is ANY else make_id(sender)

        if weak:
            self.receivers[receiver_id] = make_ref(
                receiver, self._make_cleanup_receiver(receiver_id)
            )
        else:
            self.receivers[receiver_id] = receiver

        self._by_sender[sender_id].add(receiver_id)
        self._by_receiver[receiver_id].add(sender_id)

        if sender is not ANY and sender_id not in self._weak_senders:
            # store a cleanup for weakref-able senders
            try:
                self._weak_senders[sender_id] = make_ref(
                    sender, self._make_cleanup_sender(sender_id)
                )
            except TypeError:
                pass

        if "receiver_connected" in self.__dict__ and self.receiver_connected.receivers:
            try:
                self.receiver_connected.send(
                    self, receiver=receiver, sender=sender, weak=weak
                )
            except TypeError:
                # TODO no explanation or test for this
                self.disconnect(receiver, sender)
                raise

        if _receiver_connected.receivers and self is not _receiver_connected:
            try:
                _receiver_connected.send(
                    self, receiver_arg=receiver, sender_arg=sender, weak_arg=weak
                )
            except TypeError:
                self.disconnect(receiver, sender)
                raise

        return receiver

    def connect_via(self, sender: t.Any, weak: bool = False) -> t.Callable[[F], F]:
        """Connect the decorated function as a receiver for *sender*.

        :param sender: Any object or :obj:`ANY`.  The decorated function
          will only receive :meth:`send` emissions sent by *sender*.  If
          ``ANY``, the receiver will always be notified.  A function may be
          decorated multiple times with differing *sender* values.

        :param weak: If true, the Signal will hold a weakref to the
          decorated function and automatically disconnect when *receiver*
          goes out of scope or is garbage collected.  Unlike
          :meth:`connect`, this defaults to False.

        The decorated function will be invoked by :meth:`send` with
          `sender=` as a single positional argument and any ``kwargs`` that
          were provided to the call to :meth:`send`.


        .. versionadded:: 1.1
        """

        def decorator(fn: F) -> F:
            self.connect(fn, sender, weak)
            return fn

        return decorator

    @contextmanager
    def connected_to(
        self, receiver: t.Callable[..., t.Any], sender: t.Any = ANY
    ) -> t.Generator[None, None, None]:
        """Execute a block with the signal temporarily connected to *receiver*.

        :param receiver: a receiver callable
        :param sender: optional, a sender to filter on

        This is a context manager for use in the ``with`` statement.  It can
        be useful in unit tests.  *receiver* is connected to the signal for
        the duration of the ``with`` block, and will be disconnected
        automatically when exiting the block:

        .. code-block:: python

          with on_ready.connected_to(receiver):
             # do stuff
             on_ready.send(123)

        .. versionadded:: 1.1

        """
        self.connect(receiver, sender=sender, weak=False)

        try:
            yield None
        finally:
            self.disconnect(receiver)

    @contextmanager
    def muted(self) -> t.Generator[None, None, None]:
        """Context manager for temporarily disabling signal.
        Useful for test purposes.
        """
        self.is_muted = True

        try:
            yield None
        finally:
            self.is_muted = False

    def temporarily_connected_to(
        self, receiver: t.Callable[..., t.Any], sender: t.Any = ANY
    ) -> t.ContextManager[None]:
        """An alias for :meth:`connected_to`.

        :param receiver: a receiver callable
        :param sender: optional, a sender to filter on

        .. versionadded:: 0.9

        .. deprecated:: 1.1
            Renamed to ``connected_to``. Will be removed in Blinker 1.9.
        """
        warnings.warn(
            "'temporarily_connected_to' is renamed to 'connected_to'. The old name is"
            " deprecated and will be removed in Blinker 1.9.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.connected_to(receiver, sender)

    def send(
        self,
        sender: t.Any | None = None,
        /,
        *,
        _async_wrapper: PAsyncWrapper | None = None,
        **kwargs: t.Any,
    ) -> list[tuple[t.Callable[..., t.Any], t.Any]]:
        """Emit this signal on behalf of *sender*, passing on ``kwargs``.

        Returns a list of 2-tuples, pairing receivers with their return
        value. The ordering of receiver notification is undefined.

        :param sender: Any object or ``None``.  If omitted, synonymous
          with ``None``.  Only accepts one positional argument.
        :param _async_wrapper: A callable that should wrap a coroutine
          receiver and run it when called synchronously.

        :param kwargs: Data to be sent to receivers.
        """
        if self.is_muted:
            return []

        results = []

        for receiver in self.receivers_for(sender):
            if iscoroutinefunction(receiver):
                if _async_wrapper is None:
                    raise RuntimeError("Cannot send to a coroutine function.")

                result = _async_wrapper(receiver)(sender, **kwargs)
            else:
                result = receiver(sender, **kwargs)

            results.append((receiver, result))

        return results

    async def send_async(
        self,
        sender: t.Any | None = None,
        /,
        *,
        _sync_wrapper: PSyncWrapper | None = None,
        **kwargs: t.Any,
    ) -> list[tuple[t.Callable[..., t.Any], t.Any]]:
        """Emit this signal on behalf of *sender*, passing on ``kwargs``.

        Returns a list of 2-tuples, pairing receivers with their return
        value. The ordering of receiver notification is undefined.

        :param sender: Any object or ``None``.  If omitted, synonymous
          with ``None``. Only accepts one positional argument.
        :param _sync_wrapper: A callable that should wrap a synchronous
          receiver and run it when awaited.

        :param kwargs: Data to be sent to receivers.
        """
        if self.is_muted:
            return []

        results = []

        for receiver in self.receivers_for(sender):
            if not iscoroutinefunction(receiver):
                if _sync_wrapper is None:
                    raise RuntimeError("Cannot send to a non-coroutine function.")

                result = await _sync_wrapper(receiver)(sender, **kwargs)
            else:
                result = await receiver(sender, **kwargs)

            results.append((receiver, result))

        return results

    def has_receivers_for(self, sender: t.Any) -> bool:
        """True if there is probably a receiver for *sender*.

        Performs an optimistic check only.  Does not guarantee that all
        weakly referenced receivers are still alive.  See
        :meth:`receivers_for` for a stronger search.

        """
        if not self.receivers:
            return False

        if self._by_sender[ANY_ID]:
            return True

        if sender is ANY:
            return False

        return make_id(sender) in self._by_sender

    def receivers_for(
        self, sender: t.Any
    ) -> t.Generator[t.Callable[..., t.Any], None, None]:
        """Iterate all live receivers listening for *sender*."""
        # TODO: test receivers_for(ANY)
        if not self.receivers:
            return

        sender_id = make_id(sender)

        if sender_id in self._by_sender:
            ids = self._by_sender[ANY_ID] | self._by_sender[sender_id]
        else:
            ids = self._by_sender[ANY_ID].copy()

        for receiver_id in ids:
            receiver = self.receivers.get(receiver_id)

            if receiver is None:
                continue

            if isinstance(receiver, weakref.ref):
                strong = receiver()

                if strong is None:
                    self._disconnect(receiver_id, ANY_ID)
                    continue

                yield strong
            else:
                yield receiver

    def disconnect(self, receiver: t.Callable[..., t.Any], sender: t.Any = ANY) -> None:
        """Disconnect *receiver* from this signal's events.

        :param receiver: a previously :meth:`connected<connect>` callable

        :param sender: a specific sender to disconnect from, or :obj:`ANY`
          to disconnect from all senders.  Defaults to ``ANY``.

        """
        sender_id: t.Hashable

        if sender is ANY:
            sender_id = ANY_ID
        else:
            sender_id = make_id(sender)

        receiver_id = make_id(receiver)
        self._disconnect(receiver_id, sender_id)

        if (
            "receiver_disconnected" in self.__dict__
            and self.receiver_disconnected.receivers
        ):
            self.receiver_disconnected.send(self, receiver=receiver, sender=sender)

    def _disconnect(self, receiver_id: t.Hashable, sender_id: t.Hashable) -> None:
        if sender_id == ANY_ID:
            if self._by_receiver.pop(receiver_id, None) is not None:
                for bucket in self._by_sender.values():
                    bucket.discard(receiver_id)

            self.receivers.pop(receiver_id, None)
        else:
            self._by_sender[sender_id].discard(receiver_id)
            self._by_receiver[receiver_id].discard(sender_id)

    def _make_cleanup_receiver(
        self, receiver_id: t.Hashable
    ) -> t.Callable[[weakref.ref[t.Callable[..., t.Any]]], None]:
        """Disconnect a receiver from all senders."""

        def cleanup(ref: weakref.ref[t.Callable[..., t.Any]]) -> None:
            self._disconnect(receiver_id, ANY_ID)

        return cleanup

    def _make_cleanup_sender(
        self, sender_id: t.Hashable
    ) -> t.Callable[[weakref.ref[t.Any]], None]:
        """Disconnect all receivers from a sender."""
        assert sender_id != ANY_ID

        def cleanup(ref: weakref.ref[t.Any]) -> None:
            self._weak_senders.pop(sender_id, None)

            for receiver_id in self._by_sender.pop(sender_id, ()):
                self._by_receiver[receiver_id].discard(sender_id)

        return cleanup

    def _cleanup_bookkeeping(self) -> None:
        """Prune unused sender/receiver bookkeeping. Not threadsafe.

        Connecting & disconnecting leave behind a small amount of bookkeeping
        for the receiver and sender values. Typical workloads using Blinker,
        for example in most web apps, Flask, CLI scripts, etc., are not
        adversely affected by this bookkeeping.

        With a long-running Python process performing dynamic signal routing
        with high volume- e.g. connecting to function closures, "senders" are
        all unique object instances, and doing all of this over and over- you
        may see memory usage will grow due to extraneous bookkeeping. (An empty
        set() for each stale sender/receiver pair.)

        This method will prune that bookkeeping away, with the caveat that such
        pruning is not threadsafe. The risk is that cleanup of a fully
        disconnected receiver/sender pair occurs while another thread is
        connecting that same pair. If you are in the highly dynamic, unique
        receiver/sender situation that has lead you to this method, that
        failure mode is perhaps not a big deal for you.
        """
        for mapping in (self._by_sender, self._by_receiver):
            for ident, bucket in list(mapping.items()):
                if not bucket:
                    mapping.pop(ident, None)

    def _clear_state(self) -> None:
        """Throw away all signal state.  Useful for unit tests."""
        self._weak_senders.clear()
        self.receivers.clear()
        self._by_sender.clear()
        self._by_receiver.clear()


_receiver_connected = Signal(
    """\
Sent by a :class:`Signal` after a receiver connects.

:argument: the Signal that was connected to
:keyword receiver_arg: the connected receiver
:keyword sender_arg: the sender to connect to
:keyword weak_arg: true if the connection to receiver_arg is a weak reference

.. deprecated:: 1.2
    Individual signals have their own :attr:`~Signal.receiver_connected` and
    :attr:`~Signal.receiver_disconnected` signals with a slightly simplified
    call signature. This global signal will be removed in Blinker 1.9.
"""
)


class NamedSignal(Signal):
    """A named generic notification emitter."""

    def __init__(self, name: str, doc: str | None = None) -> None:
        super().__init__(doc)

        #: The name of this signal.
        self.name: str = name

    def __repr__(self) -> str:
        base = super().__repr__()
        return f"{base[:-1]}; {self.name!r}>"  # noqa: E702


class Namespace(dict):  # type: ignore[type-arg]
    """A mapping of signal names to signals."""

    def signal(self, name: str, doc: str | None = None) -> NamedSignal:
        """Return the :class:`NamedSignal` *name*, creating it if required.

        Repeated calls to this function will return the same signal object.
        """
        try:
            return self[name]  # type: ignore[no-any-return]
        except KeyError:
            result = self.setdefault(name, NamedSignal(name, doc))
            return result  # type: ignore[no-any-return]


class _WeakNamespace(WeakValueDictionary):  # type: ignore[type-arg]
    """A weak mapping of signal names to signals.

    Automatically cleans up unused Signals when the last reference goes out
    of scope.  This namespace implementation exists for a measure of legacy
    compatibility with Blinker <= 1.2, and may be dropped in the future.

    .. versionadded:: 1.3

    .. deprecated:: 1.3
        Will be removed in Blinker 1.9.
    """

    def __init__(self) -> None:
        warnings.warn(
            "'WeakNamespace' is deprecated and will be removed in Blinker 1.9."
            " Use 'Namespace' instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__()

    def signal(self, name: str, doc: str | None = None) -> NamedSignal:
        """Return the :class:`NamedSignal` *name*, creating it if required.

        Repeated calls to this function will return the same signal object.

        """
        try:
            return self[name]  # type: ignore[no-any-return]
        except KeyError:
            result = self.setdefault(name, NamedSignal(name, doc))
            return result  # type: ignore[no-any-return]


default_namespace = Namespace()
"""A default namespace for creating named signals. :func:`signal` creates a
:class:`NamedSignal` in this namespace.
"""

signal = default_namespace.signal
"""Create a :class:`NamedSignal` in :data:`default_namespace`. Repeated calls
with the same name will return the same signal.
"""


def __getattr__(name: str) -> t.Any:
    if name == "reciever_connected":
        warnings.warn(
            "The global 'reciever_connected' signal is deprecated and will be"
            " removed in Blinker 1.9. Use 'Signal.receiver_connected' and"
            " 'Signal.reciever_disconnected' instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return _receiver_connected

    if name == "WeakNamespace":
        warnings.warn(
            "'WeakNamespace' is deprecated and will be removed in Blinker 1.9."
            " Use 'Namespace' instead.",
            DeprecationWarning,
            stacklevel=2,
        )

    raise AttributeError(name)
