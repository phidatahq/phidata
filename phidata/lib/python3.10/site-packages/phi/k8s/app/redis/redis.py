from typing import Optional, Dict, Any

from phi.app.db_app import DbApp
from phi.k8s.app.base import (
    K8sApp,
    AppVolumeType,
    ContainerContext,
    ServiceType,  # noqa: F401
    RestartPolicy,  # noqa: F401
    ImagePullPolicy,  # noqa: F401
)


class Redis(K8sApp, DbApp):
    # -*- App Name
    name: str = "redis"

    # -*- Image Configuration
    image_name: str = "redis"
    image_tag: str = "7.2.0"

    # -*- App Ports
    # Open a container port if open_port=True
    open_port: bool = True
    port_number: int = 6379
    # Port name for the opened port
    container_port_name: str = "redis"

    # -*- Service Configuration
    create_service: bool = True

    # -*- Redis Volume
    # Create a volume for redis storage
    create_volume: bool = True
    volume_type: AppVolumeType = AppVolumeType.EmptyDir
    # Path to mount the volume inside the container
    # should be the parent directory of pgdata defined above
    volume_container_path: str = "/data"
    # -*- If volume_type is AwsEbs
    ebs_volume: Optional[Any] = None
    # Add NodeSelectors to Pods, so they are scheduled in the same region and zone as the ebs_volume
    schedule_pods_in_ebs_topology: bool = True

    # -*- Redis Configuration
    # Provide REDIS_PASSWORD as redis_password or REDIS_PASSWORD in secrets_file
    redis_password: Optional[str] = None
    # Provide REDIS_SCHEMA as redis_schema or REDIS_SCHEMA in secrets_file
    redis_schema: Optional[str] = None
    redis_driver: str = "redis"
    logging_level: str = "debug"

    def get_db_password(self) -> Optional[str]:
        return self.redis_password or self.get_secret_from_file("REDIS_PASSWORD")

    def get_db_database(self) -> Optional[str]:
        return self.redis_schema or self.get_secret_from_file("REDIS_SCHEMA")

    def get_db_driver(self) -> Optional[str]:
        return self.redis_driver

    def get_db_host(self) -> Optional[str]:
        return self.get_service_name()

    def get_db_port(self) -> Optional[int]:
        return self.get_service_port()

    def get_db_connection(self) -> Optional[str]:
        password = self.get_db_password()
        password_str = f"{password}@" if password else ""
        schema = self.get_db_database()
        driver = self.get_db_driver()
        host = self.get_db_host()
        port = self.get_db_port()
        return f"{driver}://{password_str}{host}:{port}/{schema}"

    def get_db_connection_local(self) -> Optional[str]:
        password = self.get_db_password()
        password_str = f"{password}@" if password else ""
        schema = self.get_db_database()
        driver = self.get_db_driver()
        host = self.get_db_host_local()
        port = self.get_db_port_local()
        return f"{driver}://{password_str}{host}:{port}/{schema}"

    def get_container_env(self, container_context: ContainerContext) -> Dict[str, str]:
        # Container Environment
        container_env: Dict[str, str] = self.container_env or {}

        # Update the container env using env_file
        env_data_from_file = self.get_env_file_data()
        if env_data_from_file is not None:
            container_env.update({k: str(v) for k, v in env_data_from_file.items() if v is not None})

        # Update the container env with user provided env_vars
        # this overwrites any existing variables with the same key
        if self.env_vars is not None and isinstance(self.env_vars, dict):
            container_env.update({k: str(v) for k, v in self.env_vars.items() if v is not None})

        return container_env
