from typing import Optional

from phi.cli.settings import phi_cli_settings
from phi.utils.pickle import pickle_object_to_file, unpickle_object_from_file


class PhiCliCreds:
    def __init__(self, auth_token: str):
        self._auth_token = auth_token

    @property
    def auth_token(self) -> str:
        return self._auth_token


def save_auth_token(auth_token: str):
    # logger.debug(f"Storing {auth_token} to {str(phi_cli_settings.credentials_path)}")
    creds = PhiCliCreds(auth_token)
    pickle_object_to_file(creds, phi_cli_settings.credentials_path)


def read_auth_token() -> Optional[str]:
    # logger.debug(f"Reading token from {str(phi_cli_settings.credentials_path)}")
    creds: PhiCliCreds = unpickle_object_from_file(phi_cli_settings.credentials_path)
    return creds.auth_token
