from typing import Callable, List, TypeVar, Any

from phi.utils.log import logger


class Toolkit:
    def __init__(self, name: str = "toolkit"):
        """Initialize a new Toolkit.

        Args:
            name: A descriptive name for the toolkit
        """
        self.name: str = name
        self.functions: List[Callable] = []

    def register(self, function: Callable[..., Any]):
        """Register a function with the toolkit.

        Args:
            function: The callable to register

        Returns:
            The registered function
        """
        if not callable(function):
            raise ValueError("Only callable functions can be registered")

        try:
            if function not in self.functions:
                self.functions.append(function)
                logger.debug(f"Function: {function.__name__} registered with {self.name}")
            else:
                logger.warning(f"Function: {function.__name__} already registered with {self.name}")
        except Exception as e:
            logger.warning(f"Failed to register function: {function.__name__}")
            raise e

    def __repr__(self):
        functions = [f.__name__ for f in self.functions]
        return f"<{self.__class__.__name__} name={self.name} functions={functions}>"

    def __str__(self):
        return self.__repr__()
