from typing import Optional

from phi.aws.app.base import AwsApp, ContainerContext  # noqa: F401


class Qdrant(AwsApp):
    # -*- App Name
    name: str = "qdrant"

    # -*- Image Configuration
    image_name: str = "qdrant/qdrant"
    image_tag: str = "v1.3.1"

    # -*- App Ports
    # Open a container port if open_port=True
    open_port: bool = True
    # Port number on the container
    container_port: int = 6333

    # -*- ECS Configuration
    ecs_task_cpu: str = "1024"
    ecs_task_memory: str = "2048"
    ecs_service_count: int = 1
    assign_public_ip: Optional[bool] = True
