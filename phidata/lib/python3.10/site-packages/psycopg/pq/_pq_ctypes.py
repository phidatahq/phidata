"""
libpq access using ctypes
"""

# Copyright (C) 2020 The Psycopg Team

import sys
import ctypes
import ctypes.util
from ctypes import Structure, CFUNCTYPE, POINTER
from ctypes import c_char, c_char_p, c_int, c_size_t, c_ubyte, c_uint, c_void_p
from typing import List, Optional, Tuple

from .misc import find_libpq_full_path
from ..errors import NotSupportedError

libname = find_libpq_full_path()
if not libname:
    raise ImportError("libpq library not found")

pq = ctypes.cdll.LoadLibrary(libname)


class FILE(Structure):
    pass


FILE_ptr = POINTER(FILE)

if sys.platform == "linux":
    libcname = ctypes.util.find_library("c")
    if not libcname:
        # Likely this is a system using musl libc, see the following bug:
        # https://github.com/python/cpython/issues/65821
        libcname = "libc.so"
    libc = ctypes.cdll.LoadLibrary(libcname)

    fdopen = libc.fdopen
    fdopen.argtypes = (c_int, c_char_p)
    fdopen.restype = FILE_ptr


# Get the libpq version to define what functions are available.

PQlibVersion = pq.PQlibVersion
PQlibVersion.argtypes = []
PQlibVersion.restype = c_int

libpq_version = PQlibVersion()


# libpq data types


Oid = c_uint


class PGconn_struct(Structure):
    _fields_: List[Tuple[str, type]] = []


class PGresult_struct(Structure):
    _fields_: List[Tuple[str, type]] = []


class PQconninfoOption_struct(Structure):
    _fields_ = [
        ("keyword", c_char_p),
        ("envvar", c_char_p),
        ("compiled", c_char_p),
        ("val", c_char_p),
        ("label", c_char_p),
        ("dispchar", c_char_p),
        ("dispsize", c_int),
    ]


class PGnotify_struct(Structure):
    _fields_ = [
        ("relname", c_char_p),
        ("be_pid", c_int),
        ("extra", c_char_p),
    ]


class PGcancel_struct(Structure):
    _fields_: List[Tuple[str, type]] = []


class PGresAttDesc_struct(Structure):
    _fields_ = [
        ("name", c_char_p),
        ("tableid", Oid),
        ("columnid", c_int),
        ("format", c_int),
        ("typid", Oid),
        ("typlen", c_int),
        ("atttypmod", c_int),
    ]


PGconn_ptr = POINTER(PGconn_struct)
PGresult_ptr = POINTER(PGresult_struct)
PQconninfoOption_ptr = POINTER(PQconninfoOption_struct)
PGnotify_ptr = POINTER(PGnotify_struct)
PGcancel_ptr = POINTER(PGcancel_struct)
PGresAttDesc_ptr = POINTER(PGresAttDesc_struct)


# Function definitions as explained in PostgreSQL 12 documentation

# 33.1. Database Connection Control Functions

# PQconnectdbParams: doesn't seem useful, won't wrap for now

PQconnectdb = pq.PQconnectdb
PQconnectdb.argtypes = [c_char_p]
PQconnectdb.restype = PGconn_ptr

# PQsetdbLogin: not useful
# PQsetdb: not useful

# PQconnectStartParams: not useful

PQconnectStart = pq.PQconnectStart
PQconnectStart.argtypes = [c_char_p]
PQconnectStart.restype = PGconn_ptr

PQconnectPoll = pq.PQconnectPoll
PQconnectPoll.argtypes = [PGconn_ptr]
PQconnectPoll.restype = c_int

PQconndefaults = pq.PQconndefaults
PQconndefaults.argtypes = []
PQconndefaults.restype = PQconninfoOption_ptr

PQconninfoFree = pq.PQconninfoFree
PQconninfoFree.argtypes = [PQconninfoOption_ptr]
PQconninfoFree.restype = None

PQconninfo = pq.PQconninfo
PQconninfo.argtypes = [PGconn_ptr]
PQconninfo.restype = PQconninfoOption_ptr

PQconninfoParse = pq.PQconninfoParse
PQconninfoParse.argtypes = [c_char_p, POINTER(c_char_p)]
PQconninfoParse.restype = PQconninfoOption_ptr

PQfinish = pq.PQfinish
PQfinish.argtypes = [PGconn_ptr]
PQfinish.restype = None

