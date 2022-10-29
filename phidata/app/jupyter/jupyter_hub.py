from collections import OrderedDict
from pathlib import Path
from typing import Optional, Dict, Any, List, Union
from typing_extensions import Literal

from phidata.app.db import DbApp
from phidata.app.phidata_app import PhidataApp, PhidataAppArgs
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
from phidata.infra.k8s.create.apps.v1.deployment import CreateDeployment, RestartPolicy
from phidata.infra.k8s.create.core.v1.secret import CreateSecret
from phidata.infra.k8s.create.core.v1.service import CreateService, ServiceType
from phidata.infra.k8s.create.core.v1.config_map import CreateConfigMap
from phidata.infra.k8s.create.core.v1.container import CreateContainer, ImagePullPolicy
from phidata.infra.k8s.create.core.v1.service_account import CreateServiceAccount
from phidata.infra.k8s.create.rbac_authorization_k8s_io.v1.cluster_role import (
    CreateClusterRole,
    PolicyRule,
)
from phidata.infra.k8s.create.rbac_authorization_k8s_io.v1.cluste_role_binding import (
    CreateClusterRoleBinding,
)

from phidata.infra.k8s.create.core.v1.volume import (
    CreateVolume,
    HostPathVolumeSource,
    VolumeType,
)
from phidata.infra.k8s.create.common.port import CreatePort
from phidata.infra.k8s.create.group import CreateK8sResourceGroup
from phidata.infra.k8s.resource.group import (
    K8sResourceGroup,
    K8sBuildContext,
)
from phidata.utils.common import (
    get_image_str,
    get_default_container_name,
    get_default_configmap_name,
    get_default_secret_name,
    get_default_service_name,
    get_default_deploy_name,
    get_default_pod_name,
    get_default_volume_name,
    get_default_cr_name,
    get_default_crb_name,
    get_default_sa_name,
)
from phidata.utils.cli_console import print_error, print_warning
from phidata.utils.log import logger


