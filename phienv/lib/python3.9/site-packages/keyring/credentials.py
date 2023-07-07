import os
import abc


class Credential(metaclass=abc.ABCMeta):
    """Abstract class to manage credentials"""

    @abc.abstractproperty
    def username(self):
        return None

    @abc.abstractproperty
    def password(self):
        return None


class SimpleCredential(Credential):
    """Simple credentials implementation"""

    def __init__(self, username, password):
        self._username = username
        self._password = password

    @property
    def username(self):
        return self._username

    @property
    def password(self):
        return self._password


class EnvironCredential(Credential):
    """
    Source credentials from environment variables.

    Actual sourcing is deferred until requested.

    Supports comparison by equality.

    >>> e1 = EnvironCredential('a', 'b')
    >>> e2 = EnvironCredential('a', 'b')
    >>> e3 = EnvironCredential('a', 'c')
    >>> e1 == e2
    True
    >>> e2 == e3
    False
    """

    def __init__(self, user_env_var, pwd_env_var):
        self.user_env_var = user_env_var
        self.pwd_env_var = pwd_env_var

    def __eq__(self, other: object) -> bool:
        return vars(self) == vars(other)

    def _get_env(self, env_var):
        """Helper to read an environment variable"""
        value = os.environ.get(env_var)
        if not value:
            raise ValueError('Missing environment variable:%s' % env_var)
        return value

    @property
    def username(self):
        return self._get_env(self.user_env_var)

    @property
    def password(self):
        return self._get_env(self.pwd_env_var)