PQreset = pq.PQreset
PQreset.argtypes = [PGconn_ptr]
PQreset.restype = None

PQresetStart = pq.PQresetStart
PQresetStart.argtypes = [PGconn_ptr]
PQresetStart.restype = c_int

PQresetPoll = pq.PQresetPoll
PQresetPoll.argtypes = [PGconn_ptr]
PQresetPoll.restype = c_int

PQping = pq.PQping
PQping.argtypes = [c_char_p]
PQping.restype = c_int


# 33.2. Connection Status Functions

PQdb = pq.PQdb
PQdb.argtypes = [PGconn_ptr]
PQdb.restype = c_char_p

PQuser = pq.PQuser
PQuser.argtypes = [PGconn_ptr]
PQuser.restype = c_char_p

PQpass = pq.PQpass
PQpass.argtypes = [PGconn_ptr]
PQpass.restype = c_char_p

PQhost = pq.PQhost
PQhost.argtypes = [PGconn_ptr]
PQhost.restype = c_char_p

_PQhostaddr = None

if libpq_version >= 120000:
    _PQhostaddr = pq.PQhostaddr
    _PQhostaddr.argtypes = [PGconn_ptr]
    _PQhostaddr.restype = c_char_p


def PQhostaddr(pgconn: PGconn_struct) -> bytes:
    if not _PQhostaddr:
        raise NotSupportedError(
            "PQhostaddr requires libpq from PostgreSQL 12,"
            f" {libpq_version} available instead"
        )

    return _PQhostaddr(pgconn)


PQport = pq.PQport
PQport.argtypes = [PGconn_ptr]
PQport.restype = c_char_p

PQtty = pq.PQtty
PQtty.argtypes = [PGconn_ptr]
PQtty.restype = c_char_p

PQoptions = pq.PQoptions
PQoptions.argtypes = [PGconn_ptr]
PQoptions.restype = c_char_p

PQstatus = pq.PQstatus
PQstatus.argtypes = [PGconn_ptr]
PQstatus.restype = c_int

PQtransactionStatus = pq.PQtransactionStatus
PQtransactionStatus.argtypes = [PGconn_ptr]
PQtransactionStatus.restype = c_int

PQparameterStatus = pq.PQparameterStatus
PQparameterStatus.argtypes = [PGconn_ptr, c_char_p]
PQparameterStatus.restype = c_char_p

PQprotocolVersion = pq.PQprotocolVersion
PQprotocolVersion.argtypes = [PGconn_ptr]
PQprotocolVersion.restype = c_int

PQserverVersion = pq.PQserverVersion
PQserverVersion.argtypes = [PGconn_ptr]
PQserverVersion.restype = c_int

PQerrorMessage = pq.PQerrorMessage
PQerrorMessage.argtypes = [PGconn_ptr]
PQerrorMessage.restype = c_char_p

PQsocket = pq.PQsocket
PQsocket.argtypes = [PGconn_ptr]
PQsocket.restype = c_int

PQbackendPID = pq.PQbackendPID
PQbackendPID.argtypes = [PGconn_ptr]
PQbackendPID.restype = c_int

PQconnectionNeedsPassword = pq.PQconnectionNeedsPassword
PQconnectionNeedsPassword.argtypes = [PGconn_ptr]
PQconnectionNeedsPassword.restype = c_int

PQconnectionUsedPassword = pq.PQconnectionUsedPassword
PQconnectionUsedPassword.argtypes = [PGconn_ptr]
PQconnectionUsedPassword.restype = c_int

PQsslInUse = pq.PQsslInUse
PQsslInUse.argtypes = [PGconn_ptr]
PQsslInUse.restype = c_int

# TODO: PQsslAttribute, PQsslAttributeNames, PQsslStruct, PQgetssl


# 33.3. Command Execution Functions

PQexec = pq.PQexec
PQexec.argtypes = [PGconn_ptr, c_char_p]
PQexec.restype = PGresult_ptr

PQexecParams = pq.PQexecParams
PQexecParams.argtypes = [
    PGconn_ptr,
    c_char_p,
    c_int,
    POINTER(Oid),
    POINTER(c_char_p),
    POINTER(c_int),
    POINTER(c_int),
    c_int,
]
PQexecParams.restype = PGresult_ptr

PQprepare = pq.PQprepare
PQprepare.argtypes = [PGconn_ptr, c_char_p, c_char_p, c_int, POINTER(Oid)]
PQprepare.restype = PGresult_ptr

