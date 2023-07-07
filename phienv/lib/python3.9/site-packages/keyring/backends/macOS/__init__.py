import platform
import os
import warnings
import functools

from ...backend import KeyringBackend
from ...errors import PasswordSetError
from ...errors import PasswordDeleteError
from ...errors import KeyringLocked
from ...errors import KeyringError
from ..._compat import properties

try:
    from . import api
except Exception:
    pass


def warn_keychain(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        if self.keychain:
            warnings.warn("Specified keychain is ignored. See #623")
        return func(self, *args, **kwargs)

    return wrapper


class Keyring(KeyringBackend):
    """macOS Keychain"""

    keychain = os.environ.get('KEYCHAIN_PATH')
    "Path to keychain file, overriding default"

    @properties.classproperty
    def priority(cls):
        """
        Preferred for all macOS environments.
        """
        if platform.system() != 'Darwin':
            raise RuntimeError("macOS required")
        if 'api' not in globals():
            raise RuntimeError("Security API unavailable")
        return 5

    @warn_keychain
    def set_password(self, service, username, password):
        if username is None:
            username = ''

        try:
            api.set_generic_password(self.keychain, service, username, password)
        except api.KeychainDenied as e:
            raise KeyringLocked("Can't store password on keychain: " "{}".format(e))
        except api.Error as e:
            raise PasswordSetError("Can't store password on keychain: " "{}".format(e))

    @warn_keychain
    def get_password(self, service, username):
        if username is None:
            username = ''

        try:
            return api.find_generic_password(self.keychain, service, username)
        except api.NotFound:
            pass
        except api.KeychainDenied as e:
            raise KeyringLocked("Can't get password from keychain: " "{}".format(e))
        except api.Error as e:
            raise KeyringError("Can't get password from keychain: " "{}".format(e))

    @warn_keychain
    def delete_password(self, service, username):
        if username is None:
            username = ''

        try:
            return api.delete_generic_password(self.keychain, service, username)
        except api.Error as e:
            raise PasswordDeleteError(
                "Can't delete password in keychain: " "{}".format(e)
            )

    def with_keychain(self, keychain):
        warnings.warn(
            "macOS.Keyring.with_keychain is deprecated. Use with_properties instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.with_properties(keychain=keychain)
