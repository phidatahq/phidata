from typing import Optional, Union, Dict, List

from httpx import Response

from phi.api.api import api, invalid_response
from phi.api.routes import ApiRoutes
from phi.api.schemas.ai import (
    ConversationType,
    ConversationClient,
    ConversationCreateResponse,
    ConversationChatResponse,
)
from phi.api.schemas.user import UserSchema
from phi.utils.log import logger


def conversation_create(user: UserSchema) -> Optional[ConversationCreateResponse]:
    logger.debug("--o-o-- Creating Conversation")
    with api.AuthenticatedClient() as api_client:
        try:
            r: Response = api_client.post(
                ApiRoutes.AI_CONVERSATION_CREATE,
                json={
                    "user": user.model_dump(include={"id_user", "email"}),
                    "conversation": {
                        "type": ConversationType.RAG,
                        "client": ConversationClient.CLI,
                    },
                },
            )
            if invalid_response(r):
                return None

            response_json: Union[Dict, List] = r.json()
            if response_json is None:
                return None

            new_conversation = ConversationCreateResponse.model_validate(response_json)
            if new_conversation is not None:
                return new_conversation
        except Exception as e:
            logger.debug(f"Could not create conversation: {e}")
    return None


def conversation_chat(user: UserSchema, conversation_id: int, message: str) -> Optional[ConversationChatResponse]:
    logger.debug("--o-o-- Conversation Chat")
    with api.AuthenticatedClient() as api_client:
        try:
            r: Response = api_client.post(
                ApiRoutes.AI_CONVERSATION_CHAT,
                json={
                    "user": user.model_dump(include={"id_user", "email"}),
                    "conversation": {
                        "id": conversation_id,
                        "message": message,
                        "type": ConversationType.RAG,
                        "client": ConversationClient.CLI,
                    },
                },
            )
            if invalid_response(r):
                return None

            response_json: Union[Dict, List] = r.json()
            if response_json is None:
                return None

            conversation_chat_response = ConversationChatResponse.model_validate(response_json)
            if conversation_chat_response is not None:
                return conversation_chat_response
        except Exception as e:
            logger.debug(f"Failed conversation chat: {e}")
    return None
