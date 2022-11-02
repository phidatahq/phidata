from pathlib import Path
from typing import Optional, Dict, Any, Union, List, Tuple

from phidata.base import PhidataBase, PhidataBaseArgs
from phidata.utils.enums import ExtendedEnum
from phidata.utils.log import logger


class WorkspaceVolumeType(ExtendedEnum):
    HostPath = "HostPath"
    EmptyDir = "EmptyDir"
    # PersistentVolume = "PersistentVolume"
    AwsEbs = "AwsEbs"
    # AwsEfs = "AwsEfs"


class PhidataAppArgs(PhidataBaseArgs):
    name: str

    # -*- Path parameters
    # The following args are populated by the K8sWorker and DockerWorker classes.
    # The build_resource_groups() function passes these args from the
    # WorkspaceConfig -> K8sConfig -> K8sArgs -> PhidataApp

    # Path to the workspace root directory
    workspace_root_path: Optional[Path] = None
    # Path to the workspace config file
    workspace_config_file_path: Optional[Path] = None
    # Path to important directories relative to the workspace_root
    # These directories are joined to the workspace_root dir
    #   to build paths depending on the environments (local, docker, k8s)
    # defaults are set by WorkspaceConfig.__init__()
    scripts_dir: Optional[str] = None
    storage_dir: Optional[str] = None
    meta_dir: Optional[str] = None
    products_dir: Optional[str] = None
    notebooks_dir: Optional[str] = None
    workflows_dir: Optional[str] = None
    workspace_config_dir: Optional[str] = None

    # -*- Common environment variables from the WorkspaceConfig
    # Env vars added to docker env when building PhidataApps
    #   and running workflows
    docker_env: Optional[Dict[str, str]] = None
    # Env vars added to k8s env when building PhidataApps
    #   and running workflows
    k8s_env: Optional[Dict[str, str]] = None

    # -*- Image Configuration
    image_name: Optional[str] = None
    image_tag: Optional[str] = None
    entrypoint: Optional[Union[str, List]] = None
    command: Optional[Union[str, List]] = None

    # Install python dependencies using a requirements.txt file
    install_requirements: bool = False
    # Path to the requirements.txt file relative to the workspace_root
    requirements_file: str = "requirements.txt"

    # -*- Container Configuration
    # Each PhidataApp has 1 main container and multiple sidecar containers
    # The main container name
    container_name: Optional[str] = None
    # Overwrite the PYTHONPATH env var
    # which is usually set to the workspace_root_container_path
    python_path: Optional[str] = None
    # Add labels to the container
    container_labels: Optional[Dict[str, Any]] = None

    # Container env passed to the PhidataApp
    # Add env variables to container env
    env: Optional[Dict[str, str]] = None
    # Read env variables from a file in yaml format
    env_file: Optional[Path] = None

    # Container secrets
    # Add secret variables to container env
    secrets: Optional[Dict[str, str]] = None
    # Read secret variables from a file in yaml format
    secrets_file: Optional[Path] = None
    # Read secret variables from AWS Secrets
    aws_secrets: Optional[Any] = None

    # Container ports
    # Open a container port if open_container_port=True
    open_container_port: bool = False
    # Port number on the container
    container_port: int = 8000
    # Port name: Only used by the K8sContainer
    container_port_name: str = "http"
    # Host port: Only used by the DockerContainer
    container_host_port: int = 8000

    # Container volumes
    # Mount the workspace directory on the container
    mount_workspace: bool = False
    workspace_volume_name: Optional[str] = None
    workspace_volume_type: Optional[WorkspaceVolumeType] = None
    # Path to mount the workspace volume
    # This is the parent directory for the workspace on the container
    # i.e. the ws is mounted as a subdir in this dir
    # eg: if ws name is: idata, workspace_root would be: /mnt/workspaces/idata
    workspace_volume_container_path: str = "/mnt/workspaces"
    # How to mount the workspace volume
    # Option 1: Mount the workspace from the host machine
    # If None, use the workspace_root_path
    # Note: This is the default on DockerContainers. We assume that DockerContainers
    # are running locally on the user's machine so the local workspace_root_path
    # is mounted to the workspace_volume_container_path
    workspace_volume_host_path: Optional[str] = None
    # Option 2: Load the workspace from git using a git-sync sidecar container
    # This the default on K8sContainers.
    create_git_sync_sidecar: bool = False
    # Required to create an initial copy of the workspace
    create_git_sync_init_container: bool = True
    git_sync_image_name: str = "k8s.gcr.io/git-sync"
    git_sync_image_tag: str = "v3.1.1"
    git_sync_repo: Optional[str] = None
    git_sync_branch: Optional[str] = None
    git_sync_wait: int = 1

    # -*- Docker configuration
    # Run container in the background and return a Container object.
    container_detach: bool = True
    # Enable auto-removal of the container on daemon side when the container’s process exits.
    container_auto_remove: bool = True
    # Remove the container when it has finished running. Default: True.
    container_remove: bool = True
    # Username or UID to run commands as inside the container.
    container_user: Optional[Union[str, int]] = None
    # Keep STDIN open even if not attached.
    container_stdin_open: bool = True
    container_tty: bool = True
    # Specify a test to perform to check that the container is healthy.
    container_healthcheck: Optional[Dict[str, Any]] = None
    # Optional hostname for the container.
    container_hostname: Optional[str] = None
    # Platform in the format os[/arch[/variant]].
    container_platform: Optional[str] = None
    # Path to the working directory.
    container_working_dir: Optional[str] = None
    # Restart the container when it exits. Configured as a dictionary with keys:
    # Name: One of on-failure, or always.
    # MaximumRetryCount: Number of times to restart the container on failure.
    # For example: {"Name": "on-failure", "MaximumRetryCount": 5}
    container_restart_policy_docker: Optional[Dict[str, Any]] = None
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
    container_volumes_docker: Optional[Dict[str, dict]] = None
    # Add ports to DockerContainer
    # The keys of the dictionary are the ports to bind inside the container,
    # either as an integer or a string in the form port/protocol, where the protocol is either tcp, udp.
    # The values of the dictionary are the corresponding ports to open on the host, which can be either:
    #   - The port number, as an integer.
    #       For example, {'2222/tcp': 3333} will expose port 2222 inside the container as port 3333 on the host.
    #   - None, to assign a random host port. For example, {'2222/tcp': None}.
    #   - A tuple of (address, port) if you want to specify the host interface.
    #       For example, {'1111/tcp': ('127.0.0.1', 1111)}.
    #   - A list of integers, if you want to bind multiple host ports to a single container port.
    #       For example, {'1111/tcp': [1234, 4567]}.
    container_ports_docker: Optional[Dict[str, Any]] = None

    # -*- K8s configuration
    # K8s Deployment configuration
    replicas: int = 1
    pod_name: Optional[str] = None
    deploy_name: Optional[str] = None
    secret_name: Optional[str] = None
    configmap_name: Optional[str] = None
    # Type: ImagePullPolicy
    image_pull_policy: Optional[Any] = None
    pod_annotations: Optional[Dict[str, str]] = None
    pod_node_selector: Optional[Dict[str, str]] = None
    # Type: RestartPolicy
    deploy_restart_policy: Optional[Any] = None
    deploy_labels: Optional[Dict[str, Any]] = None
    termination_grace_period_seconds: Optional[int] = None
    # How to spread the deployment across a topology
    # Key to spread the pods across
    topology_spread_key: Optional[str] = None
    # The degree to which pods may be unevenly distributed
    topology_spread_max_skew: Optional[int] = None
    # How to deal with a pod if it doesn't satisfy the spread constraint.
    topology_spread_when_unsatisfiable: Optional[str] = None

    # K8s Service Configuration
    create_service: bool = False
    service_name: Optional[str] = None
    # Type: ServiceType
    service_type: Optional[Any] = None
    # The port exposed by the service.
    service_port: int = 8000
    # The node_port exposed by the service if service_type = ServiceType.NODE_PORT
    service_node_port: Optional[int] = None
    # The target_port is the port to access on the pods targeted by the service.
    # It can be the port number or port name on the pod.
    service_target_port: Optional[Union[str, int]] = None
    # Extra ports exposed by the webserver service. Type: List[CreatePort]
    service_ports: Optional[List[Any]] = None
    # Service labels
    service_labels: Optional[Dict[str, Any]] = None
    # Service annotations
    service_annotations: Optional[Dict[str, str]] = None
    # If ServiceType == ServiceType.LoadBalancer
    service_health_check_node_port: Optional[int] = None
    service_internal_traffic_policy: Optional[str] = None
    service_load_balancer_class: Optional[str] = None
    service_load_balancer_ip: Optional[str] = None
    service_load_balancer_source_ranges: Optional[List[str]] = None
    service_allocate_load_balancer_node_ports: Optional[bool] = None

    # K8s RBAC Configuration
    use_rbac: bool = False
    # Create a Namespace with name ns_name & default values
    ns_name: Optional[str] = None
    # or Provide the full Namespace definition
    # Type: CreateNamespace
    namespace: Optional[Any] = None
    # Create a ServiceAccount with name sa_name & default values
    sa_name: Optional[str] = None
    # or Provide the full ServiceAccount definition
    # Type: CreateServiceAccount
    service_account: Optional[Any] = None
    # Create a ClusterRole with name cr_name & default values
    cr_name: Optional[str] = None
    # or Provide the full ClusterRole definition
    # Type: CreateClusterRole
    cluster_role: Optional[Any] = None
    # Create a ClusterRoleBinding with name crb_name & default values
    crb_name: Optional[str] = None
    # or Provide the full ClusterRoleBinding definition
    # Type: CreateClusterRoleBinding
    cluster_role_binding: Optional[Any] = None

    # Add additional Kubernetes resources to the App
    # Type: CreateSecret
    extra_secrets: Optional[List[Any]] = None
    # Type: CreateConfigMap
    extra_configmaps: Optional[List[Any]] = None
    # Type: CreateService
    extra_services: Optional[List[Any]] = None
    # Type: CreateDeployment
    extra_deployments: Optional[List[Any]] = None
    # Type: CreatePersistentVolume
    extra_pvs: Optional[List[Any]] = None
    # Type: CreatePVC
    extra_pvcs: Optional[List[Any]] = None
    # Type: CreateContainer
    extra_containers: Optional[List[Any]] = None
    # Type: CreateContainer
    extra_init_containers: Optional[List[Any]] = None
    # Type: CreatePort
    extra_ports: Optional[List[Any]] = None
    # Type: CreateVolume
    extra_volumes: Optional[List[Any]] = None
    # Type: CreateStorageClass
    extra_storage_classes: Optional[List[Any]] = None
    # Type: CreateCustomObject
    extra_custom_objects: Optional[List[Any]] = None
    # Type: CreateCustomResourceDefinition
    extra_crds: Optional[List[Any]] = None

    # Other args
    print_env_on_load: bool = True
    # If True, skip resource creation if active resources with the same name exist.
    use_cache: bool = True

    # Extra kwargs used to ensure older versions of phidata don't throw syntax errors
    extra_kwargs: Optional[Dict[str, Any]] = None

    # -*- AWS parameters
    # Common aws params used by apps, resources and data assets
    aws_region: Optional[str] = None
    aws_profile: Optional[str] = None
    aws_config_file: Optional[str] = None
    aws_shared_credentials_file: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True


