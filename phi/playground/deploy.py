from pathlib import Path
from typing import Optional, Union
from urllib.parse import quote

from fastapi import FastAPI
from rich import box
from rich.panel import Panel

from phi.api.playground import create_playground_endpoint, PlaygroundEndpointCreate
from phi.cli.settings import phi_cli_settings
from phi.cli.console import console
from phi.utils.log import logger


def deploy_playground_app(
    app: Union[str, FastAPI],
    root_path: Path,
    **kwargs,
):
    import uvicorn
    from time import sleep
    from rich.text import Text
    from rich.panel import Panel
    from rich.live import Live
    from rich.console import Group
    from rich.status import Status
    from phi.utils.timer import Timer

    # Print using Live display
    with Live(refresh_per_second=4) as live_display:
        # Create and start timer
        response_timer = Timer()
        response_timer.start()

        # Initialize panels list with deployment info
        deployment_info = Text.assemble(
            ("📦 App: ", "bold"),
            (f"{app}\n", "cyan"),
            ("📂 Root Path: ", "bold"),
            (f"{root_path}\n", "cyan"),
            ("⏱️  Time: ", "bold"),
            ("[waiting...]", "yellow"),
        )
        panels = [
            Panel(
                deployment_info,
                title="[bold green]🚀 Deploying Playground App[/bold green]",
                border_style="cyan",
                box=box.HEAVY,
                padding=(1, 2),
            )
        ]

        # Add status with custom spinner
        status = Status(
            "[bold blue]Initializing playground...[/bold blue]",
            spinner="aesthetic",
            speed=2,
        )
        panels.append(status)

        # Initial display update
        live_display.update(Group(*panels))

        # Simulate deployment steps
        for step in ["Configuring server...", "Setting up routes...", "Starting service..."]:
            sleep(0.7)
            status.update(f"[bold blue]{step}[/bold blue]")
            # Update timer in deployment info
            deployment_info = Text.assemble(
                ("📦 App: ", "bold"),
                (f"{app}\n", "cyan"),
                ("📂 Root Path: ", "bold"),
                (f"{root_path}\n", "cyan"),
                ("⏱️  Time: ", "bold"),
                (f"{response_timer.elapsed:.1f}s", "yellow"),
            )
            panels[0] = Panel(
                deployment_info,
                title="[bold green]🚀 Deploying Playground App[/bold green]",
                border_style="cyan",
                box=box.HEAVY,
                padding=(1, 2),
            )
            live_display.update(Group(*panels))

        # Clean up status and show final state
        status.stop()
        panels.pop()  # Remove status panel
        live_display.update(Group(*panels))

    # try:
    #     create_playground_endpoint(
    #         playground=PlaygroundEndpointCreate(
    #             endpoint=f"{scheme}://{host}:{port}", playground_data={"prefix": prefix}
    #         ),
    #     )
    # except Exception as e:
    #     logger.error(f"Could not create playground endpoint: {e}")
    #     logger.error("Please try again.")
    #     return

    # logger.info(f"Starting playground on {scheme}://{host}:{port}")
    # # Encode the full endpoint (host:port)
    # encoded_endpoint = quote(f"{host}:{port}")

    # # Create a panel with the playground URL
    # url = f"{phi_cli_settings.playground_url}?endpoint={encoded_endpoint}"
    # panel = Panel(
    #     f"[bold green]URL:[/bold green] [link={url}]{url}[/link]",
    #     title="Agent Playground",
    #     expand=False,
    #     border_style="cyan",
    #     box=box.HEAVY,
    #     padding=(2, 2),
    # )

    # # Print the panel
    # console.print(panel)

    # uvicorn.run(app=app, host=host, port=port, reload=reload, **kwargs)
