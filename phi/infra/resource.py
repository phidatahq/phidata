from pathlib import Path
from typing import Any, Optional, Union, Dict, List

from pydantic import ConfigDict

from phi.base import PhiBase
from phi.utils.log import logger


class InfraResource(PhiBase):
    # Resource name is required
    name: str
    # Resource type
    resource_type: Optional[str] = None
    # Resource type filters
    resource_type_filters: Optional[List[str]] = None

    # -*- Resource Environment
    # Add env variables to resource where applicable
    env: Optional[Dict[str, Any]] = None
    # Read env from a file in yaml format
    env_file: Optional[Path] = None
    # Add secret variables to resource where applicable
    secrets: Optional[Dict[str, Any]] = None
    # Read secrets from a file in yaml format
    secrets_file: Optional[Path] = None

    # -*- Save resource output
    # If True, save output to a json file
    save_output: bool = False
    # The file to save the output to
    output_file: Optional[Union[str, Path]] = None
    # The directory for the output files
    output_dir: Optional[str] = None

    # -*- Cached Data
    cached_resource: Optional[Any] = None
    cached_env_file_data: Optional[Dict[str, Any]] = None
    cached_secret_file_data: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(arbitrary_types_allowed=True, use_enum_values=True, populate_by_name=True)

    def get_resource_name(self) -> str:
        return self.name

    def get_resource_type(self) -> str:
        if self.resource_type is None:
            return self.__class__.__name__
        return self.resource_type

    def get_output_file_path(self) -> Optional[Path]:
        if self.output_file is None:
            from phi.workspace.helpers import get_workspace_dir_from_env

            workspace_dir = get_workspace_dir_from_env()
            if workspace_dir is not None:
                if self.get_resource_name() is not None:
                    _output_fn = f"{self.get_resource_name()}.json"
                    output_dir = self.output_dir or self.get_resource_type()
                    return workspace_dir.joinpath("output", output_dir, _output_fn)

        if isinstance(self.output_file, str):
            return Path(self.output_file)
        elif isinstance(self.output_file, Path):
            return self.output_file
        return None

    def save_output_file(self) -> bool:
        output_file_path: Optional[Path] = self.get_output_file_path()
        if output_file_path is not None:
            try:
                from phidata.utils.json_io import write_json_file

                if not output_file_path.exists():
                    output_file_path.parent.mkdir(parents=True, exist_ok=True)
                    output_file_path.touch(exist_ok=True)
                write_json_file(output_file_path, self.cached_resource)
                logger.info(f"Resource saved to: {str(output_file_path)}")
                return True
            except Exception as e:
                logger.error(f"Could not write {self.get_resource_name()} to file: {e}")
        return False

    def read_resource_from_file(self) -> Optional[Dict[str, Any]]:
        output_file_path: Optional[Path] = self.get_output_file_path()
        if output_file_path is not None:
            try:
                from phidata.utils.json_io import read_json_file

                if output_file_path.exists() and output_file_path.is_file():
                    data_from_file = read_json_file(output_file_path)
                    if data_from_file is not None and isinstance(data_from_file, dict):
                        return data_from_file
                    else:
                        logger.warning(f"Could not read {self.get_resource_name()} from {output_file_path}")
            except Exception as e:
                logger.error(f"Could not read {self.get_resource_name()} from file: {e}")
        return None

    def delete_output_file(self) -> bool:
        output_file_path: Optional[Path] = self.get_output_file_path()
        if output_file_path is not None:
            try:
                if output_file_path.exists() and output_file_path.is_file():
                    output_file_path.unlink()
                    logger.debug(f"Output file deleted: {str(output_file_path)}")
                    return True
            except Exception as e:
                logger.error(f"Could not delete output file: {e}")
        return False

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

    def __hash__(self):
        return hash(self.get_resource_name())

    def __eq__(self, other):
        if isinstance(other, InfraResource):
            if other.get_resource_type() == self.get_resource_type():
                return self.get_resource_name() == other.get_resource_name()
        return False

    """
    ## Functions to be implemented by subclasses
    def create(self, api_client: ApiClient) -> bool:
    def read(self, api_client: ApiClient) -> bool:
    def update(self, api_client: ApiClient) -> bool:
    def delete(self, api_client: ApiClient) -> bool:
    def is_active(self, api_client: ApiClient) -> bool:
    """
