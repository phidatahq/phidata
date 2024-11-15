from typing import Union
from urllib.parse import quote

from fastapi import FastAPI
from rich import box
from rich.panel import Panel

from phi.api.playground import create_workflow_playground_endpoint
from phi.api.schemas.playground import WorkflowPlaygroundEndpointCreate
from phi.cli.settings import phi_cli_settings
from phi.cli.console import console
from phi.utils.log import logger


def serve_workflow_playground_app(
    app: Union[str, FastAPI],
    *,
    scheme: str = "http",
    host: str = "localhost",
    port: int = 1111,
    reload: bool = False,
    prefix="/v1",
    **kwargs,
):
    import uvicorn

    try:
        create_workflow_playground_endpoint(
            playground=WorkflowPlaygroundEndpointCreate(
                endpoint=f"{scheme}://{host}:{port}", workflow_playground_data={"prefix": prefix}
            ),
        )
    except Exception as e:
        logger.error(f"Could not create workflow playground endpoint: {e}")
        logger.error("Please try again.")
        return

    logger.info(f"Starting workflow playground on {scheme}://{host}:{port}")
    encoded_endpoint = quote(f"{host}:{port}")
    url = f"{phi_cli_settings.playground_url}?endpoint={encoded_endpoint}"
    panel = Panel(
        f"[bold green]URL:[/bold green] [link={url}]{url}[/link]",
        title="Agent Workflow Playground",
        expand=False,
        border_style="cyan",
        box=box.HEAVY,
        padding=(2, 2),
    )
    console.print(panel)

    uvicorn.run(app=app, host=host, port=port, reload=reload, **kwargs)
