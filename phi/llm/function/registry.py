from typing import List, Callable, Dict
from functools import wraps

from phi.llm.schemas import Function
from phi.utils.log import logger


class FunctionRegistry:
    def __init__(self, name: str = "default_registry"):
        self.name: str = name
        self.functions: Dict[str, Callable] = {}

    def register(self, name: str, function: Callable):
        logger.debug(f"Registering function: {name}")
        self.functions[name] = function

    def get(self, name: str):
        return self.functions[name]

    def get_functions(self) -> List[Function]:
        logger.debug("Getting functions from registry")
        # schemas: List[Function] = [Function(name=name) for name in self.functions.keys()]
        schemas: List[Function] = [
            Function(
                **{
                    "name": "get_chat_history",
                    "description": "Returns the chat history as a list of dictionaries.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "num_messages": {
                                "type": "integer",
                                "description": "number of messages to return",
                            },
                        },
                    },
                }
            ),
        ]
        logger.debug(f"Function schemas: {schemas}")
        return schemas


default_registry = FunctionRegistry()


def llm_function(func):
    default_registry.register(func.__name__, func)

    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper
