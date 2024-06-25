"""
Various functionalities to make easier to work with the libpq.
"""

# Copyright (C) 2020 The Psycopg Team

import os
import sys
import logging
import ctypes.util
from typing import cast, NamedTuple, Optional, Union

from .abc import PGconn, PGresult
from ._enums import ConnStatus, TransactionStatus, PipelineStatus
from .._compat import cache
from .._encodings import pgconn_encoding

logger = logging.getLogger("psycopg.pq")

OK = ConnStatus.OK


class PGnotify(NamedTuple):
    relname: bytes
    be_pid: int
    extra: bytes


class ConninfoOption(NamedTuple):
    keyword: bytes
    envvar: Optional[bytes]
    compiled: Optional[bytes]
    val: Optional[bytes]
    label: bytes
    dispchar: bytes
    dispsize: int


class PGresAttDesc(NamedTuple):
    name: bytes
    tableid: int
    columnid: int
    format: int
    typid: int
    typlen: int
    atttypmod: int


@cache
def find_libpq_full_path() -> Optional[str]:
    if sys.platform == "win32":
        libname = ctypes.util.find_library("libpq.dll")

    elif sys.platform == "darwin":
        libname = ctypes.util.find_library("libpq.dylib")
        # (hopefully) temporary hack: libpq not in a standard place
        # https://github.com/orgs/Homebrew/discussions/3595
        # If pg_config is available and agrees, let's use its indications.
        if not libname:
            try:
                import subprocess as sp

                libdir = sp.check_output(["pg_config", "--libdir"]).strip().decode()
                libname = os.path.join(libdir, "libpq.dylib")
                if not os.path.exists(libname):
                    libname = None
            except Exception as ex:
                logger.debug("couldn't use pg_config to find libpq: %s", ex)

    else:
        libname = ctypes.util.find_library("pq")

    return libname


def error_message(obj: Union[PGconn, PGresult], encoding: str = "utf8") -> str:
    """
    Return an error message from a `PGconn` or `PGresult`.

    The return value is a `!str` (unlike pq data which is usually `!bytes`):
    use the connection encoding if available, otherwise the `!encoding`
    parameter as a fallback for decoding. Don't raise exceptions on decoding
    errors.

    """
    bmsg: bytes

    if hasattr(obj, "error_field"):
        # obj is a PGresult
        obj = cast(PGresult, obj)
        bmsg = obj.error_message

        # strip severity and whitespaces
        if bmsg:
            bmsg = bmsg.split(b":", 1)[-1].strip()

    elif hasattr(obj, "error_message"):
        # obj is a PGconn
        if obj.status == OK:
            encoding = pgconn_encoding(obj)
        bmsg = obj.error_message

        # strip severity and whitespaces
        if bmsg:
            bmsg = bmsg.split(b":", 1)[-1].strip()

    else:
        raise TypeError(f"PGconn or PGresult expected, got {type(obj).__name__}")

    if bmsg:
        msg = bmsg.decode(encoding, "replace")
    else:
        msg = "no details available"

    return msg


def connection_summary(pgconn: PGconn) -> str:
    """
    Return summary information on a connection.

    Useful for __repr__
    """
    parts = []
    if pgconn.status == OK:
        # Put together the [STATUS]
        status = TransactionStatus(pgconn.transaction_status).name
        if pgconn.pipeline_status:
            status += f", pipeline={PipelineStatus(pgconn.pipeline_status).name}"

        # Put together the (CONNECTION)
        if not pgconn.host.startswith(b"/"):
            parts.append(("host", pgconn.host.decode()))
        if pgconn.port != b"5432":
            parts.append(("port", pgconn.port.decode()))
        if pgconn.user != pgconn.db:
            parts.append(("user", pgconn.user.decode()))
        parts.append(("database", pgconn.db.decode()))

    else:
        status = ConnStatus(pgconn.status).name

    sparts = " ".join("%s=%s" % part for part in parts)
    if sparts:
        sparts = f" ({sparts})"
    return f"[{status}]{sparts}"
