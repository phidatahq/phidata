from typing import Optional, Union, List

from phi.k8s.app.base import K8sApp, WorkspaceVolumeType, ContainerContext, AppVolumeType  # noqa: F401


class FastApi(K8sApp):
    # -*- App Name
    name: str = "fastapi"

    # -*- Image Configuration
    image_name: str = "phidata/fastapi"
    image_tag: str = "0.96"
    command: Optional[Union[str, List[str]]] = "uvicorn main:app --reload --host 0.0.0.0 --port 9090"

    # -*- App Ports
    # Open a container port if open_container_port=True
    open_container_port: bool = True
    # Port number on the container
    container_port: int = 9090
    # Host port to map to the container port
    host_port: int = 9090

    # -*- Service Configuration
    create_service: bool = True
    # The port exposed by the service
    service_port: int = 9090

    # -*- Workspace Volume
    # Mount the workspace directory from host machine to the container
    mount_workspace: bool = False
    # Path to mount the workspace volume inside the container
    workspace_volume_container_path: str = "/usr/local/app"
