from pathlib import Path
from typing import Optional, Dict, Any, Union, List

from phidata.base import PhidataBase, PhidataBaseArgs
from phidata.types.context import ContainerPathContext
from phidata.utils.enums import ExtendedEnum
from phidata.utils.log import logger


class WorkspaceVolumeType(ExtendedEnum):
    HostPath = "HostPath"
    EmptyDir = "EmptyDir"


class AppVolumeType(ExtendedEnum):
    HostPath = "HostPath"
    EmptyDir = "EmptyDir"
    AwsEbs = "AwsEbs"
    AwsEfs = "AwsEfs"
    PersistentVolume = "PersistentVolume"


class BaseAppArgs(PhidataBaseArgs):
    # -*- Path parameters
    # Path to the workspace root directory
    workspace_root_path: Optional[Path] = None
    # Path to the workspace config file
    workspace_config_file_path: Optional[Path] = None
    # Path to important directories relative to the workspace_root
    # These directories are joined to the workspace_root dir
    #   to build paths depending on the environments (local, docker, k8s)
    scripts_dir: Optional[str] = None
    storage_dir: Optional[str] = None
    meta_dir: Optional[str] = None
    products_dir: Optional[str] = None
    notebooks_dir: Optional[str] = None
    workflows_dir: Optional[str] = None
    workspace_config_dir: Optional[str] = None

    # -*- Image Configuration
    # Image can be provided as a DockerImage object
    image: Optional[Any] = None
    # OR as image_name:image_tag
    image_name: Optional[str] = None
    image_tag: Optional[str] = None
    entrypoint: Optional[Union[str, List[str]]] = None
    command: Optional[Union[str, List[str]]] = None

    # -*- Debug Mode
    debug_mode: bool = False

    # -*- Python Configuration
    # Install python dependencies using a requirements.txt file
    install_requirements: bool = False
    # Path to the requirements.txt file relative to the workspace_root
    requirements_file: str = "requirements.txt"
    # Set the PYTHONPATH env var
    set_python_path: bool = False
    # Manually provide the PYTHONPATH
    python_path: Optional[str] = None
    # Add paths to the PYTHONPATH env var
    # If python_path is provided, this value is ignored
    add_python_paths: Optional[List[str]] = None

    # -*- Container Environment
    # Add env variables to container
    env: Optional[Dict[str, Any]] = None
    # Read env variables from a file in yaml format
    env_file: Optional[Path] = None
    # Add secret variables to container
    secrets: Optional[Dict[str, Any]] = None
    # Read secret variables from a file in yaml format
    secrets_file: Optional[Path] = None
    # Read secret variables from AWS Secrets
    aws_secrets: Optional[Any] = None

    # -*- Container Ports
    # Open a container port if open_container_port=True
    open_container_port: bool = False
    # Port number on the container
    container_port: int = 80
    # Port name
    container_port_name: str = "http"
    # Host port to map to the container port
    container_host_port: int = 80

    # -*- Workspace Volume
    # Mount the workspace directory on the container
    mount_workspace: bool = False
    workspace_volume_name: Optional[str] = None
    workspace_volume_type: Optional[WorkspaceVolumeType] = None
    # Path to mount the workspace volume inside the container
    workspace_dir_container_path: str = "/mnt/workspaces"
    # Add the workspace name to the container path
    add_workspace_name_to_container_path: bool = True
    # -*- If workspace_volume_type=WorkspaceVolumeType.HostPath
    # Mount workspace_dir to workspace_dir_container_path
    # If None, use the workspace_root
    workspace_dir: Optional[str] = None
    # -*- If workspace_volume_type=WorkspaceVolumeType.EmptyDir
    # Then we can load the workspace from git using a git-sync sidecar
    create_git_sync_sidecar: bool = False
    # Required to create an initial copy of the workspace
    create_git_sync_init_container: bool = True
    git_sync_image_name: str = "k8s.gcr.io/git-sync"
    git_sync_image_tag: str = "v3.1.1"
    git_sync_repo: Optional[str] = None
    git_sync_branch: Optional[str] = None
    git_sync_wait: int = 1

    # -*- App Volume
    # Create a volume for mounting app data like notebooks, models, etc.
    create_app_volume: bool = False
    app_volume_name: Optional[str] = None
    app_volume_type: AppVolumeType = AppVolumeType.EmptyDir
    # Path to mount the app volume inside the container
    app_volume_container_path: str = "/mnt/app"
    # -*- If volume_type=AppVolumeType.HostPath
    app_volume_host_path: Optional[str] = None
    # -*- If volume_type=AppVolumeType.AwsEbs
    # EbsVolume: used to derive the volume_id, region, and az
    app_ebs_volume: Optional[Any] = None
    app_ebs_volume_region: Optional[str] = None
    app_ebs_volume_az: Optional[str] = None
    # Provide Ebs Volume-id manually
    app_ebs_volume_id: Optional[str] = None
    # -*- If volume_type=AppVolumeType.PersistentVolume
    # AccessModes is a list of ways the volume can be mounted.
    # More info: https://kubernetes.io/docs/concepts/storage/persistent-volumes#access-modes
    # Type: phidata.infra.k8s.enums.pv.PVAccessMode
    app_pv_access_modes: Optional[List[Any]] = None
    app_pv_requests_storage: Optional[str] = None
    # A list of mount options, e.g. ["ro", "soft"]. Not validated - mount will simply fail if one is invalid.
    # More info: https://kubernetes.io/docs/concepts/storage/persistent-volumes/#mount-options
    app_pv_mount_options: Optional[List[str]] = None
    # What happens to a persistent volume when released from its claim.
    #   The default policy is Retain.
    # Literal["Delete", "Recycle", "Retain"]
    app_pv_reclaim_policy: Optional[str] = None
    app_pv_storage_class: str = ""
    app_pv_labels: Optional[Dict[str, str]] = None
    # -*- If volume_type=AppVolumeType.AwsEfs
    app_efs_volume_id: Optional[str] = None

    # Add NodeSelectors to Pods, so they are scheduled in the same region and zone as the ebs_volume
    schedule_pods_in_ebs_topology: bool = True

    # -*- AWS Configuration
    aws_region: Optional[str] = None
    aws_profile: Optional[str] = None
    aws_config_file: Optional[str] = None
    aws_shared_credentials_file: Optional[str] = None

    #  -*- Other args
    print_env_on_load: bool = False

    # -*- Deprecated
    # Env vars added to docker env when building PhidataApps
    #   and running workflows
    docker_env: Optional[Dict[str, str]] = None
    # Env vars added to k8s env when building PhidataApps
    #   and running workflows
    k8s_env: Optional[Dict[str, str]] = None


