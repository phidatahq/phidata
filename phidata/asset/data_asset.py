from pathlib import Path
from typing import Optional, Any, Union, List, Dict

from phidata.base import PhidataBase, PhidataBaseArgs
from phidata.task import Task
from phidata.check import Check
from phidata.types.phidata_runtime import (
    PhidataRuntimeType,
    get_phidata_runtime,
)
from phidata.utils.enums import ExtendedEnum
from phidata.utils.log import logger


class DataLoader(ExtendedEnum):
    pandas = "pandas"
    pyarrow = "pyarrow"


class DataAssetArgs(PhidataBaseArgs):
    # local, docker or kubernetes
    phidata_runtime: Optional[PhidataRuntimeType] = None

    # Checks to run before creating the table
    pre_checks: Optional[List[Check]] = None
    # List of tasks to create the table
    create_tasks: Optional[List[Task]] = None
    # Checks to run after creating the table
    post_checks: Optional[List[Check]] = None

    # List of tasks to update the table
    update_tasks: Optional[List[Task]] = None

    # List of tasks to delete the table
    delete_tasks: Optional[List[Task]] = None

    # Control which environment the table is created in
    env: Optional[str] = None

    # Dev Args
    dev_name: Optional[str] = None
    dev_env: Optional[Dict[str, Any]] = None
    seed_dev_tasks: Optional[List[Task]] = None
    dev_stg_swap_tasks: Optional[List[Task]] = None

    # Staging Args
    stg_name: Optional[str] = None
    stg_env: Optional[Dict[str, Any]] = None
    seed_stg_tasks: Optional[List[Task]] = None
    stg_prd_swap_tasks: Optional[List[Task]] = None

    # Production Args
    prd_name: Optional[str] = None
    prd_env: Optional[Dict[str, Any]] = None

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

    # If True, continues running even if an error occurs during the creation of the resource
    continue_on_create_failure: Optional[bool] = None
    # If True, continues running even if an error occurs during the deletion of the resource
    # Defaults to True because we do not want deletion to be a blocking function
    continue_on_delete_failure: Optional[bool] = True
    # If True, continues running even if an error occurs during the update of the resource
    continue_on_update_failure: Optional[bool] = None

    # A cache for the active resource details
    active_resource: Optional[Any] = None
    # File to store the resource data
    resource_file: Optional[Union[str, Path]] = None

    # -*- Path parameters

    # The storage_dir_path is a local directory which is available
    # for use by the data asset.
    # For a file, it could be used as the base directory
    # For a URL, it could be used for temporary storage
    # Default is $WORKSPACE_ROOT/storage and
    # the absolute path depends on the environment (local vs container)
    # This is built using the storage_dir relative path
    storage_dir_path: Optional[Path] = None

    # Path to the workspace root directory
    workspace_root_path: Optional[Path] = None

    # Path to the workspace config file
    workspace_config_file_path: Optional[Path] = None

    meta_dir: Optional[Path] = None
    notebooks_dir: Optional[Path] = None
    products_dir: Optional[Path] = None
    scripts_dir: Optional[Path] = None
    workflows_dir: Optional[Path] = None
    workspace_config_dir: Optional[Path] = None


