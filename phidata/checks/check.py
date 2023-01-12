from typing import Optional, Any, Literal

from phidata.base import PhidataBase, PhidataBaseArgs
from phidata.utils.log import logger


class CheckArgs(PhidataBaseArgs):
    # Check Name
    name: str
    # How to handle check failure
    on_fail: Literal["fail", "warn", "ignore"] = "fail"


class Check(PhidataBase):
    """Base Class for all Checks"""

    def __init__(
        self,
        name: str,
        on_fail: Literal["fail", "warn", "ignore"] = "fail",
        version: Optional[str] = None,
        enabled: bool = True,
    ):
        super().__init__()
        try:
            self.args: CheckArgs = CheckArgs(
                name=name,
                on_fail=on_fail,
                version=version,
                enabled=enabled,
            )
        except Exception:
            logger.error(f"Args for {self.name} are not valid")
            raise

    @property
    def on_fail(self) -> Literal["fail", "warn", "ignore"]:
        return self.args.on_fail if self.args else "fail"

    @on_fail.setter
    def on_fail(self, on_fail: Literal["fail", "warn", "ignore"]) -> None:
        if self.args and on_fail in ["fail", "warn", "ignore"]:
            self.args.on_fail = on_fail

    def validate(self, result: bool = False) -> bool:
        if result:
            logger.info(f"-*- Check: {self.name} passed")
        else:
            if self.args.on_fail == "fail":
                raise Exception(f"Check: {self.name} failed")
            elif self.args.on_fail == "warn":
                logger.warning(f"Check: {self.name} failed")
            else:
                logger.info(f"-*- Check: {self.name} failed")

        # Blocking/failed checks return an Exception above
        return True

    def _check_polars_df(self, df: Any, **kwargs) -> bool:
        # subclasses should implement this check and return True/False
        logger.error(f"@check_dataframe not defined for {self.name}")
        return True

    def check_polars_df(self, df: Any, **kwargs) -> bool:
        return self.validate(self._check_polars_df(df, **kwargs))

    def _check_pandas_df(self, df: Any, **kwargs) -> bool:
        # subclasses should implement this check and return True/False
        logger.error(f"@check_dataframe not defined for {self.name}")
        return True

    def check_pandas_df(self, df: Any, **kwargs) -> bool:
        return self.validate(self._check_pandas_df(df, **kwargs))

    def _check_table(self, table: Any, **kwargs) -> bool:
        # subclasses should implement this check and return True/False
        logger.error(f"@check_table not defined for {self.name}")
        return True

    def check_table(self, table: Any, **kwargs) -> bool:
        return self.validate(self._check_table(table, **kwargs))
