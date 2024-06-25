from typing import Optional, Union, Dict, List, Iterator

from httpx import Response

from phi.api.api import api, invalid_response
from phi.api.routes import ApiRoutes
from phi.api.schemas.ai import (
    ConversationType,
    ConversationClient,
    ConversationCreateResponse,
)
from phi.api.schemas.user import UserSchema
from phi.llm.message import Message
from phi.tools.function import Function
from phi.utils.log import logger


def conversation_create(
    user: UserSchema,
    conversation_type: ConversationType = ConversationType.RAG,
    functions: Optional[Dict[str, Function]] = None,
) -> Optional[ConversationCreateResponse]:
    logger.debug("--o-o-- Creating Conversation")
    with api.AuthenticatedClient() as api_client:
        try:
            r: Response = api_client.post(
                ApiRoutes.AI_CONVERSATION_CREATE,
                json={
                    "user": user.model_dump(include={"id_user", "email"}),
                    "conversation": {
                        "type": conversation_type,
                        "client": ConversationClient.CLI,
                        "functions": {
                            k: v.model_dump(include={"name", "description", "parameters"}) for k, v in functions.items()
                        }
                        if functions is not None
                        else None,
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


def conversation_chat(
    user: UserSchema,
    conversation_id: str,
    message: Message,
    conversation_type: ConversationType = ConversationType.RAG,
    functions: Optional[Dict[str, Function]] = None,
    stream: bool = True,
) -> Optional[Iterator[str]]:
    with api.AuthenticatedClient() as api_client:
        if stream:
            logger.debug("--o-o-- Streaming Conversation Chat")
            try:
                with api_client.stream(
                    "POST",
                    ApiRoutes.AI_CONVERSATION_CHAT,
                    json={
                        "user": user.model_dump(include={"id_user", "email"}),
                        "conversation": {
                            "id": conversation_id,
                            "message": message.model_dump(exclude_none=True),
                            "type": conversation_type,
                            "client": ConversationClient.CLI,
                            "functions": {
                                k: v.model_dump(include={"name", "description", "parameters"})
                                for k, v in functions.items()
                            }
                            if functions is not None
                            else None,
                            "stream": stream,
                        },
                    },
                ) as streaming_resp:
                    for chunk in streaming_resp.iter_text():
                        yield chunk
            except Exception as e:
                logger.error(f"Error: {e}")
                logger.info("Please message us on https://discord.gg/4MtYHHrgA8 for help.")
                exit(1)
        else:
            logger.debug("--o-o-- Conversation Chat")
            try:
                resp: Response = api_client.post(
                    ApiRoutes.AI_CONVERSATION_CHAT,
                    json={
                        "user": user.model_dump(include={"id_user", "email"}),
                        "conversation": {
                            "id": conversation_id,
                            "message": message.model_dump(exclude_none=True),
                            "type": conversation_type,
                            "client": ConversationClient.CLI,
                            "functions": {
                                k: v.model_dump(include={"name", "description", "parameters"})
                                for k, v in functions.items()
                            }
                            if functions is not None
                            else None,
                            "stream": stream,
                        },
                    },
                )
                if invalid_response(resp):
                    return None

                response_json: Optional[Dict] = resp.json()
                if response_json is None:
                    return None

                yield response_json.get("response")
            except Exception as e:
                logger.error(f"Error: {e}")
                logger.info("Please message us on https://discord.gg/4MtYHHrgA8 for help.")
                exit(1)
    return None


# import os
# import base64
# import contextlib
# import wsproto
#
# class ConnectionClosed(Exception):
#     logger.debug("Connection closed")
#     pass
#
#
# class WebsocketConnection:
#     def __init__(self, network_steam):
#         self._ws_connection = wsproto.Connection(wsproto.ConnectionType.CLIENT)
#         self._network_stream = network_steam
#         self._events = []
#
#     async def send(self, text):
#         """
#         Send a text frame over the websocket connection.
#         """
#         try:
#             event = wsproto.events.TextMessage(text)
#             data = self._ws_connection.send(event)
#             await self._network_stream.write(data)
#         except Exception as e:
#             logger.debug(f"Failed to send: {e}")
#             logger.info("Connection closed, please start chat again.")
#             exit(1)
#
#     async def recv(self):
#         """
#         Receive the next text frame from the websocket connection.
#         """
#         try:
#             while not self._events:
#                 data = await self._network_stream.read(max_bytes=4096)
#                 self._ws_connection.receive_data(data)
#                 self._events = list(self._ws_connection.events())
#
#             event = self._events.pop(0)
#             if isinstance(event, wsproto.events.TextMessage):
#                 return event.data
#             elif isinstance(event, wsproto.events.CloseConnection):
#                 raise ConnectionClosed()
#         except Exception as e:
#             logger.debug(f"Failed to receive: {e}")
#             logger.info("Connection closed, please start chat again.")
#             exit(1)
#
#
# @contextlib.asynccontextmanager
# async def ai_ws_connect(
#     user: UserSchema,
#     conversation_id: int,
#     conversation_type: ConversationType = ConversationType.RAG,
#     stream: bool = True,
# ):
#     async with api.AuthenticatedAsyncClient() as api_client:
#         headers = {
#             "connection": "upgrade",
#             "upgrade": "websocket",
#             "sec-websocket-key": base64.b64encode(os.urandom(16)),
#             "sec-websocket-version": "13",
#             "X-PHIDATA-USER-ID": f"{user.id_user}",
#             "X-PHIDATA-CONVERSATION-ID": f"{conversation_id}",
#             "X-PHIDATA-CONVERSATION-TYPE": conversation_type.value,
#             "X-PHIDATA-CONVERSATION-STREAM": "true" if stream else "false",
#         }
#         headers.update(api.authenticated_headers)
#         logger.debug(f"Connecting to {ApiRoutes.AI_CONVERSATION_CHAT_WS}. Headers: {headers}")
#         async with api_client.stream(
#             "GET",
#             ApiRoutes.AI_CONVERSATION_CHAT_WS,
#             headers=headers,  # type: ignore
#         ) as response:
#             network_steam = response.extensions["network_stream"]
#             yield WebsocketConnection(network_steam)
#
