from pathlib import Path
from typing import Any, Optional, Type, Union, Dict, List

from pydantic import BaseModel, validator

from phidata.utils.log import logger


class InfraResource(BaseModel):
    """Base class for all Phidata infrastructure resources.
    All Models in the phidata.*.resource modules are expected to be subclasses of this Model.

    We use a pydantic model for resources because the data which creates the resource
    may come from an external sources like users or an api.
    This data needs to be validated & type checked for which we use pydantic.
    """

    # name of resource
    name: Optional[str] = None
    # type of resource
    resource_type: Optional[str] = None

    # resource management
    # If True, skip resource creation if an active resources with the same name exists.
    use_cache: bool = True
    # Force the function to be implemented
    # i.e. force recreate, force delete, force update
    force: bool = False

    # If enabled=False: mark skip_create, skip_delete, skip_update as True
    enabled: bool = True
    # If True, phi does not create the resource
    skip_create: bool = False
    # If True, phi does not read the resource
    skip_read: bool = False
    # If True, phi does not update the resource
    skip_update: bool = False
    # If True, recreate the resource on update
    # Used for deployments with EBS volumes
    recreate_on_update: bool = False
    # If True, phi does not delete the resource
    skip_delete: bool = False

    # If True, waits for the resource to be created
    wait_for_creation: bool = True
    # If True, waits for the resource to be updated
    wait_for_update: bool = True
    # If True, waits for the resource to be deleted
    wait_for_deletion: bool = True
    # The amount of time in seconds to wait between attempts.
    waiter_delay: int = 30
    # The maximum number of attempts to be made.
    waiter_max_attempts: int = 50

    # Active resource object
    active_resource: Optional[Any] = None
    # Deprecated: the class of the active resource
    active_resource_class: Optional[Type] = None

    # If True, save the resource to a file
    save_output: bool = False
    resource_file: Optional[Union[str, Path]] = None
    # Add a resource directory to the resource file path
    resource_dir: Optional[str] = None

    # Other resources this resource depends on
    # Dependencies are always created if this resource is created
    depends_on: Optional[List[Any]] = None

    # Add secret variables to resource where applicable
    secret_data: Optional[Dict[str, Any]] = None
    # Read secrets from a file in yaml format
    secrets_file: Optional[Path] = None
    # Add env variables to resource where applicable
    env_data: Optional[Dict[str, Any]] = None
    # Read env from a file in yaml format
    env_file: Optional[Path] = None

    def get_resource_name(self) -> Optional[str]:
        return self.name

    def get_resource_type(self) -> Optional[str]:
        return self.resource_type

    @validator("force", pre=True, always=True)
    def set_force(cls, force):
        from os import getenv

        force = force or getenv("PHI_WS_FORCE", False)
        return force

    @validator("skip_create", pre=True, always=True)
    def set_skip_create(cls, skip_create, values):
        skip_resource = not values.get("enabled", True)
        return True if skip_resource else skip_create

    @validator("skip_update", pre=True, always=True)
    def set_skip_update(cls, skip_update, values):
        skip_resource = not values.get("enabled", True)
        return True if skip_resource else skip_update

    @validator("skip_delete", pre=True, always=True)
    def set_skip_delete(cls, skip_delete, values):
        skip_resource = not values.get("enabled", True)
        return True if skip_resource else skip_delete

    """
    ## Functions to be implemented by subclasses
    def create(self, infra_api_client: InfraApiClient) -> bool:
    def read(self, infra_api_client: InfraApiClient) -> bool:
    def update(self, infra_api_client: InfraApiClient) -> bool:
    def delete(self, infra_api_client: InfraApiClient) -> bool:
    def is_active(self, infra_api_client: InfraApiClient) -> bool:
    """

    class Config:
        # https://pydantic-docs.helpmanual.io/usage/model_config/
        # If we need to use an alias for fields of subclasses, eg: Kubeconfig
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        use_enum_values = True

    @staticmethod
    def get_workspace_config_file_path() -> Optional[Path]:
        from os import getenv
        from phidata.constants import WORKSPACE_CONFIG_FILE_ENV_VAR

        workspace_config_file_path = getenv(WORKSPACE_CONFIG_FILE_ENV_VAR, None)
        if workspace_config_file_path is not None:
            return Path(workspace_config_file_path)
        return None

    @staticmethod
    def get_workspace_root_path() -> Optional[Path]:
        from os import getenv
        from phidata.constants import WORKSPACE_ROOT_ENV_VAR

        workspace_root_path = getenv(WORKSPACE_ROOT_ENV_VAR, None)
        if workspace_root_path is not None:
            return Path(workspace_root_path)
        return None

    @staticmethod
    def get_workspace_config_dir() -> Optional[Path]:
        from os import getenv
        from phidata.constants import WORKSPACE_CONFIG_DIR_ENV_VAR

        workspace_config_dir = getenv(WORKSPACE_CONFIG_DIR_ENV_VAR, None)
        if workspace_config_dir is not None:
            return Path(workspace_config_dir)
        return None

    @staticmethod
    def get_workflows_dir() -> Optional[Path]:
        from os import getenv
        from phidata.constants import WORKFLOWS_DIR_ENV_VAR

        workflows_dir = getenv(WORKFLOWS_DIR_ENV_VAR, None)
        if workflows_dir is not None:
            return Path(workflows_dir)
        return None

    @staticmethod
    def get_meta_dir() -> Optional[Path]:
        from os import getenv
        from phidata.constants import META_DIR_ENV_VAR

        meta_dir = getenv(META_DIR_ENV_VAR, None)
        if meta_dir is not None:
            return Path(meta_dir)
        return None

    @staticmethod
    def get_notebooks_dir() -> Optional[Path]:
        from os import getenv
        from phidata.constants import NOTEBOOKS_DIR_ENV_VAR

        notebooks_dir = getenv(NOTEBOOKS_DIR_ENV_VAR, None)
        if notebooks_dir is not None:
            return Path(notebooks_dir)
        return None

    @staticmethod
    def get_products_dir() -> Optional[Path]:
        from os import getenv
        from phidata.constants import PRODUCTS_DIR_ENV_VAR

        products_dir = getenv(PRODUCTS_DIR_ENV_VAR, None)
        if products_dir is not None:
            return Path(products_dir)
        return None

    @staticmethod
    def get_scripts_dir() -> Optional[Path]:
        from os import getenv
        from phidata.constants import SCRIPTS_DIR_ENV_VAR

        scripts_dir = getenv(SCRIPTS_DIR_ENV_VAR, None)
        if scripts_dir is not None:
            return Path(scripts_dir)
        return None

    @staticmethod
    def get_storage_dir() -> Optional[Path]:
        from os import getenv
        from phidata.constants import STORAGE_DIR_ENV_VAR

        storage_dir = getenv(STORAGE_DIR_ENV_VAR, None)
        if storage_dir is not None:
            return Path(storage_dir)
        return None

    def read_yaml_file(self, file_path: Optional[Path]) -> Optional[Dict[str, Any]]:
        if file_path is not None and file_path.exists() and file_path.is_file():
            import yaml

            logger.debug(f"Reading {file_path}")
            data_from_file = yaml.safe_load(file_path.read_text())
            if data_from_file is not None and isinstance(data_from_file, dict):
                return data_from_file
            else:
                logger.error(f"Invalid file: {file_path}")
        return None

    def get_resource_file_path(self) -> Optional[Path]:
        if self.resource_file is None:
            workspace_config_dir = self.get_workspace_config_dir()
            if workspace_config_dir is not None:
                if self.name is not None and self.resource_type is not None:
                    file_name = f"{self.name}.json"
                    resource_dir = self.resource_dir or self.resource_type
                    return workspace_config_dir.joinpath(
                        "output", resource_dir, file_name
                    )
        if isinstance(self.resource_file, str):
            return Path(self.resource_file)
        elif isinstance(self.resource_file, Path):
            return self.resource_file
        return None

    def save_resource_file(self) -> bool:
        resource_file_path: Optional[Path] = self.get_resource_file_path()
        if resource_file_path is not None:
            try:
                from phidata.utils.json_io import write_json_file

                if not resource_file_path.exists():
                    resource_file_path.parent.mkdir(parents=True, exist_ok=True)
                    resource_file_path.touch(exist_ok=True)
                write_json_file(resource_file_path, self.active_resource)
                logger.info(f"Resource saved to: {str(resource_file_path)}")
                return True
            except Exception as e:
                logger.error(f"Could not write resource to file {e}")
        return False

    def read_resource_from_file(self) -> Optional[Dict[str, Any]]:
        resource_file_path: Optional[Path] = self.get_resource_file_path()
        if resource_file_path is not None:
            try:
                from phidata.utils.json_io import read_json_file

                if resource_file_path.exists() and resource_file_path.is_file():
                    data_from_file = read_json_file(resource_file_path)
                    if data_from_file is not None and isinstance(data_from_file, dict):
                        return data_from_file
                    else:
                        logger.warning(
                            f"Could not read {self.name} from {resource_file_path}"
                        )
            except Exception as e:
                logger.error(f"Could not read resource from file {e}")
        return None

    def delete_resource_file(self) -> bool:
        resource_file_path: Optional[Path] = self.get_resource_file_path()
        if resource_file_path is not None:
            try:
                if resource_file_path.exists() and resource_file_path.is_file():
                    resource_file_path.unlink()
                    logger.debug(f"Resource file deleted: {str(resource_file_path)}")
                    return True
            except Exception as e:
                logger.error(f"Could not delete resource file {e}")
        return False

    def attribute(self, name: str) -> Optional[Any]:
        resource_attributes = self.read_resource_from_file()
        if resource_attributes is not None:
            if name in resource_attributes:
                return resource_attributes[name]
            else:
                logger.warning(f"Resource attribute not found: {name}")
        return None

    def get_secret_data(self) -> Optional[Dict[str, str]]:
        if self.secret_data is not None:
            return self.secret_data

        if self.secrets_file is not None:
            self.secret_data = self.read_yaml_file(self.secrets_file)
        return self.secret_data

    def get_env_data(self) -> Optional[Dict[str, str]]:
        if self.env_data is not None:
            return self.env_data

        if self.env_file is not None:
            self.env_data = self.read_yaml_file(self.env_file)
        return self.env_data

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        if isinstance(other, InfraResource):
            if other.get_resource_type() == self.get_resource_type():
                return self.get_resource_name() == other.get_resource_name()
        return False
