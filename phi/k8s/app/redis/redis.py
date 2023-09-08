from typing import Optional, Dict, List, Any

from phi.app.db_app import DbApp
from phi.k8s.app.base import (
    K8sApp,
    ServiceType,  # noqa: F401
    RestartPolicy,  # noqa: F401
    AppVolumeType,
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

    # -*- Redis Configuration
    # Provide REDIS_PASSWORD as redis_password or REDIS_PASSWORD in secrets_file
    redis_password: Optional[str] = None
    # Provide REDIS_SCHEMA as redis_schema or REDIS_SCHEMA in secrets_file
    redis_schema: Optional[str] = None
    redis_driver: str = "redis"
    logging_level: str = "debug"

    # -*- Service Configuration
    create_service: bool = True

    # -*- Postgres Volume
    # Create a volume for postgres storage
    create_volume: bool = True
    volume_type: AppVolumeType = AppVolumeType.EmptyDir
    # Path to mount the volume inside the container
    # should be the parent directory of pgdata defined above
    volume_container_path: str = "/data"
    # Host path to mount the postgres volume
    # -*- If volume_type is HostPath
    volume_host_path: Optional[str] = None
    # -*- If volume_type is AwsEbs
    # Provide Ebs Volume-id manually
    ebs_volume_id: Optional[str] = None
    # OR derive the volume_id, region, and az from an EbsVolume resource
    ebs_volume: Optional[Any] = None
    ebs_volume_region: Optional[str] = None
    ebs_volume_az: Optional[str] = None
    # Add NodeSelectors to Pods, so they are scheduled in the same region and zone as the ebs_volume
    schedule_pods_in_ebs_topology: bool = True
    # -*- If volume_type=AppVolumeType.AwsEfs
    # Provide Efs Volume-id manually
    efs_volume_id: Optional[str] = None
    # OR derive the volume_id from an EfsVolume resource
    efs_volume: Optional[Any] = None
    # -*- If volume_type=AppVolumeType.PersistentVolume
    # AccessModes is a list of ways the volume can be mounted.
    # More info: https://kubernetes.io/docs/concepts/storage/persistent-volumes#access-modes
    # Type: phidata.infra.k8s.enums.pv.PVAccessMode
    pv_access_modes: Optional[List[Any]] = None
    pv_requests_storage: Optional[str] = None
    # A list of mount options, e.g. ["ro", "soft"]. Not validated - mount will simply fail if one is invalid.
    # More info: https://kubernetes.io/docs/concepts/storage/persistent-volumes/#mount-options
    pv_mount_options: Optional[List[str]] = None
    # What happens to a persistent volume when released from its claim.
    #   The default policy is Retain.
    # Literal["Delete", "Recycle", "Retain"]
    pv_reclaim_policy: Optional[str] = None
    pv_storage_class: str = ""
    pv_labels: Optional[Dict[str, str]] = None

    def get_db_password(self) -> Optional[str]:
        return self.redis_password or self.get_secret_from_file("REDIS_PASSWORD")

    def get_db_schema(self) -> Optional[str]:
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
        schema = self.get_db_schema()
        driver = self.get_db_driver()
        host = self.get_db_host()
        port = self.get_db_port()
        return f"{driver}://{password_str}{host}:{port}/{schema}"

    def get_db_connection_local(self) -> Optional[str]:
        password = self.get_db_password()
        password_str = f"{password}@" if password else ""
        schema = self.get_db_schema()
        driver = self.get_db_driver()
        host = self.get_db_host_local()
        port = self.get_db_port_local()
        return f"{driver}://{password_str}{host}:{port}/{schema}"
