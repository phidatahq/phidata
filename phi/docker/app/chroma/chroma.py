from phi.docker.app.base import DockerApp, ContainerContext  # noqa: F401


class Chroma(DockerApp):
    # -*- App Name
    name: str = "chroma"

    # -*- Image Configuration
    image_name: str = "chromadb/chroma"
    image_tag: str = "0.4.22.dev23"

    # -*- App Ports
    # Open a container port if open_port=True
    open_port: bool = True
    port_number: int = 8000

    # -*- Qdrant Volume
    # Create a volume for qdrant storage
    create_volume: bool = True
    # Path to mount the volume inside the container
    volume_container_path: str = "/chroma/storage"
