import time

from phi.tools import Toolkit
from phi.utils.log import logger


class Sleep(Toolkit):
    def __init__(self):
        super().__init__(name="sleep")

        self.register(self.sleep)

    def sleep(self, seconds: int) -> str:
        """Use this function to sleep for a given number of seconds."""
        logger.info(f"Sleeping for {seconds} seconds")
        time.sleep(seconds)
        logger.info(f"Awake after {seconds} seconds")
        return f"Slept for {seconds} seconds"
