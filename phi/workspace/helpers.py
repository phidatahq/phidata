from typing import Optional
from pathlib import Path


def get_workspace_dir_from_env() -> Optional[Path]:
    from os import getenv
    from phi.constants import WORKSPACE_DIR_ENV_VAR

    workspace_dir = getenv(WORKSPACE_DIR_ENV_VAR, None)
    if workspace_dir is not None:
        return Path(workspace_dir)
    return None
