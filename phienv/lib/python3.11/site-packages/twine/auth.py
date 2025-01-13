import functools
import getpass
import logging
from typing import TYPE_CHECKING, Callable, Optional, Type, cast

# keyring has an indirect dependency on PyCA cryptography, which has no
# pre-built wheels for ppc64le and s390x, see #1158.
if TYPE_CHECKING:
    import keyring
else:
    try:
        import keyring
    except ModuleNotFoundError:  # pragma: no cover
        keyring = None

from twine import exceptions
from twine import utils

logger = logging.getLogger(__name__)


class CredentialInput:
    def __init__(
        self, username: Optional[str] = None, password: Optional[str] = None
    ) -> None:
        self.username = username
        self.password = password


class Resolver:
    def __init__(self, config: utils.RepositoryConfig, input: CredentialInput) -> None:
        self.config = config
        self.input = input

    @classmethod
    def choose(cls, interactive: bool) -> Type["Resolver"]:
        return cls if interactive else Private

    @property
    @functools.lru_cache()
    def username(self) -> Optional[str]:
        if self.is_pypi() and not self.input.username:
            # Default username.
            self.input.username = "__token__"

        return utils.get_userpass_value(
            self.input.username,
            self.config,
            key="username",
            prompt_strategy=self.username_from_keyring_or_prompt,
        )

    @property
    @functools.lru_cache()
    def password(self) -> Optional[str]:
        return utils.get_userpass_value(
            self.input.password,
            self.config,
            key="password",
            prompt_strategy=self.password_from_keyring_or_prompt,
        )

    @property
    def system(self) -> Optional[str]:
        return self.config["repository"]

    def get_username_from_keyring(self) -> Optional[str]:
        if keyring is None:
            logger.info("keyring module is not available")
            return None
        try:
            system = cast(str, self.system)
            logger.info("Querying keyring for username")
            creds = keyring.get_credential(system, None)
            if creds:
                return creds.username
        except AttributeError:
            # To support keyring prior to 15.2
            pass
        except Exception as exc:
            logger.warning("Error getting username from keyring", exc_info=exc)
        return None

    def get_password_from_keyring(self) -> Optional[str]:
        if keyring is None:
            logger.info("keyring module is not available")
            return None
        try:
            system = cast(str, self.system)
            username = cast(str, self.username)
            logger.info("Querying keyring for password")
            return cast(str, keyring.get_password(system, username))
        except Exception as exc:
            logger.warning("Error getting password from keyring", exc_info=exc)
        return None

    def username_from_keyring_or_prompt(self) -> str:
        username = self.get_username_from_keyring()
        if username:
            logger.info("username set from keyring")
            return username

        return self.prompt("username", input)

    def password_from_keyring_or_prompt(self) -> str:
        password = self.get_password_from_keyring()
        if password:
            logger.info("password set from keyring")
            return password

        # Prompt for API token when required.
        what = "API token" if self.is_pypi() else "password"

        return self.prompt(what, getpass.getpass)

    def prompt(self, what: str, how: Callable[..., str]) -> str:
        return how(f"Enter your {what}: ")

    def is_pypi(self) -> bool:
        """As of 2024-01-01, PyPI requires API tokens for uploads."""
        return cast(str, self.config["repository"]).startswith(
            (
                utils.DEFAULT_REPOSITORY,
                utils.TEST_REPOSITORY,
            )
        )


class Private(Resolver):
    def prompt(self, what: str, how: Optional[Callable[..., str]] = None) -> str:
        raise exceptions.NonInteractive(f"Credential not found for {what}.")
