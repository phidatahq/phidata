"""
psycopg -- PostgreSQL database adapter for Python
"""

# Copyright (C) 2020 The Psycopg Team

import logging

from . import pq  # noqa: F401 import early to stabilize side effects
from . import types
from . import postgres
from ._tpc import Xid
from .copy import Copy, AsyncCopy
from ._enums import IsolationLevel
from .cursor import Cursor
from .errors import Warning, Error, InterfaceError, DatabaseError
from .errors import DataError, OperationalError, IntegrityError
from .errors import InternalError, ProgrammingError, NotSupportedError
from ._column import Column
from ._pipeline import Pipeline, AsyncPipeline
from .connection import BaseConnection, Connection, Notify
from .transaction import Rollback, Transaction, AsyncTransaction
from .cursor_async import AsyncCursor
from .server_cursor import AsyncServerCursor, ServerCursor
from .client_cursor import AsyncClientCursor, ClientCursor
from ._connection_info import ConnectionInfo
from .connection_async import AsyncConnection

from . import dbapi20
from .dbapi20 import BINARY, DATETIME, NUMBER, ROWID, STRING
from .dbapi20 import Binary, Date, DateFromTicks, Time, TimeFromTicks
from .dbapi20 import Timestamp, TimestampFromTicks

from .version import __version__ as __version__  # noqa: F401

# Set the logger to a quiet default, can be enabled if needed
logger = logging.getLogger("psycopg")
if logger.level == logging.NOTSET:
    logger.setLevel(logging.WARNING)

# DBAPI compliance
connect = Connection.connect
apilevel = "2.0"
threadsafety = 2
paramstyle = "pyformat"

# register default adapters for PostgreSQL
adapters = postgres.adapters  # exposed by the package
postgres.register_default_adapters(adapters)

# After the default ones, because these can deal with the bytea oid better
dbapi20.register_dbapi20_adapters(adapters)

# Must come after all the types have been registered
types.array.register_all_arrays(adapters)

# Note: defining the exported methods helps both Sphynx in documenting that
# this is the canonical place to obtain them and should be used by MyPy too,
# so that function signatures are consistent with the documentation.
__all__ = [
    "AsyncClientCursor",
    "AsyncConnection",
    "AsyncCopy",
    "AsyncCursor",
    "AsyncPipeline",
    "AsyncServerCursor",
    "AsyncTransaction",
    "BaseConnection",
    "ClientCursor",
    "Column",
    "Connection",
    "ConnectionInfo",
    "Copy",
    "Cursor",
    "IsolationLevel",
    "Notify",
    "Pipeline",
    "Rollback",
    "ServerCursor",
    "Transaction",
    "Xid",
    # DBAPI exports
    "connect",
    "apilevel",
    "threadsafety",
    "paramstyle",
    "Warning",
    "Error",
    "InterfaceError",
    "DatabaseError",
    "DataError",
    "OperationalError",
    "IntegrityError",
    "InternalError",
    "ProgrammingError",
    "NotSupportedError",
    # DBAPI type constructors and singletons
    "Binary",
    "Date",
    "DateFromTicks",
    "Time",
    "TimeFromTicks",
    "Timestamp",
    "TimestampFromTicks",
    "BINARY",
    "DATETIME",
    "NUMBER",
    "ROWID",
    "STRING",
]
