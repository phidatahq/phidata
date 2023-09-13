from phi.docker.app.base import DockerApp, ContainerContext  # noqa: F401


class Qdrant(DockerApp):
    # -*- App Name
    name: str = "qdrant"

    # -*- Image Configuration
    image_name: str = "qdrant/qdrant"
    image_tag: str = "v1.5.1"

    # -*- App Ports
    # Open a container port if open_port=True
    open_port: bool = True
    port_number: int = 6333

    # -*- Qdrant Volume
    # Create a volume for qdrant storage
    create_volume: bool = True
    # Path to mount the volume inside the container
    volume_container_path: str = "/qdrant/storage"