class JupyterHubArgs(PhidataAppArgs):
    name: str = "jupyterhub"
    version: str = "1"
    enabled: bool = True

    # Image args
    image_name: str = "phidata/jupyterhub"
    image_tag: str = "2.3.1"
    entrypoint: Optional[Union[str, List]] = None
    command: Union[str, List] = "jupyterhub"

    # Mount the workspace directory on the container
    mount_workspace: bool = False
    workspace_volume_name: Optional[str] = None
    # Path to mount the workspace volume under
    # This is the parent directory for the workspace on the container
    # i.e. the ws is mounted as a subdir in this dir
    # eg: if ws name is: idata, workspace_dir would be: /mount/idata
    workspace_parent_container_path: str = "/mount"
    # NOTE: On DockerContainers the workspace_root_path is mounted to workspace_dir
    # because we assume that DockerContainers are running locally on the user's machine
    # On K8sContainers, we load the workspace_dir from git using a git-sync sidecar container
    create_git_sync_sidecar: bool = False
    git_sync_repo: Optional[str] = None
    git_sync_branch: Optional[str] = None
    git_sync_wait: int = 1
    # But when running k8s locally, we can mount the workspace using
    # host path as well.
    k8s_mount_local_workspace: bool = False

    # Jupyter resources directory relative to the workspace_root
    # This dir is mounted to the `/usr/local/jupyter` directory on the container
    mount_resources: bool = False
    resources_dir: str = "workspace/jupyter"
    resources_dir_container_path: str = "/usr/local/jupyter"
    resources_volume_name: Optional[str] = None

    # Path to JUPYTER_CONFIG_FILE relative to the workspace_root
    # Used to set the JUPYTER_CONFIG_FILE env var
    # This value is also appended to the command using `-f`
    jupyter_config_file: Optional[str] = None

    # Install python dependencies using a requirements.txt file
    # Sets the REQUIREMENTS_LOCAL & REQUIREMENTS_FILE_PATH env var to requirements_file
    install_requirements: bool = False
    # Path to the requirements.txt file relative to the workspace_root
    requirements_file: str = "workspace/jupyter/requirements.txt"

    # Overwrite the PYTHONPATH env var, which is usually set
    # to workspace_root_contaier_path:resources_dir_container_path
    python_path: Optional[str] = None

    # Configure Jupyter database
    wait_for_db: bool = False
    # Get database details using DbApp
    db_app: Optional[DbApp] = None
    # Provide database details
    # Set the DATABASE_USER env var
    db_user: Optional[str] = None
    # Set the DATABASE_PASSWORD env var,
    db_password: Optional[str] = None
    # Set the DATABASE_DB env var,
    db_schema: Optional[str] = None
    # Set the DATABASE_HOST env var,
    db_host: Optional[str] = None
    # Set the DATABASE_PORT env var,
    db_port: Optional[int] = None
    # Set the DATABASE_DIALECT env var,
    db_dialect: Optional[str] = None

    # Configure the container
    container_name: Optional[str] = None
    image_pull_policy: ImagePullPolicy = ImagePullPolicy.IF_NOT_PRESENT
    container_detach: bool = True
    container_auto_remove: bool = True
    container_remove: bool = True
    container_user: str = "root"

    # Add container labels
    container_labels: Optional[Dict[str, Any]] = None
    # NOTE: Available only for Docker
    # Add volumes to DockerContainer
    # container_volumes is a dictionary which adds the volumes to mount
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

    # Opens the hub port
    open_hub_port: bool = True
    # Port number on the container
    hub_port: int = 8081
    # Port name: Only used by the K8sContainer
    hub_port_name: str = "hub"
    # Host port: Only used by the DockerContainer
    hub_host_port: int = 8081

    # Open the app port if open_app_port=True
    open_app_port: bool = True
    # App port number on the container
    # Set the SUPERSET_PORT env var
    app_port: int = 8000
    # Only used by the K8sContainer
    app_port_name: str = "app"
    # Only used by the DockerContainer
    app_host_port: int = 8000

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

    # Configure the deployment
    deploy_name: Optional[str] = None
    pod_name: Optional[str] = None
    replicas: int = 1
    pod_node_selector: Optional[Dict[str, str]] = None
    restart_policy: RestartPolicy = RestartPolicy.ALWAYS
    termination_grace_period_seconds: Optional[int] = None
    # Add deployment labels
    deploy_labels: Optional[Dict[str, Any]] = None
    # Determine how to spread the deployment across a topology
    # Key to spread the pods across
    topology_spread_key: Optional[str] = None
    # The degree to which pods may be unevenly distributed
    topology_spread_max_skew: Optional[int] = None
    # How to deal with a pod if it doesn't satisfy the spread constraint.
    topology_spread_when_unsatisfiable: Optional[
        Literal["DoNotSchedule", "ScheduleAnyway"]
    ] = None

    # Configure the app service
    create_app_service: bool = True
    app_service_name: Optional[str] = None
    app_service_type: Optional[ServiceType] = None
    # The port that will be exposed by the service.
    app_service_port: int = 8000
    # The node_port that will be exposed by the service if app_service_type = ServiceType.NODE_PORT
    app_node_port: Optional[int] = None
    # The app_target_port is the port to access on the pods targeted by the service.
    # It can be the port number or port name on the pod.
    app_target_port: Optional[Union[str, int]] = None
    # Add labels to app service
    app_service_labels: Optional[Dict[str, Any]] = None

    # Configure rbac
    sa_name: Optional[str] = None
    cr_name: Optional[str] = None
    crb_name: Optional[str] = None

    print_env_on_load: bool = True
    extra_kwargs: Optional[Dict[str, Any]] = None


