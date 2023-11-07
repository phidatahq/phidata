from typing import Optional, Dict, Iterator, Any

from httpx import Response

from phi.api.api import api, invalid_response
from phi.api.routes import ApiRoutes
from phi.constants import WORKSPACE_ID_ENV_VAR, WORKSPACE_HASH_ENV_VAR
from phi.utils.env import get_from_env
from phi.utils.log import logger


def openai_chat(params: Dict[str, Any]) -> Optional[str]:
    with api.AuthenticatedClient() as api_client:
        logger.debug("--o-o-- OpenAI Chat")
        try:
            workspace_id = get_from_env(WORKSPACE_ID_ENV_VAR)
            workspace_hash = get_from_env(WORKSPACE_HASH_ENV_VAR)

            resp: Response = api_client.post(
                ApiRoutes.OPENAI_CHAT,
                json={
                    "workspace": {
                        "id_workspace": workspace_id,
                        "ws_hash": workspace_hash,
                    },
                    "params": params,
                },
            )
            if invalid_response(resp):
                return None

            return resp.json()
        except Exception as e:
            logger.error(f"Error: {e}")
            logger.info("Please message us on https://discord.gg/4MtYHHrgA8 for help.")
            exit(1)


def openai_chat_stream(params: Dict[str, Any]) -> Iterator[str]:
    with api.AuthenticatedClient() as api_client:
        logger.debug("--o-o-- OpenAI Chat Stream")
        try:
            workspace_id = get_from_env(WORKSPACE_ID_ENV_VAR)
            workspace_hash = get_from_env(WORKSPACE_HASH_ENV_VAR)

            with api_client.stream(
                "POST",
                ApiRoutes.OPENAI_CHAT,
                json={
                    "workspace": {
                        "id_workspace": workspace_id,
                        "ws_hash": workspace_hash,
                    },
                    "params": params,
                },
            ) as streaming_resp:
                for chunk in streaming_resp.iter_text():
                    yield chunk
        except Exception as e:
            logger.error(f"Error: {e}")
            logger.info("Please message us on https://discord.gg/4MtYHHrgA8 for help.")
            exit(1)


def openai_embedding(params: Dict[str, Any]) -> Optional[str]:
    with api.AuthenticatedClient() as api_client:
        logger.debug("--o-o-- OpenAI Embedding")
        try:
            workspace_id = get_from_env(WORKSPACE_ID_ENV_VAR)
            workspace_hash = get_from_env(WORKSPACE_HASH_ENV_VAR)

            resp: Response = api_client.post(
                ApiRoutes.OPENAI_EMBEDDING,
                json={
                    "workspace": {
                        "id_workspace": workspace_id,
                        "ws_hash": workspace_hash,
                    },
                    "params": params,
                },
            )
            if invalid_response(resp):
                return None

            return resp.json()
        except Exception as e:
            logger.error(f"Error: {e}")
            logger.info("Please message us on https://discord.gg/4MtYHHrgA8 for help.")
            exit(1)
