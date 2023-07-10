from typing import Optional, Union, List

from phi.docker.app.base import DockerApp, WorkspaceVolumeType, AppVolumeType, ContainerContext  # noqa: F401


class FastApi(DockerApp):
    name: str = "fastapi"
    image_name: str = "phidata/fastapi"
    image_tag: str = "0.96"
    command: Optional[Union[str, List[str]]] = "uvicorn main:app --reload --host 0.0.0.0 --port 9090"
    open_container_port: bool = True
    container_port: int = 9090
    host_port: int = 9090
    workspace_volume_container_path: str = "/usr/local/app"
