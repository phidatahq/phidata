from os import getenv
from typing import Optional, Union, Dict, List

from httpx import Response

from phi.api.api import api, invalid_response
from phi.api.routes import ApiRoutes
from phi.api.schemas.conversation import (
    ConversationEventCreate,
    ConversationWorkspace,
    ConversationEventCreateResopnse,
    ConversationUpdate,
    ConversationSchema,
)
from phi.constants import WORKSPACE_ID_ENV_VAR, WORKSPACE_HASH_ENV_VAR
from phi.cli.settings import phi_cli_settings
from phi.utils.common import str_to_int
from phi.utils.log import logger


def upsert_conversation(conversation: ConversationUpdate) -> Optional[ConversationSchema]:
    if not phi_cli_settings.api_enabled:
        return None

    logger.debug("--o-o-- Conversation upsert")
    with api.Client() as api_client:
        try:
            workspace_id = str_to_int(getenv(WORKSPACE_ID_ENV_VAR))
            if workspace_id is None:
                return None
            workspace_hash = getenv(WORKSPACE_HASH_ENV_VAR)
            if workspace_hash is None:
                return None
            workspace = ConversationWorkspace(id_workspace=workspace_id, ws_hash=workspace_hash)

            r: Response = api_client.post(
                ApiRoutes.CONVERSATION_UPSERT,
                json={
                    "conversation": conversation.model_dump(exclude_none=True),
                    "workspace": workspace.model_dump(exclude_none=True),
                },
            )
            if invalid_response(r):
                return None

            response_json: Union[Dict, List] = r.json()
            if response_json is None:
                return None

            conversation_schema: Optional[ConversationSchema] = ConversationSchema.model_validate(response_json)
            # logger.debug(f"Conversation: {conversation_schema}")
            return conversation_schema
        except Exception as e:
            logger.debug(f"Could not update conversation: {e}")
    return None


def log_conversation_event(conversation: ConversationEventCreate) -> Optional[ConversationEventCreateResopnse]:
    if not phi_cli_settings.api_enabled:
        return None

    logger.debug("--o-o-- Log conversation event")
    with api.Client() as api_client:
        try:
            workspace_id = str_to_int(getenv(WORKSPACE_ID_ENV_VAR))
            if workspace_id is None:
                return None
            workspace_hash = getenv(WORKSPACE_HASH_ENV_VAR)
            if workspace_hash is None:
                return None
            workspace = ConversationWorkspace(id_workspace=workspace_id, ws_hash=workspace_hash)

            r: Response = api_client.post(
                ApiRoutes.CONVERSATION_EVENT_CREATE,
                json={
                    "event": conversation.model_dump(exclude_none=True),
                    "workspace": workspace.model_dump(exclude_none=True),
                },
            )
            if invalid_response(r):
                return None

            response_json: Union[Dict, List] = r.json()
            if response_json is None:
                return None

            conversation_event_response: ConversationEventCreateResopnse = (
                ConversationEventCreateResopnse.model_validate(response_json)
            )
            # logger.debug(f"Conversation response: {conversation_event_response}")
            return conversation_event_response
        except Exception as e:
            logger.debug(f"Could not log conversation event: {e}")
    return None
