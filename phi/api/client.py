from httpx import Client, AsyncClient
from typing import Optional

from phi.cli.settings import phi_cli_settings
from phi.cli.credentials import read_auth_token
from phi.utils.log import logger

base_headers = {
    "user-agent": f"{phi_cli_settings.app_name}/{phi_cli_settings.app_version}",
    "Content-Type": "application/json",
}


def get_authenticated_client() -> Optional[Client]:
    """Returns an instance of httpx.Client with preconfigured auth and base url"""

    try:
        auth_token: Optional[str] = read_auth_token()
    except Exception as e:
        logger.warning(f"Failed to read auth token: {e}")
        return None

    if auth_token is None:
        return None

    authenticated_headers = base_headers.copy()
    authenticated_headers[phi_cli_settings.auth_token_header] = auth_token
    return Client(
        base_url=phi_cli_settings.api_url,
        headers=authenticated_headers,
        cookies={phi_cli_settings.auth_token_cookie: auth_token},
        timeout=60,
    )


def get_async_client() -> Optional[AsyncClient]:
    """Returns an instance of httpx.AsyncClient with preconfigured auth and base url"""

    try:
        auth_token: Optional[str] = read_auth_token()
    except Exception as e:
        logger.warning(f"Failed to read auth token: {e}")
        return None

    if auth_token is None:
        return None

    authenticated_headers = base_headers.copy()
    authenticated_headers[phi_cli_settings.auth_token_header] = auth_token
    return AsyncClient(
        base_url=phi_cli_settings.api_url,
        headers=authenticated_headers,
        cookies={phi_cli_settings.auth_token_cookie: auth_token},
        timeout=60,
    )
