from pathlib import Path
from typing import Optional, Dict, List, Union, Any

from phidata.app.db import DbApp, DbAppArgs
from phidata.infra.k8s.enums.service_type import ServiceType
from phidata.infra.k8s.enums.image_pull_policy import ImagePullPolicy
from phidata.infra.k8s.enums.restart_policy import RestartPolicy
from phidata.utils.enums import ExtendedEnum
from phidata.utils.log import logger


class PostgresVolumeType(ExtendedEnum):
    HostPath = "HostPath"
    EmptyDir = "EmptyDir"
    AwsEbs = "AwsEbs"
    # For backwards compatibility
    AWS_EBS = "AWS_EBS"


class PostgresDbArgs(DbAppArgs):
    name: str = "postgres"
    version: str = "1"
    enabled: bool = True

    # -*- Image Configuration
    image_name: str = "postgres"
    image_tag: str = "14"
    entrypoint: Optional[Union[str, List]] = None
    command: Optional[Union[str, List]] = None

    # -*- Postgres Configuration
    # Provide POSTGRES_USER as db_user or POSTGRES_USER in secrets_file
    db_user: Optional[str] = None
    # Provide POSTGRES_PASSWORD as db_password or POSTGRES_PASSWORD in secrets_file
    db_password: Optional[str] = None
    # Provide POSTGRES_DB as db_schema or POSTGRES_DB in secrets_file
    db_schema: Optional[str] = None
    db_driver: str = "postgresql"
    pgdata: Optional[str] = "/var/lib/postgresql/data/pgdata"
    postgres_initdb_args: Optional[str] = None
    postgres_initdb_waldir: Optional[str] = None
    postgres_host_auth_method: Optional[str] = None
    postgres_password_file: Optional[str] = None
    postgres_user_file: Optional[str] = None
    postgres_db_file: Optional[str] = None
    postgres_initdb_args_file: Optional[str] = None

    # -*- Container Configuration
    container_name: Optional[str] = None

    # Container ports
    # Open a container port if open_container_port=True
    open_container_port: bool = True
    # Port number on the container
    container_port: int = 5432
    # Port name: Only used by the K8sContainer
    container_port_name: str = "pg"
    # Host port: Only used by the DockerContainer
    container_host_port: int = 5432

    # Container volumes
    create_volume: bool = True
    volume_name: Optional[str] = None
    volume_type: PostgresVolumeType = PostgresVolumeType.EmptyDir
    # Container path to mount the postgres volume
    # should be the parent directory of pgdata
    volume_container_path: str = "/var/lib/postgresql/data"
    # Host path to mount the postgres volume
    # If volume_type = PostgresVolumeType.HOST_PATH
    volume_host_path: Optional[str] = None

    # Use Aws Ebs as Volume
    # EbsVolume if volume_type = PostgresVolumeType.AWS_EBS
    ebs_volume: Optional[Any] = None
    # EbsVolume region is used to determine the ebs_volume_id
    # and add topology region selectors
    ebs_volume_region: Optional[str] = None
    # Provide Ebs Volume-id manually
    ebs_volume_id: Optional[str] = None
    # Add topology az selectors
    ebs_volume_az: Optional[str] = None
    # Add NodeSelectors to Pods, so they are scheduled in the same
    # region and zone as the ebs_volume
    schedule_pods_in_ebs_topology: bool = True

    # K8s Service Configuration
    create_service: bool = True
    # The port exposed by the service.
    service_port: int = 5432


