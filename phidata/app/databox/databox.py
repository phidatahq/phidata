from collections import OrderedDict
from pathlib import Path
from typing import Optional, Dict, List, Union, Any
from typing_extensions import Literal

from phidata.app.db import DbApp
from phidata.app import PhidataApp, PhidataAppArgs
from phidata.constants import (
    SCRIPTS_DIR_ENV_VAR,
    STORAGE_DIR_ENV_VAR,
    META_DIR_ENV_VAR,
    PRODUCTS_DIR_ENV_VAR,
    NOTEBOOKS_DIR_ENV_VAR,
    WORKSPACE_CONFIG_DIR_ENV_VAR,
    PHIDATA_RUNTIME_ENV_VAR,
)
from phidata.infra.docker.resource.network import DockerNetwork
from phidata.infra.docker.resource.container import DockerContainer
from phidata.infra.docker.resource.group import (
    DockerResourceGroup,
    DockerBuildContext,
)
from phidata.infra.k8s.create.apps.v1.deployment import CreateDeployment
from phidata.infra.k8s.create.core.v1.secret import CreateSecret
from phidata.infra.k8s.create.core.v1.config_map import CreateConfigMap
from phidata.infra.k8s.create.core.v1.container import CreateContainer
from phidata.infra.k8s.create.core.v1.volume import (
    CreateVolume,
    VolumeType,
    HostPathVolumeSource,
)
from phidata.infra.k8s.create.common.port import CreatePort
from phidata.infra.k8s.create.group import CreateK8sResourceGroup
from phidata.infra.k8s.enums.image_pull_policy import ImagePullPolicy
from phidata.infra.k8s.enums.restart_policy import RestartPolicy
from phidata.infra.k8s.resource.group import (
    K8sResourceGroup,
    K8sBuildContext,
)
from phidata.utils.common import (
    get_image_str,
    get_default_container_name,
    get_default_configmap_name,
    get_default_secret_name,
    get_default_deploy_name,
    get_default_pod_name,
)
from phidata.utils.cli_console import print_error
from phidata.utils.log import logger

default_databox_name: str = "databox"


class DataboxArgs(PhidataAppArgs):
    name: str = default_databox_name
    version: str = "1"
    enabled: bool = True

    # Image args
    image_name: str = "phidata/databox"
    image_tag: str = "2.3.0"
    entrypoint: Optional[Union[str, List]] = None
    command: Optional[Union[str, List]] = None

    # Mount the workspace directory on the container
    mount_workspace: bool = True
    workspace_volume_name: str = "databox-ws-volume"
    # Path to mount the workspace volume under
    # This is the parent directory for the workspace on the container
    # i.e. the ws is mounted as a subdir in this dir
    # eg: if ws name is: idata, workspace path would be: /usr/local/workspaces/idata
    workspace_parent_container_path: str = "/usr/local/workspaces"
    # NOTE: On DockerContainers the workspace_root_path is mounted to workspace_dir
    # because we assume that DockerContainers are running locally on the user's machine
    # On K8sContainers, we usually load the workspace_dir from git using a git-sync sidecar container
    create_git_sync_sidecar: bool = True
    git_sync_repo: Optional[str] = None
    git_sync_branch: Optional[str] = None
    git_sync_wait: int = 1
    # But when running k8s locally, we can mount the workspace using
    # host path as well.
    k8s_mount_local_workspace = False

    # Install python dependencies using a requirements.txt file
    install_requirements: bool = False
    # Path to the requirements.txt file relative to the workspace_root
    requirements_file_path: str = "requirements.txt"

    # Mount aws config on the container
    # Only on DockerContainers, for K8sContainers use IamRole
    mount_aws_config: bool = False
    # Aws config dir on the host
    aws_config_path: Path = Path.home().resolve().joinpath(".aws")
    # Aws config dir on the container
    aws_config_container_path: str = "/root/.aws"

    # Only on DockerContainers
    # Mount airflow home from container to host machine
    # Useful when debugging the airflow conf
    mount_airflow_home: bool = False
    # Path to the dir on host machine relative to the workspace root
    airflow_home_dir: str = "airflow"
    # Path to airflow home on the container
    airflow_home_container_path: str = "/usr/local/airflow"

    # Configure airflow
    # If init_airflow = True, this databox initializes airflow and
    # sets the env var INIT_AIRFLOW = True
    # INIT_AIRFLOW = True is required by phidata to build dags
    init_airflow: bool = True
    # The AIRFLOW_ENV defines the current airflow runtime and can be used by DAGs to separate dev vs prd code
    airflow_env: Literal["dev", "stg", "prd"] = "dev"
    # If use_products_as_airflow_dags = True
    # set the AIRFLOW__CORE__DAGS_FOLDER to the products_dir
    use_products_as_airflow_dags: bool = True
    # If use_products_as_airflow_dags = False
    # set the AIRFLOW__CORE__DAGS_FOLDER to the airflow_dags_path
    # airflow_dags_path is the directory in the container containing the airflow dags
    airflow_dags_path: Optional[str] = None
    # Creates an airflow admin with username: admin, pass: admin
    create_airflow_admin_user: bool = False
    airflow_executor: Literal[
        "DebugExecutor",
        "LocalExecutor",
        "SequentialExecutor",
        "CeleryExecutor",
        "CeleryKubernetesExecutor",
        "DaskExecutor",
        "KubernetesExecutor",
    ] = "SequentialExecutor"

    # Configure airflow db
    # If True, initialize the airflow_db on this databox
    # If None, value is derived from init_airflow i.e. initialize the airflow_db if init_airflow = True
    #   Locally, airflow_db uses sqllite
    # If using the databox with an external Airflow db, set init_airflow_db = False
    init_airflow_db: Optional[bool] = None
    # Upgrade the airflow db
    upgrade_airflow_db: bool = False
    wait_for_airflow_db: bool = False
    # Connect to database using DbApp
    airflow_db_app: Optional[DbApp] = None
    # Connect to database manually
    airflow_db_user: Optional[str] = None
    airflow_db_password: Optional[str] = None
    airflow_db_schema: Optional[str] = None
    airflow_db_host: Optional[str] = None
    airflow_db_port: Optional[int] = None
    airflow_db_driver: str = "postgresql+psycopg2"
    # Airflow db connections in the format { conn_id: conn_url }
    # converted to env var: AIRFLOW_CONN__conn_id = conn_url
    db_connections: Optional[Dict] = None

    # Start airflow standalone
    start_airflow_standalone: bool = False
    # Open the airflow_standalone_container_port on the container
    # if start_airflow_standalone=True
    airflow_standalone_container_port: int = 8080
    # standalone port on the host machine
    airflow_standalone_host_port: int = 8080
    # standalone port name on K8sContainer
    airflow_standalone_port_name: str = "standalone"

    # Configure airflow scheduler
    # Init Airflow scheduler as a daemon process
    # DEPRECATED: use start_airflow_standalone
    init_airflow_scheduler: bool = False

    # Configure airflow webserver
    # Init Airflow webserver when the container starts
    # DEPRECATED: use start_airflow_standalone
    init_airflow_webserver: bool = False

    # Open the airflow_webserver_container_port on the container
    # if init_airflow_webserver=True
    # This is also used to set AIRFLOW__WEBSERVER__WEB_SERVER_PORT
    airflow_webserver_container_port: int = 7080
    # webserver port on the host machine
    airflow_webserver_host_port: int = 8080
    # webserver port name on K8sContainer
    airflow_webserver_port_name: str = "webserver"

    # Configure the container
    container_name: Optional[str] = None
    image_pull_policy: ImagePullPolicy = ImagePullPolicy.IF_NOT_PRESENT
    # Only used by the DockerContainer
    container_detach: bool = True
    container_auto_remove: bool = True
    container_remove: bool = True
    # Overwrite the PYTHONPATH env var, which is usually set to the workspace_root_container_path
    python_path: Optional[str] = None
    # Add container labels
    container_labels: Optional[Dict[str, Any]] = None
    # NOTE: Available only for Docker
    # Add volumes to DockerContainer
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
    container_volumes: Optional[Dict[str, dict]] = None

    # Add env variables to container env
    env: Optional[Dict[str, str]] = None
    # Read env variables from a file in yaml format
    env_file: Optional[Path] = None
    # Configure the ConfigMap used for env variables that are not Secret
    config_map_name: Optional[str] = None
    # Configure the Secret used for env variables that are Secret
    secret_name: Optional[str] = None
    # Read secrets from a file in yaml format
    secrets_file: Optional[Path] = None

    # Configure the databox deploy
    deploy_name: Optional[str] = None
    pod_name: Optional[str] = None
    replicas: int = 1
    pod_node_selector: Optional[Dict[str, str]] = None
    restart_policy: RestartPolicy = RestartPolicy.ALWAYS
    termination_grace_period_seconds: Optional[int] = None
    # Add deployment labels
    deploy_labels: Optional[Dict[str, Any]] = None

    # Other args
    load_examples: bool = False
    print_env_on_load: bool = True

    # Install phidata in development mode
    install_phidata_dev: bool = False
    phidata_volume_name: str = "databox-phidata-volume"
    phidata_dir_path: Path = Path.home().joinpath("lab", "phidata")
    phidata_dir_container_path: str = "/phidata"


