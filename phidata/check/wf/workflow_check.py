from typing import Optional, Any, Literal

from phidata.check.check import Check, CheckArgs
from phidata.utils.log import logger


class WorkflowCheckArgs(CheckArgs):
    # Check Name
    name: str
    # How to handle check failure
    on_fail: Literal["fail", "warn", "ignore"] = "fail"


class WorkflowCheck(Check):
    """Base Class for all WorkflowChecks"""

    def __init__(
        self,
        name: str,
        on_fail: Literal["fail", "warn", "ignore"] = "fail",
        version: Optional[str] = None,
        enabled: bool = True,
    ):
        super().__init__()
        self.df: Optional[Any] = None
        self.result: bool = False
        try:
            self.args: WorkflowCheckArgs = WorkflowCheckArgs(
                name=name,
                on_fail=on_fail,
                version=version,
                enabled=enabled,
            )
        except Exception as e:
            logger.error(f"Args for {self.name} are not valid")
            raise

    @property
    def on_fail(self) -> Literal["fail", "warn", "ignore"]:
        return self.args.on_fail if self.args else "fail"

    @on_fail.setter
    def on_fail(self, on_fail: Literal["fail", "warn", "ignore"]) -> None:
        if self.args and on_fail in ["fail", "warn", "ignore"]:
            self.args.on_fail = on_fail

    def check_dataframe(self, df: Any) -> bool:
        logger.error(f"@check_dataframe not defined for {self.name}")
        return False

    def check(self, df: Optional[Any] = None, **kwargs) -> bool:
        if df is None:
            logger.warning(f"{self.name}: Dataframe None")
            return False

        try:
            self.result = self.check_dataframe(df)
        except Exception as e:
            logger.error(f"Error in check {self.name}: {e}")

        if self.result:
            logger.info(f"-*- Check: {self.name} passed")
            return self.result
        else:
            if self.args.on_fail == "fail":
                raise Exception(f"Check: {self.name} failed")
            elif self.args.on_fail == "warn":
                logger.warning(f"Check: {self.name} failed")
            else:
                logger.info(f"-*- Check: {self.name} failed")
            return True
