from typing import Optional, Union, List

from phi.docker.app.base import DockerApp, ContainerContext  # noqa: F401


class Django(DockerApp):
    # -*- App Name
    name: str = "django"

    # -*- Image Configuration
    image_name: str = "phidata/django"
    image_tag: str = "4.2.2"
    command: Optional[Union[str, List[str]]] = "python manage.py runserver 0.0.0.0:8000"

    # -*- App Ports
    # Open a container port if open_port=True
    open_port: bool = True
    port_number: int = 8000

    # -*- Workspace Configuration
    # Path to the workspace directory inside the container
    workspace_dir_container_path: str = "/app"
    # Mount the workspace directory from host machine to the container
    mount_workspace: bool = False
