from typing import Optional, Union, List

from phi.docker.app.base import DockerApp, WorkspaceVolumeType, AppVolumeType, ContainerContext  # noqa: F401


class Streamlit(DockerApp):
    name: str = "streamlit"
    image_name: str = "phidata/streamlit"
    image_tag: str = "1.23"
    command: Optional[Union[str, List[str]]] = "streamlit hello"
    open_container_port: bool = True
    container_port: int = 9095
    host_port: int = 9095
    workspace_volume_container_path: str = "/usr/local/app"
