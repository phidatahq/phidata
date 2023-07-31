from typing import Optional, Union, List

from phi.k8s.app.base import K8sApp, WorkspaceVolumeType, ContainerContext, AppVolumeType  # noqa: F401


class Streamlit(K8sApp):
    # -*- App Name
    name: str = "streamlit"

    # -*- Image Configuration
    image_name: str = "phidata/streamlit"
    image_tag: str = "1.23"
    command: Optional[Union[str, List[str]]] = "streamlit hello"

    # -*- App Ports
    # Open a container port if open_container_port=True
    open_container_port: bool = True
    # Port number on the container
    container_port: int = 9095
