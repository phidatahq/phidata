from typing import Optional, Any, Literal

from phidata.check.df.dataframe_check import DataFrameCheck
from phidata.utils.log import logger


class DFNotEmpty(DataFrameCheck):
    def __init__(
        self,
        name: str = "DataFrameNotEmpty",
        on_fail: Literal["fail", "warn", "ignore"] = "fail",
        version: Optional[str] = None,
        enabled: bool = True,
    ):
        super().__init__(
            name=name,
            on_fail=on_fail,
            version=version,
            enabled=enabled,
        )

    def check_dataframe(self, df) -> bool:
        logger.info(f"-*- Running Check: {self.name}")
        if df.is_empty():
            logger.error(f"DataFrame is empty")
            return False
        return True
