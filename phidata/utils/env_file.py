from pathlib import Path
from typing import Optional, Dict

from phidata.utils.log import logger


def read_env_from_file(env_file: Path) -> Optional[Dict[str, str]]:
    if env_file is not None and env_file.exists() and env_file.is_file():
        logger.debug(f"Reading {env_file}")

        env_dict: Optional[Dict[str, str]] = None

        # logger.debug(f"name: {env_file.name}")
        # logger.debug(f"name: {type(env_file.name)}")
        if env_file.name in (".env", ".envrc"):
            from dotenv.main import dotenv_values

            dotenv_dict: Dict[str, Optional[str]] = dotenv_values(env_file)
            # logger.debug(f"dotenv_dict: {dotenv_dict}")
            env_dict = {k: v for k, v in dotenv_dict.items() if v is not None}

        elif env_file.suffix in (".yaml", ".yml"):
            import yaml

            env_data_from_file = yaml.safe_load(env_file.read_text())
            if env_data_from_file is not None and isinstance(env_data_from_file, dict):
                env_dict = env_data_from_file
            else:
                logger.error(f"Empty env_file: {env_file}")

        # logger.debug(f"env_dict: {env_dict}")
        return env_dict

    return None
