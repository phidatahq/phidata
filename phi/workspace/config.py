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
    name: str
    # WorkspaceSchema: This field indicates that the workspace is synced with the api
    schema: Optional[WorkspaceSchema] = None
    # The root directory for the workspace.
    # This field indicates that this ws has been downloaded on this machine
    workspace_root: Optional[Path] = None
    # Timestamp of when this workspace was created on the users machine
    create_ts: datetime.datetime = current_datetime_utc()

    # WorkspaceSettings
    workspace_settings: Optional[WorkspaceSettings] = None

    # List of DockerResources
    docker_resources: Optional[List[Any]] = None
    # List of K8sResources
    k8s_resources: Optional[List[Any]] = None
    # List of AwsResources
    aws_resources: Optional[List[Any]] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def load(self) -> bool:
        if self.workspace_root is None:
            raise Exception("Workspace root not set")

        # from phi.workspace.ws_loader import add_ws_dir_to_path, load_workspace
        #
        # # NOTE: When loading a workspace, relative imports or package imports dont work.
        # # This is a known problem in python :(
        # #     eg: https://stackoverflow.com/questions/6323860/sibling-package-imports/50193944#50193944
        # # To make them work, we add workspace_root to sys.path so is treated as a module
        # add_ws_dir_to_path(self.ws_root_path)
        #
        # logger.debug(f"**--> Loading WorkspaceConfig")
        # loaded_config: WorkspaceConfig = load_workspace(ws_root_path=self.ws_root_path)
        #
        # # Update cached_ws_config
        # self.cached_ws_config = loaded_config
        # self.cached_ws_config.workspace_root_path = self.ws_root_path
        # self.cached_ws_config.workspace_config_file_path = self.ws_config_file_path

        # logger.debug("WorkspaceConfig: {}".format(self.cached_ws_config.args))
        return True

    def print_to_cli(self):
        from rich.pretty import pprint

        pprint(self.model_dump_json(indent=2))
