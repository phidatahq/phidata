import random
from tenacity import retry
from phi.tools import Toolkit
import json
from phi.utils.log import logger

ß
class TestFunction(Toolkit):
    def __init__(self):
        super().__init__(name="test_function")

        self.register(self.do_something_unreliable)

    @retry
    def do_something_unreliable(self) -> str:
        """Use this function do something unreliable.

        Args:
            None
        Returns:
            The result from the unreliable function.
        """

        num = random.randint(0, 10000)
        logger.debug(f"Random number: {num}")
        if  num > 1:
            raise IOError("Broken sauce, everything is hosed!!!111one")
        else:
            return "Awesome sauce!"