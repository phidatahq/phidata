"""
CockroachDB support package.
"""

# Copyright (C) 2022 The Psycopg Team

from . import _types
from .connection import CrdbConnection, AsyncCrdbConnection, CrdbConnectionInfo

adapters = _types.adapters  # exposed by the package
connect = CrdbConnection.connect

_types.register_crdb_adapters(adapters)

__all__ = [
    "AsyncCrdbConnection",
    "CrdbConnection",
    "CrdbConnectionInfo",
]
