from pathlib import Path
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict

from agno.api.schemas.team import TeamSchema
from agno.api.schemas.workspace import WorkspaceSchema
from agno.infra.base import InfraBase
from agno.infra.resources import InfraResources
from agno.utils.log import logger
from agno.utils.py_io import get_python_objects_from_module
from agno.workspace.settings import WorkspaceSettings

# List of directories to ignore when loading the workspace
ignored_dirs = ["ignore", "test", "tests", "config"]


def get_infra_resources_from_file(resource_file: Path) -> dict:
    """Returns infra resources from a file"""
    try:
        python_objects = get_python_objects_from_module(resource_file)
        # logger.debug(f"python_objects: {python_objects}")

        infra_resources: dict[str, Any] = {}
        # Get all the infra resources from the file
        for obj_name, obj in python_objects.items():
            # Check if the object is of type InfraBase
            if isinstance(obj, InfraBase):
                logger.debug(f"Found: {obj_name}")
                infra_resources[obj_name] = obj

        return infra_resources
    except Exception:
        logger.error(f"Error reading: {resource_file}")
        raise


class WorkspaceConfig(BaseModel):
    """The WorkspaceConfig stores data for a agnodata workspace."""

    # Root directory for the workspace.
    ws_root_path: Path
    # WorkspaceSchema: This field indicates that the workspace is synced with the api
    ws_schema: Optional[WorkspaceSchema] = None
    # The Team name for the workspace
    ws_team: Optional[TeamSchema] = None
    # The API key for the workspace
    ws_api_key: Optional[str] = None

    # Path to the "workspace" directory inside the workspace root
    _workspace_dir_path: Optional[Path] = None
    # WorkspaceSettings
    _workspace_settings: Optional[WorkspaceSettings] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def to_dict(self) -> dict:
        return self.model_dump(include={"ws_root_path", "ws_schema", "ws_team", "ws_api_key"})

    @property
    def workspace_dir_path(self) -> Optional[Path]:
        if self._workspace_dir_path is None:
            if self.ws_root_path is not None:
                from agno.workspace.helpers import get_workspace_dir_path

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

    @property
    def workspace_settings(self) -> Optional[WorkspaceSettings]:
        if self._workspace_settings is not None:
            return self._workspace_settings

        ws_settings_file: Optional[Path] = None
        if self.workspace_dir_path is not None:
            _ws_settings_file = self.workspace_dir_path.joinpath("settings.py")
            if _ws_settings_file.exists() and _ws_settings_file.is_file():
                ws_settings_file = _ws_settings_file
        if ws_settings_file is None:
            logger.debug("workspace_settings file not found")
            return None

        logger.debug(f"Loading workspace_settings from {ws_settings_file}")
        try:
            python_objects = get_python_objects_from_module(ws_settings_file)
            for obj_name, obj in python_objects.items():
                if isinstance(obj, WorkspaceSettings):
                    if self.validate_workspace_settings(obj):
                        self._workspace_settings = obj
                        if self.ws_schema is not None and self._workspace_settings is not None:
                            self._workspace_settings.ws_schema = self.ws_schema
                            logger.debug("Added WorkspaceSchema to WorkspaceSettings")
        except Exception:
            logger.warning(f"Error in {ws_settings_file}")
            raise

        return self._workspace_settings

    def set_local_env(self) -> None:
        from os import environ

        from agno.constants import (
            AWS_REGION_ENV_VAR,
            SCRIPTS_DIR_ENV_VAR,
            STORAGE_DIR_ENV_VAR,
            WORKFLOWS_DIR_ENV_VAR,
            WORKSPACE_DIR_ENV_VAR,
            WORKSPACE_ID_ENV_VAR,
            WORKSPACE_NAME_ENV_VAR,
            WORKSPACE_ROOT_ENV_VAR,
        )

        if self.ws_root_path is not None:
            environ[WORKSPACE_ROOT_ENV_VAR] = str(self.ws_root_path)

            workspace_dir_path: Optional[Path] = self.workspace_dir_path
            if workspace_dir_path is not None:
                environ[WORKSPACE_DIR_ENV_VAR] = str(workspace_dir_path)

            if self.workspace_settings is not None:
                environ[WORKSPACE_NAME_ENV_VAR] = str(self.workspace_settings.ws_name)

                scripts_dir = self.ws_root_path.joinpath(self.workspace_settings.scripts_dir)
                environ[SCRIPTS_DIR_ENV_VAR] = str(scripts_dir)

                storage_dir = self.ws_root_path.joinpath(self.workspace_settings.storage_dir)
                environ[STORAGE_DIR_ENV_VAR] = str(storage_dir)

                workflows_dir = self.ws_root_path.joinpath(self.workspace_settings.workflows_dir)
                environ[WORKFLOWS_DIR_ENV_VAR] = str(workflows_dir)

        if self.ws_schema is not None:
            if self.ws_schema.id_workspace is not None:
                environ[WORKSPACE_ID_ENV_VAR] = str(self.ws_schema.id_workspace)

        if environ.get(AWS_REGION_ENV_VAR) is None:
            if self.workspace_settings is not None:
                if self.workspace_settings.aws_region is not None:
                    environ[AWS_REGION_ENV_VAR] = self.workspace_settings.aws_region

    def get_resources(
        self,
        env: Optional[str] = None,
        infra: Optional[InfraType] = None,
        order: str = "create",
    ) -> List[InfraResources]:
        if self.ws_root_path is None:
            logger.warning("WorkspaceConfig.ws_root_path is None")
            return []

        from sys import path as sys_path

        from agno.utils.load_env import load_env

        # Objects to read from the files in the workspace_dir_path
        docker_resource_groups: Optional[List[Any]] = None
        aws_resource_groups: Optional[List[Any]] = None

        logger.debug("**--> Loading WorkspaceConfig")

        logger.debug(f"Loading .env from {self.ws_root_path}")
        load_env(dotenv_dir=self.ws_root_path)

        # NOTE: When loading a workspace, relative imports or package imports do not work.
        # This is a known problem in python
        #     eg: https://stackoverflow.com/questions/6323860/sibling-package-imports/50193944#50193944
        # To make them work, we add workspace_root to sys.path so is treated as a module
        logger.debug(f"Adding {self.ws_root_path} to path")
        sys_path.insert(0, str(self.ws_root_path))

        workspace_dir_path: Optional[Path] = self.workspace_dir_path
        if workspace_dir_path is not None:
            from agno.aws.resources import AwsResources
            from agno.docker.resources import DockerResources

            logger.debug(f"--^^-- Loading workspace from: {workspace_dir_path}")
            # Create a dict of objects in the workspace directory
            workspace_objects = {}
            resource_files = workspace_dir_path.rglob("*.py")
            for resource_file in resource_files:
                if resource_file.name == "__init__.py":
                    continue

                resource_file_parts = resource_file.parts
                workspace_dir_path_parts = workspace_dir_path.parts
                resource_file_parts_after_ws = resource_file_parts[len(workspace_dir_path_parts) :]
                # Check if file in ignored directory
                if any([ignored_dir in resource_file_parts_after_ws for ignored_dir in ignored_dirs]):
                    logger.debug(f"Skipping file in ignored directory: {resource_file}")
                    continue
                logger.debug(f"Reading file: {resource_file}")
                try:
                    python_objects = get_python_objects_from_module(resource_file)
                    # logger.debug(f"python_objects: {python_objects}")
                    for obj_name, obj in python_objects.items():
                        if isinstance(
                            obj,
                            (
                                WorkspaceSettings,
                                DockerResources,
                                AwsResources,
                            ),
                        ):
                            workspace_objects[obj_name] = obj
                except Exception:
                    logger.warning(f"Error in {resource_file}")
                    raise

            # logger.debug(f"workspace_objects: {workspace_objects}")
            for obj_name, obj in workspace_objects.items():
                logger.debug(f"Reading {obj.__class__.__name__}: {obj_name}")
                if isinstance(obj, WorkspaceSettings):
                    if self.validate_workspace_settings(obj):
                        self._workspace_settings = obj
                        if self.ws_schema is not None and self._workspace_settings is not None:
                            self._workspace_settings.ws_schema = self.ws_schema
                            logger.debug("Added WorkspaceSchema to WorkspaceSettings")
                elif isinstance(obj, DockerResources):
                    if not obj.enabled:
                        logger.debug(f"Skipping {obj_name}: disabled")
                        continue
                    if docker_resource_groups is None:
                        docker_resource_groups = []
                    docker_resource_groups.append(obj)
                elif isinstance(obj, AwsResources):
                    if not obj.enabled:
                        logger.debug(f"Skipping {obj_name}: disabled")
                        continue
                    if aws_resource_groups is None:
                        aws_resource_groups = []
                    aws_resource_groups.append(obj)

        logger.debug("**--> WorkspaceConfig loaded")
        logger.debug(f"Removing {self.ws_root_path} from path")
        sys_path.remove(str(self.ws_root_path))

        # Resources filtered by infra
        filtered_infra_resources: List[InfraResources] = []
        logger.debug(f"Getting resources for env: {env} | infra: {infra} | order: {order}")
        if infra is None:
            if docker_resource_groups is not None:
                filtered_infra_resources.extend(docker_resource_groups)
            if order == "delete":
                if aws_resource_groups is not None:
                    filtered_infra_resources.extend(aws_resource_groups)
            else:
                if aws_resource_groups is not None:
                    filtered_infra_resources.extend(aws_resource_groups)
        elif infra == "docker":
            if docker_resource_groups is not None:
                filtered_infra_resources.extend(docker_resource_groups)
        elif infra == "aws":
            if aws_resource_groups is not None:
                filtered_infra_resources.extend(aws_resource_groups)

        # Resources filtered by env
        env_filtered_resource_groups: List[InfraResources] = []
        if env is None:
            env_filtered_resource_groups = filtered_infra_resources
        else:
            for resource_group in filtered_infra_resources:
                if resource_group.env == env:
                    env_filtered_resource_groups.append(resource_group)

        # Updated resource groups with the workspace settings
        if self._workspace_settings is None:
            # TODO: Create a temporary workspace settings object
            logger.debug("WorkspaceConfig._workspace_settings is None")
        if self._workspace_settings is not None:
            for resource_group in env_filtered_resource_groups:
                logger.debug(f"Setting workspace settings for {resource_group.__class__.__name__}")
                resource_group.set_workspace_settings(self._workspace_settings)
        return env_filtered_resource_groups

    @staticmethod
    def get_resources_from_file(
        resource_file: Path,
        env: Optional[str] = None,
        infra: Optional[str] = None,
        order: str = "create",
    ) -> List[InfraResources]:
        if not resource_file.exists():
            raise FileNotFoundError(f"File {resource_file} does not exist")
        if not resource_file.is_file():
            raise ValueError(f"Path {resource_file} is not a file")
        if not resource_file.suffix == ".py":
            raise ValueError(f"File {resource_file} is not a python file")

        from sys import path as sys_path

        from agno.utils.load_env import load_env

        # Workspace resources from the file
        workspace_resources: Optional[List[Any]] = None

        resource_file_parent_dir = resource_file.parent.resolve()
        logger.debug(f"Loading .env from {resource_file_parent_dir}")
        load_env(dotenv_dir=resource_file_parent_dir)

        temporary_ws_config = WorkspaceConfig(ws_root_path=resource_file_parent_dir)

        # NOTE: When loading a directory, relative imports or package imports do not work.
        # This is a known problem in python
        #     eg: https://stackoverflow.com/questions/6323860/sibling-package-imports/50193944#50193944
        # To make them work, we add workspace_root to sys.path so it can be treated as a module
        logger.debug(f"Adding {resource_file_parent_dir} to path")
        sys_path.insert(0, str(resource_file_parent_dir))

        logger.debug(f"**--> Loading resources from {resource_file}")
        # Create a dict of objects from the file
        infra_resources = get_infra_resources_from_file(resource_file)

        # logger.debug(f"Infra Resources in {resource_file}: {infra_resources}")
        for obj_name, obj in infra_resources.items():
            logger.debug(f"Reading {obj.__class__.__module__}: {obj_name}")
            if isinstance(obj, WorkspaceSettings):
                if temporary_ws_config.validate_workspace_settings(obj):
                    temporary_ws_config._workspace_settings = obj
            elif isinstance(obj, InfraBase):
                if not obj.enabled:
                    logger.debug(f"Skipping {obj_name}: disabled")
                    continue
                if workspace_resources is None:
                    workspace_resources = []
                workspace_resources.append(obj)
        logger.debug("**--> Resources loaded")

        # Resources filtered by infra
        filtered_infra_resources: List[InfraResources] = []
        logger.debug(f"Filtering resources for env: {env} | infra: {infra} | order: {order}")
        if infra is None:
            if workspace_resources is not None:
                filtered_infra_resources.extend(workspace_resources)
        else:
            # TODO: Filter by infra
            if workspace_resources is not None:
                filtered_infra_resources.extend(workspace_resources)

        # Resources filtered by env
        env_filtered_resources: List[InfraResources] = []
        if env is None:
            env_filtered_resources = filtered_infra_resources
        else:
            for resource_group in filtered_infra_resources:
                if resource_group.env == env:
                    env_filtered_resources.append(resource_group)

        # Updated resource groups with the workspace settings
        if temporary_ws_config._workspace_settings is None:
            # Create a temporary workspace settings object
            temporary_ws_config._workspace_settings = WorkspaceSettings(
                ws_root=temporary_ws_config.ws_root_path,
                ws_name=temporary_ws_config.ws_root_path.stem,
            )
        if temporary_ws_config._workspace_settings is not None:
            for resource in env_filtered_resources:
                logger.debug(f"Setting workspace settings for {resource.__class__.__name__}")
                resource.set_workspace_settings(temporary_ws_config._workspace_settings)
        return env_filtered_resources