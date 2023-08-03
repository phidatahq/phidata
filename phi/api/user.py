from typing import Optional

from phi.api.client import api_client, invalid_response
from phi.api.routes import ApiRoutes
from phi.api.schemas.user import UserSchema, EmailPasswordAuthSchema
from phi.cli.config import PhiCliConfig
from phi.cli.settings import phi_cli_settings
from phi.utils.log import logger


async def user_ping() -> bool:
    if not phi_cli_settings.api_enabled:
        return False

    logger.debug("--o-o-- Ping user api")
    try:
        async with api_client.Session() as api:
            async with api.get(ApiRoutes.USER_HEALTH) as response:
                if invalid_response(response):
                    return False

                response_json = await response.json()
                if response_json is not None and response_json.get("status") == "success":
                    return True
                return False
    except Exception as e:
        logger.debug(f"Could not ping user api: {e}")
    return False


async def authenticate_and_get_user(
    tmp_auth_token: str, existing_user: Optional[UserSchema] = None
) -> Optional[UserSchema]:
    if not phi_cli_settings.api_enabled:
        return None

    from phi.cli.credentials import save_auth_token, read_auth_token

    logger.debug("--o-o-- Getting user")
    anon_user = None
    if existing_user is not None:
        if existing_user.email == "anon":
            logger.debug(f"Claiming anonymous user: {existing_user.id_user}")
            anon_user = {
                "email": existing_user.email,
                "id_user": existing_user.id_user,
                "auth_token": read_auth_token() or "",
            }
    try:
        headers = api_client.headers.copy()
        headers[phi_cli_settings.auth_token_header] = tmp_auth_token

        async with api_client.Session() as api:
            async with api.post(ApiRoutes.USER_CLI_AUTH, headers=headers, json=anon_user) as response:
                if invalid_response(response):
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

    except Exception as e:
        logger.debug(f"Could not authenticate user: {e}")
    return None


async def sign_in_user(sign_in_data: EmailPasswordAuthSchema) -> Optional[UserSchema]:
    if not phi_cli_settings.api_enabled:
        return None

    from phi.cli.credentials import save_auth_token

    logger.debug("--o-o-- Signing in user")
    try:
        async with api_client.Session() as api:
            async with api.post(ApiRoutes.USER_SIGN_IN, json=sign_in_data.model_dump()) as response:
                if invalid_response(response):
                    return None

                phidata_auth_token = response.headers.get(phi_cli_settings.auth_token_header)
                if phidata_auth_token is None:
                    logger.error("Could not authenticate user")
                    return None

                response_json = await response.json()
                if response_json is None:
                    return None

                current_user: UserSchema = UserSchema.model_validate(response_json)
                if current_user is not None:
                    save_auth_token(phidata_auth_token)
                    return current_user
                return None
    except Exception as e:
        logger.debug(f"Could not sign in user: {e}")
    return None


async def user_is_authenticated() -> bool:
    if not phi_cli_settings.api_enabled:
        return False

    logger.debug("--o-o-- Checking if user is authenticated")
    try:
        phi_config: Optional[PhiCliConfig] = PhiCliConfig.from_saved_config()
        if phi_config is None:
            return False
        user: Optional[UserSchema] = phi_config.user
        if user is None:
            return False

        async with api_client.Session() as api:
            async with api.get(
                ApiRoutes.USER_AUTHENTICATE, json=user.model_dump(include={"id_user", "email"})
            ) as response:
                if invalid_response(response):
                    return False

                response_json = await response.json()
                if response_json is not None and response_json.get("status") == "success":
                    return True
                return False
    except Exception as e:
        logger.debug(f"Could not check if user is authenticated: {e}")
    return False


async def create_anon_user() -> Optional[UserSchema]:
    if not phi_cli_settings.api_enabled:
        return None

    from phi.cli.credentials import save_auth_token

    logger.debug("--o-o-- Creating anon user")
    try:
        async with api_client.Session() as api:
            async with api.post(
                ApiRoutes.USER_CREATE, json={"email": "anon", "username": "anon", "is_bot": True}
            ) as response:
                if invalid_response(response):
                    return None

                phidata_auth_token = response.headers.get(phi_cli_settings.auth_token_header)
                if phidata_auth_token is None:
                    logger.error("Could not authenticate user")
                    return None

                response_json = await response.json()
                if response_json is None:
                    return None

                current_user: UserSchema = UserSchema.model_validate(response_json)
                if current_user is not None:
                    save_auth_token(phidata_auth_token)
                    return current_user
    except Exception as e:
        logger.debug(f"Could not create anon user: {e}")
    return None