PQexecPrepared = pq.PQexecPrepared
PQexecPrepared.argtypes = [
    PGconn_ptr,
    c_char_p,
    c_int,
    POINTER(c_char_p),
    POINTER(c_int),
    POINTER(c_int),
    c_int,
]
PQexecPrepared.restype = PGresult_ptr

PQdescribePrepared = pq.PQdescribePrepared
PQdescribePrepared.argtypes = [PGconn_ptr, c_char_p]
PQdescribePrepared.restype = PGresult_ptr

PQdescribePortal = pq.PQdescribePortal
PQdescribePortal.argtypes = [PGconn_ptr, c_char_p]
PQdescribePortal.restype = PGresult_ptr

PQresultStatus = pq.PQresultStatus
PQresultStatus.argtypes = [PGresult_ptr]
PQresultStatus.restype = c_int

# PQresStatus: not needed, we have pretty enums

PQresultErrorMessage = pq.PQresultErrorMessage
PQresultErrorMessage.argtypes = [PGresult_ptr]
PQresultErrorMessage.restype = c_char_p

# TODO: PQresultVerboseErrorMessage

PQresultErrorField = pq.PQresultErrorField
PQresultErrorField.argtypes = [PGresult_ptr, c_int]
PQresultErrorField.restype = c_char_p

PQclear = pq.PQclear
PQclear.argtypes = [PGresult_ptr]
PQclear.restype = None


# 33.3.2. Retrieving Query Result Information

PQntuples = pq.PQntuples
PQntuples.argtypes = [PGresult_ptr]
PQntuples.restype = c_int

PQnfields = pq.PQnfields
PQnfields.argtypes = [PGresult_ptr]
PQnfields.restype = c_int

PQfname = pq.PQfname
PQfname.argtypes = [PGresult_ptr, c_int]
PQfname.restype = c_char_p

# PQfnumber: useless and hard to use

PQftable = pq.PQftable
PQftable.argtypes = [PGresult_ptr, c_int]
PQftable.restype = Oid

PQftablecol = pq.PQftablecol
PQftablecol.argtypes = [PGresult_ptr, c_int]
PQftablecol.restype = c_int

PQfformat = pq.PQfformat
PQfformat.argtypes = [PGresult_ptr, c_int]
PQfformat.restype = c_int

PQftype = pq.PQftype
PQftype.argtypes = [PGresult_ptr, c_int]
PQftype.restype = Oid

PQfmod = pq.PQfmod
PQfmod.argtypes = [PGresult_ptr, c_int]
PQfmod.restype = c_int

PQfsize = pq.PQfsize
PQfsize.argtypes = [PGresult_ptr, c_int]
PQfsize.restype = c_int

PQbinaryTuples = pq.PQbinaryTuples
PQbinaryTuples.argtypes = [PGresult_ptr]
PQbinaryTuples.restype = c_int

PQgetvalue = pq.PQgetvalue
PQgetvalue.argtypes = [PGresult_ptr, c_int, c_int]
PQgetvalue.restype = POINTER(c_char)  # not a null-terminated string

PQgetisnull = pq.PQgetisnull
PQgetisnull.argtypes = [PGresult_ptr, c_int, c_int]
PQgetisnull.restype = c_int

PQgetlength = pq.PQgetlength
PQgetlength.argtypes = [PGresult_ptr, c_int, c_int]
PQgetlength.restype = c_int

PQnparams = pq.PQnparams
PQnparams.argtypes = [PGresult_ptr]
PQnparams.restype = c_int

PQparamtype = pq.PQparamtype
PQparamtype.argtypes = [PGresult_ptr, c_int]
PQparamtype.restype = Oid

# PQprint: pretty useless

# 33.3.3. Retrieving Other Result Information

PQcmdStatus = pq.PQcmdStatus
PQcmdStatus.argtypes = [PGresult_ptr]
PQcmdStatus.restype = c_char_p

PQcmdTuples = pq.PQcmdTuples
PQcmdTuples.argtypes = [PGresult_ptr]
PQcmdTuples.restype = c_char_p

PQoidValue = pq.PQoidValue
PQoidValue.argtypes = [PGresult_ptr]
PQoidValue.restype = Oid


# 33.3.4. Escaping Strings for Inclusion in SQL Commands

PQescapeLiteral = pq.PQescapeLiteral
PQescapeLiteral.argtypes = [PGconn_ptr, c_char_p, c_size_t]
PQescapeLiteral.restype = POINTER(c_char)

