from phi.docker.app.base import DockerApp, ContainerContext  # noqa: F401


class Ollama(DockerApp):
    # -*- App Name
    name: str = "ollama"

    # -*- Image Configuration
    image_name: str = "ollama/ollama"
    image_tag: str = "latest"

    # -*- App Ports
    # Open a container port if open_port=True
    open_port: bool = True
    port_number: int = 11434
