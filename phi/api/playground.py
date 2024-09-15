from os import getenv
from typing import Union, Dict, List

from httpx import Response

from phi.api.api import api, invalid_response
from phi.api.routes import ApiRoutes
from phi.api.schemas.playground import PlaygroundEndpointCreate
from phi.constants import PHI_API_KEY_ENV_VAR
from phi.utils.log import logger


def create_playground_endpoint(playground: PlaygroundEndpointCreate) -> bool:
    phi_api_key = getenv(PHI_API_KEY_ENV_VAR)
    if phi_api_key is None:
        logger.warning(f"{PHI_API_KEY_ENV_VAR} not set. You can get one from https://phidata.app")
        return False

    logger.debug("--**-- Creating Playground Endpoint")
    with api.AuthenticatedClient() as api_client:
        try:
            r: Response = api_client.post(
                ApiRoutes.PLAYGROUND_ENDPOINT_CREATE,
                headers={
                    "Authorization": f"Bearer {phi_api_key}",
                },
                json={"playground": playground.model_dump(exclude_none=True)},
            )
            if invalid_response(r):
                return False

            response_json: Union[Dict, List] = r.json()
            if response_json is None:
                return False

            logger.debug(f"Response: {response_json}")
            return True
        except Exception as e:
            logger.debug(f"Could not create Playground Endpoint: {e}")
    return False
