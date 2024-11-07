from typing import Union, Dict, List

from httpx import Response

from phi.api.api import api, invalid_response
from phi.api.routes import ApiRoutes
from phi.api.schemas.playground import PlaygroundEndpointCreate
from phi.utils.log import logger


def create_playground_endpoint(playground: PlaygroundEndpointCreate) -> bool:
    logger.debug("--**-- Creating Playground Endpoint")
    with api.AuthenticatedClient() as api_client:
        try:
            r: Response = api_client.post(
                ApiRoutes.PLAYGROUND_ENDPOINT_CREATE,
                json={"playground": playground.model_dump(exclude_none=True)},
            )
            if invalid_response(r):
                return False

            response_json: Union[Dict, List] = r.json()
            if response_json is None:
                return False

            # logger.debug(f"Response: {response_json}")
            return True
        except Exception as e:
            logger.debug(f"Could not create Playground Endpoint: {e}")
    return False
