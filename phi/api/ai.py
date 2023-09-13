from typing import Optional, Union, Dict, List

from httpx import Response
from pydantic import BaseModel

from phi.api.api import api, invalid_response
from phi.api.routes import ApiRoutes
from phi.api.schemas.user import UserSchema
from phi.utils.log import logger


class NewConversation(BaseModel):
    message: str


def create_conversation(message: str, user: UserSchema) -> Optional[NewConversation]:
    logger.debug("--o-o-- Create Conversation")
    with api.AuthenticatedClient() as api_client:
        try:
            r: Response = api_client.post(
                ApiRoutes.AI_CONVERSATION_CREATE,
                json={
                    "user": user.model_dump(include={"id_user", "email"}),
                    "conversation": {
                        "message": message,
                    },
                },
            )
            if invalid_response(r):
                return None

            response_json: Union[Dict, List] = r.json()
            if response_json is None:
                return None

            new_conversation: NewConversation = NewConversation.model_validate(response_json)
            if new_conversation is not None:
                return new_conversation
        except Exception as e:
            logger.debug(f"Could not create conversation: {e}")
    return None