PQescapeIdentifier = pq.PQescapeIdentifier
PQescapeIdentifier.argtypes = [PGconn_ptr, c_char_p, c_size_t]
PQescapeIdentifier.restype = POINTER(c_char)

PQescapeStringConn = pq.PQescapeStringConn
# TODO: raises "wrong type" error
# PQescapeStringConn.argtypes = [
#     PGconn_ptr, c_char_p, c_char_p, c_size_t, POINTER(c_int)
# ]
PQescapeStringConn.restype = c_size_t

PQescapeString = pq.PQescapeString
# TODO: raises "wrong type" error
# PQescapeString.argtypes = [c_char_p, c_char_p, c_size_t]
PQescapeString.restype = c_size_t

PQescapeByteaConn = pq.PQescapeByteaConn
PQescapeByteaConn.argtypes = [
    PGconn_ptr,
    POINTER(c_char),  # actually POINTER(c_ubyte) but this is easier
    c_size_t,
    POINTER(c_size_t),
]
PQescapeByteaConn.restype = POINTER(c_ubyte)

PQescapeBytea = pq.PQescapeBytea
PQescapeBytea.argtypes = [
    POINTER(c_char),  # actually POINTER(c_ubyte) but this is easier
    c_size_t,
    POINTER(c_size_t),
]
PQescapeBytea.restype = POINTER(c_ubyte)


PQunescapeBytea = pq.PQunescapeBytea
PQunescapeBytea.argtypes = [
    POINTER(c_char),  # actually POINTER(c_ubyte) but this is easier
    POINTER(c_size_t),
]
PQunescapeBytea.restype = POINTER(c_ubyte)


# 33.4. Asynchronous Command Processing

PQsendQuery = pq.PQsendQuery
PQsendQuery.argtypes = [PGconn_ptr, c_char_p]
PQsendQuery.restype = c_int

PQsendQueryParams = pq.PQsendQueryParams
PQsendQueryParams.argtypes = [
    PGconn_ptr,
    c_char_p,
    c_int,
    POINTER(Oid),
    POINTER(c_char_p),
    POINTER(c_int),
    POINTER(c_int),
    c_int,
]
PQsendQueryParams.restype = c_int

PQsendPrepare = pq.PQsendPrepare
PQsendPrepare.argtypes = [PGconn_ptr, c_char_p, c_char_p, c_int, POINTER(Oid)]
PQsendPrepare.restype = c_int

PQsendQueryPrepared = pq.PQsendQueryPrepared
PQsendQueryPrepared.argtypes = [
    PGconn_ptr,
    c_char_p,
    c_int,
    POINTER(c_char_p),
    POINTER(c_int),
    POINTER(c_int),
    c_int,
]
PQsendQueryPrepared.restype = c_int

PQsendDescribePrepared = pq.PQsendDescribePrepared
PQsendDescribePrepared.argtypes = [PGconn_ptr, c_char_p]
PQsendDescribePrepared.restype = c_int

PQsendDescribePortal = pq.PQsendDescribePortal
PQsendDescribePortal.argtypes = [PGconn_ptr, c_char_p]
PQsendDescribePortal.restype = c_int

PQgetResult = pq.PQgetResult
PQgetResult.argtypes = [PGconn_ptr]
PQgetResult.restype = PGresult_ptr

PQconsumeInput = pq.PQconsumeInput
PQconsumeInput.argtypes = [PGconn_ptr]
PQconsumeInput.restype = c_int

PQisBusy = pq.PQisBusy
PQisBusy.argtypes = [PGconn_ptr]
PQisBusy.restype = c_int

PQsetnonblocking = pq.PQsetnonblocking
PQsetnonblocking.argtypes = [PGconn_ptr, c_int]
PQsetnonblocking.restype = c_int

PQisnonblocking = pq.PQisnonblocking
PQisnonblocking.argtypes = [PGconn_ptr]
PQisnonblocking.restype = c_int

PQflush = pq.PQflush
PQflush.argtypes = [PGconn_ptr]
PQflush.restype = c_int


# 33.5. Retrieving Query Results Row-by-Row
PQsetSingleRowMode = pq.PQsetSingleRowMode
PQsetSingleRowMode.argtypes = [PGconn_ptr]
PQsetSingleRowMode.restype = c_int


# 33.6. Canceling Queries in Progress

PQgetCancel = pq.PQgetCancel
PQgetCancel.argtypes = [PGconn_ptr]
PQgetCancel.restype = PGcancel_ptr