class Databox(PhidataApp):
    def __init__(
        self,
        name: str = default_databox_name,
        version: str = "1",
        enabled: bool = True,
        # Image args,
        image_name: str = "phidata/databox",
        image_tag: str = "2.3.0",
        entrypoint: Optional[Union[str, List]] = None,
        command: Optional[Union[str, List]] = None,
        # Mount the workspace directory on the container,
        mount_workspace: bool = True,
        workspace_volume_name: str = "databox-ws-volume",
        # Path to mount the workspace volume under,
        # This is the parent directory for the workspace on the container,
        # i.e. the ws is mounted as a subdir in this dir,
        # eg: if ws name is: idata, workspace path would be: /usr/local/workspaces/idata,
        workspace_parent_container_path: str = "/usr/local/workspaces",
        # NOTE: On DockerContainers the workspace_root_path is mounted to workspace_dir,
        # because we assume that DockerContainers are running locally on the user's machine,
        # On K8sContainers, we load the workspace_dir from git using a git-sync sidecar container,
        create_git_sync_sidecar: bool = True,
        git_sync_repo: Optional[str] = None,
        git_sync_branch: Optional[str] = None,
        git_sync_wait: int = 1,
        # But when running k8s locally, we can mount the workspace using
        # host path as well.
        k8s_mount_local_workspace=False,
        # Install python dependencies using a requirements.txt file,
        install_requirements: bool = False,
        # Path to the requirements.txt file relative to the workspace_root
        requirements_file_path: str = "requirements.txt",
        # Only on DockerContainers, for K8sContainers use IamRole
        # Mount aws config on the container
        mount_aws_config: bool = False,
        # Aws config dir on the host,
        aws_config_path: Path = Path.home().resolve().joinpath(".aws"),
        # Aws config dir on the container,
        aws_config_container_path: str = "/root/.aws",
        # Mount aws config on the container
        # Only on DockerContainers, for K8sContainers use IamRole
        mount_airflow_home: bool = False,
        # Path to the dir on host machine relative to the workspace root,
        airflow_home_dir: str = "airflow",
        # Path to airflow home on the container,
        airflow_home_container_path: str = "/usr/local/airflow",
        # Configure airflow,
        # If init_airflow = True, this databox initializes airflow and
        # sets the env var INIT_AIRFLOW = True
        # INIT_AIRFLOW = True is required by phidata to build dags
        init_airflow: bool = True,
        # The AIRFLOW_ENV defines the current airflow runtime and can be used by DAGs to separate dev vs prd code
        airflow_env: Literal["dev", "stg", "prd"] = "dev",
        # If use_products_as_airflow_dags = True,
        # set the AIRFLOW__CORE__DAGS_FOLDER to the products_dir,
        use_products_as_airflow_dags: bool = True,
        # If use_products_as_airflow_dags = False,
        # set the AIRFLOW__CORE__DAGS_FOLDER to the airflow_dags_path,
        # airflow_dags_path is the directory in the container containing the airflow dags,
        airflow_dags_path: Optional[str] = None,
        # Creates an airflow admin with username: admin, pass: admin,
        create_airflow_admin_user: bool = False,
        airflow_executor: Literal[
            "DebugExecutor",
            "LocalExecutor",
            "SequentialExecutor",
            "CeleryExecutor",
            "CeleryKubernetesExecutor",
            "DaskExecutor",
            "KubernetesExecutor",
        ] = "SequentialExecutor",
        # Configure airflow db,
        # If True, initialize the airflow_db on this databox,
        # If None, value is derived from init_airflow i.e. initialize the airflow_db if init_airflow = True,
        #   Locally, airflow_db uses sqllite,
        # If using the databox with an external Airflow db, set init_airflow_db = False,
        init_airflow_db: Optional[bool] = None,
        # Upgrade the airflow db
        upgrade_airflow_db: bool = False,
        wait_for_airflow_db: bool = False,
        # Connect to database using DbApp,
        airflow_db_app: Optional[DbApp] = None,
        # Connect to database manually,
        airflow_db_user: Optional[str] = None,
        airflow_db_password: Optional[str] = None,
        airflow_db_schema: Optional[str] = None,
        airflow_db_host: Optional[str] = None,
        airflow_db_port: Optional[str] = None,
        airflow_db_driver: str = "postgresql+psycopg2",
        # Airflow db connections in the format { conn_id: conn_url },
        # converted to env var: AIRFLOW_CONN__conn_id = conn_url,
        db_connections: Optional[Dict] = None,
        # Start airflow standalone
        start_airflow_standalone: bool = False,
        # Open the airflow_standalone_container_port on the container
        # if start_airflow_standalone=True
        airflow_standalone_container_port: int = 8080,
        # standalone port on the host machine
        airflow_standalone_host_port: int = 8080,
        # standalone port name on K8sContainer
        airflow_standalone_port_name: str = "standalone",
        # Configure airflow scheduler,
        # Init Airflow scheduler as a daemon process,
        # DEPRECATED: use start_airflow_standalone
        init_airflow_scheduler: bool = False,
        # Configure airflow webserver,
        # Init Airflow webserver when the container starts,
        # DEPRECATED: use start_airflow_standalone
        init_airflow_webserver: bool = False,
        # Open the airflow_webserver_container_port on the container
        # if init_airflow_webserver=True
        # This is also used to set AIRFLOW__WEBSERVER__WEB_SERVER_PORT
        airflow_webserver_container_port: int = 7080,
        # webserver port on the host machine,
        airflow_webserver_host_port: int = 8080,
        # webserver port name on K8sContainer,
        airflow_webserver_port_name: str = "webserver",
        # Configure the container,
        container_name: Optional[str] = None,
        image_pull_policy: ImagePullPolicy = ImagePullPolicy.IF_NOT_PRESENT,
        # Only used by the DockerContainer,
        container_detach: bool = True,
        container_auto_remove: bool = True,
        container_remove: bool = True,
        # Overwrite the PYTHONPATH env var, which is usually set to the workspace_root_container_path
        python_path: Optional[str] = None,
        # Add container labels
        container_labels: Optional[Dict[str, Any]] = None,
        # NOTE: Available only for Docker
        # Add volumes to DockerContainer
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
        container_volumes: Optional[Dict[str, dict]] = None,
        # Add env variables to container env,
        env: Optional[Dict[str, str]] = None,
        # Read env variables from a file in yaml format,
        env_file: Optional[Path] = None,
        # Configure the ConfigMap used for env variables that are not Secret,
        config_map_name: Optional[str] = None,
        # Configure the Secret used for env variables that are Secret,
        secret_name: Optional[str] = None,
        # Read secrets from a file in yaml format,
        secrets_file: Optional[Path] = None,
        # Configure the databox deploy,
        deploy_name: Optional[str] = None,
        pod_name: Optional[str] = None,
        replicas: int = 1,
        pod_node_selector: Optional[Dict[str, str]] = None,
        restart_policy: RestartPolicy = RestartPolicy.ALWAYS,
        termination_grace_period_seconds: Optional[int] = None,
        # Add deployment labels
        deploy_labels: Optional[Dict[str, Any]] = None,
        # Other args,
        load_examples: bool = False,
        print_env_on_load: bool = True,
        # Additional args
        # If True, skip resource creation if active resources with the same name exist.
        use_cache: bool = True,
        install_phidata_dev: bool = False,
        phidata_volume_name: str = "devbox-phidata-volume",
        phidata_dir_path: Path = Path.home().joinpath("lab", "phidata"),
        phidata_dir_container_path: str = "/phidata",
    ):
        super().__init__()
        try:
            self.args: DataboxArgs = DataboxArgs(
                name=name,
                version=version,
                enabled=enabled,
                image_name=image_name,
                image_tag=image_tag,
                entrypoint=entrypoint,
                command=command,
                mount_workspace=mount_workspace,
                workspace_volume_name=workspace_volume_name,
                workspace_parent_container_path=workspace_parent_container_path,
                create_git_sync_sidecar=create_git_sync_sidecar,
                git_sync_repo=git_sync_repo,
                git_sync_branch=git_sync_branch,
                git_sync_wait=git_sync_wait,
                k8s_mount_local_workspace=k8s_mount_local_workspace,
                install_requirements=install_requirements,
                requirements_file_path=requirements_file_path,
                mount_aws_config=mount_aws_config,
                aws_config_path=aws_config_path,
                aws_config_container_path=aws_config_container_path,
                mount_airflow_home=mount_airflow_home,
                airflow_home_dir=airflow_home_dir,
                airflow_home_container_path=airflow_home_container_path,
                init_airflow=init_airflow,
                airflow_env=airflow_env,
                use_products_as_airflow_dags=use_products_as_airflow_dags,
                airflow_dags_path=airflow_dags_path,
                create_airflow_admin_user=create_airflow_admin_user,
                airflow_executor=airflow_executor,
                init_airflow_db=init_airflow_db,
                upgrade_airflow_db=upgrade_airflow_db,
                wait_for_airflow_db=wait_for_airflow_db,
                airflow_db_app=airflow_db_app,
                airflow_db_user=airflow_db_user,
                airflow_db_password=airflow_db_password,
                airflow_db_schema=airflow_db_schema,
                airflow_db_host=airflow_db_host,
                airflow_db_port=airflow_db_port,
                airflow_db_driver=airflow_db_driver,
                db_connections=db_connections,
                start_airflow_standalone=start_airflow_standalone,
                airflow_standalone_container_port=airflow_standalone_container_port,
                airflow_standalone_host_port=airflow_standalone_host_port,
                airflow_standalone_port_name=airflow_standalone_port_name,
                init_airflow_scheduler=init_airflow_scheduler,
                init_airflow_webserver=init_airflow_webserver,
                airflow_webserver_container_port=airflow_webserver_container_port,
                airflow_webserver_host_port=airflow_webserver_host_port,
                airflow_webserver_port_name=airflow_webserver_port_name,
                container_name=container_name,
                image_pull_policy=image_pull_policy,
                container_detach=container_detach,
                container_auto_remove=container_auto_remove,
                container_remove=container_remove,
                python_path=python_path,
                container_labels=container_labels,
                container_volumes=container_volumes,
                env=env,
                env_file=env_file,
                config_map_name=config_map_name,
                secret_name=secret_name,
                secrets_file=secrets_file,
                deploy_name=deploy_name,
                pod_name=pod_name,
                replicas=replicas,
                pod_node_selector=pod_node_selector,
                restart_policy=restart_policy,
                termination_grace_period_seconds=termination_grace_period_seconds,
                deploy_labels=deploy_labels,
                load_examples=load_examples,
                print_env_on_load=print_env_on_load,
                use_cache=use_cache,
                install_phidata_dev=install_phidata_dev,
                phidata_volume_name=phidata_volume_name,
                phidata_dir_path=phidata_dir_path,
                phidata_dir_container_path=phidata_dir_container_path,
            )
        except Exception as e:
            logger.error(f"Args for {self.__class__.__name__} are not valid")
            raise

    def get_container_name(self) -> str:
        return self.args.container_name or get_default_container_name(self.args.name)

    def get_env_data_from_file(self) -> Optional[Dict[str, str]]:
        env_file_path = self.args.env_file
        if (
            env_file_path is not None
            and env_file_path.exists()
            and env_file_path.is_file()
        ):
            import yaml

            # logger.debug(f"Reading {env_file_path}")
            env_data_from_file = yaml.safe_load(env_file_path.read_text())
            if env_data_from_file is not None and isinstance(env_data_from_file, dict):
                return env_data_from_file
            else:
                print_error(f"Invalid env_file: {env_file_path}")
        return None

    def get_secret_data_from_file(self) -> Optional[Dict[str, str]]:
        secrets_file_path = self.args.secrets_file
        if (
            secrets_file_path is not None
            and secrets_file_path.exists()
            and secrets_file_path.is_file()
        ):
            import yaml

            # logger.debug(f"Reading {secrets_file_path}")
            secret_data_from_file = yaml.safe_load(secrets_file_path.read_text())
            if secret_data_from_file is not None and isinstance(
                secret_data_from_file, dict
            ):
                return secret_data_from_file
            else:
                print_error(f"Invalid secrets_file: {secrets_file_path}")
        return None

    ######################################################
    ## Docker Resources
    ######################################################

    def init_airflow_on_docker_container(self, container: DockerContainer) -> None:
        """
        Initialize airflow on a docker container
        """

        if not self.args.init_airflow:
            return

        # Update init_airflow_db arg if None
        if self.args.init_airflow_db is None:
            self.args.init_airflow_db = True

        # Workspace paths
        if self.workspace_root_path is None:
            logger.error("Invalid workspace_root_path")
            return
        workspace_name = self.workspace_root_path.stem
        workspace_root_container_path = Path(
            self.args.workspace_parent_container_path
        ).joinpath(workspace_name)
        products_dir_container_path = (
            workspace_root_container_path.joinpath(self.products_dir)
            if self.products_dir
            else None
        )

        # Airflow db connection
        airflow_db_user = self.args.airflow_db_user
        airflow_db_password = self.args.airflow_db_password
        airflow_db_schema = self.args.airflow_db_schema
        airflow_db_host = self.args.airflow_db_host
        airflow_db_port = self.args.airflow_db_port
        airflow_db_driver = self.args.airflow_db_driver
        if self.args.airflow_db_app is not None and isinstance(
            self.args.airflow_db_app, DbApp
        ):
            logger.debug(
                f"Reading db connection details from: {self.args.airflow_db_app.name}"
            )
            if airflow_db_user is None:
                airflow_db_user = self.args.airflow_db_app.get_db_user()
            if airflow_db_password is None:
                airflow_db_password = self.args.airflow_db_app.get_db_password()
            if airflow_db_schema is None:
                airflow_db_schema = self.args.airflow_db_app.get_db_schema()
            if airflow_db_host is None:
                airflow_db_host = self.args.airflow_db_app.get_db_host_docker()
            if airflow_db_port is None:
                airflow_db_port = self.args.airflow_db_app.get_db_port_docker()
            if airflow_db_driver is None:
                airflow_db_driver = self.args.airflow_db_app.get_db_driver()
        db_connection_url = f"{airflow_db_driver}://{airflow_db_user}:{airflow_db_password}@{airflow_db_host}:{airflow_db_port}/{airflow_db_schema}"

        airflow_env: Dict[str, str] = {
            "INIT_AIRFLOW": str(self.args.init_airflow),
            "AIRFLOW_ENV": self.args.airflow_env,
            "INIT_AIRFLOW_DB": str(self.args.init_airflow_db),
            "UPGRADE_AIRFLOW_DB": str(self.args.upgrade_airflow_db),
            "WAIT_FOR_AIRFLOW_DB": str(self.args.wait_for_airflow_db),
            "AIRFLOW_DB_USER": str(airflow_db_user),
            "AIRFLOW_DB_PASSWORD": str(airflow_db_password),
            "AIRFLOW_SCHEMA": str(airflow_db_schema),
            "AIRFLOW_DB_HOST": str(airflow_db_host),
            "AIRFLOW_DB_PORT": str(airflow_db_port),
            "INIT_AIRFLOW_SCHEDULER": str(self.args.init_airflow_scheduler),
            "INIT_AIRFLOW_WEBSERVER": str(self.args.init_airflow_webserver),
            "INIT_AIRFLOW_STANDALONE": str(self.args.start_airflow_standalone),
            "AIRFLOW__CORE__LOAD_EXAMPLES": str(self.args.load_examples),
            "CREATE_AIRFLOW_ADMIN_USER": str(self.args.create_airflow_admin_user),
            "AIRFLOW__CORE__EXECUTOR": str(self.args.airflow_executor),
        }

        # Set the AIRFLOW__DATABASE__SQL_ALCHEMY_CONN
        if "None" not in db_connection_url:
            logger.debug(f"AIRFLOW__DATABASE__SQL_ALCHEMY_CONN: {db_connection_url}")
            airflow_env["AIRFLOW__DATABASE__SQL_ALCHEMY_CONN"] = db_connection_url

        # Set the AIRFLOW__CORE__DAGS_FOLDER
        if self.args.mount_workspace and self.args.use_products_as_airflow_dags:
            airflow_env["AIRFLOW__CORE__DAGS_FOLDER"] = str(products_dir_container_path)
        elif self.args.airflow_dags_path is not None:
            airflow_env["AIRFLOW__CORE__DAGS_FOLDER"] = self.args.airflow_dags_path

        # Set the AIRFLOW__CONN_ variables
        if self.args.db_connections is not None:
            for conn_id, conn_url in self.args.db_connections.items():
                try:
                    af_conn_id = str("AIRFLOW_CONN_{}".format(conn_id)).upper()
                    airflow_env[af_conn_id] = conn_url
                except Exception as e:
                    logger.exception(e)
                    continue

        # if init_airflow_webserver = True
        # 1. Set the webserver port in the container env
        # 2. Open the airflow webserver port
        if self.args.init_airflow_webserver:
            # Set the webserver port in the container env
            airflow_env["AIRFLOW__WEBSERVER__WEB_SERVER_PORT"] = str(
                self.args.airflow_webserver_container_port
            )
            # Open the port
            ws_port: Dict[str, int] = {
                str(
                    self.args.airflow_webserver_container_port
                ): self.args.airflow_webserver_host_port,
            }
            if container.ports is None:
                container.ports = {}
            container.ports.update(ws_port)

        # if start_airflow_standalone = True
        # 1. Open the airflow standalone port
        if self.args.start_airflow_standalone:
            # Open the port
            standalone_port: Dict[str, int] = {
                str(
                    self.args.airflow_standalone_container_port
                ): self.args.airflow_standalone_host_port,
            }
            if container.ports is None:
                container.ports = {}
            container.ports.update(standalone_port)

        # Update the container.environment to include airflow_env
        if isinstance(container.environment, dict):
            container.environment.update(airflow_env)
        else:
            logger.warning(
                f"Could not update container environment because it is of type: {type(container.environment)}"
            )

    def get_docker_rg(
        self, docker_build_context: DockerBuildContext
    ) -> Optional[DockerResourceGroup]:

        app_name = self.args.name
        logger.debug(f"Building {app_name} DockerResourceGroup")

        # Workspace paths
        if self.workspace_root_path is None:
            logger.error("Invalid workspace_root_path")
            return None
        workspace_name = self.workspace_root_path.stem
        workspace_root_container_path = Path(
            self.args.workspace_parent_container_path
        ).joinpath(workspace_name)
        requirements_file_container_path = workspace_root_container_path.joinpath(
            self.args.requirements_file_path
        )
        scripts_dir_container_path = (
            workspace_root_container_path.joinpath(self.scripts_dir)
            if self.scripts_dir
            else None
        )
        storage_dir_container_path = (
            workspace_root_container_path.joinpath(self.storage_dir)
            if self.storage_dir
            else None
        )
        meta_dir_container_path = (
            workspace_root_container_path.joinpath(self.meta_dir)
            if self.meta_dir
            else None
        )
        products_dir_container_path = (
            workspace_root_container_path.joinpath(self.products_dir)
            if self.products_dir
            else None
        )
        notebooks_dir_container_path = (
            workspace_root_container_path.joinpath(self.notebooks_dir)
            if self.notebooks_dir
            else None
        )
        workspace_config_dir_container_path = (
            workspace_root_container_path.joinpath(self.workspace_config_dir)
            if self.workspace_config_dir
            else None
        )

        # Container pythonpath
        python_path = self.args.python_path or str(workspace_root_container_path)

        # Container Environment
        container_env: Dict[str, str] = {
            # Env variables used by data workflows and data assets
            "PHI_WORKSPACE_PARENT": str(self.args.workspace_parent_container_path),
            "PHI_WORKSPACE_ROOT": str(workspace_root_container_path),
            "PYTHONPATH": python_path,
            PHIDATA_RUNTIME_ENV_VAR: "airflow",
            SCRIPTS_DIR_ENV_VAR: str(scripts_dir_container_path),
            STORAGE_DIR_ENV_VAR: str(storage_dir_container_path),
            META_DIR_ENV_VAR: str(meta_dir_container_path),
            PRODUCTS_DIR_ENV_VAR: str(products_dir_container_path),
            NOTEBOOKS_DIR_ENV_VAR: str(notebooks_dir_container_path),
            WORKSPACE_CONFIG_DIR_ENV_VAR: str(workspace_config_dir_container_path),
            "INSTALL_REQUIREMENTS": str(self.args.install_requirements),
            "REQUIREMENTS_FILE_PATH": str(requirements_file_container_path),
            "MOUNT_WORKSPACE": str(self.args.mount_workspace),
            # Print env when the container starts
            "PRINT_ENV_ON_LOAD": str(self.args.print_env_on_load),
            "INSTALL_PHIDATA_DEV": str(self.args.install_phidata_dev),
            "PHIDATA_DIR_PATH": self.args.phidata_dir_container_path,
        }

        # Update the container env using env_file
        env_data_from_file = self.get_env_data_from_file()
        if env_data_from_file is not None:
            container_env.update(env_data_from_file)

        # Update the container env using secrets_file
        secret_data_from_file = self.get_secret_data_from_file()
        if secret_data_from_file is not None:
            container_env.update(secret_data_from_file)

        # Update the container env with user provided env
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
        container_volumes = self.args.container_volumes or {}
        # Create a volume for the workspace dir
        if self.args.mount_workspace:
            workspace_root_path_str = str(self.workspace_root_path)
            workspace_root_container_path_str = str(workspace_root_container_path)
            logger.debug(f"Mounting: {workspace_root_path_str}")
            logger.debug(f"\tto: {workspace_root_container_path_str}")
            container_volumes[workspace_root_path_str] = {
                "bind": workspace_root_container_path_str,
                "mode": "rw",
            }
        # Create a volume for aws config
        if self.args.mount_aws_config:
            aws_config_path_str = str(self.args.aws_config_path)
            logger.debug(f"Mounting: {aws_config_path_str}")
            logger.debug(f"\tto: {self.args.aws_config_container_path}")
            container_volumes[aws_config_path_str] = {
                "bind": self.args.aws_config_container_path,
                "mode": "ro",
            }
            container_env[
                "AWS_CONFIG_FILE"
            ] = f"{self.args.aws_config_container_path}/config"
            container_env[
                "AWS_SHARED_CREDENTIALS_FILE"
            ] = f"{self.args.aws_config_container_path}/credentials"
        # Create a volume for airflow home
        if self.args.mount_airflow_home:
            airflow_home_path_str = str(
                self.workspace_root_path.joinpath(self.args.airflow_home_dir)
            )
            airflow_home_container_path_str = str(self.args.airflow_home_container_path)
            logger.debug(f"Mounting: {airflow_home_path_str}")
            logger.debug(f"\tto: {airflow_home_container_path_str}")
            container_volumes[airflow_home_path_str] = {
                "bind": airflow_home_container_path_str,
                "mode": "rw",
            }
        # Create a volume for phidata in dev mode
        if self.args.install_phidata_dev and self.args.phidata_dir_path is not None:
            phidata_dir_absolute_path_str = str(self.args.phidata_dir_path)
            logger.debug(f"Mounting: {phidata_dir_absolute_path_str}")
            logger.debug(f"\tto: {self.args.phidata_dir_container_path}")
            container_volumes[phidata_dir_absolute_path_str] = {
                "bind": self.args.phidata_dir_container_path,
                "mode": "rw",
            }

        # Create the container
        docker_container = DockerContainer(
            name=self.get_container_name(),
            image=get_image_str(self.args.image_name, self.args.image_tag),
            entrypoint=self.args.entrypoint,
            command=self.args.command,
            detach=self.args.container_detach,
            auto_remove=self.args.container_auto_remove,
            remove=self.args.container_remove,
            stdin_open=True,
            tty=True,
            labels=self.args.container_labels,
            environment=container_env,
            network=docker_build_context.network,
            volumes=container_volumes,
            use_cache=self.args.use_cache,
        )
        # Initialize airflow on container
        self.init_airflow_on_docker_container(docker_container)
        # logger.debug(f"Databox Container Env: {docker_container.environment}")

        docker_rg = DockerResourceGroup(
            name=app_name,
            enabled=self.args.enabled,
            network=DockerNetwork(name=docker_build_context.network),
            containers=[docker_container],
        )
        return docker_rg

    def init_docker_resource_groups(
        self, docker_build_context: DockerBuildContext
    ) -> None:
        docker_rg = self.get_docker_rg(docker_build_context)
        if docker_rg is not None:
            if self.docker_resource_groups is None:
                self.docker_resource_groups = OrderedDict()
            self.docker_resource_groups[docker_rg.name] = docker_rg

    ######################################################
    ## K8s Resources
    ######################################################

    def init_airflow_on_k8s_container(
        self, container: CreateContainer, k8s_resource_group: CreateK8sResourceGroup
    ) -> None:
        """
        Initialize airflow on a k8s container
        """

        if not self.args.init_airflow:
            return

        # Update init_airflow_db arg if None
        if self.args.init_airflow_db is None:
            self.args.init_airflow_db = True

        # Workspace paths
        if self.workspace_root_path is None:
            logger.error("Invalid workspace_root_path")
            return
        workspace_name = self.workspace_root_path.stem
        workspace_root_container_path = Path(
            self.args.workspace_parent_container_path
        ).joinpath(workspace_name)
        products_dir_container_path = (
            workspace_root_container_path.joinpath(self.products_dir)
            if self.products_dir
            else None
        )

        # Airflow db connection
        airflow_db_user = self.args.airflow_db_user
        airflow_db_password = self.args.airflow_db_password
        airflow_db_schema = self.args.airflow_db_schema
        airflow_db_host = self.args.airflow_db_host
        airflow_db_port = self.args.airflow_db_port
        airflow_db_driver = self.args.airflow_db_driver
        if self.args.airflow_db_app is not None and isinstance(
            self.args.airflow_db_app, DbApp
        ):
            logger.debug(
                f"Reading db connection details from: {self.args.airflow_db_app.name}"
            )
            if airflow_db_user is None:
                airflow_db_user = self.args.airflow_db_app.get_db_user()
            if airflow_db_password is None:
                airflow_db_password = self.args.airflow_db_app.get_db_password()
            if airflow_db_schema is None:
                airflow_db_schema = self.args.airflow_db_app.get_db_schema()
            if airflow_db_host is None:
                airflow_db_host = self.args.airflow_db_app.get_db_host_k8s()
            if airflow_db_port is None:
                airflow_db_port = self.args.airflow_db_app.get_db_port_k8s()
            if airflow_db_driver is None:
                airflow_db_driver = self.args.airflow_db_app.get_db_driver()
        db_connection_url = f"{airflow_db_driver}://{airflow_db_user}:{airflow_db_password}@{airflow_db_host}:{airflow_db_port}/{airflow_db_schema}"

        airflow_env: Dict[str, str] = {
            "INIT_AIRFLOW": str(self.args.init_airflow),
            "AIRFLOW_ENV": self.args.airflow_env,
            "INIT_AIRFLOW_DB": str(self.args.init_airflow_db),
            "UPGRADE_AIRFLOW_DB": str(self.args.upgrade_airflow_db),
            "WAIT_FOR_AIRFLOW_DB": str(self.args.wait_for_airflow_db),
            "AIRFLOW_DB_USER": str(airflow_db_user),
            "AIRFLOW_DB_PASSWORD": str(airflow_db_password),
            "AIRFLOW_SCHEMA": str(airflow_db_schema),
            "AIRFLOW_DB_HOST": str(airflow_db_host),
            "AIRFLOW_DB_PORT": str(airflow_db_port),
            "INIT_AIRFLOW_SCHEDULER": str(self.args.init_airflow_scheduler),
            "INIT_AIRFLOW_WEBSERVER": str(self.args.init_airflow_webserver),
            "INIT_AIRFLOW_STANDALONE": str(self.args.start_airflow_standalone),
            "AIRFLOW__CORE__LOAD_EXAMPLES": str(self.args.load_examples),
            "CREATE_AIRFLOW_ADMIN_USER": str(self.args.create_airflow_admin_user),
            "AIRFLOW__CORE__EXECUTOR": str(self.args.airflow_executor),
        }

        # Set the AIRFLOW__DATABASE__SQL_ALCHEMY_CONN
        if "None" not in db_connection_url:
            logger.debug(f"AIRFLOW__DATABASE__SQL_ALCHEMY_CONN: {db_connection_url}")
            airflow_env["AIRFLOW__DATABASE__SQL_ALCHEMY_CONN"] = db_connection_url
            # TODO: use AIRFLOW__CORE__SQL_ALCHEMY_CONN for older versions

        # Set the AIRFLOW__CORE__DAGS_FOLDER
        if self.args.mount_workspace and self.args.use_products_as_airflow_dags:
            airflow_env["AIRFLOW__CORE__DAGS_FOLDER"] = str(products_dir_container_path)
        elif self.args.airflow_dags_path is not None:
            airflow_env["AIRFLOW__CORE__DAGS_FOLDER"] = self.args.airflow_dags_path

        # Set the AIRFLOW__CONN_ variables
        if self.args.db_connections is not None:
            for conn_id, conn_url in self.args.db_connections.items():
                try:
                    af_conn_id = str("AIRFLOW_CONN_{}".format(conn_id)).upper()
                    airflow_env[af_conn_id] = conn_url
                except Exception as e:
                    logger.exception(e)
                    continue

        # if init_airflow_webserver = True
        # 1. Set the webserver port in the container env
        # 2. Open the airflow webserver port
        if self.args.init_airflow_webserver:
            # Set the webserver port in the container env
            airflow_env["AIRFLOW__WEBSERVER__WEB_SERVER_PORT"] = str(
                self.args.airflow_webserver_container_port
            )
            # Open the port
            ws_port = CreatePort(
                name=self.args.airflow_webserver_port_name,
                container_port=self.args.airflow_webserver_container_port,
            )
            if container.ports is None:
                container.ports = []
            container.ports.append(ws_port)

        # if start_airflow_standalone = True
        # 1. Open the airflow standalone port
        if self.args.start_airflow_standalone:
            # Open the port
            standalone_port = CreatePort(
                name=self.args.airflow_standalone_port_name,
                container_port=self.args.airflow_standalone_container_port,
            )
            if container.ports is None:
                container.ports = []
            container.ports.append(standalone_port)

        airflow_env_cm = CreateConfigMap(
            cm_name=get_default_configmap_name("databox-airflow"),
            app_name=self.args.name,
            data=airflow_env,
        )
        # Add airflow_env_cm to container env
        if container.envs_from_configmap is None:
            container.envs_from_configmap = []
        container.envs_from_configmap.append(airflow_env_cm.cm_name)
        if k8s_resource_group.config_maps is None:
            k8s_resource_group.config_maps = []
        k8s_resource_group.config_maps.append(airflow_env_cm)

    def get_k8s_rg(
        self, k8s_build_context: K8sBuildContext
    ) -> Optional[K8sResourceGroup]:

        app_name = self.args.name
        logger.debug(f"Building {app_name} K8sResourceGroup")

        # Define K8s resources
        config_maps: List[CreateConfigMap] = []
        secrets: List[CreateSecret] = []
        volumes: List[CreateVolume] = []
        containers: List[CreateContainer] = []

        # Workspace paths
        if self.workspace_root_path is None:
            logger.error("Invalid workspace_root_path")
            return None
        workspace_name = self.workspace_root_path.stem
        workspace_root_container_path = Path(
            self.args.workspace_parent_container_path
        ).joinpath(workspace_name)
        requirements_file_container_path = workspace_root_container_path.joinpath(
            self.args.requirements_file_path
        )
        scripts_dir_container_path = (
            workspace_root_container_path.joinpath(self.scripts_dir)
            if self.scripts_dir
            else None
        )
        storage_dir_container_path = (
            workspace_root_container_path.joinpath(self.storage_dir)
            if self.storage_dir
            else None
        )
        meta_dir_container_path = (
            workspace_root_container_path.joinpath(self.meta_dir)
            if self.meta_dir
            else None
        )
        products_dir_container_path = (
            workspace_root_container_path.joinpath(self.products_dir)
            if self.products_dir
            else None
        )
        notebooks_dir_container_path = (
            workspace_root_container_path.joinpath(self.notebooks_dir)
            if self.notebooks_dir
            else None
        )
        workspace_config_dir_container_path = (
            workspace_root_container_path.joinpath(self.workspace_config_dir)
            if self.workspace_config_dir
            else None
        )

        # Container pythonpath
        python_path = self.args.python_path or str(workspace_root_container_path)

        # Container Environment
        container_env: Dict[str, str] = {
            # Env variables used by data workflows and data assets
            "PHI_WORKSPACE_PARENT": str(self.args.workspace_parent_container_path),
            "PHI_WORKSPACE_ROOT": str(workspace_root_container_path),
            "PYTHONPATH": python_path,
            PHIDATA_RUNTIME_ENV_VAR: "airflow",
            SCRIPTS_DIR_ENV_VAR: str(scripts_dir_container_path),
            STORAGE_DIR_ENV_VAR: str(storage_dir_container_path),
            META_DIR_ENV_VAR: str(meta_dir_container_path),
            PRODUCTS_DIR_ENV_VAR: str(products_dir_container_path),
            NOTEBOOKS_DIR_ENV_VAR: str(notebooks_dir_container_path),
            WORKSPACE_CONFIG_DIR_ENV_VAR: str(workspace_config_dir_container_path),
            "INSTALL_REQUIREMENTS": str(self.args.install_requirements),
            "REQUIREMENTS_FILE_PATH": str(requirements_file_container_path),
            "MOUNT_WORKSPACE": str(self.args.mount_workspace),
            # Print env when the container starts
            "PRINT_ENV_ON_LOAD": str(self.args.print_env_on_load),
        }

        # Update the container env using env_file
        env_data_from_file = self.get_env_data_from_file()
        if env_data_from_file is not None:
            container_env.update(env_data_from_file)

        # Update the container env with user provided env
        if self.args.env is not None and isinstance(self.args.env, dict):
            container_env.update(self.args.env)

        # Create a ConfigMap to set the container env variables which are not Secret
        container_env_cm = CreateConfigMap(
            cm_name=self.args.config_map_name or get_default_configmap_name(app_name),
            app_name=app_name,
            data=container_env,
        )
        config_maps.append(container_env_cm)

        # Create a Secret to set the container env variables which are Secret
        secret_data_from_file = self.get_secret_data_from_file()
        if secret_data_from_file is not None:
            container_env_secret = CreateSecret(
                secret_name=self.args.secret_name or get_default_secret_name(app_name),
                app_name=app_name,
                string_data=secret_data_from_file,
            )
            secrets.append(container_env_secret)

        # If mount_workspace=True first check if the workspace
        # should be mounted locally, otherwise
        # Create a Sidecar git-sync container and volume
        if self.args.mount_workspace:
            if self.args.k8s_mount_local_workspace:
                workspace_root_path_str = str(self.workspace_root_path)
                workspace_root_container_path_str = str(workspace_root_container_path)
                logger.debug(f"Mounting: {workspace_root_path_str}")
                logger.debug(f"\tto: {workspace_root_container_path_str}")
                workspace_volume = CreateVolume(
                    volume_name=self.args.workspace_volume_name,
                    app_name=app_name,
                    mount_path=workspace_root_container_path_str,
                    volume_type=VolumeType.HOST_PATH,
                    host_path=HostPathVolumeSource(
                        path=workspace_root_path_str,
                    ),
                )
                volumes.append(workspace_volume)

            elif self.args.create_git_sync_sidecar:
                workspace_parent_container_path_str = str(
                    self.args.workspace_parent_container_path
                )
                logger.debug(f"Creating EmptyDir")
                logger.debug(f"\tat: {workspace_parent_container_path_str}")
                workspace_volume = CreateVolume(
                    volume_name=self.args.workspace_volume_name,
                    app_name=app_name,
                    mount_path=workspace_parent_container_path_str,
                    volume_type=VolumeType.EMPTY_DIR,
                )
                volumes.append(workspace_volume)

                if self.args.git_sync_repo is None:
                    print_error("git_sync_repo invalid")
                else:
                    git_sync_env = {
                        "GIT_SYNC_REPO": self.args.git_sync_repo,
                        "GIT_SYNC_ROOT": str(self.args.workspace_parent_container_path),
                        "GIT_SYNC_DEST": workspace_name,
                    }
                    if self.args.git_sync_branch is not None:
                        git_sync_env["GIT_SYNC_BRANCH"] = self.args.git_sync_branch
                    if self.args.git_sync_wait is not None:
                        git_sync_env["GIT_SYNC_WAIT"] = str(self.args.git_sync_wait)
                    git_sync_sidecar = CreateContainer(
                        container_name="git-sync-workspaces",
                        app_name=app_name,
                        image_name="k8s.gcr.io/git-sync",
                        image_tag="v3.1.1",
                        env=git_sync_env,
                        envs_from_configmap=[cm.cm_name for cm in config_maps]
                        if len(config_maps) > 0
                        else None,
                        envs_from_secret=[secret.secret_name for secret in secrets]
                        if len(secrets) > 0
                        else None,
                        volumes=[workspace_volume],
                    )
                    containers.append(git_sync_sidecar)

        container_labels: Optional[Dict[str, Any]] = self.args.container_labels
        if k8s_build_context.labels is not None:
            if container_labels:
                container_labels.update(k8s_build_context.labels)
            else:
                container_labels = k8s_build_context.labels
        # Create the container
        k8s_container = CreateContainer(
            container_name=self.get_container_name(),
            app_name=app_name,
            image_name=self.args.image_name,
            image_tag=self.args.image_tag,
            # Equivalent to docker images CMD
            args=[self.args.command]
            if isinstance(self.args.command, str)
            else self.args.command,
            # Equivalent to docker images ENTRYPOINT
            command=self.args.entrypoint,
            image_pull_policy=self.args.image_pull_policy,
            envs_from_configmap=[cm.cm_name for cm in config_maps]
            if len(config_maps) > 0
            else None,
            envs_from_secret=[secret.secret_name for secret in secrets]
            if len(secrets) > 0
            else None,
            volumes=volumes if len(volumes) > 0 else None,
            labels=container_labels,
        )
        containers.append(k8s_container)

        # Set default container for kubectl commands
        # https://kubernetes.io/docs/reference/labels-annotations-taints/#kubectl-kubernetes-io-default-container
        pod_annotations = {
            "kubectl.kubernetes.io/default-container": k8s_container.container_name
        }

        deploy_labels: Optional[Dict[str, Any]] = self.args.deploy_labels
        if k8s_build_context.labels is not None:
            if deploy_labels:
                deploy_labels.update(k8s_build_context.labels)
            else:
                deploy_labels = k8s_build_context.labels
        # Create the deployment
        k8s_deployment = CreateDeployment(
            deploy_name=self.args.deploy_name or get_default_deploy_name(app_name),
            pod_name=self.args.pod_name or get_default_pod_name(app_name),
            app_name=app_name,
            namespace=k8s_build_context.namespace,
            service_account_name=k8s_build_context.service_account_name,
            replicas=self.args.replicas,
            containers=containers if len(containers) > 0 else None,
            pod_node_selector=self.args.pod_node_selector,
            restart_policy=self.args.restart_policy,
            termination_grace_period_seconds=self.args.termination_grace_period_seconds,
            volumes=volumes if len(volumes) > 0 else None,
            labels=deploy_labels,
            pod_annotations=pod_annotations,
        )

        # Create the K8sResourceGroup
        k8s_resource_group = CreateK8sResourceGroup(
            name=self.args.name,
            enabled=self.args.enabled,
            config_maps=config_maps if len(config_maps) > 0 else None,
            secrets=secrets if len(secrets) > 0 else None,
            deployments=[k8s_deployment],
        )

        # Initialize airflow on container
        self.init_airflow_on_k8s_container(k8s_container, k8s_resource_group)

        return k8s_resource_group.create()

    def init_k8s_resource_groups(self, k8s_build_context: K8sBuildContext) -> None:
        k8s_rg = self.get_k8s_rg(k8s_build_context)
        if k8s_rg is not None:
            if self.k8s_resource_groups is None:
                self.k8s_resource_groups = OrderedDict()
            self.k8s_resource_groups[k8s_rg.name] = k8s_rg
