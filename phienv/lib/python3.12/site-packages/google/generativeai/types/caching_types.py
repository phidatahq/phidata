# -*- coding: utf-8 -*-
# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from __future__ import annotations

import datetime
from typing import Union
from typing_extensions import TypedDict

__all__ = [
    "ExpireTime",
    "TTL",
    "TTLTypes",
    "ExpireTimeTypes",
]


class TTL(TypedDict):
    # Represents datetime.datetime.now() + desired ttl
    seconds: int
    nanos: int


class ExpireTime(TypedDict):
    # Represents seconds of UTC time since Unix epoch
    seconds: int
    nanos: int


TTLTypes = Union[TTL, int, datetime.timedelta]
ExpireTimeTypes = Union[ExpireTime, int, datetime.datetime]


def to_optional_ttl(ttl: TTLTypes | None) -> TTL | None:
    if ttl is None:
        return None
    elif isinstance(ttl, datetime.timedelta):
        return {
            "seconds": int(ttl.total_seconds()),
            "nanos": int(ttl.microseconds * 1000),
        }
    elif isinstance(ttl, dict):
        return ttl
    elif isinstance(ttl, int):
        return {"seconds": ttl, "nanos": 0}
    else:
        raise TypeError(
            f"Could not convert input to `ttl` \n'" f"  type: {type(ttl)}\n",
            ttl,
        )


def to_optional_expire_time(expire_time: ExpireTimeTypes | None) -> ExpireTime | None:
    if expire_time is None:
        return expire_time
    elif isinstance(expire_time, datetime.datetime):
        timestamp = expire_time.timestamp()
        seconds = int(timestamp)
        nanos = int((seconds % 1) * 1000)
        return {
            "seconds": seconds,
            "nanos": nanos,
        }
    elif isinstance(expire_time, dict):
        return expire_time
    elif isinstance(expire_time, int):
        return {"seconds": expire_time, "nanos": 0}
    else:
        raise TypeError(
            f"Could not convert input to `expire_time` \n'" f"  type: {type(expire_time)}\n",
            expire_time,
        )