class JupyterHub(PhidataApp):
    def __init__(
        self,
        name: str = "jupyterhub",
        version: str = "1",
        enabled: bool = True,
        # Image args,
        image_name: str = "phidata/jupyterhub",
        image_tag: str = "2.3.1",
        entrypoint: Optional[Union[str, List]] = None,
        command: Union[str, List] = "jupyterhub",
        # Mount the workspace directory on the container,
        mount_workspace: bool = False,
        workspace_volume_name: Optional[str] = None,
        # Path to mount the workspace volume under,
        # This is the parent directory for the workspace on the container,
        # i.e. the ws is mounted as a subdir in this dir,
        # eg: if ws name is: idata, workspace_dir would be: /workspaces/idata,
        workspace_parent_container_path: str = "/mount",
        # NOTE: On DockerContainers the workspace_root_path is mounted to workspace_dir,
        # because we assume that DockerContainers are running locally on the user's machine,
        # On K8sContainers, we load the workspace_dir from git using a git-sync sidecar container,
        create_git_sync_sidecar: bool = False,
        git_sync_repo: Optional[str] = None,
        git_sync_branch: Optional[str] = None,
        git_sync_wait: int = 1,
        # But when running k8s locally, we can mount the workspace using,
        # host path as well.,
        k8s_mount_local_workspace: bool = False,
        # Jupyter resources directory relative to the workspace_root,
        # This dir is mounted to the `/usr/local/jupyter` directory on the container,
        mount_resources: bool = False,
        resources_dir: str = "workspace/jupyter",
        resources_dir_container_path: str = "/usr/local/jupyter",
        resources_volume_name: Optional[str] = None,
        # Path to JUPYTER_CONFIG_FILE relative to the workspace_root
        # Used to set the JUPYTER_CONFIG_FILE env var
        # This value is also appended to the command using `-f`
        jupyter_config_file: Optional[str] = None,
        # Install python dependencies using a requirements.txt file,
        # Sets the REQUIREMENTS_LOCAL & REQUIREMENTS_FILE_PATH env var to requirements_file,
        install_requirements: bool = False,
        # Path to the requirements.txt file relative to the workspace_root,
        requirements_file: str = "workspace/jupyter/requirements.txt",
        # Overwrite the PYTHONPATH env var, which is usually set,
        # to workspace_root_contaier_path:resources_dir_container_path,
        python_path: Optional[str] = None,
        # Configure Superset database,
        wait_for_db: bool = False,
        # Get database details using DbApp,
        db_app: Optional[DbApp] = None,
        # Provide database details,
        # Set the DATABASE_USER env var,
        db_user: Optional[str] = None,
        # Set the DATABASE_PASSWORD env var,
        db_password: Optional[str] = None,
        # Set the DATABASE_DB env var,
        db_schema: Optional[str] = None,
        # Set the DATABASE_HOST env var,
        db_host: Optional[str] = None,
        # Set the DATABASE_PORT env var,
        db_port: Optional[int] = None,
        # Set the DATABASE_DIALECT env var,
        db_dialect: Optional[str] = None,
        # Configure the container,
        container_name: Optional[str] = None,
        image_pull_policy: ImagePullPolicy = ImagePullPolicy.IF_NOT_PRESENT,
        container_detach: bool = True,
        container_auto_remove: bool = True,
        container_remove: bool = True,
        container_user: str = "root",
        # Add container labels,
        container_labels: Optional[Dict[str, Any]] = None,
        # NOTE: Available only for Docker,
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
        container_volumes: Optional[Dict[str, dict]] = None,
        # Open a container port if open_hub_port=True,
        open_hub_port: bool = True,
        # Port number on the container,
        hub_port: int = 8081,
        # Port name: Only used by the K8sContainer,
        hub_port_name: str = "hub",
        # Host port: Only used by the DockerContainer,
        hub_host_port: int = 8081,
        # Open the app port if open_app_port=True,
        open_app_port: bool = True,
        # App port number on the container,
        app_port: int = 8000,
        # Only used by the K8sContainer,
        app_port_name: str = "app",
        # Only used by the DockerContainer,
        app_host_port: int = 8000,
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
        # Configure the deployment,
        deploy_name: Optional[str] = None,
        pod_name: Optional[str] = None,
        replicas: int = 1,
        pod_node_selector: Optional[Dict[str, str]] = None,
        restart_policy: RestartPolicy = RestartPolicy.ALWAYS,
        termination_grace_period_seconds: Optional[int] = None,
        # Add deployment labels,
        deploy_labels: Optional[Dict[str, Any]] = None,
        # Determine how to spread the deployment across a topology,
        # Key to spread the pods across,
        topology_spread_key: Optional[str] = None,
        # The degree to which pods may be unevenly distributed,
        topology_spread_max_skew: Optional[int] = None,
        # How to deal with a pod if it doesn't satisfy the spread constraint.,
        topology_spread_when_unsatisfiable: Optional[
            Literal["DoNotSchedule", "ScheduleAnyway"]
        ] = None,
        # Configure the app service,
        create_app_service: bool = True,
        app_service_name: Optional[str] = None,
        app_service_type: Optional[ServiceType] = None,
        # The port that will be exposed by the service.,
        app_service_port: int = 8000,
        # The node_port that will be exposed by the service if app_service_type = ServiceType.NODE_PORT,
        app_node_port: Optional[int] = None,
        # The app_target_port is the port to access on the pods targeted by the service.,
        # It can be the port number or port name on the pod.,
        app_target_port: Optional[Union[str, int]] = None,
        # Add labels to app service,
        app_service_labels: Optional[Dict[str, Any]] = None,
        # Configure rbac
        sa_name: Optional[str] = None,
        cr_name: Optional[str] = None,
        crb_name: Optional[str] = None,
        print_env_on_load: bool = True,
        # If True, use cached resources
        # i.e. skip resource creation/deletion if active resources with the same name exist.
        use_cache: bool = True,
        **extra_kwargs,
    ):
        super().__init__()
        try:
            self.args: JupyterHubArgs = JupyterHubArgs(
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
                mount_resources=mount_resources,
                resources_dir=resources_dir,
                resources_dir_container_path=resources_dir_container_path,
                resources_volume_name=resources_volume_name,
                jupyter_config_file=jupyter_config_file,
                install_requirements=install_requirements,
                requirements_file=requirements_file,
                python_path=python_path,
                wait_for_db=wait_for_db,
                db_app=db_app,
                db_user=db_user,
                db_password=db_password,
                db_schema=db_schema,
                db_host=db_host,
                db_port=db_port,
                db_dialect=db_dialect,
                container_name=container_name,
                image_pull_policy=image_pull_policy,
                container_detach=container_detach,
                container_auto_remove=container_auto_remove,
                container_remove=container_remove,
                container_user=container_user,
                container_labels=container_labels,
                container_volumes=container_volumes,
                open_hub_port=open_hub_port,
                hub_port=hub_port,
                hub_port_name=hub_port_name,
                hub_host_port=hub_host_port,
                open_app_port=open_app_port,
                app_port=app_port,
                app_port_name=app_port_name,
                app_host_port=app_host_port,
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
                topology_spread_key=topology_spread_key,
                topology_spread_max_skew=topology_spread_max_skew,
                topology_spread_when_unsatisfiable=topology_spread_when_unsatisfiable,
                create_app_service=create_app_service,
                app_service_name=app_service_name,
                app_service_type=app_service_type,
                app_service_port=app_service_port,
                app_node_port=app_node_port,
                app_target_port=app_target_port,
                app_service_labels=app_service_labels,
                sa_name=sa_name,
                cr_name=cr_name,
                crb_name=crb_name,
                print_env_on_load=print_env_on_load,
                use_cache=use_cache,
                extra_kwargs=extra_kwargs,
            )
        except Exception as e:
            logger.error(f"Args for {self.__class__.__name__} are not valid")
            raise

    def get_container_name(self) -> str:
        return self.args.container_name or get_default_container_name(self.args.name)

    def get_app_service_name(self) -> str:
        return self.args.app_service_name or get_default_service_name(self.args.name)

    def get_app_service_port(self) -> int:
        return self.args.app_service_port

    def get_env_data_from_file(self) -> Optional[Dict[str, str]]:
        return self.read_yaml_file(file_path=self.args.env_file)

    def get_secret_data_from_file(self) -> Optional[Dict[str, str]]:
        return self.read_yaml_file(file_path=self.args.secrets_file)

    ######################################################
    ## Docker Resources
    ######################################################

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
            self.args.requirements_file
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
        python_path = (
            self.args.python_path
            or f"{str(workspace_root_container_path)}:{self.args.resources_dir_container_path}"
        )

        # Container Environment
        container_env: Dict[str, str] = {
            # Env variables used by data workflows and data assets
            "PHI_WORKSPACE_PARENT": str(self.args.workspace_parent_container_path),
            "PHI_WORKSPACE_ROOT": str(workspace_root_container_path),
            "PYTHONPATH": python_path,
            PHIDATA_RUNTIME_ENV_VAR: "docker",
            SCRIPTS_DIR_ENV_VAR: str(scripts_dir_container_path),
            STORAGE_DIR_ENV_VAR: str(storage_dir_container_path),
            META_DIR_ENV_VAR: str(meta_dir_container_path),
            PRODUCTS_DIR_ENV_VAR: str(products_dir_container_path),
            NOTEBOOKS_DIR_ENV_VAR: str(notebooks_dir_container_path),
            WORKSPACE_CONFIG_DIR_ENV_VAR: str(workspace_config_dir_container_path),
            "INSTALL_REQUIREMENTS": str(self.args.install_requirements),
            "REQUIREMENTS_FILE_PATH": str(requirements_file_container_path),
            # Print env when the container starts
            "PRINT_ENV_ON_LOAD": str(self.args.print_env_on_load),
        }

        # Set airflow env vars
        self.set_aws_env_vars(env_dict=container_env)

        # Update the container env using env_file
        env_data_from_file = self.get_env_data_from_file()
        if env_data_from_file is not None:
            container_env.update(env_data_from_file)

        # Update the container env using secrets_file
        secret_data_from_file = self.get_secret_data_from_file()
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
        # Create a volume for the resources
        if self.args.mount_resources:
            resources_dir_path = str(
                self.workspace_root_path.joinpath(self.args.resources_dir)
            )
            logger.debug(f"Mounting: {resources_dir_path}")
            logger.debug(f"\tto: {self.args.resources_dir_container_path}")
            container_volumes[resources_dir_path] = {
                "bind": self.args.resources_dir_container_path,
                "mode": "ro",
            }

        # Container Ports
        # container_ports is a dictionary which configures the ports to bind
        # inside the container. The key is the port to bind inside the container
        #   either as an integer or a string in the form port/protocol
        # and the value is the corresponding port to open on the host.
        # For example:
        #   {'2222/tcp': 3333} will expose port 2222 inside the container as port 3333 on the host.
        container_ports: Dict[str, int] = {}

        # if open_hub_port = True
        if self.args.open_hub_port:
            container_ports[str(self.args.hub_port)] = self.args.hub_host_port

        # if open_app_port = True
        # 1. Set the app_port in the container env
        # 2. Open the app_port
        if self.args.open_app_port:
            # Open the port
            container_ports[str(self.args.app_port)] = self.args.app_host_port

        container_cmd: List[str] = []
        if isinstance(self.args.command, str):
            container_cmd = [self.args.command]
        else:
            container_cmd = self.args.command
        if self.args.jupyter_config_file is not None:
            config_file_container_path_str = str(
                workspace_root_container_path.joinpath(self.args.jupyter_config_file)
            )
            if config_file_container_path_str is not None:
                container_env["JUPYTER_CONFIG_FILE"] = config_file_container_path_str
                container_cmd.extend(["-f", config_file_container_path_str])

        # Create the container
        docker_container = DockerContainer(
            name=self.get_container_name(),
            image=get_image_str(self.args.image_name, self.args.image_tag),
            entrypoint=self.args.entrypoint,
            command=" ".join(container_cmd),
            detach=self.args.container_detach,
            auto_remove=self.args.container_auto_remove,
            remove=self.args.container_remove,
            user=self.args.container_user,
            stdin_open=True,
            tty=True,
            labels=self.args.container_labels,
            environment=container_env,
            network=docker_build_context.network,
            ports=container_ports if len(container_ports) > 0 else None,
            volumes=container_volumes,
            use_cache=self.args.use_cache,
        )
        # logger.debug(f"Container Env: {docker_container.environment}")

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

    def get_k8s_rg(
        self, k8s_build_context: K8sBuildContext
    ) -> Optional[K8sResourceGroup]:

        app_name = self.args.name
        logger.debug(f"Building {app_name} K8sResourceGroup")

        # Define RBAC resources first
        sa = CreateServiceAccount(
            sa_name=self.args.sa_name or get_default_sa_name(app_name),
            app_name=app_name,
            namespace=k8s_build_context.namespace,
        )

        cr = CreateClusterRole(
            cr_name=self.args.cr_name or get_default_cr_name(app_name),
            rules=[
                PolicyRule(
                    api_groups=[""],
                    resources=[
                        "pods",
                        "secrets",
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
        )

        crb = CreateClusterRoleBinding(
            crb_name=get_default_crb_name(app_name),
            cr_name=cr.cr_name,
            service_account_name=sa.sa_name,
            app_name=app_name,
            namespace=k8s_build_context.namespace,
        )

        # Define K8s resources
        config_maps: List[CreateConfigMap] = []
        secrets: List[CreateSecret] = []
        volumes: List[CreateVolume] = []
        containers: List[CreateContainer] = []
        services: List[CreateService] = []
        ports: List[CreatePort] = []

        # Workspace paths
        if self.workspace_root_path is None:
            logger.error("Invalid workspace_root_path")
            return None
        workspace_name = self.workspace_root_path.stem
        workspace_root_container_path = Path(
            self.args.workspace_parent_container_path
        ).joinpath(workspace_name)
        requirements_file_container_path = workspace_root_container_path.joinpath(
            self.args.requirements_file
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
        python_path = (
            self.args.python_path
            or f"{str(workspace_root_container_path)}:{self.args.resources_dir_container_path}"
        )

        # Container Environment
        container_env: Dict[str, str] = {
            # Env variables used by data workflows and data assets
            "PHI_WORKSPACE_PARENT": str(self.args.workspace_parent_container_path),
            "PHI_WORKSPACE_ROOT": str(workspace_root_container_path),
            "PYTHONPATH": python_path,
            PHIDATA_RUNTIME_ENV_VAR: "kubernetes",
            SCRIPTS_DIR_ENV_VAR: str(scripts_dir_container_path),
            STORAGE_DIR_ENV_VAR: str(storage_dir_container_path),
            META_DIR_ENV_VAR: str(meta_dir_container_path),
            PRODUCTS_DIR_ENV_VAR: str(products_dir_container_path),
            NOTEBOOKS_DIR_ENV_VAR: str(notebooks_dir_container_path),
            WORKSPACE_CONFIG_DIR_ENV_VAR: str(workspace_config_dir_container_path),
            "INSTALL_REQUIREMENTS": str(self.args.install_requirements),
            "REQUIREMENTS_FILE_PATH": str(requirements_file_container_path),
            # Print env when the container starts
            "PRINT_ENV_ON_LOAD": str(self.args.print_env_on_load),
            "WAIT_FOR_DB": str(self.args.wait_for_db),
            "JH_SVC_NAME": self.get_app_service_name(),
        }

        # Set airflow env vars
        self.set_aws_env_vars(env_dict=container_env)

        # Superset db connection
        db_user = self.args.db_user
        db_password = self.args.db_password
        db_schema = self.args.db_schema
        db_host = self.args.db_host
        db_port = self.args.db_port
        db_dialect = self.args.db_dialect
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
                db_port = self.args.db_app.get_db_port_k8s()
            if db_dialect is None:
                db_dialect = self.args.db_app.get_db_driver()
        db_connection_url = (
            f"{db_dialect}://{db_user}:{db_password}@{db_host}:{db_port}/{db_schema}"
        )

        if db_user is not None:
            container_env["DATABASE_USER"] = db_user
        if db_password is not None:
            container_env["DATABASE_PASSWORD"] = db_password
        if db_schema is not None:
            container_env["DATABASE_DB"] = db_schema
        if db_host is not None:
            container_env["DATABASE_HOST"] = db_host
        if db_port is not None:
            container_env["DATABASE_PORT"] = str(db_port)
        if db_dialect is not None:
            container_env["DATABASE_DIALECT"] = db_dialect
        if "None" not in db_connection_url:
            container_env["JH_DATABASE_URL"] = db_connection_url

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
        # logger.debug(f"ConfigMap {container_env_cm.cm_name}: {container_env_cm.json(indent=2)}")
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
            workspace_volume_name = (
                self.args.workspace_volume_name or get_default_volume_name(app_name)
            )

            if self.args.k8s_mount_local_workspace:
                workspace_root_path_str = str(self.workspace_root_path)
                workspace_root_container_path_str = str(workspace_root_container_path)
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

            elif self.args.create_git_sync_sidecar:
                workspace_parent_container_path_str = str(
                    self.args.workspace_parent_container_path
                )
                logger.debug(f"Creating EmptyDir")
                logger.debug(f"\tat: {workspace_parent_container_path_str}")
                workspace_volume = CreateVolume(
                    volume_name=workspace_volume_name,
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

        # Create the ports to open
        # if open_hub_port = True
        if self.args.open_hub_port:
            hub_port = CreatePort(
                name=self.args.hub_port_name,
                container_port=self.args.hub_port,
                service_port=self.args.hub_port,
            )
            ports.append(hub_port)

        # if open_app_port = True
        # 1. Set the app_port in the container env
        # 2. Open the jupyter app port
        app_port: Optional[CreatePort] = None
        if self.args.open_app_port:
            # Open the port
            app_port = CreatePort(
                name=self.args.app_port_name,
                container_port=self.args.app_port,
                service_port=self.get_app_service_port(),
                node_port=self.args.app_node_port,
                target_port=self.args.app_target_port or self.args.app_port_name,
            )
            ports.append(app_port)

        container_labels: Optional[Dict[str, Any]] = self.args.container_labels
        if k8s_build_context.labels is not None:
            if container_labels:
                container_labels.update(k8s_build_context.labels)
            else:
                container_labels = k8s_build_context.labels

        # Equivalent to docker images CMD
        container_args: List[str] = []
        if isinstance(self.args.command, str):
            container_args = [self.args.command]
        else:
            container_args = self.args.command
        if self.args.jupyter_config_file is not None:
            config_file_container_path_str = str(
                workspace_root_container_path.joinpath(self.args.jupyter_config_file)
            )
            if config_file_container_path_str is not None:
                if container_env_cm.data is not None:
                    container_env_cm.data[
                        "JUPYTER_CONFIG_FILE"
                    ] = config_file_container_path_str
                container_args.extend(["-f", config_file_container_path_str])

        # Create the container
        k8s_container = CreateContainer(
            container_name=self.get_container_name(),
            app_name=app_name,
            image_name=self.args.image_name,
            image_tag=self.args.image_tag,
            args=container_args,
            # Equivalent to docker images ENTRYPOINT
            command=[self.args.entrypoint]
            if isinstance(self.args.entrypoint, str)
            else self.args.entrypoint,
            image_pull_policy=self.args.image_pull_policy,
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
            replicas=self.args.replicas,
            deploy_name=self.args.deploy_name or get_default_deploy_name(app_name),
            pod_name=self.args.pod_name or get_default_pod_name(app_name),
            app_name=app_name,
            namespace=k8s_build_context.namespace,
            service_account_name=sa.sa_name,
            containers=containers if len(containers) > 0 else None,
            pod_node_selector=self.args.pod_node_selector,
            restart_policy=self.args.restart_policy,
            termination_grace_period_seconds=self.args.termination_grace_period_seconds,
            volumes=volumes if len(volumes) > 0 else None,
            labels=deploy_labels,
            pod_annotations=pod_annotations,
            topology_spread_key=self.args.topology_spread_key,
            topology_spread_max_skew=self.args.topology_spread_max_skew,
            topology_spread_when_unsatisfiable=self.args.topology_spread_when_unsatisfiable,
        )

        # Create the services
        if self.args.create_app_service:
            app_service_labels: Optional[Dict[str, Any]] = self.args.app_service_labels
            if k8s_build_context.labels is not None:
                if app_service_labels:
                    app_service_labels.update(k8s_build_context.labels)
                else:
                    app_service_labels = k8s_build_context.labels
            app_service = CreateService(
                service_name=self.get_app_service_name(),
                app_name=app_name,
                namespace=k8s_build_context.namespace,
                service_account_name=sa.sa_name,
                service_type=self.args.app_service_type,
                deployment=k8s_deployment,
                ports=ports if len(ports) > 0 else None,
                labels=app_service_labels,
            )
            services.append(app_service)

        # Create the K8sResourceGroup
        k8s_resource_group = CreateK8sResourceGroup(
            name=app_name,
            enabled=self.args.enabled,
            sa=sa,
            cr=cr,
            crb=crb,
            config_maps=config_maps if len(config_maps) > 0 else None,
            secrets=secrets if len(secrets) > 0 else None,
            services=services if len(services) > 0 else None,
            deployments=[k8s_deployment],
        )

        return k8s_resource_group.create()

    def init_k8s_resource_groups(self, k8s_build_context: K8sBuildContext) -> None:
        k8s_rg = self.get_k8s_rg(k8s_build_context)
        if k8s_rg is not None:
            if self.k8s_resource_groups is None:
                self.k8s_resource_groups = OrderedDict()
            self.k8s_resource_groups[k8s_rg.name] = k8s_rg
