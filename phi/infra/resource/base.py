from pathlib import Path
from typing import Any, Optional, Dict, List

from pydantic import ConfigDict

from phi.base import PhiBase
from phi.utils.log import logger


class InfraResource(PhiBase):
    # Resource name is required
    name: str
    # Resource type
    resource_type: Optional[str] = None
    # List of resource types to match against for filtering
    resource_type_list: Optional[List[str]] = None

    # -*- Cached Data
    active_resource: Optional[Any] = None
    resource_created: bool = False
    resource_updated: bool = False
    resource_deleted: bool = False

    model_config = ConfigDict(arbitrary_types_allowed=True, use_enum_values=True, populate_by_name=True)

    def get_resource_name(self) -> str:
        return self.name

    def get_resource_type(self) -> str:
        if self.resource_type is None:
            return self.__class__.__name__
        return self.resource_type

    def get_resource_type_list(self) -> List[str]:
        if self.resource_type_list is None:
            return [self.get_resource_type().lower()]

        type_list: List[str] = [resource_type.lower() for resource_type in self.resource_type_list]
        if self.get_resource_type() not in type_list:
            type_list.append(self.get_resource_type().lower())
        return type_list

    def get_output_file_path(self) -> Optional[Path]:
        workspace_dir: Optional[Path] = self.workspace_dir
        if workspace_dir is None:
            from phi.workspace.helpers import get_workspace_dir_from_env

            workspace_dir = get_workspace_dir_from_env()
        if workspace_dir is not None:
            resource_name: str = self.get_resource_name()
            if resource_name is not None:
                output_file_name = f"{resource_name}.json"
                output_dir = self.output_dir or self.get_resource_type()
                return workspace_dir.joinpath("output", output_dir.lower(), output_file_name)
        return None

    def save_output_file(self) -> bool:
        output_file_path: Optional[Path] = self.get_output_file_path()
        if output_file_path is not None:
            try:
                from phi.utils.json_io import write_json_file

                if not output_file_path.exists():
                    output_file_path.parent.mkdir(parents=True, exist_ok=True)
                    output_file_path.touch(exist_ok=True)
                write_json_file(output_file_path, self.active_resource)
                logger.info(f"Resource saved to: {str(output_file_path)}")
                return True
            except Exception as e:
                logger.error(f"Could not write {self.get_resource_name()} to file: {e}")
        return False

    def read_resource_from_file(self) -> Optional[Dict[str, Any]]:
        output_file_path: Optional[Path] = self.get_output_file_path()
        if output_file_path is not None:
            try:
                from phi.utils.json_io import read_json_file

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

    def matches_filters(
        self,
        group_filter: Optional[str] = None,
        name_filter: Optional[str] = None,
        type_filter: Optional[str] = None,
    ) -> bool:
        if group_filter is not None:
            group_name = self.get_group_name()
            logger.debug(f"Checking {group_filter} in {group_name}")
            if group_name is not None:
                if group_filter not in group_name:
                    return False
        if name_filter is not None:
            resource_name = self.get_resource_name()
            logger.debug(f"Checking {name_filter} in {resource_name}")
            if resource_name is not None:
                if name_filter not in resource_name:
                    return False
        if type_filter is not None:
            resource_type_list = self.get_resource_type_list()
            logger.debug(f"Checking {type_filter.lower()} in {resource_type_list}")
            if resource_type_list is not None:
                if type_filter.lower() not in resource_type_list:
                    return False
        return True

    def should_create(
        self,
        group_filter: Optional[str] = None,
        name_filter: Optional[str] = None,
        type_filter: Optional[str] = None,
    ) -> bool:
        if not self.enabled or self.skip_create:
            return False
        return self.matches_filters(group_filter, name_filter, type_filter)

    def should_delete(
        self,
        group_filter: Optional[str] = None,
        name_filter: Optional[str] = None,
        type_filter: Optional[str] = None,
    ) -> bool:
        if not self.enabled or self.skip_delete:
            return False
        return self.matches_filters(group_filter, name_filter, type_filter)

    def should_update(
        self,
        group_filter: Optional[str] = None,
        name_filter: Optional[str] = None,
        type_filter: Optional[str] = None,
    ) -> bool:
        if not self.enabled or self.skip_update:
            return False
        return self.matches_filters(group_filter, name_filter, type_filter)

    def __hash__(self):
        return hash(f"{self.get_resource_type()}:{self.get_resource_name()}")

    def __eq__(self, other):
        if isinstance(other, InfraResource):
            if other.get_resource_type() == self.get_resource_type():
                return self.get_resource_name() == other.get_resource_name()
        return False

    def create(self, client: Any) -> bool:
        raise NotImplementedError

    def read(self, client: Any) -> bool:
        raise NotImplementedError

    def update(self, client: Any) -> bool:
        raise NotImplementedError

    def delete(self, client: Any) -> bool:
        raise NotImplementedError

    def is_active(self, client: Any) -> bool:
        raise NotImplementedError
