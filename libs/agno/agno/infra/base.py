from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict

from agno.workspace.settings import WorkspaceSettings


class InfraBase(BaseModel):
    """Base class for all Infrastructure resources.

    Any Infrastructure Resource or App inherits from this class.
    """

    # Name of the resource
    name: Optional[str] = None
    # Group of the resource
    group: Optional[str] = None
    # Environment filter for this resource
    env: Optional[str] = None
    # Infrastructure filter for this resource
    infra: Optional[str] = None
    # Whether this resource is enabled
    enabled: bool = True

    #  -*- Resource Control
    skip_create: bool = False
    skip_read: bool = False
    skip_update: bool = False
    skip_delete: bool = False
    recreate_on_update: bool = False
    # Skip create if resource with the same name is active
    use_cache: bool = True
    # Force create/update/delete implementation
    force: Optional[bool] = None

    # -*- Wait for resource to be created, updated or deleted
    wait_for_create: bool = True
    wait_for_update: bool = True
    wait_for_delete: bool = True
    waiter_delay: int = 30
    waiter_max_attempts: int = 50

    # -*- Environment Variables for the resource (if applicable)
    # Add env variables to resource where applicable
    env_vars: Optional[Dict[str, Any]] = None
    # Read env from a file in yaml format
    env_file: Optional[Path] = None
    # Add secret variables to resource where applicable
    # secrets_dict: Optional[Dict[str, Any]] = None
    # Read secrets from a file in yaml format
    secrets_file: Optional[Path] = None
    # Read secret variables from AWS Secrets
    aws_secrets: Optional[Any] = None
    # -*- Debug Mode
    debug_mode: bool = False

    #  -*- Store resource to output directory
    # If True, save resource output to json files
    save_output: bool = False
    # The directory for the input files in the workspace directory
    input_dir: Optional[str] = None
    # The directory for the output files in the workspace directory
    output_dir: Optional[str] = None

    #  -*- Dependencies
    depends_on: Optional[List[Any]] = None

    # -*- Workspace Settings
    workspace_settings: Optional[WorkspaceSettings] = None

    # -*- Cached Data
    cached_env_file_data: Optional[Dict[str, Any]] = None
    cached_secret_file_data: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(arbitrary_types_allowed=True, populate_by_name=True)

    def get_group_name(self) -> Optional[str]:
        return self.group or self.name

    @property
    def workspace_root(self) -> Optional[Path]:
        return self.workspace_settings.ws_root if self.workspace_settings is not None else None

    @property
    def workspace_name(self) -> Optional[str]:
        return self.workspace_settings.ws_name if self.workspace_settings is not None else None

    def set_workspace_settings(self, workspace_settings: Optional[WorkspaceSettings] = None) -> None:
        if workspace_settings is not None:
            self.workspace_settings = workspace_settings

    def get_env_file_data(self) -> Optional[Dict[str, Any]]:
        if self.cached_env_file_data is None:
            from agno.utils.yaml_io import read_yaml_file

            self.cached_env_file_data = read_yaml_file(file_path=self.env_file)
        return self.cached_env_file_data

    def get_secret_file_data(self) -> Optional[Dict[str, Any]]:
        if self.cached_secret_file_data is None:
            from agno.utils.yaml_io import read_yaml_file

            self.cached_secret_file_data = read_yaml_file(file_path=self.secrets_file)
        return self.cached_secret_file_data

    def get_secret_from_file(self, secret_name: str) -> Optional[str]:
        secret_file_data = self.get_secret_file_data()
        if secret_file_data is not None:
            return secret_file_data.get(secret_name)
        return None
