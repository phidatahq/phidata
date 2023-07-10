from typing import Optional

from phi.aws.app.base import AwsApp, WorkspaceVolumeType, AppVolumeType, ContainerContext  # noqa: F401


class Qdrant(AwsApp):
    name: str = "qdrant"
    image_name: str = "qdrant/qdrant"
    image_tag: str = "v1.3.1"
    open_container_port: bool = True
    container_port: int = 6333
    host_port: int = 6333

    ecs_task_cpu: str = "1024"
    ecs_task_memory: str = "2048"
    ecs_service_count: int = 1
    assign_public_ip: Optional[bool] = False
