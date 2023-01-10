from typing import Optional, Any

from phidata.asset.data_asset import DataAsset, DataAssetArgs
from phidata.utils.log import logger


class LocalAssetArgs(DataAssetArgs):
    pass


class LocalAsset(DataAsset):
    def __init__(self) -> None:
        super().__init__()

    ######################################################
    ## Get FileSystem
    ######################################################

    def _get_fs(self) -> Optional[Any]:
        from pyarrow import fs

        logger.debug("initializing LocalFileSystem")
        return fs.LocalFileSystem()
