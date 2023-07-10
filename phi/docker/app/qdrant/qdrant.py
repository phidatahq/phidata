from phi.docker.app.base import DockerApp, WorkspaceVolumeType, AppVolumeType, ContainerContext  # noqa: F401


class Qdrant(DockerApp):
    # -*- App Name
    name: str = "qdrant"

    # -*- Image Configuration
    image_name: str = "qdrant/qdrant"
    image_tag: str = "v1.3.1"

    # -*- App Ports
    # Open a container port if open_container_port=True
    open_container_port: bool = True
    # Port number on the container
    container_port: int = 6333
    # Host port to map to the container port
    host_port: int = 6333

    # -*- Qdrant Volume
    # Create a volume for qdrant storage
    create_volume: bool = True
    # Path to mount the volume inside the container
    volume_container_path: str = "/qdrant/storage"
