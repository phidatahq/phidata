from typing import Any, Dict, List, Optional, Union

from httpx import Client, Response, NetworkError, codes

from phiterm.api.client import get_authenticated_client, base_headers
from phiterm.api.exceptions import CliAuthException
from phiterm.api.routes import ApiRoutes
from phiterm.api.handler import invalid_response
from phiterm.conf.constants import BACKEND_API_URL, PHI_AUTH_TOKEN_HEADER
from phiterm.schemas.user import UserSchema, EmailPasswordSignInSchema
from phiterm.utils.cli_console import log_network_error_msg
from phiterm.utils.log import logger


def user_ping() -> bool:
    logger.debug("--o-o-- Ping user api")

    with Client(base_url=BACKEND_API_URL, headers=base_headers, timeout=60) as api:
        try:
            r: Response = api.get(ApiRoutes.USER_PING)
            if invalid_response(r):
                return False
        except NetworkError as e:
            log_network_error_msg()
            return False

        if r.status_code == codes.OK:
            return True
    return False


def is_user_authenticated() -> bool:
    from phiterm.conf.phi_conf import PhiConf

    logger.debug("--o-o-- Authenticating user")

    authenticated_client: Optional[Client] = get_authenticated_client()
    if authenticated_client is None:
        logger.debug("Session not available")
        return False

    phi_conf: Optional[PhiConf] = PhiConf.get_saved_conf()
    if phi_conf is None:
        return False
    user: Optional[UserSchema] = phi_conf.user
    if user is None:
        return False

    with authenticated_client as api:
        try:
            r: Response = api.post(
                ApiRoutes.USER_AUTHENTICATE, data=user.json(exclude_none=True)  # type: ignore
            )
            if invalid_response(r):
                return False
        except NetworkError:
            log_network_error_msg()
            return False

        response_data: Union[Dict[Any, Any], List[Any]] = r.json()
        if response_data is None or not isinstance(response_data, dict):
            logger.error("Could not parse response")
            return False
        if response_data.get("status", "fail") == "success":
            return True
    return False


def authenticate_and_get_user(
    tmp_auth_token: str,
) -> Optional[UserSchema]:
    from phiterm.conf.auth import save_auth_token

    logger.debug("--o-o-- Getting user")

    authenticated_headers = base_headers.copy()
    authenticated_headers[PHI_AUTH_TOKEN_HEADER] = tmp_auth_token
    with Client(
        base_url=BACKEND_API_URL,
        headers=authenticated_headers,
        timeout=None,
    ) as api:
        try:
            r: Response = api.post(ApiRoutes.USER_CLI_AUTH, data={"token": tmp_auth_token})
            if invalid_response(r):
                return None
        except NetworkError:
            log_network_error_msg()
            return None

        phidata_auth_token = r.headers.get(PHI_AUTH_TOKEN_HEADER)
        if phidata_auth_token is None:
            logger.error("Could not authenticate user")
            return None

        user_data = r.json()
        if not isinstance(user_data, dict):
            raise CliAuthException("Could not parse response")

        current_user: UserSchema = UserSchema.from_dict(user_data)
        if current_user is not None:
            save_auth_token(phidata_auth_token)
            return current_user
    return None


def sign_in_user(
    sign_in_data: EmailPasswordSignInSchema,
) -> Optional[UserSchema]:
    from phiterm.conf.auth import save_auth_token

    logger.debug("--o-o-- Sign in user")

    with Client(
        base_url=BACKEND_API_URL,
        headers=base_headers,
        timeout=None,
    ) as api:
        try:
            r: Response = api.post(ApiRoutes.USER_SIGN_IN, json=sign_in_data.dict())
            if invalid_response(r):
                return None
        except NetworkError as e:
            log_network_error_msg()
            return None

        phidata_auth_token = r.headers.get(PHI_AUTH_TOKEN_HEADER)
        if phidata_auth_token is None:
            logger.error("Could not authenticate user")
            return None

        user_data = r.json()
        if not isinstance(user_data, dict):
            raise CliAuthException("Could not parse response")

        current_user: UserSchema = UserSchema.from_dict(user_data)
        if current_user is not None:
            save_auth_token(phidata_auth_token)
            return current_user
    return None
