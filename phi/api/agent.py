from typing import Union, Dict, List

from httpx import Response

from phi.api.api import api, invalid_response
from phi.api.routes import ApiRoutes
from phi.api.schemas.agent import AgentRunCreate, AgentSessionCreate
from phi.cli.settings import phi_cli_settings
from phi.utils.log import logger


def create_agent_session(session: AgentSessionCreate, monitor: bool = False) -> None:
    if not phi_cli_settings.api_enabled:
        return

    logger.debug("--**-- Logging Agent Session")
    with api.AuthenticatedClient() as api_client:
        try:
            r: Response = api_client.post(
                ApiRoutes.AGENT_SESSION_CREATE if monitor else ApiRoutes.AGENT_TELEMETRY_SESSION_CREATE,
                json={"session": session.model_dump(exclude_none=True)},
            )
            if invalid_response(r):
                logger.debug(f"Invalid response: {r.status_code}, {r.text}")
                return

            response_json: Union[Dict, List] = r.json()
            if response_json is None:
                return

            logger.debug(f"Response: {response_json}")
            return
        except Exception as e:
            logger.debug(f"Could not create Agent session: {e}")
    return


def create_agent_run(run: AgentRunCreate, monitor: bool = False) -> None:
    if not phi_cli_settings.api_enabled:
        return

    logger.debug("--**-- Logging Agent Run")
    with api.AuthenticatedClient() as api_client:
        try:
            r: Response = api_client.post(
                ApiRoutes.AGENT_RUN_CREATE if monitor else ApiRoutes.AGENT_TELEMETRY_RUN_CREATE,
                json={"run": run.model_dump(exclude_none=True)},
            )
            if invalid_response(r):
                logger.debug(f"Invalid response: {r.status_code}, {r.text}")
                return

            response_json: Union[Dict, List] = r.json()
            if response_json is None:
                return

            logger.debug(f"Response: {response_json}")
            return
        except Exception as e:
            logger.debug(f"Could not create Agent run: {e}")
    return
