from os import getenv
from typing import Union, Dict, List

from httpx import Response

from phi.api.api import api, invalid_response
from phi.api.routes import ApiRoutes
from phi.api.schemas.conversation import (
    ConversationWorkspace,
    ConversationEventCreate,
    ConversationMonitorCreate,
)
from phi.constants import WORKSPACE_ID_ENV_VAR, WORKSPACE_HASH_ENV_VAR, WORKSPACE_KEY_ENV_VAR
from phi.cli.settings import phi_cli_settings
from phi.utils.common import str_to_int
from phi.utils.log import logger


def create_conversation_monitor(monitor: ConversationMonitorCreate) -> bool:
    if not phi_cli_settings.api_enabled:
        return True

    # logger.debug("--o-o-- Creating Conversation Monitor")
    with api.AuthenticatedClient() as api_client:
        try:
            conversation_workspace = ConversationWorkspace(
                id_workspace=str_to_int(getenv(WORKSPACE_ID_ENV_VAR)),
                ws_hash=getenv(WORKSPACE_HASH_ENV_VAR),
                ws_key=getenv(WORKSPACE_KEY_ENV_VAR),
            )
            r: Response = api_client.post(
                ApiRoutes.CONVERSATION_MONITOR_CREATE,
                json={
                    "monitor": monitor.model_dump(exclude_none=True),
                    "workspace": conversation_workspace.model_dump(exclude_none=True),
                },
            )
            if invalid_response(r):
                return False

            response_json: Union[Dict, List] = r.json()
            if response_json is None:
                return False

            # logger.debug(f"Response: {response_json}")
            return True
        except Exception as e:
            logger.debug(f"Could not create conversation monitor: {e}")
    return False


def create_conversation_event(conversation: ConversationEventCreate) -> bool:
    if not phi_cli_settings.api_enabled:
        return True

    # logger.debug("--o-o-- Creating Conversation Event")
    with api.AuthenticatedClient() as api_client:
        try:
            conversation_workspace = ConversationWorkspace(
                id_workspace=str_to_int(getenv(WORKSPACE_ID_ENV_VAR)),
                ws_hash=getenv(WORKSPACE_HASH_ENV_VAR),
                ws_key=getenv(WORKSPACE_KEY_ENV_VAR),
            )
            r: Response = api_client.post(
                ApiRoutes.CONVERSATION_EVENT_CREATE,
                json={
                    "event": conversation.model_dump(exclude_none=True),
                    "workspace": conversation_workspace.model_dump(exclude_none=True),
                },
            )
            if invalid_response(r):
                return False

            response_json: Union[Dict, List] = r.json()
            if response_json is None:
                return False

            # logger.debug(f"Response: {response_json}")
            return True
        except Exception as e:
            logger.debug(f"Could not log conversation event: {e}")
    return False
