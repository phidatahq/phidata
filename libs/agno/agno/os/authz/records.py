"""Per-record grants for resource types whose routes address one stored record.

A scope can name the records it covers: ``products:research:write`` grants one Product,
``products:own:write`` grants the caller's own Products, and ``products:write`` or
``products:*:write`` grants every Product. Under user isolation a grant that covers every
record narrows to the caller's own, so existing roles keep today's owner-only behaviour and
only an explicitly named record widens access.

A resource type opts in by registering a :class:`RecordType` on the app. The route gate then
resolves the record id from the path and decides the request; endpoints read the result with
:func:`record_owner_scope`.
"""

import asyncio
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, FrozenSet, List, Optional, Set, Tuple

OWN = "own"

# (record exists, its owner)
RecordOwner = Tuple[bool, Optional[str]]


@dataclass(frozen=True)
class RecordGrant:
    """Which records of one type a caller may act on."""

    every: bool = False
    own: bool = False
    ids: FrozenSet[str] = frozenset()

    @classmethod
    def from_ids(cls, ids: Set[str]) -> "RecordGrant":
        """Read a provider's ``accessible_resource_ids`` answer, where ``*`` means every record."""
        return cls(every="*" in ids, own=OWN in ids, ids=frozenset(ids - {"*", OWN}))

    def isolated(self) -> "RecordGrant":
        """User isolation narrows a grant on every record to the caller's own."""
        return RecordGrant(own=self.own or self.every, ids=self.ids)

    @property
    def empty(self) -> bool:
        return not (self.every or self.own or self.ids)


@dataclass(frozen=True)
class RecordType:
    """A resource type the route gate decides per record.

    Args:
        name: The scope namespace, e.g. ``products``.
        path: A regex whose first group is the record id, matched against the request path.
        owner: Returns whether the record exists and who owns it.
        aowner: Async twin of ``owner``. Defaults to ``owner`` in a worker thread.
        record_ids: Ids a role editor can grant, for the scope catalog.
        arecord_ids: Async twin of ``record_ids``.
        actions: The actions that take a per-record grant.
        label: The singular noun used in a denial, e.g. ``product``.
    """

    name: str
    path: str
    owner: Callable[[str], RecordOwner]
    aowner: Optional[Callable[[str], Any]] = None
    record_ids: Optional[Callable[[], List[str]]] = None
    arecord_ids: Optional[Callable[[], Any]] = None
    actions: Tuple[str, ...] = ("write", "delete")
    label: str = "record"
    _pattern: Any = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_pattern", re.compile(self.path))

    def owner_denial(self, owner: Optional[str]) -> str:
        """The 403 detail when an ``own`` grant does not cover the record."""
        if owner is None:
            return "Cannot modify unowned " + self.label
        return "Cannot modify " + self.label + " owned by another user"

    def match(self, path: str) -> Optional[str]:
        found = self._pattern.match(path)
        return found.group(1) if found else None

    async def aowner_of(self, record_id: str) -> RecordOwner:
        if self.aowner is not None:
            return await self.aowner(record_id)
        return await asyncio.to_thread(self.owner, record_id)

    async def agrantable_ids(self) -> List[str]:
        if self.arecord_ids is not None:
            return await self.arecord_ids()
        if self.record_ids is not None:
            return await asyncio.to_thread(self.record_ids)
        return []


def get_record_types(app_or_request: Any) -> Dict[str, RecordType]:
    """The record types registered on the app, keyed by name."""
    app = getattr(app_or_request, "app", app_or_request)
    return getattr(getattr(app, "state", None), "record_types", None) or {}


def match_record_route(app_or_request: Any, path: str) -> Optional[Tuple[RecordType, str]]:
    """The registered record type and id a path addresses, if any."""
    for record_type in get_record_types(app_or_request).values():
        record_id = record_type.match(path)
        if record_id is not None:
            return record_type, record_id
    return None


def record_owner_scope(request: Any) -> Tuple[bool, Optional[str]]:
    """``(decided, owner)`` for a record route.

    ``decided`` is False when the route gate did not decide this request, for example with
    authorization off or for a service-account token; the endpoint then applies its own owner
    check. When decided, ``owner`` is the caller if access came from an ``own`` grant, so storage
    still filters by owner, and None when the grant named the record or covered every record.
    """
    if not getattr(request.state, "record_grant_decided", False):
        return False, None
    return True, getattr(request.state, "record_owner", None)
