import datetime
from pathlib import Path
from typing import Optional, List, Any

from pydantic import BaseModel, ConfigDict

from phi.infra.enums import InfraType
from phi.infra.resource.group import InfraResourceGroup
from phi.api.schemas.workspace import WorkspaceSchema
from phi.workspace.settings import WorkspaceSettings
from phi.utils.dttm import current_datetime_utc
from phi.utils.log import logger


class WorkspaceConfig(BaseModel):
    """The WorkspaceConfig stores data for a phidata workspace."""

    # Name of the workspace
    ws_name: str
    # WorkspaceSchema: This field indicates that the workspace is synced with the api
    ws_schema: Optional[WorkspaceSchema] = None
    # The root directory for the workspace.
    # This field indicates that the ws has been downloaded on this machine
    ws_root_path: Optional[Path] = None
    # WorkspaceSettings
    workspace_settings: Optional[WorkspaceSettings] = None
    # Path to the workspace directory
    _workspace_dir_path: Optional[Path] = None
    # Timestamp of when this workspace was created on the users machine
    create_ts: datetime.datetime = current_datetime_utc()

    # List of DockerResourceGroup
    docker_resource_groups: Optional[List[Any]] = None
    # List of K8sResourceGroup
    k8s_resource_groups: Optional[List[Any]] = None
    # List of AwsResourceGroup
    aws_resource_groups: Optional[List[Any]] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @property
    def workspace_dir_path(self) -> Optional[Path]:
        if self._workspace_dir_path is None:
            if self.ws_root_path is not None:
                from phi.workspace.helpers import get_workspace_dir_path

                self._workspace_dir_path = get_workspace_dir_path(self.ws_root_path)
        return self._workspace_dir_path

    def validate_workspace_settings(self, obj: Any) -> bool:
        if not isinstance(obj, WorkspaceSettings):
            raise Exception("WorkspaceSettings must be of type WorkspaceSettings")
        if self.ws_root_path is not None and obj.ws_root is not None:
            if obj.ws_root != self.ws_root_path:
                raise Exception(f"WorkspaceSettings.ws_root ({obj.ws_root}) must match {self.ws_root_path}")
        if obj.workspace_dir is not None:
            if self.workspace_dir_path is not None:
                if self.ws_root_path is None:
                    raise Exception("Workspace root not set")
                workspace_dir = self.ws_root_path.joinpath(obj.workspace_dir)
                if workspace_dir != self.workspace_dir_path:
                    raise Exception(
                        f"WorkspaceSettings.workspace_dir ({workspace_dir}) must match {self.workspace_dir_path}"  # noqa
                    )
        return True

    def load(self) -> bool:
        if self.ws_root_path is None:
            raise Exception("Workspace root not set")

        logger.debug("**--> Loading WorkspaceConfig")
        from sys import path as sys_path
        from phi.utils.load_env import load_env
        from phi.utils.py_io import get_python_objects_from_module

        logger.debug(f"Loading .env from {self.ws_root_path}")
        load_env(dotenv_dir=self.ws_root_path)

        # NOTE: When loading a workspace, relative imports or package imports dont work.
        # This is a known problem in python
        #     eg: https://stackoverflow.com/questions/6323860/sibling-package-imports/50193944#50193944
        # To make them work, we add workspace_root to sys.path so is treated as a module
        logger.debug(f"Adding {self.ws_root_path} to path")
        sys_path.insert(0, str(self.ws_root_path))

        workspace_dir_path: Optional[Path] = self.workspace_dir_path
        if workspace_dir_path is not None:
            logger.debug(f"--^^-- Loading workspace from: {workspace_dir_path}")
            # Create a dict of objects in the workspace directory
            workspace_objects = {}
            resource_files = workspace_dir_path.rglob("*.py")
            for resource_file in resource_files:
                if resource_file.name == "__init__.py":
                    continue
                logger.debug(f"Reading file: {resource_file}")
                try:
                    python_objects = get_python_objects_from_module(resource_file)
                    # logger.debug(f"python_objects: {python_objects}")
                    for obj_name, obj in python_objects.items():
                        _type_name = obj.__class__.__name__
                        if _type_name in [
                            "WorkspaceSettings",
                            "DockerResourceGroup",
                            "K8sResourceGroup",
                            "AwsResourceGroup",
                        ]:
                            workspace_objects[obj_name] = obj
                except Exception as e:
                    parent_dir = resource_file.parent.name
                    parent_parent_dir = resource_file.parent.parent.name
                    # Ignore errors in resources and tests subdirectories
                    if parent_dir in ("resources", "tests") or parent_parent_dir in (
                        "resources",
                        "tests",
                    ):
                        pass
                    else:
                        logger.warning(f"Error in {resource_file}: {e}")
                    pass

            # logger.debug(f"workspace_objects: {workspace_objects}")
            for obj_name, obj in workspace_objects.items():
                _obj_type = obj.__class__.__name__
                logger.debug(f"Adding {obj_name} | Type: {_obj_type}")
                if _obj_type == "WorkspaceSettings":
                    if self.validate_workspace_settings(obj):
                        self.workspace_settings = obj
                elif _obj_type == "DockerResourceGroup":
                    if self.docker_resource_groups is None:
                        self.docker_resource_groups = []
                    self.docker_resource_groups.append(obj)
                elif _obj_type == "K8sResourceGroup":
                    if self.k8s_resource_groups is None:
                        self.k8s_resource_groups = []
                    self.k8s_resource_groups.append(obj)
                elif _obj_type == "AwsResourceGroup":
                    if self.aws_resource_groups is None:
                        self.aws_resource_groups = []
                    self.aws_resource_groups.append(obj)

        logger.debug("**--> WorkspaceConfig loaded")
        return True

    def set_local_env(self) -> None:
        from os import environ

        from phi.constants import (
            SCRIPTS_DIR_ENV_VAR,
            STORAGE_DIR_ENV_VAR,
            WORKFLOWS_DIR_ENV_VAR,
            WORKSPACE_NAME_ENV_VAR,
            WORKSPACE_ROOT_ENV_VAR,
            WORKSPACE_DIR_ENV_VAR,
        )

        if self.ws_name is not None:
            environ[WORKSPACE_NAME_ENV_VAR] = str(self.ws_name)

        if self.ws_root_path is not None:
            environ[WORKSPACE_ROOT_ENV_VAR] = str(self.ws_root_path)

            workspace_dir_path: Optional[Path] = self.workspace_dir_path
            if workspace_dir_path is not None:
                environ[WORKSPACE_DIR_ENV_VAR] = str(workspace_dir_path)

            if self.workspace_settings is not None:
                scripts_dir = self.ws_root_path.joinpath(self.workspace_settings.scripts_dir)
                environ[SCRIPTS_DIR_ENV_VAR] = str(scripts_dir)

                storage_dir = self.ws_root_path.joinpath(self.workspace_settings.storage_dir)
                environ[STORAGE_DIR_ENV_VAR] = str(storage_dir)

                workflows_dir = self.ws_root_path.joinpath(self.workspace_settings.workflows_dir)
                environ[WORKFLOWS_DIR_ENV_VAR] = str(workflows_dir)

    def get_resource_groups(
        self, env: Optional[str] = None, infra: Optional[InfraType] = None, order: str = "create"
    ) -> List[InfraResourceGroup]:
        # Get all resource groups
        all_resource_groups: List[InfraResourceGroup] = []
        if infra is None:
            if self.docker_resource_groups is not None:
                all_resource_groups.extend(self.docker_resource_groups)
            if order == "delete":
                if self.k8s_resource_groups is not None:
                    all_resource_groups.extend(self.k8s_resource_groups)
                if self.aws_resource_groups is not None:
                    all_resource_groups.extend(self.aws_resource_groups)
            else:
                if self.aws_resource_groups is not None:
                    all_resource_groups.extend(self.aws_resource_groups)
                if self.k8s_resource_groups is not None:
                    all_resource_groups.extend(self.k8s_resource_groups)
        elif infra == "docker":
            if self.docker_resource_groups is not None:
                all_resource_groups.extend(self.docker_resource_groups)
        elif infra == "k8s":
            if self.k8s_resource_groups is not None:
                all_resource_groups.extend(self.k8s_resource_groups)
        elif infra == "aws":
            if self.aws_resource_groups is not None:
                all_resource_groups.extend(self.aws_resource_groups)

        # Filter by env
        filtered_resource_groups: List[InfraResourceGroup] = []
        if env is None:
            filtered_resource_groups = all_resource_groups
        else:
            for resource_group in all_resource_groups:
                if resource_group.env == env:
                    filtered_resource_groups.append(resource_group)

        # Updated filtered resource groups with the workspace settings
        if self.workspace_settings is not None:
            for resource_group in filtered_resource_groups:
                logger.debug(f"Setting workspace settings for {resource_group.__class__.__name__}")
                resource_group.set_workspace_settings(self.workspace_settings)
        return filtered_resource_groups
