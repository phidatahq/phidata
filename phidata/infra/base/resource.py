from pathlib import Path
from typing import Any, Optional, Type, Union

from pydantic import BaseModel, validator

from phidata.utils.log import logger


class InfraResource(BaseModel):
    """Base class for all Phidata infrastructure resources.
    All Models in the phidata.infra.*.resource modules are expected to be subclasses of this Model.

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

    # If enabled=False: mark skip_create, skip_delete, skip_update as True
    enabled: bool = True
    # If True, phi does not create the resource
    skip_create: bool = False
    # If True, phi does not read the resource
    skip_read: bool = False
    # If True, phi does not update the resource
    skip_update: bool = False
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

    active_resource: Optional[Any] = None
    active_resource_class: Optional[Type] = None

    resource_file: Optional[Union[str, Path]] = None

    def get_resource_name(self) -> Optional[str]:
        return self.name

    def get_resource_type(self) -> Optional[str]:
        return self.resource_type

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

    def save_resource_file(self) -> bool:

        if self.resource_file is not None:
            resource_file_path: Optional[Path] = None
            if isinstance(self.resource_file, str):
                resource_file_path = Path(self.resource_file)
            elif isinstance(self.resource_file, Path):
                resource_file_path = self.resource_file

            if resource_file_path is None or not isinstance(resource_file_path, Path):
                logger.error(f"Invalid resource_file: {resource_file_path}")

            try:
                if not resource_file_path.exists():
                    resource_file_path.parent.mkdir(parents=True, exist_ok=True)
                    resource_file_path.touch(exist_ok=True)
                resource_file_path.write_text(self.json(indent=2))
                logger.debug(f"Resource stored at: {str(resource_file_path)}")
                return True
            except Exception as e:
                logger.error("Could not write resource to file")
                logger.error(e)
        return False
