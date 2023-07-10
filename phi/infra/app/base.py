from enum import Enum
from typing import Optional, Dict, Any, Union, List

from phi.base import PhiBase
from phi.infra.app.context import ContainerContext
from phi.infra.resource.base import InfraResource
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


class InfraApp(PhiBase):
    # -*- App Name (required)
    name: str

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

    # -*- App Ports
    # Open a container port if open_container_port=True
    open_container_port: bool = False
    # Port number on the container
    container_port: int = 80
    # Host port to map to the container port
    host_port: int = 80

    # -*- Extra Resources created "before" the App resources
    resources: Optional[List[InfraResource]] = None

    #  -*- Other args
    print_env_on_load: bool = False

    # -*- App specific args (updated by subclasses)
    container_env: Optional[Dict[str, Any]] = None
    container_context: Optional[ContainerContext] = None

    # -*- Cached Data
    cached_resources: Optional[List[Any]] = None

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

    def build_container_context(self) -> Optional[ContainerContext]:
        logger.debug("Building ContainerContext")

        if self.container_context is not None:
            return self.container_context

        workspace_name = self.workspace_name
        if workspace_name is None:
            logger.warning("Invalid workspace_name")
            return None

        workspace_volume_container_path: str = self.workspace_volume_container_path
        if workspace_volume_container_path is None:
            logger.warning("Invalid workspace_volume_container_path")
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
            self.container_context.requirements_file = f"{workspace_volume_container_path}/{self.requirements_file}"

        return self.container_context

    def build_resources(self, build_context: Any) -> Optional[Any]:
        logger.debug(f"@build_resource_group not defined for {self.get_app_name()}")
        return None

    def get_dependencies(self) -> Optional[List[InfraResource]]:
        return self.depends_on

    def add_app_properties_to_resources(self, resources: List[InfraResource]) -> List[InfraResource]:
        updated_resources = []
        app_properties = self.model_dump(exclude_defaults=True)
        app_group = self.get_group_name()
        app_output_dir = self.get_app_name()

        app_skip_create = app_properties.get("skip_create", None)
        app_skip_read = app_properties.get("skip_read", None)
        app_skip_update = app_properties.get("skip_update", None)
        app_skip_delete = app_properties.get("skip_delete", None)
        app_recreate_on_update = app_properties.get("recreate_on_update", None)
        app_use_cache = app_properties.get("use_cache", None)
        app_force = app_properties.get("force", None)
        app_debug_mode = app_properties.get("debug_mode", None)
        app_wait_for_create = app_properties.get("wait_for_create", None)
        app_wait_for_update = app_properties.get("wait_for_update", None)
        app_wait_for_delete = app_properties.get("wait_for_delete", None)
        app_save_output = app_properties.get("save_output", None)

        for resource in resources:
            resource_properties = resource.model_dump(exclude_defaults=True)
            resource_skip_create = resource_properties.get("skip_create", None)
            resource_skip_read = resource_properties.get("skip_read", None)
            resource_skip_update = resource_properties.get("skip_update", None)
            resource_skip_delete = resource_properties.get("skip_delete", None)
            resource_recreate_on_update = resource_properties.get("recreate_on_update", None)
            resource_use_cache = resource_properties.get("use_cache", None)
            resource_force = resource_properties.get("force", None)
            resource_debug_mode = resource_properties.get("debug_mode", None)
            resource_wait_for_create = resource_properties.get("wait_for_create", None)
            resource_wait_for_update = resource_properties.get("wait_for_update", None)
            resource_wait_for_delete = resource_properties.get("wait_for_delete", None)
            resource_save_output = resource_properties.get("save_output", None)

            # If skip_create on resource is not set, use app level skip_create (if set on app)
            if resource_skip_create is None and app_skip_create is not None:
                resource.skip_create = app_skip_create
            # If skip_read on resource is not set, use app level skip_read (if set on app)
            if resource_skip_read is None and app_skip_read is not None:
                resource.skip_read = app_skip_read
            # If skip_update on resource is not set, use app level skip_update (if set on app)
            if resource_skip_update is None and app_skip_update is not None:
                resource.skip_update = app_skip_update
            # If skip_delete on resource is not set, use app level skip_delete (if set on app)
            if resource_skip_delete is None and app_skip_delete is not None:
                resource.skip_delete = app_skip_delete
            # If recreate_on_update on resource is not set, use app level recreate_on_update (if set on app)
            if resource_recreate_on_update is None and app_recreate_on_update is not None:
                resource.recreate_on_update = app_recreate_on_update
            # If use_cache on resource is not set, use app level use_cache (if set on app)
            if resource_use_cache is None and app_use_cache is not None:
                resource.use_cache = app_use_cache
            # If force on resource is not set, use app level force (if set on app)
            if resource_force is None and app_force is not None:
                resource.force = app_force
            # If debug_mode on resource is not set, use app level debug_mode (if set on app)
            if resource_debug_mode is None and app_debug_mode is not None:
                resource.debug_mode = app_debug_mode
            # If wait_for_create on resource is not set, use app level wait_for_create (if set on app)
            if resource_wait_for_create is None and app_wait_for_create is not None:
                resource.wait_for_create = app_wait_for_create
            # If wait_for_update on resource is not set, use app level wait_for_update (if set on app)
            if resource_wait_for_update is None and app_wait_for_update is not None:
                resource.wait_for_update = app_wait_for_update
            # If wait_for_delete on resource is not set, use app level wait_for_delete (if set on app)
            if resource_wait_for_delete is None and app_wait_for_delete is not None:
                resource.wait_for_delete = app_wait_for_delete
            # If save_output on resource is not set, use app level save_output (if set on app)
            if resource_save_output is None and app_save_output is not None:
                resource.save_output = app_save_output
            # If workspace_settings on resource is not set, use app level workspace_settings (if set on app)
            if resource.workspace_settings is None and self.workspace_settings is not None:
                resource.set_workspace_settings(self.workspace_settings)

            resource.group = app_group
            resource.output_dir = app_output_dir

            app_dependencies = self.get_dependencies()
            if app_dependencies is not None:
                if resource.depends_on is None:
                    resource.depends_on = app_dependencies
                else:
                    resource.depends_on.extend(app_dependencies)

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
        # logger.debug(f"Resources: {self.cached_resources}")
        return self.cached_resources

    def matches_filters(self, group_filter: Optional[str] = None) -> bool:
        if group_filter is not None:
            group_name = self.get_group_name()
            logger.debug(f"Checking {group_filter} in {group_name}")
            if group_name is not None:
                if group_filter not in group_name:
                    return False
        return True

    def should_create(self, group_filter: Optional[str] = None) -> bool:
        if not self.enabled or self.skip_create:
            return False
        return self.matches_filters(group_filter)

    def should_delete(self, group_filter: Optional[str] = None) -> bool:
        if not self.enabled or self.skip_delete:
            return False
        return self.matches_filters(group_filter)

    def should_update(self, group_filter: Optional[str] = None) -> bool:
        if not self.enabled or self.skip_update:
            return False
        return self.matches_filters(group_filter)
