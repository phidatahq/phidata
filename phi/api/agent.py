import asyncio
from os import getenv
from typing import Union, Dict, List

from httpx import Response

from phi.api.api import api, invalid_response
from phi.api.routes import ApiRoutes
from phi.api.schemas.agent import AgentRunCreate, AgentSessionCreate
from phi.constants import PHI_API_KEY_ENV_VAR
from phi.cli.settings import phi_cli_settings
from phi.utils.log import logger


async def create_agent_session(session: AgentSessionCreate) -> None:
    if not phi_cli_settings.api_enabled:
        return

    phi_api_key = getenv(PHI_API_KEY_ENV_VAR)
    if phi_api_key is None:
        logger.warning(f"{PHI_API_KEY_ENV_VAR} not set. You can get one from https://phidata.app")
        return

    logger.debug("--**-- Logging Agent Session")
    async with api.AuthenticatedAsyncClient() as api_client:
        try:
            r: Response = await api_client.post(
                ApiRoutes.AGENT_SESSION_CREATE,
                headers={
                    "Authorization": f"Bearer {phi_api_key}",
                },
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


def trigger_agent_session_creation(session: AgentSessionCreate) -> None:
    try:
        # Get the current event loop if it exists
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # If no loop is found, create a new one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    if loop.is_running():
        # Schedule the coroutine within the running loop
        asyncio.create_task(create_agent_session(session))
    else:
        # Create a new event loop to run the task
        loop.run_until_complete(create_agent_session(session))


async def create_agent_run(run: AgentRunCreate) -> None:
    if not phi_cli_settings.api_enabled:
        return

    phi_api_key = getenv(PHI_API_KEY_ENV_VAR)
    if phi_api_key is None:
        logger.warning(f"{PHI_API_KEY_ENV_VAR} not set. You can get one from https://phidata.app")
        return

    logger.debug("--**-- Logging Agent Run")
    async with api.AuthenticatedAsyncClient() as api_client:
        try:
            r: Response = await api_client.post(
                ApiRoutes.AGENT_RUN_CREATE,
                headers={
                    "Authorization": f"Bearer {phi_api_key}",
                },
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


def trigger_agent_run_creation(run: AgentRunCreate) -> None:
    try:
        # Get the current event loop if it exists
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # If no loop is found, create a new one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    if loop.is_running():
        # Schedule the coroutine within the running loop
        asyncio.create_task(create_agent_run(run))
    else:
        # Create a new event loop to run the task
        loop.run_until_complete(create_agent_run(run))
