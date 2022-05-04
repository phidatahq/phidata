from pathlib import Path
from typing import Optional, Any

from phidata.utils.log import logger


def get_path_from_workspace_config(
    current_file: Any, add_path_str: Optional[str] = None
) -> Path:
    """
    Used in the config files, this utility function returns the workspace root path
    from within the workspace directory
    If add_path_str is provided, add it to the workspace root path
    Args:
        current_file:
        add_path_str:

    Returns:
        workspace_root_path
    """
    workspace_root_dir: Path = Path(current_file).parent.parent.resolve()
    # logger.debug(f"Workspace root: {workspace_root_dir}")
    if add_path_str:
        return workspace_root_dir.joinpath(add_path_str)
    return workspace_root_dir


def get_relative_path(relative_path_str: str) -> Path:
    """
    A utility function that resolved the relative_path from the current file
    Args:
        relative_path_str:
    """
    return Path(".").joinpath(relative_path_str).resolve()
