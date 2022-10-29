from pathlib import Path
from typing import Optional, Dict, Any, List, Union
from typing_extensions import Literal

from phidata.app.db import DbApp
from phidata.app.phidata_app import PhidataApp, PhidataAppArgs, WorkspaceVolumeType
from phidata.infra.k8s.enums.service_type import ServiceType
from phidata.infra.k8s.enums.image_pull_policy import ImagePullPolicy
from phidata.infra.k8s.enums.restart_policy import RestartPolicy
from phidata.utils.enums import ExtendedEnum
from phidata.utils.log import logger


class AirflowLogsVolumeType(ExtendedEnum):
    HostPath = "HostPath"
    EmptyDir = "EmptyDir"
    # PersistentVolume = "PersistentVolume"
    # AwsEbs = "AwsEbs"
    # AwsEfs = "AwsEfs"


class AirflowBaseArgs(PhidataAppArgs):
    name: str = "airflow"
    version: str = "1"
    enabled: bool = True

    # -*- Image Configuration
    image_name: str = "phidata/airflow"
    image_tag: str = "2.4.2"
    entrypoint: Optional[Union[str, List]] = None
    command: Optional[Union[str, List]] = None

    # -*- Airflow Configuration
    # The AIRFLOW_ENV defines the current airflow runtime and can be used by
    # DAGs to separate dev/stg/prd code
    airflow_env: Optional[str] = None
    # Set the AIRFLOW_HOME env variable
    # Defaults to container env variable: /usr/local/airflow
    airflow_home: Optional[str] = None
    # If use_products_as_airflow_dags = True
    # set the AIRFLOW__CORE__DAGS_FOLDER to the products_dir
    use_products_as_airflow_dags: bool = True
    # If use_products_as_airflow_dags = False
    # set the AIRFLOW__CORE__DAGS_FOLDER to the airflow_dags_path
    # airflow_dags_path is the directory in the container containing the airflow dags
    airflow_dags_path: Optional[str] = None
    # Creates an airflow admin with username: admin, pass: admin
    create_airflow_admin_user: bool = False
    # Airflow Executor
    executor: Union[
        str,
        Literal[
            "DebugExecutor",
            "LocalExecutor",
            "SequentialExecutor",
            "CeleryExecutor",
            "CeleryKubernetesExecutor",
            "DaskExecutor",
            "KubernetesExecutor",
        ],
    ] = "SequentialExecutor"

    # Configure airflow db
    # If init_airflow_db = True, initialize the airflow_db
    init_airflow_db: bool = False
    # Upgrade the airflow db
    upgrade_airflow_db: bool = False
    wait_for_db: bool = False
    # delay start by 60 seconds for the db to be initialized
    wait_for_db_init: bool = False
    # Connect to database using a DbApp
    db_app: Optional[DbApp] = None
    # Provide database connection details manually
    # db_user can be provided here or as the
    # DATABASE_USER env var in the secrets_file
    db_user: Optional[str] = None
    # db_password can be provided here or as the
    # DATABASE_PASSWORD env var in the secrets_file
    db_password: Optional[str] = None
    # db_schema can be provided here or as the
    # DATABASE_DB env var in the secrets_file
    db_schema: Optional[str] = None
    # db_host can be provided here or as the
    # DATABASE_HOST env var in the secrets_file
    db_host: Optional[str] = None
    # db_port can be provided here or as the
    # DATABASE_PORT env var in the secrets_file
    db_port: Optional[int] = None
    # db_driver can be provided here or as the
    # DATABASE_DRIVER env var in the secrets_file
    db_driver: str = "postgresql+psycopg2"
    db_result_backend_driver: str = "db+postgresql"
    # Airflow db connections in the format { conn_id: conn_url }
    # converted to env var: AIRFLOW_CONN__conn_id = conn_url
    db_connections: Optional[Dict] = None

    # Configure airflow redis
    wait_for_redis: bool = False
    # Connect to redis using a PhidataApp
    redis_app: Optional[DbApp] = None
    # Provide redis connection details manually
    # redis_password can be provided here or as the
    # REDIS_PASSWORD env var in the secrets_file
    redis_password: Optional[str] = None
    # redis_schema can be provided here or as the
    # REDIS_SCHEMA env var in the secrets_file
    redis_schema: Optional[str] = None
    # redis_host can be provided here or as the
    # REDIS_HOST env var in the secrets_file
    redis_host: Optional[str] = None
    # redis_port can be provided here or as the
    # REDIS_PORT env var in the secrets_file
    redis_port: Optional[int] = None
    # redis_driver can be provided here or as the
    # REDIS_DRIVER env var in the secrets_file
    redis_driver: Optional[str] = None

    # -*- Container Configuration
    container_name: Optional[str] = None
    # Overwrite the PYTHONPATH env var,
    # which is usually set to the workspace_root_container_path
    python_path: Optional[str] = None
    # Add labels to the container
    container_labels: Optional[Dict[str, Any]] = None

    # Container ports
    # Open the webserver port if open_webserver_port=True
    open_webserver_port: bool = False
    # Webserver port number on the container
    webserver_port: int = 8080
    # Port name: Only used by the K8sContainer
    webserver_port_name: str = "webserver"
    # Host port: Only used by the DockerContainer
    webserver_host_port: int = 8080

    # Open the worker_log_port if open_worker_log_port=True
    # When you start an airflow worker, airflow starts a tiny web server subprocess to serve the workers
    # local log files to the airflow main web server, which then builds pages and sends them to users.
    # This defines the port on which the logs are served. It needs to be unused, and open visible from
    # the main web server to connect into the workers.
    open_worker_log_port: bool = False
    worker_log_port: int = 8793
    # Port name: Only used by the K8sContainer
    worker_log_port_name: str = "worker"
    # Host port: Only used by the DockerContainer
    worker_log_host_port: int = 8793

    # Open the flower port if open_flower_port=True
    open_flower_port: bool = False
    # Flower port number on the container
    flower_port: int = 5555
    # Port name: Only used by the K8sContainer
    flower_port_name: str = "flower"
    # Host port: Only used by the DockerContainer
    flower_host_port: int = 5555

    # Container volumes
    # Mount the logs directory on the container
    mount_logs: bool = True
    logs_volume_name: Optional[str] = None
    logs_volume_type: AirflowLogsVolumeType = AirflowLogsVolumeType.EmptyDir
    # Container path to mount the volume
    # - If logs_volume_container_path is provided, use that
    # - If logs_volume_container_path is None and airflow_home is set
    #       use airflow_home/logs
    # - If logs_volume_container_path is None and airflow_home is None
    #       use "/usr/local/airflow/logs"
    logs_volume_container_path: Optional[str] = None
    # Host path to mount the postgres volume
    # If volume_type = PostgresVolumeType.HOST_PATH
    logs_volume_host_path: Optional[Path] = None
    # Logs PersistentVolume configuration
    logs_pv_labels: Optional[Dict[str, str]] = None
    # AccessModes is a list of ways the volume can be mounted.
    # More info: https://kubernetes.io/docs/concepts/storage/persistent-volumes#access-modes
    # Type: phidata.infra.k8s.enums.pv.PVAccessMode
    logs_pv_access_modes: Optional[List[Any]] = None
    logs_pv_requests_storage: Optional[str] = None
    # A list of mount options, e.g. ["ro", "soft"]. Not validated - mount will simply fail if one is invalid.
    # More info: https://kubernetes.io/docs/concepts/storage/persistent-volumes/#mount-options
    logs_pv_mount_options: Optional[List[str]] = None
    # What happens to a persistent volume when released from its claim.
    #   The default policy is Retain.
    logs_pv_reclaim_policy: Optional[Literal["Delete", "Recycle", "Retain"]] = None
    logs_pv_storage_class: str = ""
    # Logs EFS configuration
    # EFS volume_id
    logs_efs_volume_id: Optional[str] = None

    # K8s Service Configuration
    create_webserver_service: bool = False
    # Configure the webserver service
    ws_svc_name: Optional[str] = None
    ws_svc_type: Optional[ServiceType] = None
    # The port exposed by the webserver service.
    ws_svc_port: int = 8080
    # The node_port exposed by the service if ws_svc_type = ServiceType.NODE_PORT
    ws_node_port: Optional[int] = None
    # The ws_target_port is the port to access on the pods targeted by the service.
    # It can be the port number or port name on the pod.
    ws_target_port: Optional[Union[str, int]] = None
    # Extra ports exposed by the webserver service
    ws_svc_ports: Optional[List[Any]] = None
    # Add labels to webserver service
    ws_svc_labels: Optional[Dict[str, Any]] = None
    # Add annotations to webserver service
    ws_svc_annotations: Optional[Dict[str, str]] = None
    # If ServiceType == LoadBalancer
    ws_svc_health_check_node_port: Optional[int] = None
    ws_svc_internal_taffic_policy: Optional[str] = None
    ws_svc_load_balancer_class: Optional[str] = None
    ws_svc_load_balancer_ip: Optional[str] = None
    ws_svc_load_balancer_source_ranges: Optional[List[str]] = None
    ws_svc_allocate_load_balancer_node_ports: Optional[bool] = None

    # Configure the flower service
    create_flower_service: bool = False
    flower_svc_name: Optional[str] = None
    flower_svc_type: Optional[ServiceType] = None
    # The port exposed by the service.
    flower_svc_port: int = 5555
    # The node_port exposed by the service if ws_svc_type = ServiceType.NODE_PORT
    flower_node_port: Optional[int] = None
    # The flower_target_port is the port to access on the pods targeted by the service.
    # It can be the port number or port name on the pod.
    flower_target_port: Optional[Union[str, int]] = None
    # Extra ports exposed by the flower service
    flower_svc_ports: Optional[List[Any]] = None
    # Add labels to flower service
    flower_svc_labels: Optional[Dict[str, Any]] = None
    # Add annotations to flower service
    flower_svc_annotations: Optional[Dict[str, str]] = None
    # If ServiceType == LoadBalancer
    flower_svc_health_check_node_port: Optional[int] = None
    flower_svc_internal_taffic_policy: Optional[str] = None
    flower_svc_load_balancer_class: Optional[str] = None
    flower_svc_load_balancer_ip: Optional[str] = None
    flower_svc_load_balancer_source_ranges: Optional[List[str]] = None
    flower_svc_allocate_load_balancer_node_ports: Optional[bool] = None

    # Other args
    load_examples: bool = False


