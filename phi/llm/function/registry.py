from collections import OrderedDict
from typing import Callable, Dict

from phi.llm.schemas import Function
from phi.utils.log import logger


class FunctionRegistry:
    def __init__(self, name: str = "default_registry"):
        self.name: str = name
        self.functions: Dict[str, Function] = OrderedDict()

    def register(self, function: Callable):
        try:
            f = Function.from_callable(function)
            self.functions[f.name] = f
            logger.debug(f"Function: {f.name} registered with {self.name}")
            logger.debug(f"Json Schema: {f.to_dict()}")
        except Exception as e:
            logger.warning(f"Failed to create Function for: {function.__name__}")
            raise e

    def __repr__(self):
        return f"<{self.__class__.__name__} name={self.name} functions={list(self.functions.keys())}>"

    def __str__(self):
        return self.__repr__()
