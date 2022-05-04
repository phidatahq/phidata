import os
from typing import Dict, Any, Optional

from phidata.utils.log import logger


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
            _env_value = os.getenv(env_var_key)
            if str(env_var_value) != str(_env_value):
                # logger.debug(f"EnvVar {env_var_key} invalid. Value {_env_value}")
                return False
        return True

    # Return false if env_var_dict is not a dict
    return False
