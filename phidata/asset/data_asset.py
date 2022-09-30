from pathlib import Path
from typing import Optional, Any

from phidata.base import PhidataBase, PhidataBaseArgs
from phidata.constants import STORAGE_DIR_ENV_VAR, META_DIR_ENV_VAR
from phidata.types.phidata_runtime import (
    PhidataRuntimeType,
    get_phidata_runtime,
)
from phidata.utils.log import logger


class DataAssetArgs(PhidataBaseArgs):
    # local, docker or kubernetes
    phidata_runtime: Optional[PhidataRuntimeType] = None

    # The storage_dir_path is a local directory which is available
    # for use by the data asset.
    # For a file, it could be used as the base directory
    # For a URL, it could be used for temporary storage
    # Default is $WORKSPACE_ROOT/storage and
    # the absolute path depends on the environment (local vs container)
    storage_dir_path: Optional[Path] = None
    metadata_dir_path: Optional[Path] = None


class DataAsset(PhidataBase):
    """Base Class for all DataAssets"""

    def __init__(self) -> None:
        super().__init__()
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

        storage_dir_env = getenv(STORAGE_DIR_ENV_VAR)
        # logger.debug(f"{STORAGE_DIR_ENV_VAR}: {storage_dir_env}")
        if storage_dir_env is not None:
            self.args.storage_dir_path = Path(storage_dir_env)
        return self.args.storage_dir_path

    @storage_dir_path.setter
    def storage_dir_path(self, storage_dir_path: Optional[Path]) -> None:
        if self.args is not None and storage_dir_path is not None:
            self.args.storage_dir_path = storage_dir_path

    @property
    def metadata_dir_path(self) -> Optional[Path]:
        """
        Returns the META_DIR_ENV_VAR for the data_asset.
        """
        # data_asset not yet initialized
        if self.args is None:
            return None

        if self.args.metadata_dir_path:
            # use cached value if available
            return self.args.metadata_dir_path

        from os import getenv

        meta_dir_env = getenv(META_DIR_ENV_VAR)
        # logger.debug(f"{META_DIR_ENV_VAR}: {meta_dir_env}")
        if meta_dir_env is not None:
            self.args.metadata_dir_path = Path(meta_dir_env)
        return self.args.metadata_dir_path

    @metadata_dir_path.setter
    def metadata_dir_path(self, metadata_dir_path: Optional[Path]) -> None:
        if self.args is not None and metadata_dir_path is not None:
            self.args.metadata_dir_path = metadata_dir_path

    ######################################################
    ## Build and validate data asset
    ######################################################

    def build(self) -> bool:
        logger.debug(f"@build not defined for {self.__class__.__name__}")
        return False

    ######################################################
    ## Write DataAsset
    ######################################################

    def write_pandas_df(self, df: Any = None) -> bool:
        logger.debug(f"@write_pandas_df not defined for {self.__class__.__name__}")
        return False

    ######################################################
    ## Read DataAsset
    ######################################################

    def read_pandas_df(self) -> Optional[Any]:
        logger.debug(f"@read_pandas_df not defined for {self.__class__.__name__}")
        return False

    ######################################################
    ## Delete DataAsset
    ######################################################

    def delete(self) -> bool:
        logger.debug(f"@delete not defined for {self.__class__.__name__}")
        return False

    ######################################################
    ## Print
    ######################################################

    def __str__(self) -> str:
        if self.args is not None:
            return self.args.json(indent=2, exclude_none=True, exclude={"enabled"})
        else:
            return self.__class__.__name__
