import contextlib
import ctypes
from ctypes import (
    c_void_p,
    c_uint32,
    c_int32,
    byref,
)
from ctypes.util import find_library


OS_status = c_int32


class error:
    item_not_found = -25300
    keychain_denied = -128
    sec_auth_failed = -25293
    plist_missing = -67030
    sec_interaction_not_allowed = -25308


_sec = ctypes.CDLL(find_library('Security'))
_core = ctypes.CDLL(find_library('CoreServices'))
_found = ctypes.CDLL(find_library('Foundation'))

CFDictionaryCreate = _found.CFDictionaryCreate
CFDictionaryCreate.restype = c_void_p
CFDictionaryCreate.argtypes = (
    c_void_p,
    c_void_p,
    c_void_p,
    c_int32,
    c_void_p,
    c_void_p,
)

CFStringCreateWithCString = _found.CFStringCreateWithCString
CFStringCreateWithCString.restype = c_void_p
CFStringCreateWithCString.argtypes = [c_void_p, c_void_p, c_uint32]

CFNumberCreate = _found.CFNumberCreate
CFNumberCreate.restype = c_void_p
CFNumberCreate.argtypes = [c_void_p, c_uint32, ctypes.c_void_p]

SecItemAdd = _sec.SecItemAdd
SecItemAdd.restype = OS_status
SecItemAdd.argtypes = (c_void_p, c_void_p)

SecItemCopyMatching = _sec.SecItemCopyMatching
SecItemCopyMatching.restype = OS_status
SecItemCopyMatching.argtypes = (c_void_p, c_void_p)

SecItemDelete = _sec.SecItemDelete
SecItemDelete.restype = OS_status
SecItemDelete.argtypes = (c_void_p,)

CFDataGetBytePtr = _found.CFDataGetBytePtr
CFDataGetBytePtr.restype = c_void_p
CFDataGetBytePtr.argtypes = (c_void_p,)

CFDataGetLength = _found.CFDataGetLength
CFDataGetLength.restype = c_int32
CFDataGetLength.argtypes = (c_void_p,)


def k_(s):
    return c_void_p.in_dll(_sec, s)


def create_cfbool(b):
    return CFNumberCreate(None, 0x9, ctypes.byref(c_int32(1 if b else 0)))  # int32


def create_cfstr(s):
    return CFStringCreateWithCString(
        None, s.encode('utf8'), 0x08000100
    )  # kCFStringEncodingUTF8


def create_query(**kwargs):
    return CFDictionaryCreate(
        None,
        (c_void_p * len(kwargs))(*[k_(k) for k in kwargs.keys()]),
        (c_void_p * len(kwargs))(
            *[create_cfstr(v) if isinstance(v, str) else v for v in kwargs.values()]
        ),
        len(kwargs),
        _found.kCFTypeDictionaryKeyCallBacks,
        _found.kCFTypeDictionaryValueCallBacks,
    )


def cfstr_to_str(data):
    return ctypes.string_at(CFDataGetBytePtr(data), CFDataGetLength(data)).decode(
        'utf-8'
    )


class Error(Exception):
    @classmethod
    def raise_for_status(cls, status):
        if status == 0:
            return
        if status == error.item_not_found:
            raise NotFound(status, "Item not found")
        if status == error.keychain_denied:
            raise KeychainDenied(status, "Keychain Access Denied")
        if status == error.sec_auth_failed or status == error.plist_missing:
            raise SecAuthFailure(
                status,
                "Security Auth Failure: make sure "
                "python is signed with codesign util",
            )
        raise cls(status, "Unknown Error")


class NotFound(Error):
    pass


class KeychainDenied(Error):
    pass


class SecAuthFailure(Error):
    pass


def find_generic_password(kc_name, service, username, not_found_ok=False):
    q = create_query(
        kSecClass=k_('kSecClassGenericPassword'),
        kSecMatchLimit=k_('kSecMatchLimitOne'),
        kSecAttrService=service,
        kSecAttrAccount=username,
        kSecReturnData=create_cfbool(True),
    )

    data = c_void_p()
    status = SecItemCopyMatching(q, byref(data))

    if status == error.item_not_found and not_found_ok:
        return

    Error.raise_for_status(status)

    return cfstr_to_str(data)


def set_generic_password(name, service, username, password):
    with contextlib.suppress(NotFound):
        delete_generic_password(name, service, username)

    q = create_query(
        kSecClass=k_('kSecClassGenericPassword'),
        kSecAttrService=service,
        kSecAttrAccount=username,
        kSecValueData=password,
    )

    status = SecItemAdd(q, None)
    Error.raise_for_status(status)


def delete_generic_password(name, service, username):
    q = create_query(
        kSecClass=k_('kSecClassGenericPassword'),
        kSecAttrService=service,
        kSecAttrAccount=username,
    )

    status = SecItemDelete(q)
    Error.raise_for_status(status)
