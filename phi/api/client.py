from typing import Optional

import aiohttp

from phi.cli.settings import phi_cli_settings
from phi.cli.credentials import read_auth_token
from phi.utils.log import logger


class ApiClient:
    def __init__(self):
        self.base_url = phi_cli_settings.api_url
        self.headers = {
            "user-agent": f"{phi_cli_settings.app_name}/{phi_cli_settings.app_version}",
            "Content-Type": "application/json",
        }
        self._authenticated_headers = None
        self._client_session = None
        self._authenticated_session = None

    @property
    def auth_token(self) -> Optional[str]:
        try:
            return read_auth_token()
        except Exception as e:
            logger.warning(f"Failed to read auth token: {e}")
            return None

    @property
    def authenticated_headers(self):
        if self._authenticated_headers is None:
            self._authenticated_headers = self.headers.copy()
            if self.auth_token is not None:
                self._authenticated_headers[phi_cli_settings.auth_token_header] = self.auth_token
        return self._authenticated_headers

    def Session(self):
        return aiohttp.ClientSession(base_url=self.base_url, headers=self.headers)

    def AuthenticatedSession(self):
        return aiohttp.ClientSession(base_url=self.base_url, headers=self.authenticated_headers)


api_client = ApiClient()


def invalid_respose(response: aiohttp.ClientResponse):
    status = response.status
    if status >= 400:
        return True
    return False
