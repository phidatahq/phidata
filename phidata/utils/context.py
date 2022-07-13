from datetime import datetime
from pathlib import Path
from typing import Optional

from phidata.constants import (
    SCRIPTS_DIR_ENV_VAR,
    STORAGE_DIR_ENV_VAR,
    META_DIR_ENV_VAR,
    PRODUCTS_DIR_ENV_VAR,
    NOTEBOOKS_DIR_ENV_VAR,
    WORKSPACE_CONFIG_DIR_ENV_VAR,
)
from phidata.types.context import PathContext, RunContext, AirflowContext
from phidata.utils.log import logger


def get_run_date(
    run_context: Optional[RunContext] = None,
    airflow_context: Optional[AirflowContext] = None,
) -> datetime:

    if run_context is not None and run_context.run_date is not None:
        return run_context.run_date
    if airflow_context is not None and airflow_context.logical_date is not None:
        return airflow_context.logical_date
    return datetime.now()


def build_path_context_from_env() -> Optional[PathContext]:

    logger.debug(f"--++**++--> Building PathContext from env")
    path_context = PathContext()

    import os

    scripts_dir = os.getenv(SCRIPTS_DIR_ENV_VAR)
    storage_dir = os.getenv(STORAGE_DIR_ENV_VAR)
    meta_dir = os.getenv(META_DIR_ENV_VAR)
    products_dir = os.getenv(PRODUCTS_DIR_ENV_VAR)
    notebooks_dir = os.getenv(NOTEBOOKS_DIR_ENV_VAR)
    workspace_config_dir = os.getenv(WORKSPACE_CONFIG_DIR_ENV_VAR)

    if storage_dir is None:
        logger.error(f"{STORAGE_DIR_ENV_VAR} not set")
    if products_dir is None:
        logger.error(f"{PRODUCTS_DIR_ENV_VAR} not set")

    try:
        if scripts_dir is not None:
            path_context.scripts_dir = Path(scripts_dir)
        if storage_dir is not None:
            path_context.storage_dir = Path(storage_dir)
        if meta_dir is not None:
            path_context.meta_dir = Path(meta_dir)
        if products_dir is not None:
            path_context.products_dir = Path(products_dir)
        if notebooks_dir is not None:
            path_context.notebooks_dir = Path(notebooks_dir)
        if workspace_config_dir is not None:
            path_context.workspace_config_dir = Path(workspace_config_dir)
    except Exception as e:
        raise
    logger.debug(f"--++**++--> PathContext loaded")
    return path_context
