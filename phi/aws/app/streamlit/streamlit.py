from typing import Optional, Union, List

from phi.aws.app.base import AwsApp, WorkspaceVolumeType, AppVolumeType, ContainerContext  # noqa: F401


class Streamlit(AwsApp):
    name: str = "streamlit"
    image_name: str = "phidata/streamlit"
    image_tag: str = "1.23"
    command: Optional[Union[str, List[str]]] = "streamlit hello"
    open_container_port: bool = True
    container_port: int = 9095
    host_port: int = 9095
    workspace_volume_container_path: str = "/usr/local/app"

    ecs_task_cpu: str = "1024"
    ecs_task_memory: str = "2048"
    ecs_service_count: int = 1
    assign_public_ip: Optional[bool] = True
