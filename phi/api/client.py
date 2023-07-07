from httpx import Client, AsyncClient
from typing import Optional

from phiterm.conf.constants import (
    APP_NAME,
    APP_VERSION,
    BACKEND_API_URL,
    PHI_AUTH_TOKEN_COOKIE,
    PHI_AUTH_TOKEN_HEADER,
)
from phiterm.utils.log import logger

base_headers = {
    "user-agent": f"{APP_NAME}/{APP_VERSION}",
    "Content-Type": "application/json",
}


def get_authenticated_client() -> Optional[Client]:
    """Returns an instance of httpx.Client which with preconfigured auth and base url"""

    from phiterm.conf.auth import read_auth_token

    try:
        auth_token: Optional[str] = read_auth_token()
    except Exception as e:
        # logger.warning(f"Failed to read auth token: {e}")
        return None

    if auth_token is None:
        return None

    authenticated_headers = base_headers.copy()
    authenticated_headers[PHI_AUTH_TOKEN_HEADER] = auth_token
    return Client(
        base_url=BACKEND_API_URL,
        headers=authenticated_headers,
        cookies={PHI_AUTH_TOKEN_COOKIE: auth_token},
        timeout=60,
    )


def get_async_client() -> Optional[AsyncClient]:
    """Returns an instance of httpx.AsyncClient which with preconfigured auth and base url"""

    from phiterm.conf.auth import read_auth_token

    try:
        auth_token: Optional[str] = read_auth_token()
    except Exception:
        # logger.warning(f"Failed to read auth token: {e}")
        return None

    if auth_token is None:
        return None

    authenticated_headers = base_headers.copy()
    authenticated_headers[PHI_AUTH_TOKEN_HEADER] = auth_token
    return AsyncClient(
        base_url=BACKEND_API_URL,
        headers=authenticated_headers,
        cookies={PHI_AUTH_TOKEN_COOKIE: auth_token},
        timeout=60,
    )
