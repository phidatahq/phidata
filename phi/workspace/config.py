import datetime
from pathlib import Path
from typing import Optional, List, Any

from pydantic import BaseModel, ConfigDict

from phi.schemas.workspace import WorkspaceSchema
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
    workspace_dir_path: Optional[Path] = None
    # Timestamp of when this workspace was created on the users machine
    create_ts: datetime.datetime = current_datetime_utc()

    # List of DockerResources
    docker_resources: Optional[List[Any]] = None
    # List of K8sResources
    k8s_resources: Optional[List[Any]] = None
    # List of AwsResources
    aws_resources: Optional[List[Any]] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def load(self) -> bool:
        if self.ws_root_path is None:
            raise Exception("Workspace root not set")

        from sys import path as sys_path
        from phi.workspace.helpers import get_workspace_dir_path
        from phi.utils.py_io import get_python_objects_from_module

        # NOTE: When loading a workspace, relative imports or package imports dont work.
        # This is a known problem in python
        #     eg: https://stackoverflow.com/questions/6323860/sibling-package-imports/50193944#50193944
        # To make them work, we add workspace_root to sys.path so is treated as a module
        logger.debug(f"Adding {self.ws_root_path} to path")
        sys_path.insert(0, str(self.ws_root_path))

        logger.debug("**--> Loading WorkspaceConfig")
        self.workspace_dir_path: Optional[Path] = get_workspace_dir_path(self.ws_root_path)
        if self.workspace_dir_path is not None:
            logger.debug(f"--^^-- Loading workspace from: {self.workspace_dir_path}")
            # Create a dict of objects in the workspace directory
            workspace_objects = {}
            resource_files = self.workspace_dir_path.rglob("*.py")
            for resource_file in resource_files:
                if resource_file.name == "__init__.py":
                    continue
                logger.debug(f"Reading file: {resource_file}")
                try:
                    python_objects = get_python_objects_from_module(resource_file)
                    logger.debug(f"python_objects: {python_objects}")
                    for obj_name, obj in python_objects.items():
                        _type_name = obj.__class__.__name__
                        if _type_name in [
                            "WorkspaceSettings",
                            "DockerResources",
                            "K8sResources",
                            "AwsResources",
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

            logger.debug(f"workspace_objects: {workspace_objects}")
            for obj_name, obj in workspace_objects.items():
                _obj_type = obj.__class__.__name__
                logger.debug(f"Adding {obj_name} | Type: {_obj_type}")
                if _obj_type == "WorkspaceSettings":
                    self.workspace_settings = obj
                elif _obj_type == "DockerResources":
                    if self.docker_resources is None:
                        self.docker_resources = []
                    self.docker_resources.append(obj)
                elif _obj_type == "K8sResources":
                    if self.k8s_resources is None:
                        self.k8s_resources = []
                    self.k8s_resources.append(obj)
                elif _obj_type == "AwsResources":
                    if self.aws_resources is None:
                        self.aws_resources = []
                    self.aws_resources.append(obj)

        logger.debug("**--> WorkspaceConfig loaded")
        return True

    def print_to_cli(self):
        from rich.pretty import pprint

        pprint(self.model_dump_json(indent=2))