PQfreeCancel = pq.PQfreeCancel
PQfreeCancel.argtypes = [PGcancel_ptr]
PQfreeCancel.restype = None

PQcancel = pq.PQcancel
# TODO: raises "wrong type" error
# PQcancel.argtypes = [PGcancel_ptr, POINTER(c_char), c_int]
PQcancel.restype = c_int


# 33.8. Asynchronous Notification

PQnotifies = pq.PQnotifies
PQnotifies.argtypes = [PGconn_ptr]
PQnotifies.restype = PGnotify_ptr


# 33.9. Functions Associated with the COPY Command

PQputCopyData = pq.PQputCopyData
PQputCopyData.argtypes = [PGconn_ptr, c_char_p, c_int]
PQputCopyData.restype = c_int

PQputCopyEnd = pq.PQputCopyEnd
PQputCopyEnd.argtypes = [PGconn_ptr, c_char_p]
PQputCopyEnd.restype = c_int

PQgetCopyData = pq.PQgetCopyData
PQgetCopyData.argtypes = [PGconn_ptr, POINTER(c_char_p), c_int]
PQgetCopyData.restype = c_int


# 33.10. Control Functions

PQtrace = pq.PQtrace
PQtrace.argtypes = [PGconn_ptr, FILE_ptr]
PQtrace.restype = None

_PQsetTraceFlags = None

if libpq_version >= 140000:
    _PQsetTraceFlags = pq.PQsetTraceFlags
    _PQsetTraceFlags.argtypes = [PGconn_ptr, c_int]
    _PQsetTraceFlags.restype = None


def PQsetTraceFlags(pgconn: PGconn_struct, flags: int) -> None:
    if not _PQsetTraceFlags:
        raise NotSupportedError(
            "PQsetTraceFlags requires libpq from PostgreSQL 14,"
            f" {libpq_version} available instead"
        )

    _PQsetTraceFlags(pgconn, flags)


PQuntrace = pq.PQuntrace
PQuntrace.argtypes = [PGconn_ptr]
PQuntrace.restype = None

# 33.11. Miscellaneous Functions

PQfreemem = pq.PQfreemem
PQfreemem.argtypes = [c_void_p]
PQfreemem.restype = None

if libpq_version >= 100000:
    _PQencryptPasswordConn = pq.PQencryptPasswordConn
    _PQencryptPasswordConn.argtypes = [
        PGconn_ptr,
        c_char_p,
        c_char_p,
        c_char_p,
    ]
    _PQencryptPasswordConn.restype = POINTER(c_char)


def PQencryptPasswordConn(
    pgconn: PGconn_struct, passwd: bytes, user: bytes, algorithm: bytes
) -> Optional[bytes]:
    if not _PQencryptPasswordConn:
        raise NotSupportedError(
            "PQencryptPasswordConn requires libpq from PostgreSQL 10,"
            f" {libpq_version} available instead"
        )

    return _PQencryptPasswordConn(pgconn, passwd, user, algorithm)


PQmakeEmptyPGresult = pq.PQmakeEmptyPGresult
PQmakeEmptyPGresult.argtypes = [PGconn_ptr, c_int]
PQmakeEmptyPGresult.restype = PGresult_ptr

PQsetResultAttrs = pq.PQsetResultAttrs
PQsetResultAttrs.argtypes = [PGresult_ptr, c_int, PGresAttDesc_ptr]
PQsetResultAttrs.restype = c_int


# 33.12. Notice Processing

PQnoticeReceiver = CFUNCTYPE(None, c_void_p, PGresult_ptr)

PQsetNoticeReceiver = pq.PQsetNoticeReceiver
PQsetNoticeReceiver.argtypes = [PGconn_ptr, PQnoticeReceiver, c_void_p]
PQsetNoticeReceiver.restype = PQnoticeReceiver

# 34.5 Pipeline Mode

_PQpipelineStatus = None
_PQenterPipelineMode = None
_PQexitPipelineMode = None
_PQpipelineSync = None
_PQsendFlushRequest = None