class PostgresDb(DbApp):
    def __init__(
        self,
        name: str = "postgres",
        version: str = "1",
        enabled: bool = True,
        # -*- Image Configuration,
        image_name: str = "postgres",
        image_tag: str = "14",
        entrypoint: Optional[Union[str, List]] = None,
        command: Optional[Union[str, List]] = None,
        # -*- Postgres Configuration,
        # Provide POSTGRES_USER as db_user or POSTGRES_USER in secrets_file,
        db_user: Optional[str] = None,
        # Provide POSTGRES_PASSWORD as db_password or POSTGRES_PASSWORD in secrets_file,
        db_password: Optional[str] = None,
        # Provide POSTGRES_DB as db_schema or POSTGRES_DB in secrets_file,
        db_schema: Optional[str] = None,
        db_driver: str = "postgresql",
        pgdata: Optional[str] = "/var/lib/postgresql/data/pgdata",
        postgres_initdb_args: Optional[str] = None,
        postgres_initdb_waldir: Optional[str] = None,
        postgres_host_auth_method: Optional[str] = None,
        postgres_password_file: Optional[str] = None,
        postgres_user_file: Optional[str] = None,
        postgres_db_file: Optional[str] = None,
        postgres_initdb_args_file: Optional[str] = None,
        # -*- Container Configuration,
        container_name: Optional[str] = None,
        # Add labels to the container,
        container_labels: Optional[Dict[str, Any]] = None,
        # Container env passed to the PhidataApp,
        # Add env variables to container env,
        env: Optional[Dict[str, str]] = None,
        # Read env variables from a file in yaml format,
        env_file: Optional[Path] = None,
        # Container secrets,
        # Add secret variables to container env,
        secrets: Optional[Dict[str, str]] = None,
        # Read secret variables from a file in yaml format,
        secrets_file: Optional[Path] = None,
        # Read secret variables from AWS Secrets,
        aws_secrets: Optional[Any] = None,
        # Container ports,
        # Open a container port if open_container_port=True,
        open_container_port: bool = True,
        # Port number on the container,
        container_port: int = 5432,
        # Port name: Only used by the K8sContainer,
        container_port_name: str = "pg",
        # Host port: Only used by the DockerContainer,
        container_host_port: int = 5432,
        # Container volumes,
        create_volume: bool = True,
        volume_name: Optional[str] = None,
        volume_type: PostgresVolumeType = PostgresVolumeType.EmptyDir,
        # Container path to mount the postgres volume,
        # should be the parent directory of pgdata,
        volume_container_path: str = "/var/lib/postgresql/data",
        # Host path to mount the postgres volume,
        # If volume_type = PostgresVolumeType.HostPath,
        volume_host_path: Optional[str] = None,
        # Use Aws Ebs as Volume,
        # EbsVolume if volume_type = PostgresVolumeType.AwsEbs,
        ebs_volume: Optional[Any] = None,
        # EbsVolume region is used to determine the ebs_volume_id,
        # and add topology region selectors,
        ebs_volume_region: Optional[str] = None,
        # Provide Ebs Volume-id manually,
        ebs_volume_id: Optional[str] = None,
        # Add topology az selectors,
        ebs_volume_az: Optional[str] = None,
        # Add NodeSelectors to Pods, so they are scheduled in the same,
        # region and zone as the ebs_volume,
        schedule_pods_in_ebs_topology: bool = True,
        # -*- Docker configuration,
        # Run container in the background and return a Container object.,
        container_detach: bool = True,
        # Enable auto-removal of the container on daemon side when the container’s process exits.,
        container_auto_remove: bool = True,
        # Remove the container when it has finished running. Default: True.,
        container_remove: bool = True,
        # Username or UID to run commands as inside the container.,
        container_user: Optional[Union[str, int]] = None,
        # Keep STDIN open even if not attached.,
        container_stdin_open: bool = True,
        container_tty: bool = True,
        # Specify a test to perform to check that the container is healthy.,
        container_healthcheck: Optional[Dict[str, Any]] = None,
        # Optional hostname for the container.,
        container_hostname: Optional[str] = None,
        # Platform in the format os[/arch[/variant]].,
        container_platform: Optional[str] = None,
        # Path to the working directory.,
        container_working_dir: Optional[str] = None,
        # Restart the container when it exits. Configured as a dictionary with keys:,
        # Name: One of on-failure, or always.,
        # MaximumRetryCount: Number of times to restart the container on failure.,
        # For example: {"Name": "on-failure", "MaximumRetryCount": 5},
        container_restart_policy_docker: Optional[Dict[str, Any]] = None,
        # Add volumes to DockerContainer,
        # container_volumes is a dictionary which adds the volumes to mount,
        # inside the container. The key is either the host path or a volume name,,
        # and the value is a dictionary with 2 keys:,
        #   bind - The path to mount the volume inside the container,
        #   mode - Either rw to mount the volume read/write, or ro to mount it read-only.,
        # For example:,
        # {,
        #   '/home/user1/': {'bind': '/mnt/vol2', 'mode': 'rw'},,
        #   '/var/www': {'bind': '/mnt/vol1', 'mode': 'ro'},
        # },
        container_volumes_docker: Optional[Dict[str, dict]] = None,
        # Add ports to DockerContainer,
        # The keys of the dictionary are the ports to bind inside the container,,
        # either as an integer or a string in the form port/protocol, where the protocol is either tcp, udp.,
        # The values of the dictionary are the corresponding ports to open on the host, which can be either:,
        #   - The port number, as an integer.,
        #       For example, {'2222/tcp': 3333} will expose port 2222 inside the container as port 3333 on the host.,
        #   - None, to assign a random host port. For example, {'2222/tcp': None}.,
        #   - A tuple of (address, port) if you want to specify the host interface.,
        #       For example, {'1111/tcp': ('127.0.0.1', 1111)}.,
        #   - A list of integers, if you want to bind multiple host ports to a single container port.,
        #       For example, {'1111/tcp': [1234, 4567]}.,
        container_ports_docker: Optional[Dict[str, Any]] = None,
        # -*- K8s configuration
        # K8s Deployment configuration
        replicas: int = 1,
        pod_name: Optional[str] = None,
        deploy_name: Optional[str] = None,
        secret_name: Optional[str] = None,
        configmap_name: Optional[str] = None,
        # Type: ImagePullPolicy,
        image_pull_policy: Optional[ImagePullPolicy] = None,
        pod_annotations: Optional[Dict[str, str]] = None,
        pod_node_selector: Optional[Dict[str, str]] = None,
        # Type: RestartPolicy,
        deploy_restart_policy: Optional[Any] = None,
        deploy_labels: Optional[Dict[str, Any]] = None,
        termination_grace_period_seconds: Optional[int] = None,
        # How to spread the deployment across a topology,
        # Key to spread the pods across,
        topology_spread_key: Optional[str] = None,
        # The degree to which pods may be unevenly distributed,
        topology_spread_max_skew: Optional[int] = None,
        # How to deal with a pod if it doesn't satisfy the spread constraint.,
        topology_spread_when_unsatisfiable: Optional[str] = None,
        # K8s Service Configuration,
        create_service: bool = True,
        service_name: Optional[str] = None,
        # Type: ServiceType,
        service_type: Optional[ServiceType] = None,
        # The port exposed by the service.,
        service_port: int = 5432,
        # The node_port exposed by the service if service_type = ServiceType.NODE_PORT,
        service_node_port: Optional[int] = None,
        # The target_port is the port to access on the pods targeted by the service.,
        # It can be the port number or port name on the pod.,
        service_target_port: Optional[Union[str, int]] = None,
        # Extra ports exposed by the webserver service. Type: List[CreatePort],
        service_ports: Optional[List[Any]] = None,
        # Service labels,
        service_labels: Optional[Dict[str, Any]] = None,
        # Service annotations,
        service_annotations: Optional[Dict[str, str]] = None,
        # If ServiceType == ServiceType.LoadBalancer,
        service_health_check_node_port: Optional[int] = None,
        service_internal_traffic_policy: Optional[str] = None,
        service_load_balancer_class: Optional[str] = None,
        service_load_balancer_ip: Optional[str] = None,
        service_load_balancer_source_ranges: Optional[List[str]] = None,
        service_allocate_load_balancer_node_ports: Optional[bool] = None,
        # K8s RBAC Configuration,
        use_rbac: bool = False,
        # Create a Namespace with name ns_name & default values,
        ns_name: Optional[str] = None,
        # or Provide the full Namespace definition,
        # Type: CreateNamespace,
        namespace: Optional[Any] = None,
        # Create a ServiceAccount with name sa_name & default values,
        sa_name: Optional[str] = None,
        # or Provide the full ServiceAccount definition,
        # Type: CreateServiceAccount,
        service_account: Optional[Any] = None,
        # Create a ClusterRole with name cr_name & default values,
        cr_name: Optional[str] = None,
        # or Provide the full ClusterRole definition,
        # Type: CreateClusterRole,
        cluster_role: Optional[Any] = None,
        # Create a ClusterRoleBinding with name crb_name & default values,
        crb_name: Optional[str] = None,
        # or Provide the full ClusterRoleBinding definition,
        # Type: CreateClusterRoleBinding,
        cluster_role_binding: Optional[Any] = None,
        # Add additional Kubernetes resources to the App,
        # Type: CreateSecret,
        extra_secrets: Optional[List[Any]] = None,
        # Type: CreateConfigMap,
        extra_configmaps: Optional[List[Any]] = None,
        # Type: CreateService,
        extra_services: Optional[List[Any]] = None,
        # Type: CreateDeployment,
        extra_deployments: Optional[List[Any]] = None,
        # Type: CreatePersistentVolume,
        extra_pvs: Optional[List[Any]] = None,
        # Type: CreatePVC,
        extra_pvcs: Optional[List[Any]] = None,
        # Type: CreateContainer,
        extra_containers: Optional[List[Any]] = None,
        # Type: CreateContainer,
        extra_init_containers: Optional[List[Any]] = None,
        # Type: CreatePort,
        extra_ports: Optional[List[Any]] = None,
        # Type: CreateVolume,
        extra_volumes: Optional[List[Any]] = None,
        # Type: CreateStorageClass,
        extra_storage_classes: Optional[List[Any]] = None,
        # Type: CreateCustomObject,
        extra_custom_objects: Optional[List[Any]] = None,
        # Type: CreateCustomResourceDefinition,
        extra_crds: Optional[List[Any]] = None,
        # Other args
        # If True, skip resource creation if active resources with the same name exist.
        use_cache: bool = True,
        **kwargs,
    ):
        super().__init__()
        try:
            self.args: PostgresDbArgs = PostgresDbArgs(
                name=name,
                version=version,
                enabled=enabled,
                image_name=image_name,
                image_tag=image_tag,
                entrypoint=entrypoint,
                command=command,
                db_user=db_user,
                db_password=db_password,
                db_schema=db_schema,
                db_driver=db_driver,
                pgdata=pgdata,
                postgres_initdb_args=postgres_initdb_args,
                postgres_initdb_waldir=postgres_initdb_waldir,
                postgres_host_auth_method=postgres_host_auth_method,
                postgres_password_file=postgres_password_file,
                postgres_user_file=postgres_user_file,
                postgres_db_file=postgres_db_file,
                postgres_initdb_args_file=postgres_initdb_args_file,
                container_name=container_name,
                container_labels=container_labels,
                env=env,
                env_file=env_file,
                secrets=secrets,
                secrets_file=secrets_file,
                aws_secrets=aws_secrets,
                open_container_port=open_container_port,
                container_port=container_port,
                container_port_name=container_port_name,
                container_host_port=container_host_port,
                create_volume=create_volume,
                volume_name=volume_name,
                volume_type=volume_type,
                volume_container_path=volume_container_path,
                volume_host_path=volume_host_path,
                ebs_volume=ebs_volume,
                ebs_volume_region=ebs_volume_region,
                ebs_volume_id=ebs_volume_id,
                ebs_volume_az=ebs_volume_az,
                schedule_pods_in_ebs_topology=schedule_pods_in_ebs_topology,
                container_detach=container_detach,
                container_auto_remove=container_auto_remove,
                container_remove=container_remove,
                container_user=container_user,
                container_stdin_open=container_stdin_open,
                container_tty=container_tty,
                container_healthcheck=container_healthcheck,
                container_hostname=container_hostname,
                container_platform=container_platform,
                container_working_dir=container_working_dir,
                container_restart_policy_docker=container_restart_policy_docker,
                container_volumes_docker=container_volumes_docker,
                container_ports_docker=container_ports_docker,
                replicas=replicas,
                pod_name=pod_name,
                deploy_name=deploy_name,
                secret_name=secret_name,
                configmap_name=configmap_name,
                image_pull_policy=image_pull_policy,
                pod_annotations=pod_annotations,
                pod_node_selector=pod_node_selector,
                deploy_restart_policy=deploy_restart_policy,
                deploy_labels=deploy_labels,
                termination_grace_period_seconds=termination_grace_period_seconds,
                topology_spread_key=topology_spread_key,
                topology_spread_max_skew=topology_spread_max_skew,
                topology_spread_when_unsatisfiable=topology_spread_when_unsatisfiable,
                create_service=create_service,
                service_name=service_name,
                service_type=service_type,
                service_port=service_port,
                service_node_port=service_node_port,
                service_target_port=service_target_port,
                service_ports=service_ports,
                service_labels=service_labels,
                service_annotations=service_annotations,
                service_health_check_node_port=service_health_check_node_port,
                service_internal_traffic_policy=service_internal_traffic_policy,
                service_load_balancer_class=service_load_balancer_class,
                service_load_balancer_ip=service_load_balancer_ip,
                service_load_balancer_source_ranges=service_load_balancer_source_ranges,
                service_allocate_load_balancer_node_ports=service_allocate_load_balancer_node_ports,
                use_rbac=use_rbac,
                ns_name=ns_name,
                namespace=namespace,
                sa_name=sa_name,
                service_account=service_account,
                cr_name=cr_name,
                cluster_role=cluster_role,
                crb_name=crb_name,
                cluster_role_binding=cluster_role_binding,
                extra_secrets=extra_secrets,
                extra_configmaps=extra_configmaps,
                extra_services=extra_services,
                extra_deployments=extra_deployments,
                extra_pvs=extra_pvs,
                extra_pvcs=extra_pvcs,
                extra_containers=extra_containers,
                extra_init_containers=extra_init_containers,
                extra_ports=extra_ports,
                extra_volumes=extra_volumes,
                extra_storage_classes=extra_storage_classes,
                extra_custom_objects=extra_custom_objects,
                extra_crds=extra_crds,
                use_cache=use_cache,
                extra_kwargs=kwargs,
            )
        except Exception:
            logger.error(f"Args for {self.name} are not valid")
            raise

    def get_db_user(self) -> Optional[str]:
        db_user_var: Optional[str] = self.args.db_user if self.args else None
        if db_user_var is None and self.args.secrets_file is not None:
            # read from secrets_file
            # logger.debug(f"Reading POSTGRES_USER from secrets_file")
            secret_data_from_file = self.get_secret_data()
            if secret_data_from_file is not None:
                db_user_var = secret_data_from_file.get("POSTGRES_USER", db_user_var)
        return db_user_var

    def get_db_password(self) -> Optional[str]:
        db_password_var: Optional[str] = self.args.db_password if self.args else None
        if db_password_var is None and self.args.secrets_file is not None:
            # read from secrets_file
            # logger.debug(f"Reading POSTGRES_PASSWORD from secrets_file")
            secret_data_from_file = self.get_secret_data()
            if secret_data_from_file is not None:
                db_password_var = secret_data_from_file.get(
                    "POSTGRES_PASSWORD", db_password_var
                )
        return db_password_var

    def get_db_schema(self) -> Optional[str]:
        db_schema_var: Optional[str] = self.args.db_schema if self.args else None
        if db_schema_var is None and self.args.secrets_file is not None:
            # read from secrets_file
            # logger.debug(f"Reading POSTGRES_DB from secrets_file")
            secret_data_from_file = self.get_secret_data()
            if secret_data_from_file is not None:
                db_schema_var = secret_data_from_file.get("POSTGRES_DB", db_schema_var)
        return db_schema_var

    def get_db_driver(self) -> Optional[str]:
        return self.args.db_driver if self.args else "postgresql"

    def get_db_host_local(self) -> Optional[str]:
        return "localhost"

    def get_db_port_local(self) -> Optional[int]:
        return self.args.container_host_port if self.args else None

    def get_db_host_docker(self) -> Optional[str]:
        return self.get_container_name()

    def get_db_port_docker(self) -> Optional[int]:
        return self.args.container_port if self.args else None

    def get_db_host_k8s(self) -> Optional[str]:
        return self.get_service_name()

    def get_db_port_k8s(self) -> Optional[int]:
        return self.get_service_port()

    def get_db_connection_url_local(self) -> Optional[str]:
        user = self.get_db_user()
        password = self.get_db_password()
        schema = self.get_db_schema()
        driver = self.get_db_driver()
        host = self.get_db_host_local()
        port = self.get_db_port_local()
        return f"{driver}://{user}:{password}@{host}:{port}/{schema}"

    def get_db_connection_url_docker(self) -> Optional[str]:
        user = self.get_db_user()
        password = self.get_db_password()
        schema = self.get_db_schema()
        driver = self.get_db_driver()
        host = self.get_db_host_docker()
        port = self.get_db_port_docker()
        return f"{driver}://{user}:{password}@{host}:{port}/{schema}"

    def get_db_connection_url_k8s(self) -> Optional[str]:
        user = self.get_db_user()
        password = self.get_db_password()
        schema = self.get_db_schema()
        driver = self.get_db_driver()
        host = self.get_db_host_k8s()
        port = self.get_db_port_k8s()
        return f"{driver}://{user}:{password}@{host}:{port}/{schema}"

    ######################################################
    ## Docker Resources
    ######################################################

    def get_docker_rg(self, docker_build_context: Any) -> Optional[Any]:

        app_name = self.args.name
        logger.debug(f"Building {app_name} DockerResourceGroup")

        from phidata.infra.docker.resource.group import (
            DockerNetwork,
            DockerContainer,
            DockerResourceGroup,
            DockerBuildContext,
        )
        from phidata.utils.common import get_default_volume_name

        if docker_build_context is None or not isinstance(
            docker_build_context, DockerBuildContext
        ):
            logger.error("docker_build_context must be a DockerBuildContext")
            return None

        # Container Environment
        container_env: Dict[str, str] = {}

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
        if self.args.pgdata:
            container_env["PGDATA"] = self.args.pgdata
        if self.args.postgres_initdb_args:
            container_env["POSTGRES_INITDB_ARGS"] = self.args.postgres_initdb_args
        if self.args.postgres_initdb_waldir:
            container_env["POSTGRES_INITDB_WALDIR"] = self.args.postgres_initdb_waldir
        if self.args.postgres_host_auth_method:
            container_env[
                "POSTGRES_HOST_AUTH_METHOD"
            ] = self.args.postgres_host_auth_method
        if self.args.postgres_password_file:
            container_env["POSTGRES_PASSWORD_FILE"] = self.args.postgres_password_file
        if self.args.postgres_user_file:
            container_env["POSTGRES_USER_FILE"] = self.args.postgres_user_file
        if self.args.postgres_db_file:
            container_env["POSTGRES_DB_FILE"] = self.args.postgres_db_file
        if self.args.postgres_initdb_args_file:
            container_env[
                "POSTGRES_INITDB_ARGS_FILE"
            ] = self.args.postgres_initdb_args_file

        # Set airflow env vars
        self.set_aws_env_vars(env_dict=container_env)

        # Update the container env using env_file
        env_data_from_file = self.get_env_data()
        if env_data_from_file is not None:
            container_env.update(env_data_from_file)

        # Update the container env using secrets_file
        secret_data_from_file = self.get_secret_data()
        if secret_data_from_file is not None:
            container_env.update(secret_data_from_file)

        # Update the container env with user provided env
        if self.args.env is not None and isinstance(self.args.env, dict):
            container_env.update(self.args.env)

        # Container Volumes
        container_volumes: Dict[str, dict] = self.args.container_volumes_docker or {}
        # Create a volume for the postgres data
        if self.args.create_volume:
            if self.args.volume_type == PostgresVolumeType.EmptyDir:
                volume_name = self.args.volume_name or get_default_volume_name(app_name)
                logger.debug(f"Mounting: {volume_name}")
                logger.debug(f"\tto: {self.args.volume_container_path}")
                container_volumes[volume_name] = {
                    "bind": self.args.volume_container_path,
                    "mode": "rw",
                }
            elif self.args.volume_type == PostgresVolumeType.HostPath:
                if self.args.volume_host_path is not None:
                    volume_host_path_str = str(self.args.volume_host_path)
                    logger.debug(f"Mounting: {volume_host_path_str}")
                    logger.debug(f"\tto: {self.args.volume_container_path}")
                    container_volumes[volume_host_path_str] = {
                        "bind": self.args.volume_container_path,
                        "mode": "rw",
                    }
                else:
                    logger.error("PostgresDb: volume_host_path not provided")
                    return None
            else:
                logger.error(f"{self.args.volume_type.value} not supported")
                return None

        # Container Ports
        container_ports: Dict[str, int] = self.args.container_ports_docker or {}

        # if open_container_port = True
        if self.args.open_container_port:
            container_ports[
                str(self.args.container_port)
            ] = self.args.container_host_port

        # Create the container
        docker_container = DockerContainer(
            name=self.get_container_name(),
            image=self.get_image_str(),
            entrypoint=self.args.entrypoint,
            command=self.args.command,
            detach=self.args.container_detach,
            auto_remove=self.args.container_auto_remove,
            healthcheck=self.args.container_healthcheck,
            hostname=self.args.container_hostname,
            labels=self.args.container_labels,
            environment=container_env,
            network=docker_build_context.network,
            platform=self.args.container_platform,
            ports=container_ports if len(container_ports) > 0 else None,
            remove=self.args.container_remove,
            restart_policy=self.args.container_restart_policy_docker,
            stdin_open=self.args.container_stdin_open,
            tty=self.args.container_tty,
            user=self.args.container_user,
            volumes=container_volumes if len(container_volumes) > 0 else None,
            working_dir=self.args.container_working_dir,
            use_cache=self.args.use_cache,
        )

        docker_rg = DockerResourceGroup(
            name=app_name,
            enabled=self.args.enabled,
            network=DockerNetwork(name=docker_build_context.network),
            containers=[docker_container],
        )
        return docker_rg

    def init_docker_resource_groups(self, docker_build_context: Any) -> None:
        docker_rg = self.get_docker_rg(docker_build_context)
        if docker_rg is not None:
            from collections import OrderedDict

            if self.docker_resource_groups is None:
                self.docker_resource_groups = OrderedDict()
            self.docker_resource_groups[docker_rg.name] = docker_rg

    ######################################################
    ## K8s Resources
    ######################################################

    def get_k8s_rg(self, k8s_build_context: Any) -> Optional[Any]:

        app_name = self.args.name
        logger.debug(f"Building {app_name} K8sResourceGroup")

        from phidata.infra.k8s.create.common.port import CreatePort
        from phidata.infra.k8s.create.core.v1.container import CreateContainer
        from phidata.infra.k8s.create.core.v1.volume import (
            CreateVolume,
            HostPathVolumeSource,
            AwsElasticBlockStoreVolumeSource,
            VolumeType,
        )
        from phidata.infra.k8s.create.group import (
            CreateK8sResourceGroup,
            CreateNamespace,
            CreateServiceAccount,
            CreateClusterRole,
            CreateClusterRoleBinding,
            CreateSecret,
            CreateConfigMap,
            CreateStorageClass,
            CreateService,
            CreateDeployment,
            CreateCustomObject,
            CreateCustomResourceDefinition,
            CreatePersistentVolume,
            CreatePVC,
        )
        from phidata.infra.k8s.resource.group import K8sBuildContext
        from phidata.utils.common import get_default_volume_name

        if k8s_build_context is None or not isinstance(
            k8s_build_context, K8sBuildContext
        ):
            logger.error("k8s_build_context must be a K8sBuildContext")
            return None

        # Init K8s resources for the CreateK8sResourceGroup
        ns: Optional[CreateNamespace] = self.args.namespace
        sa: Optional[CreateServiceAccount] = self.args.service_account
        cr: Optional[CreateClusterRole] = self.args.cluster_role
        crb: Optional[CreateClusterRoleBinding] = self.args.cluster_role_binding
        secrets: List[CreateSecret] = self.args.extra_secrets or []
        config_maps: List[CreateConfigMap] = self.args.extra_configmaps or []
        services: List[CreateService] = self.args.extra_services or []
        deployments: List[CreateDeployment] = self.args.extra_deployments or []
        pvs: List[CreatePersistentVolume] = self.args.extra_pvs or []
        pvcs: List[CreatePVC] = self.args.extra_pvcs or []
        containers: List[CreateContainer] = self.args.extra_containers or []
        init_containers: List[CreateContainer] = self.args.extra_init_containers or []
        ports: List[CreatePort] = self.args.extra_ports or []
        volumes: List[CreateVolume] = self.args.extra_volumes or []
        storage_classes: List[CreateStorageClass] = (
            self.args.extra_storage_classes or []
        )
        custom_objects: List[CreateCustomObject] = self.args.extra_custom_objects or []
        crds: List[CreateCustomResourceDefinition] = self.args.extra_crds or []

        # Common variables used by all resources
        # Use the Namespace provided with the App or
        # use the default Namespace from the k8s_build_context
        ns_name: str = self.args.ns_name or k8s_build_context.namespace
        sa_name: Optional[str] = (
            self.args.sa_name or k8s_build_context.service_account_name
        )
        common_labels: Optional[Dict[str, str]] = k8s_build_context.labels

        # -*- Use K8s RBAC
        # If use_rbac is True, use separate RBAC for this App
        # Create a namespace, service account, cluster role and cluster role binding
        if self.args.use_rbac:
            # Create Namespace for this App
            if ns is None:
                ns = CreateNamespace(
                    ns=ns_name,
                    app_name=app_name,
                    labels=common_labels,
                )
            ns_name = ns.ns

            # Create Service Account for this App
            if sa is None:
                sa = CreateServiceAccount(
                    sa_name=sa_name or self.get_sa_name(),
                    app_name=app_name,
                    namespace=ns_name,
                )
            sa_name = sa.sa_name

            # Create Cluster Role for this App
            from phidata.infra.k8s.create.rbac_authorization_k8s_io.v1.cluster_role import (
                PolicyRule,
            )

            if cr is None:
                cr = CreateClusterRole(
                    cr_name=self.args.cr_name or self.get_cr_name(),
                    rules=[
                        PolicyRule(
                            api_groups=[""],
                            resources=[
                                "pods",
                                "secrets",
                                "configmaps",
                            ],
                            verbs=[
                                "get",
                                "list",
                                "watch",
                                "create",
                                "update",
                                "patch",
                                "delete",
                            ],
                        ),
                    ],
                    app_name=app_name,
                    labels=common_labels,
                )

            # Create ClusterRoleBinding for this App
            if crb is None:
                crb = CreateClusterRoleBinding(
                    crb_name=self.args.crb_name or self.get_crb_name(),
                    cr_name=cr.cr_name,
                    service_account_name=sa.sa_name,
                    app_name=app_name,
                    namespace=ns_name,
                    labels=common_labels,
                )

        # Container Environment
        container_env: Dict[str, str] = {}

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
        if self.args.pgdata:
            container_env["PGDATA"] = self.args.pgdata
        if self.args.postgres_initdb_args:
            container_env["POSTGRES_INITDB_ARGS"] = self.args.postgres_initdb_args
        if self.args.postgres_initdb_waldir:
            container_env["POSTGRES_INITDB_WALDIR"] = self.args.postgres_initdb_waldir
        if self.args.postgres_host_auth_method:
            container_env[
                "POSTGRES_HOST_AUTH_METHOD"
            ] = self.args.postgres_host_auth_method
        if self.args.postgres_password_file:
            container_env["POSTGRES_PASSWORD_FILE"] = self.args.postgres_password_file
        if self.args.postgres_user_file:
            container_env["POSTGRES_USER_FILE"] = self.args.postgres_user_file
        if self.args.postgres_db_file:
            container_env["POSTGRES_DB_FILE"] = self.args.postgres_db_file
        if self.args.postgres_initdb_args_file:
            container_env[
                "POSTGRES_INITDB_ARGS_FILE"
            ] = self.args.postgres_initdb_args_file

        # Set airflow env vars
        self.set_aws_env_vars(env_dict=container_env)

        # Update the container env using env_file
        env_data_from_file = self.get_env_data()
        if env_data_from_file is not None:
            container_env.update(env_data_from_file)

        # Update the container env with user provided env
        if self.args.env is not None and isinstance(self.args.env, dict):
            container_env.update(self.args.env)

        # Create a ConfigMap to set the container env variables which are not Secret
        container_env_cm = CreateConfigMap(
            cm_name=self.args.configmap_name or self.get_configmap_name(),
            app_name=app_name,
            namespace=ns_name,
            data=container_env,
            labels=common_labels,
        )
        config_maps.append(container_env_cm)

        # Create a Secret to set the container env variables which are Secret
        _secret_data = self.get_secret_data()
        if _secret_data is not None:
            container_env_secret = CreateSecret(
                secret_name=self.args.secret_name or self.get_secret_name(),
                app_name=app_name,
                string_data=_secret_data,
                namespace=ns_name,
                labels=common_labels,
            )
            secrets.append(container_env_secret)

        # Container Volumes
        # Add NodeSelectors to Pods in case we create az sensitive volumes
        pod_node_selector: Optional[Dict[str, str]] = self.args.pod_node_selector
        if self.args.create_volume:
            volume_name = self.args.volume_name or get_default_volume_name(app_name)
            if self.args.volume_type == PostgresVolumeType.EmptyDir:
                pg_volume = CreateVolume(
                    volume_name=volume_name,
                    app_name=app_name,
                    mount_path=self.args.volume_container_path,
                    volume_type=VolumeType.EMPTY_DIR,
                )
                volumes.append(pg_volume)
            elif self.args.volume_type == PostgresVolumeType.HostPath:
                if self.args.volume_host_path is not None:
                    volume_host_path_str = str(self.args.volume_host_path)
                    pg_volume = CreateVolume(
                        volume_name=volume_name,
                        app_name=app_name,
                        mount_path=self.args.volume_container_path,
                        volume_type=VolumeType.HOST_PATH,
                        host_path=HostPathVolumeSource(
                            path=volume_host_path_str,
                        ),
                    )
                    volumes.append(pg_volume)
                else:
                    logger.error("PostgresDb: volume_host_path not provided")
                    return None
            elif self.args.volume_type in (
                PostgresVolumeType.AwsEbs,
                PostgresVolumeType.AWS_EBS,
            ):
                if (
                    self.args.ebs_volume_id is not None
                    or self.args.ebs_volume is not None
                ):
                    # To use an EbsVolume as the volume_type we:
                    # 1. Need the volume_id
                    # 2. Need to make sure pods are scheduled in the
                    #       same region/az as the volume

                    # For the volume_id we can either:
                    # 1. Use self.args.ebs_volume_id
                    # 2. Derive it from the self.args.ebs_volume
                    ebs_volume_id = self.args.ebs_volume_id

                    # For the aws_region/az:
                    # 1. Use self.args.ebs_volume_region
                    # 2. Derive it from self.args.ebs_volume
                    # 3. Derive it from the PhidataAppArgs
                    ebs_volume_region = self.args.ebs_volume_region
                    ebs_volume_az = self.args.ebs_volume_az

                    # Derive the aws_region from self.args.ebs_volume if needed
                    if ebs_volume_region is None and self.args.ebs_volume is not None:
                        # Note: this will use the `$AWS_REGION` env var if set
                        _aws_region_from_ebs_volume = (
                            self.args.ebs_volume.get_aws_region()
                        )
                        if _aws_region_from_ebs_volume is not None:
                            ebs_volume_region = _aws_region_from_ebs_volume

                    # Derive the aws_region from the PhidataAppArgs if needed
                    if ebs_volume_region is None:
                        ebs_volume_region = self.aws_region

                    # Derive the availability_zone from self.args.ebs_volume if needed
                    if ebs_volume_az is None and self.args.ebs_volume is not None:
                        ebs_volume_az = self.args.ebs_volume.availability_zone

                    logger.debug(f"ebs_volume_region: {ebs_volume_region}")
                    logger.debug(f"ebs_volume_az: {ebs_volume_az}")

                    # Derive ebs_volume_id from self.args.ebs_volume if needed
                    if ebs_volume_id is None and self.args.ebs_volume is not None:
                        ebs_volume_id = self.args.ebs_volume.get_volume_id(
                            aws_region=ebs_volume_region,
                            aws_profile=self.aws_profile,
                        )

                    logger.debug(f"ebs_volume_id: {ebs_volume_id}")
                    if ebs_volume_id is None:
                        logger.error("Could not find volume_id for EbsVolume")
                        return None

                    pg_volume = CreateVolume(
                        volume_name=volume_name,
                        app_name=app_name,
                        mount_path=self.args.volume_container_path,
                        volume_type=VolumeType.AWS_EBS,
                        aws_ebs=AwsElasticBlockStoreVolumeSource(
                            volume_id=ebs_volume_id,
                        ),
                    )
                    volumes.append(pg_volume)

                    # VERY IMPORTANT: pods should be scheduled in the same region/az as the volume
                    # To do this, we add NodeSelectors to Pods
                    if self.args.schedule_pods_in_ebs_topology:
                        if pod_node_selector is None:
                            pod_node_selector = {}

                        # Add NodeSelectors to Pods, so they are scheduled in the same
                        # region and zone as the ebs_volume
                        # https://kubernetes.io/docs/reference/labels-annotations-taints/#topologykubernetesiozone
                        if ebs_volume_region is not None:
                            pod_node_selector[
                                "topology.kubernetes.io/region"
                            ] = ebs_volume_region

                        if ebs_volume_az is not None:
                            pod_node_selector[
                                "topology.kubernetes.io/zone"
                            ] = ebs_volume_az
                else:
                    logger.error("PostgresDb: ebs_volume not provided")
                    return None
            else:
                logger.error(f"{self.args.volume_type.value} not supported")
                return None

        # Create the ports to open
        if self.args.open_container_port:
            container_port = CreatePort(
                name=self.args.container_port_name,
                container_port=self.args.container_port,
                service_port=self.args.service_port,
                target_port=self.args.service_target_port
                or self.args.container_port_name,
            )
            ports.append(container_port)

            # Validate NODE_PORT before adding it to the container_port
            # If ServiceType == NODE_PORT then validate self.args.service_node_port is available
            if self.args.service_type == ServiceType.NODE_PORT:
                if (
                    self.args.service_node_port is None
                    or self.args.service_node_port < 30000
                    or self.args.service_node_port > 32767
                ):
                    logger.error(f"NodePort: {self.args.service_node_port} invalid")
                    logger.error(f"Skipping this service")
                    return None
                else:
                    container_port.node_port = self.args.service_node_port
            # If ServiceType == LOAD_BALANCER then validate self.args.service_node_port only IF available
            elif self.args.service_type == ServiceType.LOAD_BALANCER:
                if self.args.service_node_port is not None:
                    if (
                        self.args.service_node_port < 30000
                        or self.args.service_node_port > 32767
                    ):
                        logger.error(f"NodePort: {self.args.service_node_port} invalid")
                        logger.error(f"Skipping this service")
                        return None
                    else:
                        container_port.node_port = self.args.service_node_port
            # else validate self.args.service_node_port is NOT available
            elif self.args.service_node_port is not None:
                logger.warning(
                    f"NodePort: {self.args.service_node_port} provided without specifying ServiceType as NODE_PORT or LOAD_BALANCER"
                )
                logger.warning("NodePort value will be ignored")
                self.args.service_node_port = None

        container_labels: Dict[str, Any] = common_labels or {}
        if self.args.container_labels is not None and isinstance(
            self.args.container_labels, dict
        ):
            container_labels.update(self.args.container_labels)

        # Create the Postgres container
        pg_container = CreateContainer(
            container_name=self.get_container_name(),
            app_name=app_name,
            image_name=self.args.image_name,
            image_tag=self.args.image_tag,
            # Equivalent to docker images CMD
            args=[self.args.command]
            if isinstance(self.args.command, str)
            else self.args.command,
            # Equivalent to docker images ENTRYPOINT
            command=[self.args.entrypoint]
            if isinstance(self.args.entrypoint, str)
            else self.args.entrypoint,
            image_pull_policy=self.args.image_pull_policy
            or ImagePullPolicy.IF_NOT_PRESENT,
            envs_from_configmap=[cm.cm_name for cm in config_maps]
            if len(config_maps) > 0
            else None,
            envs_from_secret=[secret.secret_name for secret in secrets]
            if len(secrets) > 0
            else None,
            ports=ports if len(ports) > 0 else None,
            volumes=volumes if len(volumes) > 0 else None,
            labels=container_labels,
        )
        # Add Postgres container to the front of the containers list
        containers.insert(0, pg_container)

        # Set default container for kubectl commands
        # https://kubernetes.io/docs/reference/labels-annotations-taints/#kubectl-kubernetes-io-default-container
        pod_annotations = {
            "kubectl.kubernetes.io/default-container": pg_container.container_name,
        }
        if self.args.pod_annotations is not None and isinstance(
            self.args.pod_annotations, dict
        ):
            pod_annotations.update(self.args.pod_annotations)

        deploy_labels: Dict[str, Any] = common_labels or {}
        if self.args.deploy_labels is not None and isinstance(
            self.args.deploy_labels, dict
        ):
            deploy_labels.update(self.args.deploy_labels)

        # Create the Postgres deployment
        pg_deployment = CreateDeployment(
            deploy_name=self.get_deploy_name(),
            pod_name=self.get_pod_name(),
            app_name=app_name,
            namespace=ns_name,
            service_account_name=sa_name,
            replicas=self.args.replicas,
            containers=containers,
            init_containers=init_containers if len(init_containers) > 0 else None,
            pod_node_selector=pod_node_selector,
            restart_policy=self.args.deploy_restart_policy or RestartPolicy.ALWAYS,
            termination_grace_period_seconds=self.args.termination_grace_period_seconds,
            volumes=volumes if len(volumes) > 0 else None,
            labels=deploy_labels,
            pod_annotations=pod_annotations,
            topology_spread_key=self.args.topology_spread_key,
            topology_spread_max_skew=self.args.topology_spread_max_skew,
            topology_spread_when_unsatisfiable=self.args.topology_spread_when_unsatisfiable,
        )
        deployments.append(pg_deployment)

        # Create the Postgres service
        if self.args.create_service:
            service_labels: Dict[str, Any] = common_labels or {}
            if self.args.service_labels is not None and isinstance(
                self.args.service_labels, dict
            ):
                service_labels.update(self.args.service_labels)

            pg_service = CreateService(
                service_name=self.get_service_name(),
                app_name=app_name,
                namespace=ns_name,
                service_account_name=sa_name,
                service_type=self.args.service_type,
                deployment=pg_deployment,
                ports=ports if len(ports) > 0 else None,
                labels=service_labels,
            )
            services.append(pg_service)

        # Create the K8sResourceGroup
        k8s_resource_group = CreateK8sResourceGroup(
            name=app_name,
            enabled=self.args.enabled,
            ns=ns,
            sa=sa,
            cr=cr,
            crb=crb,
            secrets=secrets if len(secrets) > 0 else None,
            config_maps=config_maps if len(config_maps) > 0 else None,
            storage_classes=storage_classes if len(storage_classes) > 0 else None,
            services=services if len(services) > 0 else None,
            deployments=deployments if len(deployments) > 0 else None,
            custom_objects=custom_objects if len(custom_objects) > 0 else None,
            crds=crds if len(crds) > 0 else None,
            pvs=pvs if len(pvs) > 0 else None,
            pvcs=pvcs if len(pvcs) > 0 else None,
        )

        return k8s_resource_group.create()

    def init_k8s_resource_groups(self, k8s_build_context: Any) -> None:
        k8s_rg = self.get_k8s_rg(k8s_build_context)
        if k8s_rg is not None:
            from collections import OrderedDict

            if self.k8s_resource_groups is None:
                self.k8s_resource_groups = OrderedDict()
            self.k8s_resource_groups[k8s_rg.name] = k8s_rg
