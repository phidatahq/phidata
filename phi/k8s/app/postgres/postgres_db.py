from typing import Optional, Dict, List, Any

from phi.app.db_app import DbApp
from phi.k8s.app.base import (
    K8sApp,
    ContainerContext,
    ServiceType,  # noqa: F401
    RestartPolicy,  # noqa: F401
    AppVolumeType,
    ImagePullPolicy,  # noqa: F401
)


class PostgresDb(K8sApp, DbApp):
    # -*- App Name
    name: str = "postgres"

    # -*- Image Configuration
    image_name: str = "postgres"
    image_tag: str = "15.3"

    # -*- App Ports
    # Open a container port if open_port=True
    open_port: bool = True
    port_number: int = 5432
    # Port name for the opened port
    container_port_name: str = "pg"

    # -*- Postgres Configuration
    # Provide POSTGRES_USER as db_user or POSTGRES_USER in secrets_file
    db_user: Optional[str] = None
    # Provide POSTGRES_PASSWORD as db_password or POSTGRES_PASSWORD in secrets_file
    db_password: Optional[str] = None
    # Provide POSTGRES_DB as db_schema or POSTGRES_DB in secrets_file
    db_schema: Optional[str] = None
    db_driver: str = "postgresql+psycopg"
    pgdata: Optional[str] = "/var/lib/postgresql/data/pgdata"
    postgres_initdb_args: Optional[str] = None
    postgres_initdb_waldir: Optional[str] = None
    postgres_host_auth_method: Optional[str] = None
    postgres_password_file: Optional[str] = None
    postgres_user_file: Optional[str] = None
    postgres_db_file: Optional[str] = None
    postgres_initdb_args_file: Optional[str] = None

    # -*- Service Configuration
    create_service: bool = True

    # -*- Postgres Volume
    # Create a volume for postgres storage
    create_volume: bool = True
    volume_type: AppVolumeType = AppVolumeType.EmptyDir
    # Path to mount the volume inside the container
    # should be the parent directory of pgdata defined above
    volume_container_path: str = "/var/lib/postgresql/data"
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

    def get_db_user(self) -> Optional[str]:
        return self.db_user or self.get_secret_from_file("POSTGRES_USER")

    def get_db_password(self) -> Optional[str]:
        return self.db_password or self.get_secret_from_file("POSTGRES_PASSWORD")

    def get_db_schema(self) -> Optional[str]:
        return self.db_schema or self.get_secret_from_file("POSTGRES_DB")

    def get_db_driver(self) -> Optional[str]:
        return self.db_driver

    def get_db_host(self) -> Optional[str]:
        return self.get_service_name()

    def get_db_port(self) -> Optional[int]:
        return self.get_service_port()

    def get_container_env(self, container_context: ContainerContext) -> Dict[str, str]:
        # Container Environment
        container_env: Dict[str, str] = self.container_env or {}

        # Set postgres env vars
        # Check: https://hub.docker.com/_/postgres
        db_user = self.get_db_user()
        if db_user:
            container_env["POSTGRES_USER"] = db_user
        db_password = self.get_db_password()
        if db_password:
            container_env["POSTGRES_PASSWORD"] = db_password
        db_schema = self.get_db_schema()
        if db_schema:
            container_env["POSTGRES_DB"] = db_schema
        if self.pgdata:
            container_env["PGDATA"] = self.pgdata
        if self.postgres_initdb_args:
            container_env["POSTGRES_INITDB_ARGS"] = self.postgres_initdb_args
        if self.postgres_initdb_waldir:
            container_env["POSTGRES_INITDB_WALDIR"] = self.postgres_initdb_waldir
        if self.postgres_host_auth_method:
            container_env["POSTGRES_HOST_AUTH_METHOD"] = self.postgres_host_auth_method
        if self.postgres_password_file:
            container_env["POSTGRES_PASSWORD_FILE"] = self.postgres_password_file
        if self.postgres_user_file:
            container_env["POSTGRES_USER_FILE"] = self.postgres_user_file
        if self.postgres_db_file:
            container_env["POSTGRES_DB_FILE"] = self.postgres_db_file
        if self.postgres_initdb_args_file:
            container_env["POSTGRES_INITDB_ARGS_FILE"] = self.postgres_initdb_args_file

        # Set aws region and profile
        self.set_aws_env_vars(env_dict=container_env)

        # Update the container env using env_file
        env_data_from_file = self.get_env_file_data()
        if env_data_from_file is not None:
            container_env.update({k: str(v) for k, v in env_data_from_file.items() if v is not None})

        # Update the container env with user provided env_vars
        # this overwrites any existing variables with the same key
        if self.env_vars is not None and isinstance(self.env_vars, dict):
            container_env.update({k: str(v) for k, v in self.env_vars.items() if v is not None})

        return container_env