class BaseApp(PhidataBase):
    """Base Class for all PhidataApps"""

    def __init__(self) -> None:
        super().__init__()

        # Cache env_data & secret_data
        self.env_data: Optional[Dict[str, Any]] = None
        self.secret_data: Optional[Dict[str, Any]] = None

        # Env variables used by the app
        self.container_env: Optional[Dict[str, str]] = None
        # Container paths used by the app
        self.container_paths: Optional[ContainerPathContext] = None

        # Args for the BaseApp, updated by the subclass
        self.args: BaseAppArgs = BaseAppArgs()

    @property
    def app_name(self) -> str:
        return self.name

    @property
    def workspace_root_path(self) -> Optional[Path]:
        return self.args.workspace_root_path

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
        return self.args.scripts_dir

    @scripts_dir.setter
    def scripts_dir(self, scripts_dir: str) -> None:
        if self.args is not None and scripts_dir is not None:
            self.args.scripts_dir = scripts_dir

    @property
    def storage_dir(self) -> Optional[str]:
        return self.args.storage_dir

    @storage_dir.setter
    def storage_dir(self, storage_dir: str) -> None:
        if self.args is not None and storage_dir is not None:
            self.args.storage_dir = storage_dir

    @property
    def meta_dir(self) -> Optional[str]:
        return self.args.meta_dir

    @meta_dir.setter
    def meta_dir(self, meta_dir: str) -> None:
        if self.args is not None and meta_dir is not None:
            self.args.meta_dir = meta_dir

    @property
    def products_dir(self) -> Optional[str]:
        return self.args.products_dir

    @products_dir.setter
    def products_dir(self, products_dir: str) -> None:
        if self.args is not None and products_dir is not None:
            self.args.products_dir = products_dir

    @property
    def notebooks_dir(self) -> Optional[str]:
        return self.args.notebooks_dir

    @notebooks_dir.setter
    def notebooks_dir(self, notebooks_dir: str) -> None:
        if self.args is not None and notebooks_dir is not None:
            self.args.notebooks_dir = notebooks_dir

    @property
    def workflows_dir(self) -> Optional[str]:
        return self.args.workflows_dir

    @workflows_dir.setter
    def workflows_dir(self, workflows_dir: str) -> None:
        if self.args is not None and workflows_dir is not None:
            self.args.workflows_dir = workflows_dir

    @property
    def workspace_config_dir(self) -> Optional[str]:
        return self.args.workspace_config_dir

    @workspace_config_dir.setter
    def workspace_config_dir(self, workspace_config_dir: str) -> None:
        if self.args is not None and workspace_config_dir is not None:
            self.args.workspace_config_dir = workspace_config_dir

    @property
    def docker_env(self) -> Optional[Dict[str, str]]:
        return self.args.docker_env

    @docker_env.setter
    def docker_env(self, docker_env: Dict[str, str]) -> None:
        if self.args is not None and docker_env is not None:
            self.args.docker_env = docker_env

    @property
    def k8s_env(self) -> Optional[Dict[str, str]]:
        return self.args.k8s_env

    @k8s_env.setter
    def k8s_env(self, k8s_env: Dict[str, str]) -> None:
        if self.args is not None and k8s_env is not None:
            self.args.k8s_env = k8s_env

    @property
    def container_port(self) -> int:
        return self.args.container_port

    @container_port.setter
    def container_port(self, container_port: int) -> None:
        if self.args is not None and container_port is not None:
            self.args.container_port = container_port

    @property
    def container_host_port(self) -> int:
        return self.args.container_host_port

    @container_host_port.setter
    def container_host_port(self, container_host_port: int) -> None:
        if self.args is not None and container_host_port is not None:
            self.args.container_host_port = container_host_port

    @property
    def aws_region(self) -> Optional[str]:
        return self.args.aws_region

    @aws_region.setter
    def aws_region(self, aws_region: str) -> None:
        if self.args is not None and aws_region is not None:
            self.args.aws_region = aws_region

    @property
    def aws_profile(self) -> Optional[str]:
        return self.args.aws_profile

    @aws_profile.setter
    def aws_profile(self, aws_profile: str) -> None:
        if self.args is not None and aws_profile is not None:
            self.args.aws_profile = aws_profile

    @property
    def aws_config_file(self) -> Optional[str]:
        return self.args.aws_config_file

    @aws_config_file.setter
    def aws_config_file(self, aws_config_file: str) -> None:
        if self.args is not None and aws_config_file is not None:
            self.args.aws_config_file = aws_config_file

    @property
    def aws_shared_credentials_file(self) -> Optional[str]:
        return self.args.aws_shared_credentials_file

    @aws_shared_credentials_file.setter
    def aws_shared_credentials_file(self, aws_shared_credentials_file: str) -> None:
        if self.args is not None and aws_shared_credentials_file is not None:
            self.args.aws_shared_credentials_file = aws_shared_credentials_file

    def get_image_str(self):
        if self.args.image:
            return f"{self.args.image.name}:{self.args.image.tag}"
        elif self.args.image_name and self.args.image_tag:
            return f"{self.args.image_name}:{self.args.image_tag}"
        elif self.args.image_name:
            return f"{self.args.image_name}:latest"
        else:
            return None

    def get_env_data(self) -> Optional[Dict[str, str]]:
        if self.env_data is None:
            from phidata.utils.yaml_io import read_yaml_file

            self.env_data = read_yaml_file(file_path=self.args.env_file)
        return self.env_data

    def get_secret_data(self) -> Optional[Dict[str, str]]:
        if self.secret_data is None:
            from phidata.utils.yaml_io import read_yaml_file

            self.secret_data = read_yaml_file(file_path=self.args.secrets_file)
        return self.secret_data

    def build_container_paths(self) -> Optional[ContainerPathContext]:
        logger.debug("Building ContainerPathContext")

        if self.container_paths is not None:
            return self.container_paths

        if self.workspace_root_path is None:
            logger.error("Invalid workspace_root_path")
            return None

        workspace_name = self.workspace_root_path.stem
        if workspace_name is None:
            return None

        workspace_volume_container_path: str = self.args.workspace_dir_container_path
        if workspace_volume_container_path is None:
            return None

        workspace_root_container_path = (
            f"{workspace_volume_container_path}/{workspace_name}"
            if self.args.add_workspace_name_to_container_path
            else workspace_volume_container_path
        )
        container_paths = ContainerPathContext(
            workspace_name=workspace_name,
            workspace_root=workspace_root_container_path,
            # Required for git-sync and K8s volume mounts
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

        self.container_paths = container_paths
        return self.container_paths

    def set_aws_env_vars(self, env_dict: Dict[str, str]) -> None:
        from phidata.constants import (
            AWS_REGION_ENV_VAR,
            AWS_DEFAULT_REGION_ENV_VAR,
        )

        if self.aws_region is not None:
            env_dict[AWS_REGION_ENV_VAR] = self.aws_region
            env_dict[AWS_DEFAULT_REGION_ENV_VAR] = self.aws_region

    def get_docker_resource_groups(
        self, docker_build_context: Any
    ) -> Optional[Dict[str, Any]]:
        logger.debug(f"@get_docker_resource_groups not defined for {self.name}")
        return None

    def get_k8s_resource_groups(
        self, k8s_build_context: Any
    ) -> Optional[Dict[str, Any]]:
        logger.debug(f"@get_k8s_resource_groups not defined for {self.name}")
        return None

    def get_aws_resource_groups(
        self, aws_build_context: Any
    ) -> Optional[Dict[str, Any]]:
        logger.debug(f"@get_aws_resource_groups not defined for {self.name}")
        return None