class AirflowBase(PhidataApp):
    def __init__(
        self,
        name: str = "airflow",
        version: str = "1",
        enabled: bool = True,
        # -*- Image Configuration,
        image_name: str = "phidata/airflow",
        image_tag: str = "2.4.2",
        entrypoint: Optional[Union[str, List]] = None,
        command: Optional[Union[str, List]] = None,
        # Install python dependencies using a requirements.txt file,
        install_requirements: bool = False,
        # Path to the requirements.txt file relative to the workspace_root,
        requirements_file: str = "requirements.txt",
        # -*- Airflow Configuration,
        # The AIRFLOW_ENV defines the current airflow runtime and can be used by,
        # DAGs to separate dev/stg/prd code,
        airflow_env: Optional[str] = None,
        # Set the AIRFLOW_HOME env variable,
        # Defaults to container env variable: /usr/local/airflow,
        airflow_home: Optional[str] = None,
        # If use_products_as_airflow_dags = True,
        # set the AIRFLOW__CORE__DAGS_FOLDER to the products_dir,
        use_products_as_airflow_dags: bool = True,
        # If use_products_as_airflow_dags = False,
        # set the AIRFLOW__CORE__DAGS_FOLDER to the airflow_dags_path,
        # airflow_dags_path is the directory in the container containing the airflow dags,
        airflow_dags_path: Optional[str] = None,
        # Creates an airflow admin with username: admin, pass: admin,
        create_airflow_admin_user: bool = False,
        # Airflow Executor,
        executor: str = "SequentialExecutor",
        # Configure airflow db,
        # If init_airflow_db = True, initialize the airflow_db,
        init_airflow_db: bool = False,
        # Upgrade the airflow db,
        upgrade_airflow_db: bool = False,
        wait_for_db: bool = False,
        # delay start by 60 seconds for the db to be initialized,
        wait_for_db_init: bool = False,
        # Connect to database using a DbApp,
        db_app: Optional[DbApp] = None,
        # Provide database connection details manually,
        # db_user can be provided here or as the,
        # DATABASE_USER env var in the secrets_file,
        db_user: Optional[str] = None,
        # db_password can be provided here or as the,
        # DATABASE_PASSWORD env var in the secrets_file,
        db_password: Optional[str] = None,
        # db_schema can be provided here or as the,
        # DATABASE_DB env var in the secrets_file,
        db_schema: Optional[str] = None,
        # db_host can be provided here or as the,
        # DATABASE_HOST env var in the secrets_file,
        db_host: Optional[str] = None,
        # db_port can be provided here or as the,
        # DATABASE_PORT env var in the secrets_file,
        db_port: Optional[int] = None,
        # db_driver can be provided here or as the,
        # DATABASE_DRIVER env var in the secrets_file,
        db_driver: str = "postgresql+psycopg2",
        db_result_backend_driver: str = "db+postgresql",
        # Airflow db connections in the format { conn_id: conn_url },
        # converted to env var: AIRFLOW_CONN__conn_id = conn_url,
        db_connections: Optional[Dict] = None,
        # Configure airflow redis,
        wait_for_redis: bool = False,
        # Connect to redis using a PhidataApp,
        redis_app: Optional[DbApp] = None,
        # Provide redis connection details manually,
        # redis_password can be provided here or as the,
        # REDIS_PASSWORD env var in the secrets_file,
        redis_password: Optional[str] = None,
        # redis_schema can be provided here or as the,
        # REDIS_SCHEMA env var in the secrets_file,
        redis_schema: Optional[str] = None,
        # redis_host can be provided here or as the,
        # REDIS_HOST env var in the secrets_file,
        redis_host: Optional[str] = None,
        # redis_port can be provided here or as the,
        # REDIS_PORT env var in the secrets_file,
        redis_port: Optional[int] = None,
        # redis_driver can be provided here or as the,
        # REDIS_DRIVER env var in the secrets_file,
        redis_driver: Optional[str] = None,
        # -*- Container Configuration,
        container_name: Optional[str] = None,
        # Overwrite the PYTHONPATH env var,,
        # which is usually set to the workspace_root_container_path,
        python_path: Optional[str] = None,
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
        open_container_port: bool = False,
        # Port number on the container,
        container_port: int = 8000,
        # Port name: Only used by the K8sContainer,
        container_port_name: str = "http",
        # Host port: Only used by the DockerContainer,
        container_host_port: int = 8000,
        # Open the webserver port if open_webserver_port=True,
        open_webserver_port: bool = False,
        # Webserver port number on the container,
        webserver_port: int = 8080,
        # Port name: Only used by the K8sContainer,
        webserver_port_name: str = "webserver",
        # Host port: Only used by the DockerContainer,
        webserver_host_port: int = 8080,
        # Open the worker_log_port if open_worker_log_port=True,
        # When you start an airflow worker, airflow starts a tiny web server subprocess to serve the workers,
        # local log files to the airflow main web server, which then builds pages and sends them to users.,
        # This defines the port on which the logs are served. It needs to be unused, and open visible from,
        # the main web server to connect into the workers.,
        open_worker_log_port: bool = False,
        worker_log_port: int = 8793,
        # Port name: Only used by the K8sContainer,
        worker_log_port_name: str = "worker",
        # Host port: Only used by the DockerContainer,
        worker_log_host_port: int = 8793,
        # Open the flower port if open_flower_port=True,
        open_flower_port: bool = False,
        # Flower port number on the container,
        flower_port: int = 5555,
        # Port name: Only used by the K8sContainer,
        flower_port_name: str = "flower",
        # Host port: Only used by the DockerContainer,
        flower_host_port: int = 5555,
        # Container volumes,
        # Mount the workspace directory on the container,
        mount_workspace: bool = False,
        workspace_volume_name: Optional[str] = None,
        workspace_volume_type: Optional[WorkspaceVolumeType] = None,
        # Path to mount the workspace volume,
        # This is the parent directory for the workspace on the container,
        # i.e. the ws is mounted as a subdir in this dir,
        # eg: if ws name is: idata, workspace_root would be: /mnt/workspaces/idata,
        workspace_volume_container_path: str = "/mnt/workspaces",
        # How to mount the workspace volume,
        # Option 1: Mount the workspace from the host machine,
        # If None, use the workspace_root_path,
        # Note: This is the default on DockerContainers. We assume that DockerContainers,
        # are running locally on the user's machine so the local workspace_root_path,
        # is mounted to the workspace_volume_container_path,
        workspace_volume_host_path: Optional[str] = None,
        # Option 2: Load the workspace from git using a git-sync sidecar container,
        # This the default on K8sContainers.,
        create_git_sync_sidecar: bool = False,
        # Required to create an initial copy of the workspace,
        create_git_sync_init_container: bool = True,
        git_sync_image_name: str = "k8s.gcr.io/git-sync",
        git_sync_image_tag: str = "v3.1.1",
        git_sync_repo: Optional[str] = None,
        git_sync_branch: Optional[str] = None,
        git_sync_wait: int = 1,
        # Mount the logs directory on the container,
        mount_logs: bool = True,
        logs_volume_name: Optional[str] = None,
        logs_volume_type: AirflowLogsVolumeType = AirflowLogsVolumeType.EmptyDir,
        # Container path to mount the volume,
        # - If logs_volume_container_path is provided, use that,
        # - If logs_volume_container_path is None and airflow_home is set,
        #       use airflow_home/logs,
        # - If logs_volume_container_path is None and airflow_home is None,
        #       use "/usr/local/airflow/logs",
        logs_volume_container_path: Optional[str] = None,
        # Logs PersistentVolume configuration,
        logs_pv_labels: Optional[Dict[str, str]] = None,
        # AccessModes is a list of ways the volume can be mounted.,
        # More info: https://kubernetes.io/docs/concepts/storage/persistent-volumes#access-modes,
        # Type: phidata.infra.k8s.enums.pv.PVAccessMode
        logs_pv_access_modes: Optional[List[Any]] = None,
        logs_pv_requests_storage: Optional[str] = None,
        # A list of mount options, e.g. ["ro", "soft"]. Not validated - mount will simply fail if one is invalid.,
        # More info: https://kubernetes.io/docs/concepts/storage/persistent-volumes/#mount-options,
        logs_pv_mount_options: Optional[List[str]] = None,
        # What happens to a persistent volume when released from its claim.,
        #   The default policy is Retain.,
        logs_pv_reclaim_policy: Optional[Literal["Delete", "Recycle", "Retain"]] = None,
        logs_pv_storage_class: str = "",
        # Logs EFS configuration,
        # EFS volume_id,
        logs_efs_volume_id: Optional[str] = None,
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
        # -*- K8s configuration,
        # K8s Deployment configuration,
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
        deploy_restart_policy: Optional[RestartPolicy] = None,
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
        create_service: bool = False,
        service_name: Optional[str] = None,
        # Type: ServiceType,
        service_type: Optional[Any] = None,
        # The port exposed by the service.,
        service_port: int = 8000,
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
        create_webserver_service: bool = False,
        # Configure the webserver service,
        ws_svc_name: Optional[str] = None,
        ws_svc_type: Optional[ServiceType] = None,
        # The port exposed by the webserver service.,
        ws_svc_port: int = 8080,
        # The node_port exposed by the service if ws_svc_type = ServiceType.NODE_PORT,
        ws_node_port: Optional[int] = None,
        # The ws_target_port is the port to access on the pods targeted by the service.,
        # It can be the port number or port name on the pod.,
        ws_target_port: Optional[Union[str, int]] = None,
        # Extra ports exposed by the webserver service,
        ws_svc_ports: Optional[List[Any]] = None,
        # Add labels to webserver service,
        ws_svc_labels: Optional[Dict[str, Any]] = None,
        # Add annotations to webserver service,
        ws_svc_annotations: Optional[Dict[str, str]] = None,
        # If ServiceType == LoadBalancer,
        ws_svc_health_check_node_port: Optional[int] = None,
        ws_svc_internal_taffic_policy: Optional[str] = None,
        ws_svc_load_balancer_class: Optional[str] = None,
        ws_svc_load_balancer_ip: Optional[str] = None,
        ws_svc_load_balancer_source_ranges: Optional[List[str]] = None,
        ws_svc_allocate_load_balancer_node_ports: Optional[bool] = None,
        # Configure the flower service,
        create_flower_service: bool = False,
        flower_svc_name: Optional[str] = None,
        flower_svc_type: Optional[ServiceType] = None,
        # The port exposed by the service.,
        flower_svc_port: int = 5555,
        # The node_port exposed by the service if ws_svc_type = ServiceType.NODE_PORT,
        flower_node_port: Optional[int] = None,
        # The flower_target_port is the port to access on the pods targeted by the service.,
        # It can be the port number or port name on the pod.,
        flower_target_port: Optional[Union[str, int]] = None,
        # Extra ports exposed by the flower service,
        flower_svc_ports: Optional[List[Any]] = None,
        # Add labels to flower service,
        flower_svc_labels: Optional[Dict[str, Any]] = None,
        # Add annotations to flower service,
        flower_svc_annotations: Optional[Dict[str, str]] = None,
        # If ServiceType == LoadBalancer,
        flower_svc_health_check_node_port: Optional[int] = None,
        flower_svc_internal_taffic_policy: Optional[str] = None,
        flower_svc_load_balancer_class: Optional[str] = None,
        flower_svc_load_balancer_ip: Optional[str] = None,
        flower_svc_load_balancer_source_ranges: Optional[List[str]] = None,
        flower_svc_allocate_load_balancer_node_ports: Optional[bool] = None,
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
        # Other args,
        load_examples: bool = False,
        print_env_on_load: bool = True,
        # If True, skip resource creation if active resources with the same name exist.,
        use_cache: bool = True,
        **kwargs,
    ):
        super().__init__()
        try:
            self.args: AirflowBaseArgs = AirflowBaseArgs(
                name=name,
                version=version,
                enabled=enabled,
                image_name=image_name,
                image_tag=image_tag,
                entrypoint=entrypoint,
                command=command,
                install_requirements=install_requirements,
                requirements_file=requirements_file,
                airflow_env=airflow_env,
                airflow_home=airflow_home,
                use_products_as_airflow_dags=use_products_as_airflow_dags,
                airflow_dags_path=airflow_dags_path,
                create_airflow_admin_user=create_airflow_admin_user,
                executor=executor,
                init_airflow_db=init_airflow_db,
                upgrade_airflow_db=upgrade_airflow_db,
                wait_for_db=wait_for_db,
                wait_for_db_init=wait_for_db_init,
                db_app=db_app,
                db_user=db_user,
                db_password=db_password,
                db_schema=db_schema,
                db_host=db_host,
                db_port=db_port,
                db_driver=db_driver,
                db_result_backend_driver=db_result_backend_driver,
                db_connections=db_connections,
                wait_for_redis=wait_for_redis,
                redis_app=redis_app,
                redis_password=redis_password,
                redis_schema=redis_schema,
                redis_host=redis_host,
                redis_port=redis_port,
                redis_driver=redis_driver,
                container_name=container_name,
                python_path=python_path,
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
                open_webserver_port=open_webserver_port,
                webserver_port=webserver_port,
                webserver_port_name=webserver_port_name,
                webserver_host_port=webserver_host_port,
                open_worker_log_port=open_worker_log_port,
                worker_log_port=worker_log_port,
                worker_log_port_name=worker_log_port_name,
                worker_log_host_port=worker_log_host_port,
                open_flower_port=open_flower_port,
                flower_port=flower_port,
                flower_port_name=flower_port_name,
                flower_host_port=flower_host_port,
                mount_workspace=mount_workspace,
                workspace_volume_name=workspace_volume_name,
                workspace_volume_type=workspace_volume_type,
                workspace_volume_container_path=workspace_volume_container_path,
                workspace_volume_host_path=workspace_volume_host_path,
                create_git_sync_sidecar=create_git_sync_sidecar,
                create_git_sync_init_container=create_git_sync_init_container,
                git_sync_image_name=git_sync_image_name,
                git_sync_image_tag=git_sync_image_tag,
                git_sync_repo=git_sync_repo,
                git_sync_branch=git_sync_branch,
                git_sync_wait=git_sync_wait,
                mount_logs=mount_logs,
                logs_volume_name=logs_volume_name,
                logs_volume_type=logs_volume_type,
                logs_volume_container_path=logs_volume_container_path,
                logs_pv_labels=logs_pv_labels,
                logs_pv_access_modes=logs_pv_access_modes,
                logs_pv_requests_storage=logs_pv_requests_storage,
                logs_pv_mount_options=logs_pv_mount_options,
                logs_pv_reclaim_policy=logs_pv_reclaim_policy,
                logs_pv_storage_class=logs_pv_storage_class,
                logs_efs_volume_id=logs_efs_volume_id,
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
                create_webserver_service=create_webserver_service,
                ws_svc_name=ws_svc_name,
                ws_svc_type=ws_svc_type,
                ws_svc_port=ws_svc_port,
                ws_node_port=ws_node_port,
                ws_target_port=ws_target_port,
                ws_svc_ports=ws_svc_ports,
                ws_svc_labels=ws_svc_labels,
                ws_svc_annotations=ws_svc_annotations,
                ws_svc_health_check_node_port=ws_svc_health_check_node_port,
                ws_svc_internal_taffic_policy=ws_svc_internal_taffic_policy,
                ws_svc_load_balancer_class=ws_svc_load_balancer_class,
                ws_svc_load_balancer_ip=ws_svc_load_balancer_ip,
                ws_svc_load_balancer_source_ranges=ws_svc_load_balancer_source_ranges,
                ws_svc_allocate_load_balancer_node_ports=ws_svc_allocate_load_balancer_node_ports,
                create_flower_service=create_flower_service,
                flower_svc_name=flower_svc_name,
                flower_svc_type=flower_svc_type,
                flower_svc_port=flower_svc_port,
                flower_node_port=flower_node_port,
                flower_target_port=flower_target_port,
                flower_svc_ports=flower_svc_ports,
                flower_svc_labels=flower_svc_labels,
                flower_svc_annotations=flower_svc_annotations,
                flower_svc_health_check_node_port=flower_svc_health_check_node_port,
                flower_svc_internal_taffic_policy=flower_svc_internal_taffic_policy,
                flower_svc_load_balancer_class=flower_svc_load_balancer_class,
                flower_svc_load_balancer_ip=flower_svc_load_balancer_ip,
                flower_svc_load_balancer_source_ranges=flower_svc_load_balancer_source_ranges,
                flower_svc_allocate_load_balancer_node_ports=flower_svc_allocate_load_balancer_node_ports,
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
                load_examples=load_examples,
                print_env_on_load=print_env_on_load,
                use_cache=use_cache,
                extra_kwargs=kwargs,
            )
        except Exception as e:
            logger.error(f"Args for {self.name} are not valid")
            raise

    def get_ws_service_name(self) -> str:
        from phidata.utils.common import get_default_service_name

        return self.args.ws_svc_name or get_default_service_name(self.args.name)

    def get_ws_service_port(self) -> int:
        return self.args.ws_svc_port

    def get_flower_service_name(self) -> str:
        from phidata.utils.common import get_default_service_name

        return self.args.flower_svc_name or get_default_service_name(self.args.name)

    def get_flower_service_port(self) -> int:
        return self.args.flower_svc_port

    def get_db_user(self) -> Optional[str]:
        db_user_var: Optional[str] = self.args.db_user if self.args else None
        if db_user_var is None:
            # read from secrets_file
            logger.debug(f"Reading DATABASE_USER from secrets")
            secret_data = self.get_secret_data()
            if secret_data is not None:
                db_user_var = secret_data.get("DATABASE_USER", db_user_var)
        return db_user_var

    def get_db_password(self) -> Optional[str]:
        db_password_var: Optional[str] = self.args.db_password if self.args else None
        if db_password_var is None:
            # read from secrets_file
            logger.debug(f"Reading DATABASE_PASSWORD from secrets")
            secret_data = self.get_secret_data()
            if secret_data is not None:
                db_password_var = secret_data.get("DATABASE_PASSWORD", db_password_var)
        return db_password_var

    def get_db_schema(self) -> Optional[str]:
        db_schema_var: Optional[str] = self.args.db_schema if self.args else None
        if db_schema_var is None:
            # read from secrets_file
            logger.debug(f"Reading DATABASE_DB from secrets")
            secret_data = self.get_secret_data()
            if secret_data is not None:
                db_schema_var = secret_data.get("DATABASE_DB", db_schema_var)
        return db_schema_var

    def get_db_host(self) -> Optional[str]:
        db_host_var: Optional[str] = self.args.db_host if self.args else None
        if db_host_var is None:
            # read from secrets_file
            logger.debug(f"Reading DATABASE_HOST from secrets")
            secret_data = self.get_secret_data()
            if secret_data is not None:
                db_host_var = secret_data.get("DATABASE_HOST", db_host_var)
        return db_host_var

    def get_db_port(self) -> Optional[str]:
        db_port_var: Optional[Union[int, str]] = (
            self.args.db_port if self.args else None
        )
        if db_port_var is None:
            # read from secrets_file
            logger.debug(f"Reading DATABASE_PORT from secrets")
            secret_data = self.get_secret_data()
            if secret_data is not None:
                db_port_var = secret_data.get("DATABASE_PORT", db_port_var)
        return str(db_port_var) if db_port_var is not None else db_port_var

    def get_db_driver(self) -> Optional[str]:
        db_driver_var: Optional[str] = self.args.db_driver if self.args else None
        if db_driver_var is None:
            # read from secrets_file
            logger.debug(f"Reading DATABASE_DRIVER from secrets")
            secret_data = self.get_secret_data()
            if secret_data is not None:
                db_driver_var = secret_data.get("DATABASE_DRIVER", db_driver_var)
        return db_driver_var

    def get_redis_password(self) -> Optional[str]:
        redis_password_var: Optional[str] = (
            self.args.redis_password if self.args else None
        )
        if redis_password_var is None:
            # read from secrets_file
            logger.debug(f"Reading REDIS_PASSWORD from secrets")
            secret_data = self.get_secret_data()
            if secret_data is not None:
                redis_password_var = secret_data.get(
                    "REDIS_PASSWORD", redis_password_var
                )
        return redis_password_var

    def get_redis_schema(self) -> Optional[str]:
        redis_schema_var: Optional[str] = self.args.redis_schema if self.args else None
        if redis_schema_var is None:
            # read from secrets_file
            logger.debug(f"Reading REDIS_SCHEMA from secrets")
            secret_data = self.get_secret_data()
            if secret_data is not None:
                redis_schema_var = secret_data.get("REDIS_SCHEMA", redis_schema_var)
        return redis_schema_var

    def get_redis_host(self) -> Optional[str]:
        redis_host_var: Optional[str] = self.args.redis_host if self.args else None
        if redis_host_var is None:
            # read from secrets_file
            logger.debug(f"Reading REDIS_HOST from secrets")
            secret_data = self.get_secret_data()
            if secret_data is not None:
                redis_host_var = secret_data.get("REDIS_HOST", redis_host_var)
        return redis_host_var

    def get_redis_port(self) -> Optional[str]:
        redis_port_var: Optional[Union[int, str]] = (
            self.args.redis_port if self.args else None
        )
        if redis_port_var is None:
            # read from secrets_file
            logger.debug(f"Reading REDIS_PORT from secrets")
            secret_data = self.get_secret_data()
            if secret_data is not None:
                redis_port_var = secret_data.get("REDIS_PORT", redis_port_var)
        return str(redis_port_var) if redis_port_var is not None else redis_port_var

    def get_redis_driver(self) -> Optional[str]:
        redis_driver_var: Optional[str] = self.args.redis_driver if self.args else None
        if redis_driver_var is None:
            # read from secrets_file
            logger.debug(f"Reading REDIS_DRIVER from secrets")
            secret_data = self.get_secret_data()
            if secret_data is not None:
                redis_driver_var = secret_data.get("REDIS_DRIVER", redis_driver_var)
        return redis_driver_var

    ######################################################
    ## Docker Resources
    ######################################################

    def get_docker_rg(self, docker_build_context: Any) -> Optional[Any]:

        app_name = self.args.name
        logger.debug(f"Building {app_name} DockerResourceGroup")

        from phidata.constants import (
            PYTHONPATH_ENV_VAR,
            PHIDATA_RUNTIME_ENV_VAR,
            SCRIPTS_DIR_ENV_VAR,
            STORAGE_DIR_ENV_VAR,
            META_DIR_ENV_VAR,
            PRODUCTS_DIR_ENV_VAR,
            NOTEBOOKS_DIR_ENV_VAR,
            WORKFLOWS_DIR_ENV_VAR,
            WORKSPACE_ROOT_ENV_VAR,
            WORKSPACES_MOUNT_ENV_VAR,
            WORKSPACE_CONFIG_DIR_ENV_VAR,
            INIT_AIRFLOW_ENV_VAR,
            AIRFLOW_ENV_ENV_VAR,
            AIRFLOW_DAGS_FOLDER_ENV_VAR,
            AIRFLOW_EXECUTOR_ENV_VAR,
            AIRFLOW_DB_CONN_URL_ENV_VAR,
        )
        from phidata.infra.docker.resource.group import (
            DockerNetwork,
            DockerContainer,
            DockerResourceGroup,
            DockerBuildContext,
        )
        from phidata.types.context import ContainerPathContext
        from phidata.utils.common import get_default_volume_name

        if docker_build_context is None or not isinstance(
            docker_build_context, DockerBuildContext
        ):
            logger.error("docker_build_context must be a DockerBuildContext")
            return None

        # Workspace paths
        if self.workspace_root_path is None:
            logger.error("Invalid workspace_root_path")
            return None

        workspace_name = self.workspace_root_path.stem
        container_paths: Optional[ContainerPathContext] = self.get_container_paths()
        if container_paths is None:
            logger.error("Could not build container paths")
            return None
        logger.debug(f"Container Paths: {container_paths.json(indent=2)}")

        # Container pythonpath
        python_path = self.args.python_path or container_paths.workspace_root

        # Container Environment
        container_env: Dict[str, Any] = {
            # Env variables used by data workflows and data assets
            PYTHONPATH_ENV_VAR: python_path,
            PHIDATA_RUNTIME_ENV_VAR: "docker",
            SCRIPTS_DIR_ENV_VAR: container_paths.scripts_dir,
            STORAGE_DIR_ENV_VAR: container_paths.storage_dir,
            META_DIR_ENV_VAR: container_paths.meta_dir,
            PRODUCTS_DIR_ENV_VAR: container_paths.products_dir,
            NOTEBOOKS_DIR_ENV_VAR: container_paths.notebooks_dir,
            WORKFLOWS_DIR_ENV_VAR: container_paths.workflows_dir,
            WORKSPACE_ROOT_ENV_VAR: container_paths.workspace_root,
            WORKSPACES_MOUNT_ENV_VAR: container_paths.workspace_parent,
            WORKSPACE_CONFIG_DIR_ENV_VAR: container_paths.workspace_config_dir,
            "INSTALL_REQUIREMENTS": str(self.args.install_requirements),
            "REQUIREMENTS_FILE_PATH": container_paths.requirements_file,
            "MOUNT_WORKSPACE": str(self.args.mount_workspace),
            "MOUNT_LOGS": str(self.args.mount_logs),
            # Env variables used by Airflow
            # INIT_AIRFLOW env var is required for phidata to generate DAGs
            INIT_AIRFLOW_ENV_VAR: str(True),
            "WAIT_FOR_DB": str(self.args.wait_for_db),
            "WAIT_FOR_DB_INIT": str(self.args.wait_for_db_init),
            "INIT_AIRFLOW_DB": str(self.args.init_airflow_db),
            "UPGRADE_AIRFLOW_DB": str(self.args.upgrade_airflow_db),
            "WAIT_FOR_REDIS": str(self.args.wait_for_redis),
            "AIRFLOW__CORE__LOAD_EXAMPLES": str(self.args.load_examples),
            "CREATE_AIRFLOW_ADMIN_USER": str(self.args.create_airflow_admin_user),
            AIRFLOW_EXECUTOR_ENV_VAR: str(self.args.executor),
            # Print env when the container starts
            "PRINT_ENV_ON_LOAD": str(self.args.print_env_on_load),
        }

        # Set airflow env vars
        self.set_aws_env_vars(env_dict=container_env)

        # Set the AIRFLOW__CORE__DAGS_FOLDER
        if self.args.mount_workspace and self.args.use_products_as_airflow_dags:
            container_env[AIRFLOW_DAGS_FOLDER_ENV_VAR] = container_paths.products_dir
        elif self.args.airflow_dags_path is not None:
            container_env[AIRFLOW_DAGS_FOLDER_ENV_VAR] = self.args.airflow_dags_path

        # Set the AIRFLOW_ENV
        if self.args.airflow_env is not None:
            container_env[AIRFLOW_ENV_ENV_VAR] = self.args.airflow_env

        # Set the AIRFLOW__CONN_ variables
        if self.args.db_connections is not None:
            for conn_id, conn_url in self.args.db_connections.items():
                try:
                    af_conn_id = str("AIRFLOW_CONN_{}".format(conn_id)).upper()
                    container_env[af_conn_id] = conn_url
                except Exception as e:
                    logger.exception(e)
                    continue

        # Airflow db connection
        db_user = self.get_db_user()
        db_password = self.get_db_password()
        db_schema = self.get_db_schema()
        db_host = self.get_db_host()
        db_port = self.get_db_port()
        db_driver = self.get_db_driver()
        if self.args.db_app is not None and isinstance(self.args.db_app, DbApp):
            logger.debug(f"Reading db connection details from: {self.args.db_app.name}")
            if db_user is None:
                db_user = self.args.db_app.get_db_user()
            if db_password is None:
                db_password = self.args.db_app.get_db_password()
            if db_schema is None:
                db_schema = self.args.db_app.get_db_schema()
            if db_host is None:
                db_host = self.args.db_app.get_db_host_docker()
            if db_port is None:
                db_port = str(self.args.db_app.get_db_port_docker())
            if db_driver is None:
                db_driver = self.args.db_app.get_db_driver()
        db_connection_url = (
            f"{db_driver}://{db_user}:{db_password}@{db_host}:{db_port}/{db_schema}"
        )

        # Set the AIRFLOW__DATABASE__SQL_ALCHEMY_CONN
        if "None" not in db_connection_url:
            # logger.debug(f"AIRFLOW__DATABASE__SQL_ALCHEMY_CONN: {db_connection_url}")
            container_env[AIRFLOW_DB_CONN_URL_ENV_VAR] = db_connection_url

        # Set the database connection details in the container env
        if db_host is not None:
            container_env["DATABASE_HOST"] = db_host
        if db_port is not None:
            container_env["DATABASE_PORT"] = str(db_port)

        # Airflow redis connection
        if self.args.executor == "CeleryExecutor":
            # Airflow celery result backend
            celery_result_backend_driver = (
                self.args.db_result_backend_driver or db_driver
            )
            celery_result_backend_url = f"{celery_result_backend_driver}://{db_user}:{db_password}@{db_host}:{db_port}/{db_schema}"
            # Set the AIRFLOW__CELERY__RESULT_BACKEND
            if "None" not in celery_result_backend_url:
                container_env[
                    "AIRFLOW__CELERY__RESULT_BACKEND"
                ] = celery_result_backend_url

            # Airflow celery broker url
            _redis_pass = self.get_redis_password()
            redis_password = f"{_redis_pass}@" if _redis_pass else ""
            redis_schema = self.get_redis_schema()
            redis_host = self.get_redis_host()
            redis_port = self.get_redis_port()
            redis_driver = self.get_redis_driver()
            if self.args.redis_app is not None and isinstance(
                self.args.redis_app, DbApp
            ):
                logger.debug(
                    f"Reading redis connection details from: {self.args.redis_app.name}"
                )
                if redis_password is None:
                    redis_password = self.args.redis_app.get_db_password()
                if redis_schema is None:
                    redis_schema = self.args.redis_app.get_db_schema() or "0"
                if redis_host is None:
                    redis_host = self.args.redis_app.get_db_host_docker()
                if redis_port is None:
                    redis_port = str(self.args.redis_app.get_db_port_docker())
                if redis_driver is None:
                    redis_driver = self.args.redis_app.get_db_driver()

            # Set the AIRFLOW__CELERY__RESULT_BACKEND
            celery_broker_url = f"{redis_driver}://{redis_password}{redis_host}:{redis_port}/{redis_schema}"
            if "None" not in celery_broker_url:
                # logger.debug(f"AIRFLOW__CELERY__BROKER_URL: {celery_broker_url}")
                container_env["AIRFLOW__CELERY__BROKER_URL"] = celery_broker_url

            # Set the redis connection details in the container env
            if redis_host is not None:
                container_env["REDIS_HOST"] = redis_host
            if redis_port is not None:
                container_env["REDIS_PORT"] = str(redis_port)

        # Update the container env using env_file
        env_data_from_file = self.get_env_data()
        if env_data_from_file is not None:
            container_env.update(env_data_from_file)

        # Update the container env using secrets_file or a secrets backend
        secret_data_from_file = self.get_secret_data()
        if secret_data_from_file is not None:
            container_env.update(secret_data_from_file)

        # Update the container env with user provided env, this overwrites any existing variables
        if self.args.env is not None and isinstance(self.args.env, dict):
            container_env.update(self.args.env)

        # Container Volumes
        # container_volumes is a dictionary which configures the volumes to mount
        # inside the container. The key is either the host path or a volume name,
        # and the value is a dictionary with 2 keys:
        #   bind - The path to mount the volume inside the container
        #   mode - Either rw to mount the volume read/write, or ro to mount it read-only.
        # For example:
        # {
        #   '/home/user1/': {'bind': '/mnt/vol2', 'mode': 'rw'},
        #   '/var/www': {'bind': '/mnt/vol1', 'mode': 'ro'}
        # }
        container_volumes = self.args.container_volumes_docker or {}
        # Create a volume for the workspace dir
        if self.args.mount_workspace:
            workspace_volume_container_path_str = container_paths.workspace_root

            if (
                self.args.workspace_volume_type is None
                or self.args.workspace_volume_type == WorkspaceVolumeType.HostPath
            ):
                workspace_volume_host_path = (
                    self.args.workspace_volume_host_path
                    or str(self.workspace_root_path)
                )
                logger.debug(f"Mounting: {workspace_volume_host_path}")
                logger.debug(f"\tto: {workspace_volume_container_path_str}")
                container_volumes[workspace_volume_host_path] = {
                    "bind": workspace_volume_container_path_str,
                    "mode": "rw",
                }
            elif self.args.workspace_volume_type == WorkspaceVolumeType.EmptyDir:
                workspace_volume_name = self.args.workspace_volume_name
                if workspace_volume_name is None:
                    if workspace_name is not None:
                        workspace_volume_name = get_default_volume_name(
                            f"airflow-{workspace_name}-ws"
                        )
                    else:
                        workspace_volume_name = get_default_volume_name("airflow-ws")
                logger.debug(f"Mounting: {workspace_volume_name}")
                logger.debug(f"\tto: {workspace_volume_container_path_str}")
                container_volumes[workspace_volume_name] = {
                    "bind": workspace_volume_container_path_str,
                    "mode": "rw",
                }
            else:
                logger.error(f"{self.args.workspace_volume_type.value} not supported")
                return None

        # Create a volume for logs
        if self.args.mount_logs:
            logs_volume_container_path_str = self.args.logs_volume_container_path
            if logs_volume_container_path_str is None:
                if self.args.airflow_home is not None:
                    logs_volume_container_path_str = f"{self.args.airflow_home}/logs"
                else:
                    logs_volume_container_path_str = "/usr/local/airflow/logs"

            if self.args.logs_volume_type == AirflowLogsVolumeType.EmptyDir:
                logs_volume_name = self.args.logs_volume_name
                if logs_volume_name is None:
                    if workspace_name is not None:
                        logs_volume_name = get_default_volume_name(
                            f"airflow-{workspace_name}-logs"
                        )
                    else:
                        logs_volume_name = get_default_volume_name("airflow-logs")
                logger.debug(f"Mounting: {logs_volume_name}")
                logger.debug(f"\tto: {logs_volume_container_path_str}")
                container_volumes[logs_volume_name] = {
                    "bind": logs_volume_container_path_str,
                    "mode": "rw",
                }
            elif self.args.logs_volume_type == AirflowLogsVolumeType.HostPath:
                if self.args.logs_volume_host_path is not None:
                    logs_volume_host_path_str = str(self.args.logs_volume_host_path)
                    logger.debug(f"Mounting: {logs_volume_host_path_str}")
                    logger.debug(f"\tto: {logs_volume_container_path_str}")
                    container_volumes[logs_volume_host_path_str] = {
                        "bind": logs_volume_container_path_str,
                        "mode": "rw",
                    }
                else:
                    logger.error("Airflow: logs_volume_host_path is None")
                    return None
            else:
                logger.error(f"{self.args.logs_volume_type.value} not supported")
                return None

        # Container Ports
        # container_ports is a dictionary which configures the ports to bind
        # inside the container. The key is the port to bind inside the container
        #   either as an integer or a string in the form port/protocol
        # and the value is the corresponding port to open on the host.
        # For example:
        #   {'2222/tcp': 3333} will expose port 2222 inside the container as port 3333 on the host.
        container_ports: Dict[str, int] = self.args.container_ports_docker or {}

        # if open_container_port = True
        if self.args.open_container_port:
            container_ports[
                str(self.args.container_port)
            ] = self.args.container_host_port

        # if open_webserver_port = True
        # 1. Set the webserver_port in the container env
        # 2. Open the webserver_port
        if self.args.open_webserver_port:
            # Set the webserver port in the container_env
            container_env["AIRFLOW__WEBSERVER__WEB_SERVER_PORT"] = str(
                self.args.webserver_port
            )
            # Open the port
            container_ports[
                str(self.args.webserver_port)
            ] = self.args.webserver_host_port

        # if open_worker_log_port = True
        # 1. Set the worker_log_port in the container env
        # 2. Open the worker_log_port
        if self.args.open_worker_log_port:
            # Set the worker_log_port in the container_env
            container_env["AIRFLOW__LOGGING__WORKER_LOG_SERVER_PORT"] = str(
                self.args.worker_log_port
            )
            # Open the port
            container_ports[
                str(self.args.worker_log_port)
            ] = self.args.worker_log_host_port

        # if open_flower_port = True
        # 1. Set the flower_port in the container env
        # 2. Open the flower_port
        if self.args.open_flower_port:
            # Set the flower_port in the container_env
            container_env["AIRFLOW__CELERY__FLOWER_PORT"] = str(self.args.flower_port)
            # Open the port
            container_ports[str(self.args.flower_port)] = self.args.flower_host_port

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

        from phidata.constants import (
            PYTHONPATH_ENV_VAR,
            PHIDATA_RUNTIME_ENV_VAR,
            SCRIPTS_DIR_ENV_VAR,
            STORAGE_DIR_ENV_VAR,
            META_DIR_ENV_VAR,
            PRODUCTS_DIR_ENV_VAR,
            NOTEBOOKS_DIR_ENV_VAR,
            WORKFLOWS_DIR_ENV_VAR,
            WORKSPACE_ROOT_ENV_VAR,
            WORKSPACES_MOUNT_ENV_VAR,
            WORKSPACE_CONFIG_DIR_ENV_VAR,
            INIT_AIRFLOW_ENV_VAR,
            AIRFLOW_ENV_ENV_VAR,
            AIRFLOW_DAGS_FOLDER_ENV_VAR,
            AIRFLOW_EXECUTOR_ENV_VAR,
            AIRFLOW_DB_CONN_URL_ENV_VAR,
        )
        from phidata.infra.k8s.create.common.port import CreatePort
        from phidata.infra.k8s.create.core.v1.container import CreateContainer
        from phidata.infra.k8s.create.core.v1.volume import (
            CreateVolume,
            HostPathVolumeSource,
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
        from phidata.types.context import ContainerPathContext
        from phidata.utils.common import get_default_volume_name

        if k8s_build_context is None or not isinstance(
            k8s_build_context, K8sBuildContext
        ):
            logger.error("k8s_build_context must be a K8sBuildContext")
            return None

        # Workspace paths
        if self.workspace_root_path is None:
            logger.error("Invalid workspace_root_path")
            return None

        workspace_name = self.workspace_root_path.stem
        container_paths: Optional[ContainerPathContext] = self.get_container_paths()
        if container_paths is None:
            logger.error("Could not build container paths")
            return None
        logger.debug(f"Container Paths: {container_paths.json(indent=2)}")

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
        # WebUI/Scheduler pods should run with serviceAccount which have RBAC
        # permissions on the k8s cluster to get logs
        # https://github.com/apache/airflow/issues/11696#issuecomment-715886117
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
                        PolicyRule(
                            api_groups=[""],
                            resources=[
                                "pods/logs",
                            ],
                            verbs=[
                                "get",
                                "list",
                            ],
                        ),
                        # PolicyRule(
                        #     api_groups=[""],
                        #     resources=[
                        #         "pods/exec",
                        #     ],
                        #     verbs=[
                        #         "get",
                        #         "create",
                        #     ],
                        # ),
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

        # Container pythonpath
        python_path = self.args.python_path or container_paths.workspace_root

        # Container Environment
        container_env: Dict[str, Any] = {
            # Env variables used by data workflows and data assets
            PYTHONPATH_ENV_VAR: python_path,
            PHIDATA_RUNTIME_ENV_VAR: "kubernetes",
            SCRIPTS_DIR_ENV_VAR: container_paths.scripts_dir,
            STORAGE_DIR_ENV_VAR: container_paths.storage_dir,
            META_DIR_ENV_VAR: container_paths.meta_dir,
            PRODUCTS_DIR_ENV_VAR: container_paths.products_dir,
            NOTEBOOKS_DIR_ENV_VAR: container_paths.notebooks_dir,
            WORKFLOWS_DIR_ENV_VAR: container_paths.workflows_dir,
            WORKSPACE_ROOT_ENV_VAR: container_paths.workspace_root,
            WORKSPACES_MOUNT_ENV_VAR: container_paths.workspace_parent,
            WORKSPACE_CONFIG_DIR_ENV_VAR: container_paths.workspace_config_dir,
            "INSTALL_REQUIREMENTS": str(self.args.install_requirements),
            "REQUIREMENTS_FILE_PATH": container_paths.requirements_file,
            "MOUNT_WORKSPACE": str(self.args.mount_workspace),
            "MOUNT_LOGS": str(self.args.mount_logs),
            # Env variables used by Airflow
            # INIT_AIRFLOW env var is required for phidata to generate DAGs
            INIT_AIRFLOW_ENV_VAR: str(True),
            "WAIT_FOR_DB": str(self.args.wait_for_db),
            "WAIT_FOR_DB_INIT": str(self.args.wait_for_db_init),
            "INIT_AIRFLOW_DB": str(self.args.init_airflow_db),
            "UPGRADE_AIRFLOW_DB": str(self.args.upgrade_airflow_db),
            "WAIT_FOR_REDIS": str(self.args.wait_for_redis),
            "AIRFLOW__CORE__LOAD_EXAMPLES": str(self.args.load_examples),
            "CREATE_AIRFLOW_ADMIN_USER": str(self.args.create_airflow_admin_user),
            AIRFLOW_EXECUTOR_ENV_VAR: str(self.args.executor),
            # Print env when the container starts
            "PRINT_ENV_ON_LOAD": str(self.args.print_env_on_load),
        }

        # Set airflow env vars
        self.set_aws_env_vars(env_dict=container_env)

        # Set the AIRFLOW__CORE__DAGS_FOLDER
        if self.args.mount_workspace and self.args.use_products_as_airflow_dags:
            container_env[AIRFLOW_DAGS_FOLDER_ENV_VAR] = container_paths.products_dir
        elif self.args.airflow_dags_path is not None:
            container_env[AIRFLOW_DAGS_FOLDER_ENV_VAR] = self.args.airflow_dags_path

        # Set the AIRFLOW_ENV
        if self.args.airflow_env is not None:
            container_env[AIRFLOW_ENV_ENV_VAR] = self.args.airflow_env

        # Set the AIRFLOW__CONN_ variables
        if self.args.db_connections is not None:
            for conn_id, conn_url in self.args.db_connections.items():
                try:
                    af_conn_id = str("AIRFLOW_CONN_{}".format(conn_id)).upper()
                    container_env[af_conn_id] = conn_url
                except Exception as e:
                    logger.exception(e)
                    continue

        # Airflow db connection
        db_user = self.get_db_user()
        db_password = self.get_db_password()
        db_schema = self.get_db_schema()
        db_host = self.get_db_host()
        db_port = self.get_db_port()
        db_driver = self.get_db_driver()
        if self.args.db_app is not None and isinstance(self.args.db_app, DbApp):
            logger.debug(f"Reading db connection details from: {self.args.db_app.name}")
            if db_user is None:
                db_user = self.args.db_app.get_db_user()
            if db_password is None:
                db_password = self.args.db_app.get_db_password()
            if db_schema is None:
                db_schema = self.args.db_app.get_db_schema()
            if db_host is None:
                db_host = self.args.db_app.get_db_host_k8s()
            if db_port is None:
                db_port = str(self.args.db_app.get_db_port_k8s())
            if db_driver is None:
                db_driver = self.args.db_app.get_db_driver()
        db_connection_url = (
            f"{db_driver}://{db_user}:{db_password}@{db_host}:{db_port}/{db_schema}"
        )

        # Set the AIRFLOW__DATABASE__SQL_ALCHEMY_CONN
        if "None" not in db_connection_url:
            # logger.debug(f"AIRFLOW__DATABASE__SQL_ALCHEMY_CONN: {db_connection_url}")
            container_env[AIRFLOW_DB_CONN_URL_ENV_VAR] = db_connection_url

        # Set the database connection details in the container env
        if db_host is not None:
            container_env["DATABASE_HOST"] = db_host
        if db_port is not None:
            container_env["DATABASE_PORT"] = str(db_port)

        # Airflow redis connection
        if self.args.executor == "CeleryExecutor":
            # Airflow celery result backend
            celery_result_backend_driver = (
                self.args.db_result_backend_driver or db_driver
            )
            celery_result_backend_url = f"{celery_result_backend_driver}://{db_user}:{db_password}@{db_host}:{db_port}/{db_schema}"
            # Set the AIRFLOW__CELERY__RESULT_BACKEND
            if "None" not in celery_result_backend_url:
                container_env[
                    "AIRFLOW__CELERY__RESULT_BACKEND"
                ] = celery_result_backend_url

            # Airflow celery broker url
            _redis_pass = self.get_redis_password()
            redis_password = f"{_redis_pass}@" if _redis_pass else ""
            redis_schema = self.get_redis_schema()
            redis_host = self.get_redis_host()
            redis_port = self.get_redis_port()
            redis_driver = self.get_redis_driver()
            if self.args.redis_app is not None and isinstance(
                self.args.redis_app, DbApp
            ):
                logger.debug(
                    f"Reading redis connection details from: {self.args.redis_app.name}"
                )
                if redis_password is None:
                    redis_password = self.args.redis_app.get_db_password()
                if redis_schema is None:
                    redis_schema = self.args.redis_app.get_db_schema() or "0"
                if redis_host is None:
                    redis_host = self.args.redis_app.get_db_host_k8s()
                if redis_port is None:
                    redis_port = str(self.args.redis_app.get_db_port_k8s())
                if redis_driver is None:
                    redis_driver = self.args.redis_app.get_db_driver()

            # Set the AIRFLOW__CELERY__RESULT_BACKEND
            celery_broker_url = f"{redis_driver}://{redis_password}{redis_host}:{redis_port}/{redis_schema}"
            if "None" not in celery_broker_url:
                # logger.debug(f"AIRFLOW__CELERY__BROKER_URL: {celery_broker_url}")
                container_env["AIRFLOW__CELERY__BROKER_URL"] = celery_broker_url

            # Set the redis connection details in the container env
            if redis_host is not None:
                container_env["REDIS_HOST"] = redis_host
            if redis_port is not None:
                container_env["REDIS_PORT"] = str(redis_port)

        # Update the container env using env_file
        env_data_from_file = self.get_env_data()
        if env_data_from_file is not None:
            container_env.update(env_data_from_file)

        # Update the container env with user provided env, this overwrites any existing variables
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
        if self.args.mount_workspace:
            workspace_volume_name = self.args.workspace_volume_name
            if workspace_volume_name is None:
                if workspace_name is not None:
                    workspace_volume_name = get_default_volume_name(
                        f"airflow-{workspace_name}-ws"
                    )
                else:
                    workspace_volume_name = get_default_volume_name("airflow-ws")

            # Mount workspace volume as EmptyDir then use git-sync to sync the workspace from github
            if (
                self.args.workspace_volume_type is None
                or self.args.workspace_volume_type == WorkspaceVolumeType.EmptyDir
            ):
                workspace_parent_container_path_str = container_paths.workspace_parent
                logger.debug(f"Creating EmptyDir")
                logger.debug(f"\tat: {workspace_parent_container_path_str}")
                workspace_volume = CreateVolume(
                    volume_name=workspace_volume_name,
                    app_name=app_name,
                    mount_path=workspace_parent_container_path_str,
                    volume_type=VolumeType.EMPTY_DIR,
                )
                volumes.append(workspace_volume)

                if self.args.create_git_sync_sidecar:
                    if self.args.git_sync_repo is not None:
                        git_sync_env = {
                            "GIT_SYNC_REPO": self.args.git_sync_repo,
                            "GIT_SYNC_ROOT": workspace_parent_container_path_str,
                            "GIT_SYNC_DEST": workspace_name,
                        }
                        if self.args.git_sync_branch is not None:
                            git_sync_env["GIT_SYNC_BRANCH"] = self.args.git_sync_branch
                        if self.args.git_sync_wait is not None:
                            git_sync_env["GIT_SYNC_WAIT"] = str(self.args.git_sync_wait)
                        git_sync_container = CreateContainer(
                            container_name="git-sync",
                            app_name=app_name,
                            image_name=self.args.git_sync_image_name,
                            image_tag=self.args.git_sync_image_name,
                            env=git_sync_env,
                            envs_from_configmap=[cm.cm_name for cm in config_maps]
                            if len(config_maps) > 0
                            else None,
                            envs_from_secret=[secret.secret_name for secret in secrets]
                            if len(secrets) > 0
                            else None,
                            volumes=[workspace_volume],
                        )
                        containers.append(git_sync_container)

                        if self.args.create_git_sync_init_container:
                            git_sync_init_env: Dict[str, Any] = {
                                "GIT_SYNC_ONE_TIME": True
                            }
                            git_sync_init_env.update(git_sync_env)
                            _git_sync_init_container = CreateContainer(
                                container_name="git-sync-init",
                                app_name=git_sync_container.app_name,
                                image_name=git_sync_container.image_name,
                                image_tag=git_sync_container.image_tag,
                                env=git_sync_init_env,
                                envs_from_configmap=git_sync_container.envs_from_configmap,
                                envs_from_secret=git_sync_container.envs_from_secret,
                                volumes=git_sync_container.volumes,
                            )
                            init_containers.append(_git_sync_init_container)
                    else:
                        logger.error("GIT_SYNC_REPO invalid")

            elif self.args.workspace_volume_type == WorkspaceVolumeType.HostPath:
                workspace_root_path_str = str(self.workspace_root_path)
                workspace_root_container_path_str = container_paths.workspace_root
                logger.debug(f"Mounting: {workspace_root_path_str}")
                logger.debug(f"\tto: {workspace_root_container_path_str}")
                workspace_volume = CreateVolume(
                    volume_name=workspace_volume_name,
                    app_name=app_name,
                    mount_path=workspace_root_container_path_str,
                    volume_type=VolumeType.HOST_PATH,
                    host_path=HostPathVolumeSource(
                        path=workspace_root_path_str,
                    ),
                )
                volumes.append(workspace_volume)

        # if self.args.mount_logs:
        #     logs_volume_name = self.args.logs_volume_name or get_default_volume_name(
        #         f"{app_name}-logs"
        #     )
        #     if self.args.logs_volume_type == AirflowLogsVolumeType.PERSISTENT_VOLUME:
        #         default_mount_options = [
        #             "rsize=1048576",
        #             "wsize=1048576",
        #             "hard",
        #             "timeo=600",
        #             "retrans=2",
        #             "noresvport",
        #         ]
        #
        #         logs_pv_labels: Dict[str, Any] = common_labels or {}
        #         if self.args.logs_pv_labels is not None and isinstance(
        #             self.args.logs_pv_labels, dict
        #         ):
        #             logs_pv_labels.update(self.args.logs_pv_labels)
        #
        #         logs_pvc = CreatePVC(
        #             pvc_name=f"{logs_volume_name}-pvc",
        #             app_name=app_name,
        #             namespace=ns_name,
        #             request_storage=(self.args.logs_pv_requests_storage or "1Mi"),
        #             storage_class_name="",
        #             access_modes=(
        #                 self.args.logs_pv_access_modes or [PVAccessMode.READ_WRITE_MANY]
        #             ),
        #             labels=logs_pv_labels,
        #         )
        #         pvcs.append(logs_pvc)
        #
        #         logs_pv = CreatePersistentVolume(
        #             pv_name=f"{logs_volume_name}-pv",
        #             app_name=app_name,
        #             labels=logs_pv_labels,
        #             access_modes=(
        #                 self.args.logs_pv_access_modes or [PVAccessMode.READ_WRITE_MANY]
        #             ),
        #             capacity={"storage": (self.args.logs_pv_requests_storage or "1Mi")},
        #             mount_options=(
        #                 self.args.logs_pv_mount_options or default_mount_options
        #             ),
        #             persistent_volume_reclaim_policy=(
        #                 self.args.logs_pv_reclaim_policy or "Retain"
        #             ),
        #             storage_class_name=self.args.logs_pv_storage_class,
        #             volume_type=VolumeType.NFS,
        #             # nfs=NFSVolumeSource(
        #             #     path=self.args.logs_volume_container_path,
        #             # ),
        #             # claim_ref=ClaimRef(
        #             #     name=logs_pvc.pvc_name,
        #             #     namespace=logs_pvc.namespace,
        #             # ),
        #         )
        #         pvs.append(logs_pv)
        #
        #         logs_volume = CreateVolume(
        #             volume_name=logs_volume_name,
        #             app_name=app_name,
        #             mount_path=self.args.logs_volume_container_path,
        #             volume_type=VolumeType.PERSISTENT_VOLUME_CLAIM,
        #             pvc=PersistentVolumeClaimVolumeSource(
        #                 claim_name=logs_volume_name,
        #             ),
        #         )
        #         volumes.append(logs_volume)
        #     else:
        #         logger.error(f"{self.args.logs_volume_type.value} not supported")
        #         return None

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

        # if open_webserver_port = True
        # 1. Set the webserver_port in the container env
        # 2. Open the airflow webserver port
        webserver_port: Optional[CreatePort] = None
        if self.args.open_webserver_port:
            # Set the webserver port in the container env
            if container_env_cm.data is not None:
                container_env_cm.data["AIRFLOW__WEBSERVER__WEB_SERVER_PORT"] = str(
                    self.args.webserver_port
                )
            # Open the port
            webserver_port = CreatePort(
                name=self.args.webserver_port_name,
                container_port=self.args.webserver_port,
                service_port=self.get_ws_service_port(),
                node_port=self.args.ws_node_port,
                target_port=self.args.ws_target_port or self.args.webserver_port_name,
            )
            ports.append(webserver_port)

        # if open_worker_log_port = True
        # 1. Set the worker_log_port in the container env
        # 2. Open the worker_log_port
        if self.args.open_worker_log_port:
            # Set the worker_log_port in the container_env
            if container_env_cm.data is not None:
                container_env_cm.data["AIRFLOW__LOGGING__WORKER_LOG_SERVER_PORT"] = str(
                    self.args.worker_log_port
                )
            # Open the port
            worker_log_port = CreatePort(
                name=self.args.worker_log_port_name,
                container_port=self.args.worker_log_port,
            )
            ports.append(worker_log_port)

        # if open_flower_port = True
        # 1. Set the flower_port in the container env
        # 2. Open the flower_port
        flower_port: Optional[CreatePort] = None
        if self.args.open_flower_port:
            # Set the flower_port in the container_env
            if container_env_cm.data is not None:
                container_env_cm.data["AIRFLOW__CELERY__FLOWER_PORT"] = str(
                    self.args.flower_port
                )
            # Open the port
            flower_port = CreatePort(
                name=self.args.flower_port_name,
                container_port=self.args.flower_port,
                service_port=self.get_flower_service_port(),
                target_port=self.args.flower_target_port or self.args.flower_port_name,
            )
            ports.append(flower_port)

        container_labels: Dict[str, Any] = common_labels or {}
        if self.args.container_labels is not None and isinstance(
            self.args.container_labels, dict
        ):
            container_labels.update(self.args.container_labels)

        # Create the Airflow container
        airflow_container = CreateContainer(
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
        containers.insert(0, airflow_container)

        # Set default container for kubectl commands
        # https://kubernetes.io/docs/reference/labels-annotations-taints/#kubectl-kubernetes-io-default-container
        pod_annotations = {
            "kubectl.kubernetes.io/default-container": airflow_container.container_name,
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

        # Create the deployment
        airflow_deployment = CreateDeployment(
            deploy_name=self.get_deploy_name(),
            pod_name=self.get_pod_name(),
            app_name=app_name,
            namespace=ns_name,
            service_account_name=sa_name,
            replicas=self.args.replicas,
            containers=containers,
            init_containers=init_containers if len(init_containers) > 0 else None,
            pod_node_selector=self.args.pod_node_selector,
            restart_policy=self.args.deploy_restart_policy or RestartPolicy.ALWAYS,
            termination_grace_period_seconds=self.args.termination_grace_period_seconds,
            volumes=volumes if len(volumes) > 0 else None,
            labels=deploy_labels,
            pod_annotations=pod_annotations,
            topology_spread_key=self.args.topology_spread_key,
            topology_spread_max_skew=self.args.topology_spread_max_skew,
            topology_spread_when_unsatisfiable=self.args.topology_spread_when_unsatisfiable,
        )
        deployments.append(airflow_deployment)

        # Create the services
        if self.args.create_service:
            service_labels: Dict[str, Any] = common_labels or {}
            if self.args.service_labels is not None and isinstance(
                self.args.service_labels, dict
            ):
                service_labels.update(self.args.service_labels)

            _service = CreateService(
                service_name=self.get_service_name(),
                app_name=app_name,
                namespace=ns_name,
                service_account_name=sa_name,
                service_type=self.args.service_type,
                deployment=airflow_deployment,
                ports=ports if len(ports) > 0 else None,
                labels=service_labels,
            )
            services.append(_service)

        if self.args.create_webserver_service:
            ws_svc_labels: Dict[str, Any] = common_labels or {}
            if self.args.ws_svc_labels is not None and isinstance(
                self.args.ws_svc_labels, dict
            ):
                ws_svc_labels.update(self.args.ws_svc_labels)

            ws_service = CreateService(
                service_name=self.get_ws_service_name(),
                app_name=app_name,
                namespace=ns_name,
                service_account_name=sa_name,
                service_type=self.args.ws_svc_type,
                deployment=airflow_deployment,
                ports=[webserver_port] if webserver_port else None,
                labels=ws_svc_labels,
            )
            services.append(ws_service)

        if self.args.create_flower_service:
            flower_svc_labels = common_labels or {}
            if self.args.flower_svc_labels is not None and isinstance(
                self.args.flower_svc_labels, dict
            ):
                flower_svc_labels.update(self.args.flower_svc_labels)
            flower_service = CreateService(
                service_name=self.get_flower_service_name(),
                app_name=app_name,
                namespace=ns_name,
                service_account_name=sa_name,
                service_type=self.args.flower_svc_type,
                deployment=airflow_deployment,
                ports=[flower_port] if flower_port else None,
                labels=flower_svc_labels,
            )
            services.append(flower_service)

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
