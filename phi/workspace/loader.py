from pathlib import Path
from typing import Optional, Dict

from phiterm.workspace.ws_utils import get_ws_config_dir_path
from phiterm.utils.get_python_objects_from_module import get_python_objects_from_module

from phiterm.utils.log import logger


def add_ws_dir_to_path(ws_root_path: Path) -> None:
    # Add ws_root_path to sys.path so is treated as a package
    try:
        import sys

        logger.debug(f"Adding {ws_root_path} to path")
        sys.path.insert(0, str(ws_root_path))
    except Exception as e:
        logger.warning(f"Could not add {ws_root_path} to Path. This will break workspace imports")
        logger.exception(e)


def load_workspace(ws_root_path: Path) -> WorkspaceConfig:
    """
    Loads a workspace into a WorkspaceConfig
    """

    ws_config: WorkspaceConfig = WorkspaceConfig()
    config_dir_path: Optional[Path] = get_ws_config_dir_path(ws_root_path)
    if config_dir_path is not None:
        logger.debug(f"--^^-- Loading workspace from: {config_dir_path}")
        workspace_config_objects = {}
        config_files = config_dir_path.rglob("*.py")
        for _config_file in config_files:
            if _config_file.name == "__init__.py":
                continue
            logger.debug(f"Reading file: {_config_file}")
            try:
                python_objects = get_python_objects_from_module(_config_file)
                for obj_name, obj in python_objects.items():
                    _type_name = obj.__class__.__name__
                    if _type_name in [
                        "WorkspaceSettings",
                        "DockerConfig",
                        "K8sConfig",
                        "AwsConfig",
                    ]:
                        workspace_config_objects[obj_name] = obj
            except Exception as e:
                parent_dir = _config_file.parent.name
                parent_parent_dir = _config_file.parent.parent.name
                if parent_dir in ("resources", "tests") or parent_parent_dir in (
                    "resources",
                    "tests",
                ):
                    pass
                else:
                    logger.warning(f"Error in {_config_file}: {e}")
                pass

        # logger.debug(f"workspace_config_objects: {workspace_config_objects}")
        for obj_name, obj in workspace_config_objects.items():
            _obj_type = obj.__class__.__name__
            logger.debug(f"Adding {obj_name} | Type: {_obj_type}")
            if _obj_type == "WorkspaceSettings":
                ws_config.ws_settings = obj
                try:
                    ws_config.default_env = obj.default_env or obj.dev_env
                    ws_config.default_config = obj.default_config
                except Exception as e:
                    logger.debug(f"Error loading default settings: {e}")
                    pass

                try:
                    ws_config.aws_region = obj.aws_region
                    ws_config.aws_profile = obj.aws_profile
                    ws_config.aws_config_file = obj.aws_config_file
                    ws_config.aws_shared_credentials_file = obj.aws_shared_credentials_file
                except Exception as e:
                    logger.debug(f"Error loading aws settings: {e}")
                    pass
            elif _obj_type == "DockerConfig":
                if ws_config.docker is None:
                    ws_config.docker = []
                ws_config.docker.append(obj)
            elif _obj_type == "K8sConfig":
                if ws_config.k8s is None:
                    ws_config.k8s = []
                ws_config.k8s.append(obj)
            elif _obj_type == "AwsConfig":
                if ws_config.aws is None:
                    ws_config.aws = []
                ws_config.aws.append(obj)

    # logger.debug(f"ws_config: {ws_config}")
    return ws_config
