from typing import Any, Dict, List, Optional, Union

from phi.api.client import api_client, invalid_respose
from phi.api.routes import ApiRoutes
from phi.api.schemas.user import UserSchema, EmailPasswordAuthSchema
from phi.cli.settings import phi_cli_settings
from phi.utils.log import logger


async def user_ping() -> bool:
    logger.debug("--o-o-- Ping user api")
    async with api_client.Session() as api:
        async with api.get(ApiRoutes.USER_HEALTH) as response:
            if invalid_respose(response):
                return False

            response_json = await response.json()
            if response_json is not None and response_json.get("status") == "success":
                return True
            return False


async def authenticate_and_get_user(tmp_auth_token: str) -> Optional[UserSchema]:
    from phi.cli.credentials import save_auth_token

    logger.debug("--o-o-- Getting user")
    headers = api_client.headers.copy()
    headers[phi_cli_settings.auth_token_header] = tmp_auth_token

    async with api_client.Session() as api:
        async with api.post(ApiRoutes.USER_CLI_AUTH, headers=headers) as response:
            if invalid_respose(response):
                return None

            new_auth_token = response.headers.get(phi_cli_settings.auth_token_header)
            if new_auth_token is None:
                logger.error("Could not authenticate user")
                return None

            response_json = await response.json()
            if response_json is None:
                return None

            current_user: UserSchema = UserSchema.model_validate(response_json)
            if current_user is not None:
                save_auth_token(new_auth_token)
                return current_user
            return None
