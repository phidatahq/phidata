from typing import Union

from fastapi import FastAPI

from phi.api.playground import create_playground_endpoint, PlaygroundEndpointCreate
from phi.utils.log import logger


def serve_playground_app(
    app: Union[str, FastAPI],
    *,
    scheme: str = "http",
    host: str = "localhost",
    port: int = 7777,
    reload: bool = False,
    prefix="/v1",
    **kwargs,
):
    import uvicorn

    try:
        create_playground_endpoint(
            playground=PlaygroundEndpointCreate(
                endpoint=f"{scheme}://{host}:{port}", playground_data={"prefix": prefix}
            ),
        )
    except Exception as e:
        logger.error(f"Could not create playground endpoint: {e}")
        logger.error("Please try again.")
        return

    uvicorn.run(app=app, host=host, port=port, reload=reload, **kwargs)
