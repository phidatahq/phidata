from collections import OrderedDict
from typing import Callable, Dict

from phi.tools.function import Function
from phi.utils.log import logger


class Toolkit:
    def __init__(self, name: str = "toolkit"):
        self.name: str = name
        self.functions: Dict[str, Function] = OrderedDict()

    def register(self, function: Callable, sanitize_arguments: bool = True):
        try:
            f = Function.from_callable(function)
            f.sanitize_arguments = sanitize_arguments
            self.functions[f.name] = f
            logger.debug(f"Function: {f.name} registered with {self.name}")
            # logger.debug(f"Json Schema: {f.to_dict()}")
        except Exception as e:
            logger.warning(f"Failed to create Function for: {function.__name__}")
            raise e

    def instructions(self) -> str:
        return ""

    def __repr__(self):
        return f"<{self.__class__.__name__} name={self.name} functions={list(self.functions.keys())}>"

    def __str__(self):
        return self.__repr__()