class DataAsset(PhidataBase):
    """Base Class for all DataAssets"""

    def __init__(self) -> None:
        super().__init__()
        self.resource_created: bool = False
        self.resource_updated: bool = False
        self.resource_deleted: bool = False
        self.args: Optional[DataAssetArgs] = None

    @property
    def phidata_runtime(self) -> Optional[PhidataRuntimeType]:
        # data_asset not yet initialized
        if self.args is None:
            return PhidataRuntimeType.local

        if self.args.phidata_runtime:
            # use cached value if available
            return self.args.phidata_runtime

        self.args.phidata_runtime = get_phidata_runtime()
        return self.args.phidata_runtime

    @phidata_runtime.setter
    def phidata_runtime(self, phidata_runtime: PhidataRuntimeType) -> None:
        if self.args is not None and phidata_runtime is not None:
            self.args.phidata_runtime = phidata_runtime

    @property
    def pre_checks(self) -> Optional[List[Check]]:
        return self.args.pre_checks if self.args else None

    @pre_checks.setter
    def pre_checks(self, pre_checks: List[Check]) -> None:
        if self.args and pre_checks:
            self.args.pre_checks = pre_checks

    @property
    def create_tasks(self) -> Optional[List[Task]]:
        return self.args.create_tasks if self.args else None

    @create_tasks.setter
    def create_tasks(self, create_tasks: List[Task]) -> None:
        if self.args and create_tasks:
            self.args.create_tasks = create_tasks

    @property
    def post_checks(self) -> Optional[List[Check]]:
        return self.args.post_checks if self.args else None

    @post_checks.setter
    def post_checks(self, post_checks: List[Check]) -> None:
        if self.args and post_checks:
            self.args.post_checks = post_checks

    @property
    def update_tasks(self) -> Optional[List[Task]]:
        return self.args.update_tasks if self.args else None

    @update_tasks.setter
    def update_tasks(self, update_tasks: List[Task]) -> None:
        if self.args and update_tasks:
            self.args.update_tasks = update_tasks

    @property
    def delete_tasks(self) -> Optional[List[Task]]:
        return self.args.delete_tasks if self.args else None

    @delete_tasks.setter
    def delete_tasks(self, delete_tasks: List[Task]) -> None:
        if self.args and delete_tasks:
            self.args.delete_tasks = delete_tasks

    @property
    def env(self) -> Optional[str]:
        return self.args.env if self.args else None

    @env.setter
    def env(self, env: str) -> None:
        if self.args and env:
            self.args.env = env

    @property
    def dev_name(self) -> Optional[str]:
        return self.args.dev_name if self.args else None

    @dev_name.setter
    def dev_name(self, dev_name: str) -> None:
        if self.args and dev_name:
            self.args.dev_name = dev_name

    @property
    def dev_env(self) -> Optional[Dict[str, Any]]:
        return self.args.dev_env if self.args else None

    @dev_env.setter
    def dev_env(self, dev_env: Dict[str, Any]) -> None:
        if self.args and dev_env:
            self.args.dev_env = dev_env

    @property
    def seed_dev_tasks(self) -> Optional[List[Task]]:
        return self.args.seed_dev_tasks if self.args else None

    @seed_dev_tasks.setter
    def seed_dev_tasks(self, seed_dev_tasks: List[Task]) -> None:
        if self.args and seed_dev_tasks:
            self.args.seed_dev_tasks = seed_dev_tasks

    @property
    def dev_stg_swap_tasks(self) -> Optional[List[Task]]:
        return self.args.dev_stg_swap_tasks if self.args else None

    @dev_stg_swap_tasks.setter
    def dev_stg_swap_tasks(self, dev_stg_swap_tasks: List[Task]) -> None:
        if self.args and dev_stg_swap_tasks:
            self.args.dev_stg_swap_tasks = dev_stg_swap_tasks

    @property
    def stg_name(self) -> Optional[str]:
        return self.args.stg_name if self.args else None

    @stg_name.setter
    def stg_name(self, stg_name: str) -> None:
        if self.args and stg_name:
            self.args.stg_name = stg_name

    @property
    def stg_env(self) -> Optional[Dict[str, Any]]:
        return self.args.stg_env if self.args else None

    @stg_env.setter
    def stg_env(self, stg_env: Dict[str, Any]) -> None:
        if self.args and stg_env:
            self.args.stg_env = stg_env

    @property
    def seed_stg_tasks(self) -> Optional[List[Task]]:
        return self.args.seed_stg_tasks if self.args else None

    @seed_stg_tasks.setter
    def seed_stg_tasks(self, seed_stg_tasks: List[Task]) -> None:
        if self.args and seed_stg_tasks:
            self.args.seed_stg_tasks = seed_stg_tasks

    @property
    def stg_prd_swap_tasks(self) -> Optional[List[Task]]:
        return self.args.stg_prd_swap_tasks if self.args else None

    @stg_prd_swap_tasks.setter
    def stg_prd_swap_tasks(self, stg_prd_swap_tasks: List[Task]) -> None:
        if self.args and stg_prd_swap_tasks:
            self.args.stg_prd_swap_tasks = stg_prd_swap_tasks

    @property
    def prd_name(self) -> Optional[str]:
        return self.args.prd_name if self.args else None

    @prd_name.setter
    def prd_name(self, prd_name: str) -> None:
        if self.args and prd_name:
            self.args.prd_name = prd_name

    @property
    def prd_env(self) -> Optional[Dict[str, Any]]:
        return self.args.prd_env if self.args else None

    @prd_env.setter
    def prd_env(self, prd_env: Dict[str, Any]) -> None:
        if self.args and prd_env:
            self.args.prd_env = prd_env

    @property
    def skip_create(self) -> Optional[bool]:
        return self.args.skip_create if self.args else None

    @skip_create.setter
    def skip_create(self, skip_create: bool) -> None:
        if self.args is not None and skip_create is not None:
            self.args.skip_create = skip_create

    @property
    def skip_read(self) -> Optional[bool]:
        return self.args.skip_read if self.args else None

    @skip_read.setter
    def skip_read(self, skip_read: bool) -> None:
        if self.args is not None and skip_read is not None:
            self.args.skip_read = skip_read

    @property
    def skip_update(self) -> Optional[bool]:
        return self.args.skip_update if self.args else None

    @skip_update.setter
    def skip_update(self, skip_update: bool) -> None:
        if self.args is not None and skip_update is not None:
            self.args.skip_update = skip_update

    @property
    def skip_delete(self) -> Optional[bool]:
        return self.args.skip_delete if self.args else None

    @skip_delete.setter
    def skip_delete(self, skip_delete: bool) -> None:
        if self.args is not None and skip_delete is not None:
            self.args.skip_delete = skip_delete

    @property
    def wait_for_creation(self) -> Optional[bool]:
        return self.args.wait_for_creation if self.args else None

    @wait_for_creation.setter
    def wait_for_creation(self, wait_for_creation: bool) -> None:
        if self.args is not None and wait_for_creation is not None:
            self.args.wait_for_creation = wait_for_creation

    @property
    def wait_for_update(self) -> Optional[bool]:
        return self.args.wait_for_update if self.args else None

    @wait_for_update.setter
    def wait_for_update(self, wait_for_update: bool) -> None:
        if self.args is not None and wait_for_update is not None:
            self.args.wait_for_update = wait_for_update

    @property
    def wait_for_deletion(self) -> Optional[bool]:
        return self.args.wait_for_deletion if self.args else None

    @wait_for_deletion.setter
    def wait_for_deletion(self, wait_for_deletion: bool) -> None:
        if self.args is not None and wait_for_deletion is not None:
            self.args.wait_for_deletion = wait_for_deletion

    @property
    def waiter_delay(self) -> Optional[int]:
        return self.args.waiter_delay if self.args else None

    @waiter_delay.setter
    def waiter_delay(self, waiter_delay: int) -> None:
        if self.args is not None and waiter_delay is not None:
            self.args.waiter_delay = waiter_delay

    @property
    def waiter_max_attempts(self) -> Optional[int]:
        return self.args.waiter_max_attempts if self.args else None

    @waiter_max_attempts.setter
    def waiter_max_attempts(self, waiter_max_attempts: int) -> None:
        if self.args is not None and waiter_max_attempts is not None:
            self.args.waiter_max_attempts = waiter_max_attempts

    @property
    def continue_on_create_failure(self) -> Optional[bool]:
        return self.args.continue_on_create_failure if self.args else None

    @continue_on_create_failure.setter
    def continue_on_create_failure(self, continue_on_create_failure: bool) -> None:
        if self.args is not None and continue_on_create_failure is not None:
            self.args.continue_on_create_failure = continue_on_create_failure

    @property
    def continue_on_delete_failure(self) -> Optional[bool]:
        return self.args.continue_on_delete_failure if self.args else None

    @continue_on_delete_failure.setter
    def continue_on_delete_failure(self, continue_on_delete_failure: bool) -> None:
        if self.args is not None and continue_on_delete_failure is not None:
            self.args.continue_on_delete_failure = continue_on_delete_failure

    @property
    def continue_on_update_failure(self) -> Optional[bool]:
        return self.args.continue_on_update_failure if self.args else None

    @continue_on_update_failure.setter
    def continue_on_update_failure(self, continue_on_update_failure: bool) -> None:
        if self.args is not None and continue_on_update_failure is not None:
            self.args.continue_on_update_failure = continue_on_update_failure

    @property
    def active_resource(self) -> Optional[Any]:
        return self.args.active_resource if self.args else None

    @active_resource.setter
    def active_resource(self, active_resource: Any) -> None:
        if self.args is not None and active_resource is not None:
            self.args.active_resource = active_resource

    @property
    def resource_file(self) -> Optional[Union[str, Path]]:
        return self.args.resource_file if self.args else None

    @resource_file.setter
    def resource_file(self, resource_file: Union[str, Path]) -> None:
        if self.args is not None and resource_file is not None:
            self.args.resource_file = resource_file

    @property
    def storage_dir_path(self) -> Optional[Path]:
        """
        Returns the STORAGE_DIR for the data_asset.
        This base dir depends on the environment (local vs container)
        """
        # data_asset not yet initialized
        if self.args is None:
            return None

        if self.args.storage_dir_path:
            # use cached value if available
            return self.args.storage_dir_path

        from os import getenv
        from phidata.constants import STORAGE_DIR_ENV_VAR

        storage_dir = getenv(STORAGE_DIR_ENV_VAR, None)
        if storage_dir is not None:
            self.args.storage_dir_path = Path(storage_dir)
        return self.args.storage_dir_path

    @storage_dir_path.setter
    def storage_dir_path(self, storage_dir_path: Optional[Path]) -> None:
        if self.args is not None and storage_dir_path is not None:
            self.args.storage_dir_path = storage_dir_path

    @property
    def workspace_root_path(self) -> Optional[Path]:
        # data_asset not yet initialized
        if self.args is None:
            return None

        if self.args.workspace_root_path:
            # use cached value if available
            return self.args.workspace_root_path

        from os import getenv
        from phidata.constants import WORKSPACE_ROOT_ENV_VAR

        workspace_root_path = getenv(WORKSPACE_ROOT_ENV_VAR, None)
        if workspace_root_path is not None:
            self.args.workspace_root_path = Path(workspace_root_path)
        return self.args.workspace_root_path

    @workspace_root_path.setter
    def workspace_root_path(self, workspace_root_path: Optional[Path]) -> None:
        if self.args is not None and workspace_root_path is not None:
            self.args.workspace_root_path = workspace_root_path

    @property
    def workspace_config_file_path(self) -> Optional[Path]:
        # data_asset not yet initialized
        if self.args is None:
            return None

        if self.args.workspace_config_file_path:
            # use cached value if available
            return self.args.workspace_config_file_path

        from os import getenv
        from phidata.constants import WORKSPACE_CONFIG_FILE_ENV_VAR

        workspace_config_file_path = getenv(WORKSPACE_CONFIG_FILE_ENV_VAR, None)
        if workspace_config_file_path is not None:
            self.args.workspace_config_file_path = Path(workspace_config_file_path)
        return self.args.workspace_config_file_path

    @workspace_config_file_path.setter
    def workspace_config_file_path(
        self, workspace_config_file_path: Optional[Path]
    ) -> None:
        if self.args is not None and workspace_config_file_path is not None:
            self.args.workspace_config_file_path = workspace_config_file_path

    @property
    def meta_dir(self) -> Optional[Path]:
        # data_asset not yet initialized
        if self.args is None:
            return None

        if self.args.meta_dir:
            # use cached value if available
            return self.args.meta_dir

        from os import getenv
        from phidata.constants import META_DIR_ENV_VAR

        meta_dir = getenv(META_DIR_ENV_VAR, None)
        if meta_dir is not None:
            self.args.meta_dir = Path(meta_dir)
        return self.args.meta_dir

    @meta_dir.setter
    def meta_dir(self, meta_dir: Optional[Path]) -> None:
        if self.args is not None and meta_dir is not None:
            self.args.meta_dir = meta_dir

    @property
    def notebooks_dir(self) -> Optional[Path]:
        # data_asset not yet initialized
        if self.args is None:
            return None

        if self.args.notebooks_dir:
            # use cached value if available
            return self.args.notebooks_dir

        from os import getenv
        from phidata.constants import NOTEBOOKS_DIR_ENV_VAR

        notebooks_dir = getenv(NOTEBOOKS_DIR_ENV_VAR, None)
        if notebooks_dir is not None:
            self.args.notebooks_dir = Path(notebooks_dir)
        return self.args.notebooks_dir

    @notebooks_dir.setter
    def notebooks_dir(self, notebooks_dir: Optional[Path]) -> None:
        if self.args is not None and notebooks_dir is not None:
            self.args.notebooks_dir = notebooks_dir

    @property
    def products_dir(self) -> Optional[Path]:
        # data_asset not yet initialized
        if self.args is None:
            return None

        if self.args.products_dir:
            # use cached value if available
            return self.args.products_dir

        from os import getenv
        from phidata.constants import PRODUCTS_DIR_ENV_VAR

        products_dir = getenv(PRODUCTS_DIR_ENV_VAR, None)
        if products_dir is not None:
            self.args.products_dir = Path(products_dir)
        return self.args.products_dir

    @products_dir.setter
    def products_dir(self, products_dir: Optional[Path]) -> None:
        if self.args is not None and products_dir is not None:
            self.args.products_dir = products_dir

    @property
    def scripts_dir(self) -> Optional[Path]:
        # data_asset not yet initialized
        if self.args is None:
            return None

        if self.args.scripts_dir:
            # use cached value if available
            return self.args.scripts_dir

        from os import getenv
        from phidata.constants import SCRIPTS_DIR_ENV_VAR

        scripts_dir = getenv(SCRIPTS_DIR_ENV_VAR, None)
        if scripts_dir is not None:
            self.args.scripts_dir = Path(scripts_dir)
        return self.args.scripts_dir

    @scripts_dir.setter
    def scripts_dir(self, scripts_dir: Optional[Path]) -> None:
        if self.args is not None and scripts_dir is not None:
            self.args.scripts_dir = scripts_dir

    @property
    def workflows_dir(self) -> Optional[Path]:
        # data_asset not yet initialized
        if self.args is None:
            return None

        if self.args.workflows_dir:
            # use cached value if available
            return self.args.workflows_dir

        from os import getenv
        from phidata.constants import WORKFLOWS_DIR_ENV_VAR

        workflows_dir = getenv(WORKFLOWS_DIR_ENV_VAR, None)
        if workflows_dir is not None:
            self.args.workflows_dir = Path(workflows_dir)
        return self.args.workflows_dir

    @workflows_dir.setter
    def workflows_dir(self, workflows_dir: Optional[Path]) -> None:
        if self.args is not None and workflows_dir is not None:
            self.args.workflows_dir = workflows_dir

    @property
    def workspace_config_dir(self) -> Optional[Path]:
        # data_asset not yet initialized
        if self.args is None:
            return None

        if self.args.workspace_config_dir:
            # use cached value if available
            return self.args.workspace_config_dir

        from os import getenv
        from phidata.constants import WORKSPACE_CONFIG_DIR_ENV_VAR

        workspace_config_dir = getenv(WORKSPACE_CONFIG_DIR_ENV_VAR, None)
        if workspace_config_dir is not None:
            self.args.workspace_config_dir = Path(workspace_config_dir)
        return self.args.workspace_config_dir

    @workspace_config_dir.setter
    def workspace_config_dir(self, workspace_config_dir: Optional[Path]) -> None:
        if self.args is not None and workspace_config_dir is not None:
            self.args.workspace_config_dir = workspace_config_dir

    ######################################################
    ## Build data asset
    ######################################################

    def build(self) -> bool:
        logger.debug(f"@build not defined for {self.__class__.__name__}")
        return False

    ######################################################
    ## Create DataAsset
    ######################################################

    def is_valid(self) -> bool:
        # DataAssets can use this function to add validation checks
        return True

    def _create(self) -> bool:
        logger.error(f"@_create not defined for {self.__class__.__name__}")
        return False

    def create(self) -> bool:
        # Step 1: Check if resource is valid
        if not self.is_valid():
            return False

        # Step 2: Skip resource creation if skip_create = True
        if self.skip_create:
            logger.debug(f"Skipping create: {self.name}")
            return True

        # Step 3: Create the resource
        self.resource_created = self._create()

        # Step 5: Run post create steps
        if self.resource_created:
            logger.debug(f"Running post-create steps for {self.name}.")
            return self.post_create()
        return self.resource_created

    def post_create(self) -> bool:
        # return True because this function is not used for most resources
        return True

    def write_pandas_df(self, df: Any = None) -> bool:
        logger.debug(f"@write_pandas_df not defined for {self.__class__.__name__}")
        return False

    ######################################################
    ## Read DataAsset
    ######################################################

    def read_pandas_df(self) -> Optional[Any]:
        logger.debug(f"@read_pandas_df not defined for {self.__class__.__name__}")
        return False

    def _read(self) -> Any:
        logger.error(f"@_read not defined for {self.__class__.__name__}")
        return False

    def read(self) -> Any:
        # Step 1: Check if resource is valid
        if not self.is_valid():
            return None

        # Step 2: Skip resource read if skip_read = True
        if self.skip_read:
            logger.debug(f"Skipping read: {self.name}")
            return True

        # Step 3: Read resource
        return self._read()

    ######################################################
    ## Update DataAsset
    ######################################################

    def update_pandas_df(self) -> Optional[Any]:
        logger.debug(f"@update_pandas_df not defined for {self.__class__.__name__}")
        return False

    def _update(self) -> Any:
        logger.error(f"@_update not defined for {self.__class__.__name__}")
        return False

    def update(self) -> bool:
        # Step 1: Check if resource is valid
        if not self.is_valid():
            return False

        # Step 2: Skip resource update if skip_update = True
        if self.skip_update:
            logger.debug(f"Skipping update: {self.name}")
            return True

        # Step 3: Update the resource
        self.resource_updated = self._update()

        # Step 4: Run post update steps
        if self.resource_updated:
            logger.debug(f"Running post-update steps for {self.name}.")
            return self.post_update()
        return self.resource_updated

    def post_update(self) -> bool:
        # return True because this function is not used for most resources
        return True

    ######################################################
    ## Delete DataAsset
    ######################################################

    def _delete(self) -> Any:
        logger.error(f"@_delete not defined for {self.__class__.__name__}")
        return False

    def delete(self) -> bool:
        # Step 1: Check if resource is valid
        if not self.is_valid():
            return False

        # Step 2: Skip resource deletion if skip_delete = True
        if self.skip_delete:
            logger.debug(f"Skipping delete: {self.name}")
            return True

        # Step 3: Delete the resource
        self.resource_deleted = self._delete()

        # Step 4: Run post delete steps
        if self.resource_deleted:
            logger.debug(f"Running post-delete steps for {self.name}.")
            return self.post_delete()
        return self.resource_deleted

    def post_delete(self) -> bool:
        # return True because this function is not used for most resources
        return True

    ######################################################
    ## Print
    ######################################################

    def __str__(self) -> str:
        if self.args is not None:
            return self.args.json(indent=2, exclude_none=True, exclude={"enabled"})
        else:
            return self.__class__.__name__

    def save_to_file(self) -> bool:

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
                    # resource_file_path.touch(exist_ok=True)

                if self.args is not None:
                    resource_file_path.write_text(
                        self.args.json(
                            indent=2,
                            exclude_none=True,
                            exclude_defaults=True,
                            exclude_unset=True,
                        )
                    )
                logger.debug(f"Resource stored at: {str(resource_file_path)}")
                return True
            except Exception as e:
                logger.error("Could not write resource to file")
                logger.error(e)
        return False
