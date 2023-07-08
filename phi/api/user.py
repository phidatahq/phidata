from typing import Any, Dict, List, Optional, Union

from httpx import Client, Response, NetworkError

from phi.api.client import base_headers, get_authenticated_client
from phi.api.helpers import is_valid_response, is_invalid_response
from phi.api.routes import ApiRoutes
from phi.cli.config import PhiCliConfig
from phi.cli.console import log_network_error_msg
from phi.cli.settings import phi_cli_settings
from phi.schemas.user import UserSchema, EmailPasswordSignInSchema
from phi.utils.log import logger


def user_ping() -> bool:
    logger.debug("--o-o-- Ping user api")
    with Client(base_url=phi_cli_settings.api_url, headers=base_headers, timeout=60) as api:
        try:
            r: Response = api.get(ApiRoutes.USER_PING)
            if is_invalid_response(r):
                return False
        except NetworkError:
            log_network_error_msg()
            return False

        if is_valid_response(r):
            return True
    return False


def is_user_authenticated() -> bool:
    logger.debug("--o-o-- Authenticating user")
    authenticated_client: Optional[Client] = get_authenticated_client()
    if authenticated_client is None:
        logger.debug("Session not available")
        return False

    phi_config: Optional[PhiCliConfig] = PhiCliConfig.from_saved_config()
    if phi_config is None:
        return False
    user: Optional[UserSchema] = phi_config.user
    if user is None:
        return False

    with authenticated_client as api:
        try:
            r: Response = api.post(
                ApiRoutes.USER_AUTHENTICATE, data=user.model_dump_json(exclude_none=True)  # type: ignore
            )
            if is_invalid_response(r):
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
    from phi.cli.credentials import save_auth_token

    logger.debug("--o-o-- Getting user")
    authenticated_headers = base_headers.copy()
    authenticated_headers[phi_cli_settings.auth_token_header] = tmp_auth_token
    with Client(
        base_url=phi_cli_settings.api_url,
        headers=authenticated_headers,
        timeout=None,
    ) as api:
        try:
            r: Response = api.post(ApiRoutes.USER_CLI_AUTH, data={"token": tmp_auth_token})
            if is_invalid_response(r):
                return None
        except NetworkError:
            log_network_error_msg()
            return None

        phidata_auth_token = r.headers.get(phi_cli_settings.auth_token_header)
        if phidata_auth_token is None:
            logger.error("Could not authenticate user")
            return None

        user_data = r.json()
        if not isinstance(user_data, dict):
            raise Exception("Could not parse response")

        current_user: UserSchema = UserSchema.from_dict(user_data)
        if current_user is not None:
            save_auth_token(phidata_auth_token)
            return current_user
    return None


def sign_in_user(
    sign_in_data: EmailPasswordSignInSchema,
) -> Optional[UserSchema]:
    from phi.cli.credentials import save_auth_token

    logger.debug("--o-o-- Sign in user")
    with Client(
        base_url=phi_cli_settings.api_url,
        headers=base_headers,
        timeout=None,
    ) as api:
        try:
            r: Response = api.post(ApiRoutes.USER_SIGN_IN, json=sign_in_data.dict())
            if is_invalid_response(r):
                return None
        except NetworkError:
            log_network_error_msg()
            return None

        phidata_auth_token = r.headers.get(phi_cli_settings.auth_token_header)
        if phidata_auth_token is None:
            logger.error("Could not authenticate user")
            return None

        user_data = r.json()
        if not isinstance(user_data, dict):
            raise Exception("Could not parse response")

        current_user: UserSchema = UserSchema.from_dict(user_data)
        if current_user is not None:
            save_auth_token(phidata_auth_token)
            return current_user
    return None
