from typing import Optional, Union, List

from phi.aws.app.base import AwsApp, WorkspaceVolumeType, AppVolumeType, ContainerContext  # noqa: F401


class Streamlit(AwsApp):
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

    # -*- ECS Configuration
    ecs_task_cpu: str = "1024"
    ecs_task_memory: str = "2048"
    ecs_service_count: int = 1
    assign_public_ip: Optional[bool] = True
