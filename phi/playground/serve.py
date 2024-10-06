from typing import Union

from fastapi import FastAPI

from phi.api.playground import create_playground_endpoint, PlaygroundEndpointCreate
from phi.utils.log import logger


def serve_playground_app(
    app: Union[str, FastAPI],
    *,
    host: str = "localhost",
    port: int = 7777,
    reload: bool = False,
    **kwargs,
):
    import uvicorn

    try:
        create_playground_endpoint(
            playground=PlaygroundEndpointCreate(endpoint=f"http://{host}:{port}"),
        )
    except Exception as e:
        logger.error(f"Could not create Playground Endpoint: {e}")
        logger.error("Please try again.")
        return

    uvicorn.run(app=app, host=host, port=port, reload=reload, **kwargs)
