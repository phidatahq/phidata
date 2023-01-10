from phidata.base import PhidataBase, PhidataBaseArgs
from phidata.utils.log import logger


class CheckArgs(PhidataBaseArgs):
    pass


class Check(PhidataBase):
    """Base Class for all Checks"""

    def __init__(self):
        super().__init__()
        self.result: bool = False

    def check(self, **kwargs) -> bool:
        logger.debug(f"@check not defined for {self.name}")
        return False
