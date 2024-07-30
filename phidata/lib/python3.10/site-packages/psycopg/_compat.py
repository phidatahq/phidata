"""
compatibility functions for different Python versions
"""

# Copyright (C) 2021 The Psycopg Team

import sys
import asyncio
from typing import Any, Awaitable, Generator, Optional, Sequence, Union, TypeVar

# NOTE: TypeAlias cannot be exported by this module, as pyright special-cases it.
# For this raisin it must be imported directly from typing_extension where used.
# See https://github.com/microsoft/pyright/issues/4197
from typing_extensions import TypeAlias

if sys.version_info >= (3, 8):
    from typing import Protocol
else:
    from typing_extensions import Protocol

T = TypeVar("T")
FutureT: TypeAlias = Union["asyncio.Future[T]", Generator[Any, None, T], Awaitable[T]]

if sys.version_info >= (3, 8):
    create_task = asyncio.create_task
    from math import prod

else:

    def create_task(
        coro: FutureT[T], name: Optional[str] = None
    ) -> "asyncio.Future[T]":
        return asyncio.create_task(coro)

    from functools import reduce

    def prod(seq: Sequence[int]) -> int:
        return reduce(int.__mul__, seq, 1)


if sys.version_info >= (3, 9):
    from zoneinfo import ZoneInfo
    from functools import cache
    from collections import Counter, deque as Deque
else:
    from typing import Counter, Deque
    from functools import lru_cache
    from backports.zoneinfo import ZoneInfo

    cache = lru_cache(maxsize=None)

if sys.version_info >= (3, 10):
    from typing import TypeGuard
else:
    from typing_extensions import TypeGuard

if sys.version_info >= (3, 11):
    from typing import LiteralString, Self
else:
    from typing_extensions import LiteralString, Self

__all__ = [
    "Counter",
    "Deque",
    "LiteralString",
    "Protocol",
    "Self",
    "TypeGuard",
    "ZoneInfo",
    "cache",
    "create_task",
    "prod",
]
