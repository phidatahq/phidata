from pathlib import Path
from typing import Optional, Dict
from typing_extensions import Literal

from pydantic import BaseModel


class InfraArgs(BaseModel):
    name: Optional[str] = None
    env: Optional[Literal["dev", "stg", "prd"]] = None
    version: Optional[str] = None
    enabled: bool = True

    # Path to the workspace root directory
    workspace_root_path: Optional[Path] = None
    # Path to the workspace config file
    workspace_config_file_path: Optional[Path] = None

    # Path to important directories relative to the workspace_root
    # These directories are joined to the workspace_root dir
    #   to build paths depending on the environments (local, docker, k8s)
    # defaults are set by WorkspaceConfig.__init__()
    scripts_dir: Optional[str] = None
    storage_dir: Optional[str] = None
    meta_dir: Optional[str] = None
    products_dir: Optional[str] = None
    notebooks_dir: Optional[str] = None
    workspace_config_dir: Optional[str] = None

    # Env vars added to local env when running workflows
    local_env: Optional[Dict[str, str]] = None
    # Env vars added to docker env when building PhidataApps
    #   and running workflows
    docker_env: Optional[Dict[str, str]] = None
    # Env vars added to k8s env when building PhidataApps
    #   and running workflows
    k8s_env: Optional[Dict[str, str]] = None

    class Config:
        arbitrary_types_allowed = True