if libpq_version >= 140000:
    _PQpipelineStatus = pq.PQpipelineStatus
    _PQpipelineStatus.argtypes = [PGconn_ptr]
    _PQpipelineStatus.restype = c_int

    _PQenterPipelineMode = pq.PQenterPipelineMode
    _PQenterPipelineMode.argtypes = [PGconn_ptr]
    _PQenterPipelineMode.restype = c_int

    _PQexitPipelineMode = pq.PQexitPipelineMode
    _PQexitPipelineMode.argtypes = [PGconn_ptr]
    _PQexitPipelineMode.restype = c_int

    _PQpipelineSync = pq.PQpipelineSync
    _PQpipelineSync.argtypes = [PGconn_ptr]
    _PQpipelineSync.restype = c_int

    _PQsendFlushRequest = pq.PQsendFlushRequest
    _PQsendFlushRequest.argtypes = [PGconn_ptr]
    _PQsendFlushRequest.restype = c_int


def PQpipelineStatus(pgconn: PGconn_struct) -> int:
    if not _PQpipelineStatus:
        raise NotSupportedError(
            "PQpipelineStatus requires libpq from PostgreSQL 14,"
            f" {libpq_version} available instead"
        )
    return _PQpipelineStatus(pgconn)


def PQenterPipelineMode(pgconn: PGconn_struct) -> int:
    if not _PQenterPipelineMode:
        raise NotSupportedError(
            "PQenterPipelineMode requires libpq from PostgreSQL 14,"
            f" {libpq_version} available instead"
        )
    return _PQenterPipelineMode(pgconn)


def PQexitPipelineMode(pgconn: PGconn_struct) -> int:
    if not _PQexitPipelineMode:
        raise NotSupportedError(
            "PQexitPipelineMode requires libpq from PostgreSQL 14,"
            f" {libpq_version} available instead"
        )
    return _PQexitPipelineMode(pgconn)


def PQpipelineSync(pgconn: PGconn_struct) -> int:
    if not _PQpipelineSync:
        raise NotSupportedError(
            "PQpipelineSync requires libpq from PostgreSQL 14,"
            f" {libpq_version} available instead"
        )
    return _PQpipelineSync(pgconn)


def PQsendFlushRequest(pgconn: PGconn_struct) -> int:
    if not _PQsendFlushRequest:
        raise NotSupportedError(
            "PQsendFlushRequest requires libpq from PostgreSQL 14,"
            f" {libpq_version} available instead"
        )
    return _PQsendFlushRequest(pgconn)


# 33.18. SSL Support

PQinitOpenSSL = pq.PQinitOpenSSL
PQinitOpenSSL.argtypes = [c_int, c_int]
PQinitOpenSSL.restype = None


def generate_stub() -> None:
    import re
    from ctypes import _CFuncPtr  # type: ignore

    def type2str(fname, narg, t):
        if t is None:
            return "None"
        elif t is c_void_p:
            return "Any"
        elif t is c_int or t is c_uint or t is c_size_t:
            return "int"
        elif t is c_char_p or t.__name__ == "LP_c_char":
            if narg is not None:
                return "bytes"
            else:
                return "Optional[bytes]"

        elif t.__name__ in (
            "LP_PGconn_struct",
            "LP_PGresult_struct",
            "LP_PGcancel_struct",
        ):
            if narg is not None:
                return f"Optional[{t.__name__[3:]}]"
            else:
                return t.__name__[3:]

        elif t.__name__ in ("LP_PQconninfoOption_struct",):
            return f"Sequence[{t.__name__[3:]}]"

        elif t.__name__ in (
            "LP_c_ubyte",
            "LP_c_char_p",
            "LP_c_int",
            "LP_c_uint",
            "LP_c_ulong",
            "LP_FILE",
        ):
            return f"_Pointer[{t.__name__[3:]}]"

        else:
            assert False, f"can't deal with {t} in {fname}"

    fn = __file__ + "i"
    with open(fn) as f:
        lines = f.read().splitlines()

    istart, iend = (
        i
        for i, line in enumerate(lines)
        if re.match(r"\s*#\s*autogenerated:\s+(start|end)", line)
    )

    known = {
        line[4:].split("(", 1)[0] for line in lines[:istart] if line.startswith("def ")
    }

    signatures = []

    for name, obj in globals().items():
        if name in known:
            continue
        if not isinstance(obj, _CFuncPtr):
            continue

        params = []
        for i, t in enumerate(obj.argtypes):
            params.append(f"arg{i + 1}: {type2str(name, i, t)}")

        resname = type2str(name, None, obj.restype)

        signatures.append(f"def {name}({', '.join(params)}) -> {resname}: ...")

    lines[istart + 1 : iend] = signatures

    with open(fn, "w") as f:
        f.write("\n".join(lines))
        f.write("\n")


if __name__ == "__main__":
    generate_stub()
