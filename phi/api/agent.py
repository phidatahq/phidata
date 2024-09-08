from os import getenv
from typing import Union, Dict, List

from httpx import Response

from phi.api.api import api, invalid_response
from phi.api.routes import ApiRoutes
from phi.api.schemas.agent import AgentRunCreate, AgentSessionCreate
from phi.constants import PHI_API_KEY_ENV_VAR, PHI_WS_KEY_ENV_VAR
from phi.cli.settings import phi_cli_settings
from phi.utils.log import logger


def create_agent_session(session: AgentSessionCreate) -> bool:
    if not phi_cli_settings.api_enabled:
        return True

    logger.debug("--**-- Creating Agent Session")
    with api.AuthenticatedClient() as api_client:
        try:
            r: Response = api_client.post(
                ApiRoutes.AGENT_SESSION_CREATE,
                headers={
                    "Authorization": f"Bearer {getenv(PHI_API_KEY_ENV_VAR)}",
                    "PHI-WORKSPACE": f"{getenv(PHI_WS_KEY_ENV_VAR)}",
                },
                json={"session": session.model_dump(exclude_none=True)},
            )
            if invalid_response(r):
                return False

            response_json: Union[Dict, List] = r.json()
            if response_json is None:
                return False

            logger.debug(f"Response: {response_json}")
            return True
        except Exception as e:
            logger.debug(f"Could not create assistant run: {e}")
    return False


def create_agent_run(run: AgentRunCreate) -> bool:
    if not phi_cli_settings.api_enabled:
        return True

    logger.debug("--**-- Creating Assistant Event")
    with api.AuthenticatedClient() as api_client:
        try:
            r: Response = api_client.post(
                ApiRoutes.AGENT_RUN_CREATE,
                headers={
                    "Authorization": f"Bearer {getenv(PHI_API_KEY_ENV_VAR)}",
                    "PHI-WORKSPACE": f"{getenv(PHI_WS_KEY_ENV_VAR)}",
                },
                json={"run": run.model_dump(exclude_none=True)},
            )
            if invalid_response(r):
                return False

            response_json: Union[Dict, List] = r.json()
            if response_json is None:
                return False

            logger.debug(f"Response: {response_json}")
            return True
        except Exception as e:
            logger.debug(f"Could not create assistant event: {e}")
    return False
