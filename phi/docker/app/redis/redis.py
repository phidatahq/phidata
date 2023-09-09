from typing import Optional

from phi.app.db_app import DbApp
from phi.docker.app.base import DockerApp, ContainerContext  # noqa: F401


class Redis(DockerApp, DbApp):
    # -*- App Name
    name: str = "redis"

    # -*- Image Configuration
    image_name: str = "redis"
    image_tag: str = "7.2.0"

    # -*- App Ports
    # Open a container port if open_port=True
    open_port: bool = True
    port_number: int = 6379

    # -*- Redis Volume
    # Create a volume for redis storage
    create_volume: bool = True
    # Path to mount the volume inside the container
    volume_container_path: str = "/data"

    # -*- Redis Configuration
    # Provide REDIS_USER as redis_user or REDIS_USER in secrets_file
    redis_user: Optional[str] = None
    # Provide REDIS_PASSWORD as redis_password or REDIS_PASSWORD in secrets_file
    redis_password: Optional[str] = None
    # Provide REDIS_SCHEMA as redis_schema or REDIS_SCHEMA in secrets_file
    redis_schema: Optional[str] = None
    redis_driver: str = "redis"
    logging_level: str = "debug"

    def get_db_user(self) -> Optional[str]:
        return self.db_user or self.get_secret_from_file("REDIS_USER")

    def get_db_password(self) -> Optional[str]:
        return self.db_password or self.get_secret_from_file("REDIS_PASSWORD")

    def get_db_schema(self) -> Optional[str]:
        return self.db_schema or self.get_secret_from_file("REDIS_SCHEMA")

    def get_db_driver(self) -> Optional[str]:
        return self.db_driver

    def get_db_host(self) -> Optional[str]:
        return self.get_container_name()

    def get_db_port(self) -> Optional[int]:
        return self.container_port
