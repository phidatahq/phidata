from pathlib import Path
from typing import Optional, Any, Literal, cast

from phidata.base import PhidataBase, PhidataBaseArgs
from phidata.constants import STORAGE_DIR_ENV_VAR, PHIDATA_RUNTIME_ENV_VAR
from phidata.utils.log import logger


class DataAssetArgs(PhidataBaseArgs):
    # The base_dir_path is the root dir for the data_asset.
    # Normally corresponds to $WORKSPACE_ROOT/storage
    # This path depends on the environment (local vs container) and is
    # used by the data_asset to build the absolute path in different environments
    base_dir_path: Optional[Path] = None
    phidata_runtime: Optional[Literal["local", "airflow"]] = None


class DataAsset(PhidataBase):
    """Base Class for all DataAssets"""

    def __init__(self) -> None:
        super().__init__()
        self.args: Optional[DataAssetArgs] = None

    @property
    def base_dir_path(self) -> Optional[Path]:
        """
        Returns the base dir for the data_asset.
        This base dir depends on the environment (local vs container) and is
        used by the data_asset to build the absolute path.
        """
        # data_asset not yet initialized
        if self.args is None:
            return None

        if self.args.base_dir_path:
            # use cached value if available
            return self.args.base_dir_path

        import os

        storage_dir_env = os.getenv(STORAGE_DIR_ENV_VAR)
        # logger.debug(f"{STORAGE_DIR_ENV_VAR}: {storage_dir_env}")
        if storage_dir_env is not None:
            self.args.base_dir_path = Path(storage_dir_env)
        return self.args.base_dir_path

    @base_dir_path.setter
    def base_dir_path(self, base_dir_path: Optional[Path]) -> None:
        if self.args is not None and base_dir_path is not None:
            self.args.base_dir_path = base_dir_path

    @property
    def phidata_runtime(self) -> Literal["local", "airflow"]:
        # data_asset not yet initialized
        if self.args is None:
            return "local"

        if self.args.phidata_runtime:
            # use cached value if available
            return self.args.phidata_runtime

        import os

        phidata_runtime_env = os.getenv(PHIDATA_RUNTIME_ENV_VAR)
        # logger.debug(f"{PHIDATA_RUNTIME_ENV_VAR}: {phidata_runtime_env}")
        if phidata_runtime_env is not None and phidata_runtime_env in (
            "local",
            "airflow",
        ):
            phidata_runtime_env = cast(Literal["local", "airflow"], phidata_runtime_env)
            self.args.phidata_runtime = phidata_runtime_env
        else:
            self.args.phidata_runtime = "local"
        return self.args.phidata_runtime

    @phidata_runtime.setter
    def phidata_runtime(self, phidata_runtime: Literal["local", "airflow"]) -> None:
        if (
            self.args is not None
            and phidata_runtime is not None
            and phidata_runtime in ("local", "airflow")
        ):
            self.args.phidata_runtime = phidata_runtime

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
