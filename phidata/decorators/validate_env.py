from typing import Dict, Any
import functools

from phidata.utils.env_var import validate_env_vars


def validate_env(env_var_dict: Dict[str, Any]):
    """
    This decorator returns the function it decorates
    IF each env_var in env_var_dict matches its value in the running environment

    Args:
        env_var_dict:

    Returns:

    Notes:
        - Create a decorator with an argument
        https://realpython.com/primer-on-python-decorators/#decorators-with-arguments
    """
    # Return this decorator if env is valid
    def decorator_validate_env(func):
        @functools.wraps(func)
        def wrapper_validate_env(*args, **kwargs):
            value = func(*args, **kwargs)
            return value

        return wrapper_validate_env

    # Return this decorator instead if the env doesnt match
    def decorator_return_none(func):
        @functools.wraps(func)
        def wrapper_return_none(*args, **kwargs):
            return None

        return wrapper_return_none

    if validate_env_vars(env_var_dict):
        return decorator_validate_env
    return decorator_return_none
