from typing import Optional, Any, Literal

from phidata.checks.check import Check
from phidata.utils.log import logger


class NotEmpty(Check):
    def __init__(
        self,
        name: str = "TableNotEmpty",
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

    def _check_table(self, table: Any, **kwargs) -> bool:
        logger.info(f"-*- Running Check: {self.name}")
        if table is None:
            logger.error(f"Table is empty")
            return False
        return True
