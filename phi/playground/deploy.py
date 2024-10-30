import tarfile
from pathlib import Path
from typing import Optional, List

from rich import box
from rich.text import Text
from rich.panel import Panel

from phi.cli.settings import phi_cli_settings
from phi.api.playground import upload_tar_archive
from phi.utils.log import logger


def create_deployment_info(
    app: str, mount: Path, elapsed_time: str = "[waiting...]", status: Optional[str] = None, error: Optional[str] = None
) -> Text:
    """Create a formatted text display showing deployment information.

    Args:
        app (str): The name of the application being deployed
        mount (Path): The path to the mounted directory
        elapsed_time (str): The elapsed deployment time. Defaults to "[waiting...]"
        status (Optional[str]): The current deployment status. Defaults to None
        error (Optional[str]): The deployment error message. Defaults to None

    Returns:
        Text: A Rich Text object containing formatted deployment information
    """
    # Base info always shown
    elements = [
        ("📦 App: ", "bold"),
        (f"{app}\n", "cyan"),
        ("📂 Mount: ", "bold"),
        (f"{mount}\n", "cyan"),
        ("⏱️  Time: ", "bold"),
        (f"{elapsed_time}\n", "yellow"),
    ]

    # Add either status or error, not both
    if error is not None:
        elements.extend(
            [
                ("🚨 Error: ", "bold"),
                (f"{error}", "red"),
            ]
        )
    elif status is not None:
        elements.extend(
            [
                ("🚧 Status: ", "bold"),
                (f"{status}", "yellow"),
            ]
        )

    return Text.assemble(*elements)


def create_info_panel(deployment_info: Text) -> Panel:
    """Create a formatted panel to display deployment information.

    Args:
        deployment_info (Text): The Rich Text object containing deployment information

    Returns:
        Panel: A Rich Panel object containing the formatted deployment information
    """
    return Panel(
        deployment_info,
        title="[bold green]🚀 Deploying Playground App[/bold green]",
        border_style="cyan",
        box=box.HEAVY,
        padding=(1, 2),
    )


def create_error_panel(deployment_info: Text) -> Panel:
    """Create a formatted panel to display deployment error information.

    Args:
        deployment_info (Text): The Rich Text object containing deployment error information

    Returns:
        Panel: A Rich Panel object containing the formatted deployment error information
    """
    return Panel(
        deployment_info,
        title="[bold red]🚨 Deployment Failed[/bold red]",
        border_style="red",
        box=box.HEAVY,
        padding=(1, 2),
    )


def create_tar_archive(mount: Path) -> Path:
    """Create a gzipped tar archive of the playground files.

    Args:
        mount (Path): The path to the directory to be archived

    Returns:
        Path: The path to the created tar archive

    Raises:
        Exception: If archive creation fails
    """
    tar_path = mount.with_suffix(".tar.gz")
    try:
        logger.debug(f"Creating playground archive: {tar_path.name}")
        with tarfile.open(tar_path, "w:gz") as tar:
            tar.add(mount, arcname=mount.name)
        logger.debug(f"Successfully created playground archive: {tar_path.name}")
        return tar_path
    except Exception as e:
        logger.error(f"Failed to create playground archive: {e}")
        raise


def upload_archive(name: str, tar_path: Path) -> None:
    """Upload the tar archive to phi-cloud.

    Args:
        tar_path (Path): The path to the tar archive to be uploaded

    Raises:
        Exception: If the upload process fails
    """
    try:
        logger.debug(f"Uploading playground archive: {tar_path.name}")
        upload_tar_archive(name=name, tar_path=tar_path)
        logger.debug(f"Successfully uploaded playground archive: {tar_path.name}")
    except Exception:
        raise


def cleanup_archive(tar_path: Path) -> None:
    """Delete the temporary tar archive after deployment.

    Args:
        tar_path (Path): The path to the tar archive to be deleted

    Raises:
        Exception: If the deletion process fails
    """
    try:
        logger.debug(f"Deleting playground archive: {tar_path.name}")
        tar_path.unlink()
        logger.debug(f"Successfully deleted playground archive: {tar_path.name}")
    except Exception as e:
        logger.error(f"Failed to delete playground archive: {e}")
        raise


def deploy_playground_app(
    app: str,
    name: str,
    mount: Path,
) -> None:
    """Deploy a playground application to phi-cloud.

    This function:
    1. Creates a tar archive of the mount directory.
    2. Uploades the archive to phi-cloud.
    3. Cleaning up temporary files.
    4. Displaying real-time progress updates.

    Args:
        app (str): The application to deploy as a string identifier.
                It should be the name of the module containing the Playground app from the mount path.
        name (str): The name of the playground app.
        mount (Path): The mount path containing the application files.

    Raises:
        Exception: If any step of the deployment process fails
    """

    phi_cli_settings.gate_alpha_feature()

    from time import sleep
    from rich.live import Live
    from rich.console import Group
    from rich.status import Status
    from phi.utils.timer import Timer

    with Live(refresh_per_second=4) as live_display:
        response_timer = Timer()
        response_timer.start()
        try:
            # Initialize display
            deployment_info = create_deployment_info(app=app, mount=mount, status="Initializing...")
            panels: List[Panel] = [create_info_panel(deployment_info=deployment_info)]

            status = Status(
                "[bold blue]Initializing playground...[/bold blue]",
                spinner="aesthetic",
                speed=2,
            )
            panels.append(status)  # type: ignore
            live_display.update(Group(*panels))

            # Step 1: Create archive
            status.update("[bold blue]Creating playground archive...[/bold blue]")
            tar_path = create_tar_archive(mount=mount)
            panels[0] = create_info_panel(
                create_deployment_info(
                    app=app, mount=mount, elapsed_time=f"{response_timer.elapsed:.1f}s", status="Creating archive..."
                )
            )
            live_display.update(Group(*panels))
            sleep(0.7)

            # Step 2: Upload archive
            status.update("[bold blue]Uploading playground archive...[/bold blue]")
            upload_archive(name=name, tar_path=tar_path)
            panels[0] = create_info_panel(
                create_deployment_info(
                    app=app, mount=mount, elapsed_time=f"{response_timer.elapsed:.1f}s", status="Uploading archive..."
                )
            )
            live_display.update(Group(*panels))
            sleep(0.7)

            # Step 3: Cleanup
            status.update("[bold blue]Deleting playground archive...[/bold blue]")
            cleanup_archive(tar_path)
            panels[0] = create_info_panel(
                create_deployment_info(
                    app=app, mount=mount, elapsed_time=f"{response_timer.elapsed:.1f}s", status="Deleting archive..."
                )
            )
            live_display.update(Group(*panels))
            sleep(0.7)

            # Final display update
            status.stop()
            panels.pop()
            live_display.update(Group(*panels))
        except Exception as e:
            status.update(f"[bold red]Deployment failed: {str(e)}[/bold red]")
            panels[0] = create_error_panel(
                create_deployment_info(
                    app=app, mount=mount, elapsed_time=f"{response_timer.elapsed:.1f}s", error=str(e)
                )
            )
            status.stop()
            panels.pop()
            live_display.update(Group(*panels))