class PhidataApp(PhidataBase):
    """Base Class for all PhidataApps"""

    def __init__(self) -> None:
        super().__init__()

        # Cache env_data & secret_data
        self.env_data: Optional[Dict[str, Any]] = None
        self.secret_data: Optional[Dict[str, Any]] = None

        # Args for the PhidataApp, provided by the subclass
        self.args: PhidataAppArgs

        # Dict of DockerResourceGroups
        # Type: Optional[Dict[str, DockerResourceGroup]]
        self.docker_resource_groups: Optional[Dict[str, Any]] = None

        # Dict of KubernetesResourceGroups
        # Type: Optional[Dict[str, K8sResourceGroup]]
        self.k8s_resource_groups: Optional[Dict[str, Any]] = None

    @property
    def workspace_root_path(self) -> Optional[Path]:
        return self.args.workspace_root_path if self.args else None

    @workspace_root_path.setter
    def workspace_root_path(self, workspace_root_path: Path) -> None:
        if self.args is not None and workspace_root_path is not None:
            self.args.workspace_root_path = workspace_root_path

    @property
    def workspace_config_file_path(self) -> Optional[Path]:
        return self.args.workspace_config_file_path if self.args else None

    @workspace_config_file_path.setter
    def workspace_config_file_path(self, workspace_config_file_path: Path) -> None:
        if self.args is not None and workspace_config_file_path is not None:
            self.args.workspace_config_file_path = workspace_config_file_path

    @property
    def scripts_dir(self) -> Optional[str]:
        return self.args.scripts_dir if self.args else None

    @scripts_dir.setter
    def scripts_dir(self, scripts_dir: str) -> None:
        if self.args is not None and scripts_dir is not None:
            self.args.scripts_dir = scripts_dir

    @property
    def storage_dir(self) -> Optional[str]:
        return self.args.storage_dir if self.args else None

    @storage_dir.setter
    def storage_dir(self, storage_dir: str) -> None:
        if self.args is not None and storage_dir is not None:
            self.args.storage_dir = storage_dir

    @property
    def meta_dir(self) -> Optional[str]:
        return self.args.meta_dir if self.args else None

    @meta_dir.setter
    def meta_dir(self, meta_dir: str) -> None:
        if self.args is not None and meta_dir is not None:
            self.args.meta_dir = meta_dir

    @property
    def products_dir(self) -> Optional[str]:
        return self.args.products_dir if self.args else None

    @products_dir.setter
    def products_dir(self, products_dir: str) -> None:
        if self.args is not None and products_dir is not None:
            self.args.products_dir = products_dir

    @property
    def notebooks_dir(self) -> Optional[str]:
        return self.args.notebooks_dir if self.args else None

    @notebooks_dir.setter
    def notebooks_dir(self, notebooks_dir: str) -> None:
        if self.args is not None and notebooks_dir is not None:
            self.args.notebooks_dir = notebooks_dir

    @property
    def workflows_dir(self) -> Optional[str]:
        return self.args.workflows_dir if self.args else None

    @workflows_dir.setter
    def workflows_dir(self, workflows_dir: str) -> None:
        if self.args is not None and workflows_dir is not None:
            self.args.workflows_dir = workflows_dir

    @property
    def workspace_config_dir(self) -> Optional[str]:
        return self.args.workspace_config_dir if self.args else None

    @workspace_config_dir.setter
    def workspace_config_dir(self, workspace_config_dir: str) -> None:
        if self.args is not None and workspace_config_dir is not None:
            self.args.workspace_config_dir = workspace_config_dir

    @property
    def docker_env(self) -> Optional[Dict[str, str]]:
        return self.args.docker_env if self.args else None

    @docker_env.setter
    def docker_env(self, docker_env: Dict[str, str]) -> None:
        if self.args is not None and docker_env is not None:
            self.args.docker_env = docker_env

    @property
    def k8s_env(self) -> Optional[Dict[str, str]]:
        return self.args.k8s_env if self.args else None

    @k8s_env.setter
    def k8s_env(self, k8s_env: Dict[str, str]) -> None:
        if self.args is not None and k8s_env is not None:
            self.args.k8s_env = k8s_env

    @property
    def aws_region(self) -> Optional[str]:
        return self.args.aws_region if self.args else None

    @aws_region.setter
    def aws_region(self, aws_region: str) -> None:
        if self.args is not None and aws_region is not None:
            self.args.aws_region = aws_region

    @property
    def aws_profile(self) -> Optional[str]:
        return self.args.aws_profile if self.args else None

    @aws_profile.setter
    def aws_profile(self, aws_profile: str) -> None:
        if self.args is not None and aws_profile is not None:
            self.args.aws_profile = aws_profile

    @property
    def aws_config_file(self) -> Optional[str]:
        return self.args.aws_config_file if self.args else None

    @aws_config_file.setter
    def aws_config_file(self, aws_config_file: str) -> None:
        if self.args is not None and aws_config_file is not None:
            self.args.aws_config_file = aws_config_file

    @property
    def aws_shared_credentials_file(self) -> Optional[str]:
        return self.args.aws_shared_credentials_file if self.args else None

    @aws_shared_credentials_file.setter
    def aws_shared_credentials_file(self, aws_shared_credentials_file: str) -> None:
        if self.args is not None and aws_shared_credentials_file is not None:
            self.args.aws_shared_credentials_file = aws_shared_credentials_file

    ######################################################
    ## Get App Attributes
    ######################################################

    def get_image_str(self):
        return f"{self.args.image_name}:{self.args.image_tag}"

    def get_container_name(self) -> str:
        from phidata.utils.common import get_default_container_name

        return self.args.container_name or get_default_container_name(self.args.name)

    def get_container_port(self) -> int:
        return self.args.container_port

    def get_container_host_port(self) -> int:
        return self.args.container_host_port

    def get_pod_name(self) -> str:
        from phidata.utils.common import get_default_pod_name

        return self.args.pod_name or get_default_pod_name(self.args.name)

    def get_deploy_name(self) -> str:
        from phidata.utils.common import get_default_deploy_name

        return self.args.deploy_name or get_default_deploy_name(self.args.name)

    def get_secret_name(self) -> str:
        from phidata.utils.common import get_default_secret_name

        return self.args.secret_name or get_default_secret_name(self.args.name)

    def get_configmap_name(self) -> str:
        from phidata.utils.common import get_default_configmap_name

        return self.args.configmap_name or get_default_configmap_name(self.args.name)

    def get_service_name(self) -> str:
        from phidata.utils.common import get_default_service_name

        return self.args.service_name or get_default_service_name(self.args.name)

    def get_service_port(self) -> int:
        return self.args.service_port

    def get_sa_name(self) -> str:
        from phidata.utils.common import get_default_sa_name

        return self.args.sa_name or get_default_sa_name(self.args.name)

    def get_cr_name(self) -> str:
        from phidata.utils.common import get_default_cr_name

        return self.args.cr_name or get_default_cr_name(self.args.name)

    def get_crb_name(self) -> str:
        from phidata.utils.common import get_default_crb_name

        return self.args.crb_name or get_default_crb_name(self.args.name)

    def get_env_data(self) -> Optional[Dict[str, str]]:
        if self.env_data is None:
            self.env_data = self.read_yaml_file(file_path=self.args.env_file)
        return self.env_data

    def get_secret_data(self) -> Optional[Dict[str, str]]:
        if self.secret_data is None:
            self.secret_data = self.read_yaml_file(file_path=self.args.secrets_file)
        return self.secret_data

    ######################################################
    ## Docker functions
    ######################################################

    def init_docker_resource_groups(self, docker_build_context: Any) -> None:
        logger.debug(
            f"@init_docker_resource_groups not defined for {self.__class__.__name__}"
        )

    def get_docker_resource_groups(
        self, docker_build_context: Any
    ) -> Optional[Dict[str, Any]]:
        if self.docker_resource_groups is None:
            self.init_docker_resource_groups(docker_build_context)
        # # Comment out in production
        # if self.docker_resource_groups:
        #     logger.debug("DockerResourceGroups:")
        #     for rg_name, rg in self.docker_resource_groups.items():
        #         logger.debug(
        #             "{}: {}".format(rg_name, rg.json(exclude_none=True, indent=2))
        #         )
        return self.docker_resource_groups

    ######################################################
    ## K8s functions
    ######################################################

    def init_k8s_resource_groups(self, k8s_build_context: Any) -> None:
        logger.debug(
            f"@init_docker_resource_groups not defined for {self.__class__.__name__}"
        )

    def get_k8s_resource_groups(
        self, k8s_build_context: Any
    ) -> Optional[Dict[str, Any]]:
        if self.k8s_resource_groups is None:
            self.init_k8s_resource_groups(k8s_build_context)
        # # Comment out in production
        # if self.k8s_resource_groups:
        #     logger.debug("K8sResourceGroups:")
        #     for rg_name, rg in self.k8s_resource_groups.items():
        #         logger.debug(
        #             "{}:{}\n{}".format(rg_name, type(rg), rg)
        #         )
        return self.k8s_resource_groups

    ######################################################
    ## Helpers
    ######################################################

    def get_container_paths(self) -> Optional[Any]:
        if self.workspace_root_path is None:
            return None

        workspace_name = self.workspace_root_path.stem
        if workspace_name is None:
            return None

        workspace_volume_container_path: str = self.args.workspace_volume_container_path
        if workspace_volume_container_path is None:
            return None

        from phidata.types.context import ContainerPathContext

        workspace_root_container_path = (
            f"{workspace_volume_container_path}/{workspace_name}"
        )
        container_paths = ContainerPathContext(
            workspace_name=workspace_name,
            workspace_root=workspace_root_container_path,
            workspace_parent=workspace_volume_container_path,
        )

        if self.args.scripts_dir is not None:
            container_paths.scripts_dir = (
                f"{workspace_root_container_path}/{self.args.scripts_dir}"
            )

        if self.args.storage_dir is not None:
            container_paths.storage_dir = (
                f"{workspace_root_container_path}/{self.args.storage_dir}"
            )

        if self.args.meta_dir is not None:
            container_paths.meta_dir = (
                f"{workspace_root_container_path}/{self.args.meta_dir}"
            )

        if self.args.products_dir is not None:
            container_paths.products_dir = (
                f"{workspace_root_container_path}/{self.args.products_dir}"
            )

        if self.args.notebooks_dir is not None:
            container_paths.notebooks_dir = (
                f"{workspace_root_container_path}/{self.args.notebooks_dir}"
            )

        if self.args.workflows_dir is not None:
            container_paths.workflows_dir = (
                f"{workspace_root_container_path}/{self.args.workflows_dir}"
            )

        if self.args.workspace_config_dir is not None:
            container_paths.workspace_config_dir = (
                f"{workspace_root_container_path}/{self.args.workspace_config_dir}"
            )

        if self.args.requirements_file is not None:
            container_paths.requirements_file = (
                f"{workspace_root_container_path}/{self.args.requirements_file}"
            )

        return container_paths

    def read_yaml_file(self, file_path: Optional[Path]) -> Optional[Dict[str, Any]]:
        if file_path is not None and file_path.exists() and file_path.is_file():
            import yaml

            # logger.debug(f"Reading {file_path}")
            data_from_file = yaml.safe_load(file_path.read_text())
            if data_from_file is not None and isinstance(data_from_file, dict):
                return data_from_file
            else:
                logger.error(f"Invalid file: {file_path}")
        return None

    def set_aws_env_vars(self, env_dict: Dict[str, str]) -> None:
        """Set AWS environment variables."""
        from phidata.constants import (
            AWS_REGION_ENV_VAR,
            AWS_DEFAULT_REGION_ENV_VAR,
            # AWS_PROFILE_ENV_VAR,
            # AWS_CONFIG_FILE_ENV_VAR,
            # AWS_SHARED_CREDENTIALS_FILE_ENV_VAR,
        )

        if self.aws_region is not None:
            env_dict[AWS_REGION_ENV_VAR] = self.aws_region
            env_dict[AWS_DEFAULT_REGION_ENV_VAR] = self.aws_region
        # if self.aws_profile is not None:
        #     env_dict[AWS_PROFILE_ENV_VAR] = self.aws_profile
        # if self.aws_config_file is not None:
        #     env_dict[AWS_CONFIG_FILE_ENV_VAR] = self.aws_config_file
        # if self.aws_shared_credentials_file is not None:
        #     env_dict[
        #         AWS_SHARED_CREDENTIALS_FILE_ENV_VAR
        #     ] = self.aws_shared_credentials_file
