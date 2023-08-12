from functools import wraps

from phi.utils.log import logger


class FunctionRegistry:
    def __init__(self):
        self.functions = {}

    def register(self, name, function):
        logger.debug(f"Registering function: {name}")
        self.functions[name] = function

    def get(self, name):
        return self.functions[name]


default_registry = FunctionRegistry()


def llm_function(func):
    default_registry.register(func.__name__, func)

    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper
