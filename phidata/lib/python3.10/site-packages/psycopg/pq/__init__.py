"""
psycopg libpq wrapper

This package exposes the libpq functionalities as Python objects and functions.

The real implementation (the binding to the C library) is
implementation-dependant but all the implementations share the same interface.
"""

# Copyright (C) 2020 The Psycopg Team

import os
import logging
from typing import Callable, List, Type

from . import abc
from .misc import ConninfoOption, PGnotify, PGresAttDesc
from .misc import error_message
from ._enums import ConnStatus, DiagnosticField, ExecStatus, Format, Trace
from ._enums import Ping, PipelineStatus, PollingStatus, TransactionStatus

logger = logging.getLogger(__name__)

__impl__: str
"""The currently loaded implementation of the `!psycopg.pq` package.

Possible values include ``python``, ``c``, ``binary``.
"""

__build_version__: int
"""The libpq version the C package was built with.

A number in the same format of `~psycopg.ConnectionInfo.server_version`
representing the libpq used to build the speedup module (``c``, ``binary``) if
available.

Certain features might not be available if the built version is too old.
"""

version: Callable[[], int]
PGconn: Type[abc.PGconn]
PGresult: Type[abc.PGresult]
Conninfo: Type[abc.Conninfo]
Escaping: Type[abc.Escaping]
PGcancel: Type[abc.PGcancel]


def import_from_libpq() -> None:
    """
    Import pq objects implementation from the best libpq wrapper available.

    If an implementation is requested try to import only it, otherwise
    try to import the best implementation available.
    """
    # import these names into the module on success as side effect
    global __impl__, version, __build_version__
    global PGconn, PGresult, Conninfo, Escaping, PGcancel

    impl = os.environ.get("PSYCOPG_IMPL", "").lower()
    module = None
    attempts: List[str] = []

    def handle_error(name: str, e: Exception) -> None:
        if not impl:
            msg = f"couldn't import psycopg '{name}' implementation: {e}"
            logger.debug(msg)
            attempts.append(msg)
        else:
            msg = f"couldn't import requested psycopg '{name}' implementation: {e}"
            raise ImportError(msg) from e

    # The best implementation: fast but requires the system libpq installed
    if not impl or impl == "c":
        try:
            from psycopg_c import pq as module  # type: ignore
        except Exception as e:
            handle_error("c", e)

    # Second best implementation: fast and stand-alone
    if not module and (not impl or impl == "binary"):
        try:
            from psycopg_binary import pq as module  # type: ignore
        except Exception as e:
            handle_error("binary", e)

    # Pure Python implementation, slow and requires the system libpq installed.
    if not module and (not impl or impl == "python"):
        try:
            from . import pq_ctypes as module  # type: ignore[assignment]
        except Exception as e:
            handle_error("python", e)

    if module:
        __impl__ = module.__impl__
        version = module.version
        PGconn = module.PGconn
        PGresult = module.PGresult
        Conninfo = module.Conninfo
        Escaping = module.Escaping
        PGcancel = module.PGcancel
        __build_version__ = module.__build_version__
    elif impl:
        raise ImportError(f"requested psycopg implementation '{impl}' unknown")
    else:
        sattempts = "\n".join(f"- {attempt}" for attempt in attempts)
        raise ImportError(
            f"""\
no pq wrapper available.
Attempts made:
{sattempts}"""
        )


import_from_libpq()

__all__ = (
    "ConnStatus",
    "PipelineStatus",
    "PollingStatus",
    "TransactionStatus",
    "ExecStatus",
    "Ping",
    "DiagnosticField",
    "Format",
    "Trace",
    "PGconn",
    "PGnotify",
    "Conninfo",
    "PGresAttDesc",
    "error_message",
    "ConninfoOption",
    "version",
)
