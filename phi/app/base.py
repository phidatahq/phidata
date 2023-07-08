from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any, Union, List

from phi.base import PhiBase
from phi.app.context import ContainerContext
from phi.infra.resource import InfraResource
from phi.workspace.settings import WorkspaceSettings
from phi.utils.log import logger


class WorkspaceVolumeType(str, Enum):
    HostPath = "HostPath"
    EmptyDir = "EmptyDir"


class AppVolumeType(str, Enum):
    HostPath = "HostPath"
    EmptyDir = "EmptyDir"
    AwsEbs = "AwsEbs"
    AwsEfs = "AwsEfs"
    PersistentVolume = "PersistentVolume"


class AppBase(PhiBase):
    # App name is required
    name: str

    # -*- Workspace Configuration
    # Added when the App is being built by the InfraResourceGroup
    workspace_root: Optional[Path] = None
    workspace_settings: Optional[WorkspaceSettings] = None

    # -*- Image Configuration
    # Image can be provided as a DockerImage object
    image: Optional[Any] = None
    # OR as image_name:image_tag str
    image_str: Optional[str] = None
    # OR as image_name and image_tag
    image_name: Optional[str] = None
    image_tag: Optional[str] = None
    # Entrypoint for the container
    entrypoint: Optional[Union[str, List[str]]] = None
    # Command for the container
    command: Optional[Union[str, List[str]]] = None

    # -*- Python Configuration
    # Install python dependencies using a requirements.txt file
    install_requirements: bool = False
    # Path to the requirements.txt file relative to the workspace_root
    requirements_file: str = "requirements.txt"
    # Set the PYTHONPATH env var
    set_python_path: bool = False
    # Manually provide the PYTHONPATH.
    # If None, PYTHONPATH is set to workspace_root
    python_path: Optional[str] = None
    # Add paths to the PYTHONPATH env var
    # If python_path is provided, this value is ignored
    add_python_paths: Optional[List[str]] = None

    # -*- App Environment
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

    # -*- App Ports
    # Open a container port if open_container_port=True
    open_container_port: bool = False
    # Port number on the container
    container_port: int = 80
    # Port name (used by k8s)
    container_port_name: str = "http"
    # Host port to map to the container port
    host_port: int = 80

    # -*- Workspace Volume
    # Mount the workspace directory from host machine to the container
    mount_workspace: bool = False
    # Path to mount the workspace volume inside the container
    workspace_volume_container_path: str = "/mnt/workspace"
    # -*- If workspace_volume_type is None or WorkspaceVolumeType.HostPath
    # Mount the workspace_root to workspace_volume_container_path
    workspace_volume_type: Optional[WorkspaceVolumeType] = None
    # -*- If workspace_volume_type=WorkspaceVolumeType.EmptyDir
    # Create an empty volume with the name workspace_volume_name
    workspace_volume_name: Optional[str] = None
    # Then we can load the workspace from git using a git-sync sidecar
    create_git_sync_sidecar: bool = False
    # Use an init-container to create an initial copy of the workspace
    create_git_sync_init_container: bool = True
    git_sync_image_name: str = "k8s.gcr.io/git-sync"
    git_sync_image_tag: str = "v3.1.1"
    # Repository to sync
    git_sync_repo: Optional[str] = None
    # Branch to sync
    git_sync_branch: Optional[str] = None
    git_sync_wait: int = 1

    # -*- App Volume
    # Create a volume for mounting App data like notebooks, models, etc.
    create_app_volume: bool = False
    app_volume_name: Optional[str] = None
    # Path to mount the app volume inside the container
    app_volume_container_path: str = "/mnt/app"
    # Type of volume to create
    # -*- If volume_type=AppVolumeType.EmptyDir
    # Create an empty volume with the name app_volume_name
    app_volume_type: AppVolumeType = AppVolumeType.EmptyDir
    # -*- If volume_type=AppVolumeType.HostPath
    # Mount the app_volume_host_path to app_volume_container_path
    app_volume_host_path: Optional[str] = None
    # -*- If volume_type=AppVolumeType.AwsEbs
    # Mount an AWS EBS volume to app_volume_container_path
    # EbsVolume: used to derive the volume_id, region, and az
    app_ebs_volume: Optional[Any] = None
    # Or provide Ebs Volume-id manually
    app_ebs_volume_id: Optional[str] = None
    # And provide region and az
    app_ebs_volume_region: Optional[str] = None
    app_ebs_volume_az: Optional[str] = None
    # -*- If volume_type=AppVolumeType.AwsEfs
    # Mount an AWS EFS volume to app_volume_container_path
    # EfsVolume: used to derive the volume_id
    app_efs_volume: Optional[Any] = None
    # Or provide Efs Volume-id manually
    app_efs_volume_id: Optional[str] = None

    # -*- Extra Resources created "before" the App resources
    resources: Optional[List[InfraResource]] = None

    #  -*- Other args
    print_env_on_load: bool = False

    # -*- App specific args (updated by subclassed)
    container_env: Optional[Dict[str, Any]] = None
    container_context: Optional[ContainerContext] = None

    # -*- Cached Data
    cached_resources: Optional[List[Any]] = None
    cached_env_file_data: Optional[Dict[str, Any]] = None
    cached_secret_file_data: Optional[Dict[str, Any]] = None

    def get_app_name(self) -> str:
        return self.name

    def get_image_str(self) -> str:
        if self.image:
            return f"{self.image.name}:{self.image.tag}"
        elif self.image_str:
            return self.image_str
        elif self.image_name and self.image_tag:
            return f"{self.image_name}:{self.image_tag}"
        elif self.image_name:
            return f"{self.image_name}:latest"
        else:
            return ""

    def get_env_file_data(self) -> Optional[Dict[str, Any]]:
        if self.cached_env_file_data is None:
            from phi.utils.yaml_io import read_yaml_file

            self.cached_env_file_data = read_yaml_file(file_path=self.env_file)
        return self.cached_env_file_data

    def get_secret_file_data(self) -> Optional[Dict[str, Any]]:
        if self.cached_secret_file_data is None:
            from phi.utils.yaml_io import read_yaml_file

            self.cached_secret_file_data = read_yaml_file(file_path=self.secrets_file)
        return self.cached_secret_file_data

    def set_aws_env_vars(self, env_dict: Dict[str, str]) -> None:
        from phi.constants import (
            AWS_REGION_ENV_VAR,
            AWS_DEFAULT_REGION_ENV_VAR,
            AWS_PROFILE_ENV_VAR,
        )

        if self.workspace_settings is not None and self.workspace_settings.aws_region is not None:
            env_dict[AWS_REGION_ENV_VAR] = self.workspace_settings.aws_region
            env_dict[AWS_DEFAULT_REGION_ENV_VAR] = self.workspace_settings.aws_region
        if self.workspace_settings is not None and self.workspace_settings.aws_profile is not None:
            env_dict[AWS_PROFILE_ENV_VAR] = self.workspace_settings.aws_profile

    def build_container_context(self) -> Optional[ContainerContext]:
        logger.debug("Building ContainerContext")

        if self.container_context is not None:
            return self.container_context

        if self.workspace_root is None:
            logger.error("Invalid workspace_root")
            return None

        workspace_name = self.workspace_root.stem
        if workspace_name is None:
            return None

        workspace_volume_container_path: str = self.workspace_volume_container_path
        if workspace_volume_container_path is None:
            return None

        workspace_parent_paths = workspace_volume_container_path.split("/")[0:-1]
        workspace_parent = "/".join(workspace_parent_paths)

        self.container_context = ContainerContext(
            workspace_name=workspace_name,
            workspace_root=workspace_volume_container_path,
            # Required for git-sync and K8s volume mounts
            workspace_parent=workspace_parent,
        )

        if self.workspace_settings is not None and self.workspace_settings.scripts_dir is not None:
            self.container_context.scripts_dir = (
                f"{workspace_volume_container_path}/{self.workspace_settings.scripts_dir}"
            )

        if self.workspace_settings is not None and self.workspace_settings.storage_dir is not None:
            self.container_context.storage_dir = (
                f"{workspace_volume_container_path}/{self.workspace_settings.storage_dir}"
            )

        if self.workspace_settings is not None and self.workspace_settings.workflows_dir is not None:
            self.container_context.workflows_dir = (
                f"{workspace_volume_container_path}/{self.workspace_settings.workflows_dir}"
            )

        if self.workspace_settings is not None and self.workspace_settings.workspace_dir is not None:
            self.container_context.workspace_dir = (
                f"{workspace_volume_container_path}/{self.workspace_settings.workspace_dir}"
            )

        if self.requirements_file is not None:
            self.container_context.requirements_file = (
                f"{workspace_volume_container_path}/{self.requirements_file}"
            )

        return self.container_context

    def build_resources(self, build_context: Any) -> Optional[Any]:
        logger.debug(f"@build_resource_group not defined for {self.get_app_name()}")
        return None

    def get_dependencies(self) -> List[InfraResource]:
        return []

    def add_workspace_settings_to_app(
        self, workspace_root: Optional[Path] = None, workspace_settings: Optional[WorkspaceSettings] = None
    ) -> None:
        if workspace_root is not None:
            self.workspace_root = workspace_root
        if workspace_settings is not None:
            self.workspace_settings = workspace_settings

    def add_app_properties_to_resources(self, resources: List[InfraResource]) -> List[InfraResource]:
        updated_resources = []
        for resource in resources:
            resource.group = resource.group or self.group
            resource.wait_for_create = resource.wait_for_create or self.wait_for_create
            resource.wait_for_update = resource.wait_for_update or self.wait_for_update
            resource.wait_for_delete = resource.wait_for_delete or self.wait_for_delete
            resource.save_output = resource.save_output or self.save_output
            resource.output_dir = resource.output_dir or self.get_app_name()
            resource.depends_on = resource.depends_on or self.get_dependencies()
            updated_resources.append(resource)
        return updated_resources

    def get_resources(self, build_context: Any) -> List[InfraResource]:
        if self.cached_resources is not None and len(self.cached_resources) > 0:
            return self.cached_resources

        base_resources = self.resources or []
        app_resources = self.build_resources(build_context)
        if app_resources is not None:
            base_resources.extend(app_resources)

        self.cached_resources = self.add_app_properties_to_resources(base_resources)
        logger.debug(f"Resources: {self.cached_resources}")
        return self.cached_resources

    def should_create(self, group_filter: Optional[str] = None) -> bool:
        if not self.enabled or self.skip_create:
            return False
        if group_filter is not None:
            group_name = self.get_group_name()
            if group_name is not None:
                if group_name != group_filter:
                    return False
        return True
