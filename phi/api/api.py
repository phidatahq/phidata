from typing import Optional

from httpx import Client as HttpxClient, AsyncClient as HttpxAsyncClient, Response

from phi.cli.settings import phi_cli_settings
from phi.cli.credentials import read_auth_token
from phi.utils.log import logger


class Api:
    def __init__(self):
        self.headers = {
            "user-agent": f"{phi_cli_settings.app_name}/{phi_cli_settings.app_version}",
            "Content-Type": "application/json",
        }
        self._authenticated_headers = None
        self._client = None
        self._async_client = None
        self._authenticated_client = None
        self._authenticated_async_client = None

    @property
    def auth_token(self) -> Optional[str]:
        try:
            return read_auth_token()
        except Exception as e:
            logger.debug(f"Failed to read auth token: {e}")
            return None

    @property
    def authenticated_headers(self):
        if self._authenticated_headers is None:
            self._authenticated_headers = self.headers.copy()
            token = self.auth_token
            if token is not None:
                self._authenticated_headers[phi_cli_settings.auth_token_header] = token
        return self._authenticated_headers

    def Client(self) -> HttpxClient:
        if self._client is None:
            self._client = HttpxClient(
                base_url=phi_cli_settings.api_url,
                headers=self.headers,
                timeout=60,
            )
        return self._client

    def AuthenticatedClient(self) -> HttpxClient:
        if self._authenticated_client is None:
            self._authenticated_client = HttpxClient(
                base_url=phi_cli_settings.api_url,
                headers=self.authenticated_headers,
                timeout=60,
            )
        return self._authenticated_client

    def AsyncClient(self):
        if self._async_client is None:
            self._async_client = HttpxAsyncClient(
                base_url=phi_cli_settings.api_url,
                headers=self.headers,
                timeout=60,
            )
        return self._async_client

    def AuthenticatedAsyncClient(self):
        if self._authenticated_async_client is None:
            self._authenticated_async_client = HttpxAsyncClient(
                base_url=phi_cli_settings.api_url,
                headers=self.authenticated_headers,
                timeout=60,
            )
        return self._authenticated_async_client


api = Api()


def invalid_response(r: Response) -> bool:
    """Returns true if the response is invalid"""

    if r.status_code >= 400:
        return True
    return False
