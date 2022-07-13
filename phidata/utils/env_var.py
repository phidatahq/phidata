from os import getenv
from typing import Dict, Any, Optional

from phidata.utils.log import logger


def env_var_is_true(name: str, default: bool = False) -> bool:
    """
    Return True if the env var "name" is set to True.
    Returns the default value if env var is not set.

    Args:
        name: Name of env var to check
        default: Default value to return when env var is not set

    Returns:
        bool
    """
    var_name = name
    var_value: Optional[str] = getenv(var_name)
    if var_value is None:
        return default
    return var_value.lower().startswith("true")


def validate_env_vars(env_var_dict: Optional[Dict[str, Any]]) -> bool:
    """
    Return True if each env_var in env_var_dict matches
    its value in the running environment

    Args:
        env_var_dict:

    Returns:
        bool
    """
    # logger.debug("Validating env: {}".format(env_var_dict))
    if env_var_dict is None:
        # nothing to validate
        return True

    if isinstance(env_var_dict, dict):
        # return True if each env_var matches
        for env_var_key, env_var_value in env_var_dict.items():
            _env_value = getenv(env_var_key)
            if str(env_var_value) != str(_env_value):
                # logger.debug(f"EnvVar {env_var_key} invalid. Value {_env_value}")
                return False
        return True

    # Return false if env_var_dict is not a dict
    return False
