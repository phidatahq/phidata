from pathlib import Path
from typing import Optional, Dict
from typing_extensions import Literal

from phidata.base import PhidataBaseArgs


class InfraArgs(PhidataBaseArgs):
    env: Optional[Literal["dev", "stg", "prd"]] = None

    # -*- Path parameters
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

    # -*- Environment parameters
    # Env vars added to local env when running workflows
    local_env: Optional[Dict[str, str]] = None
    # Env vars added to docker env when building PhidataApps
    #   and running workflows
    docker_env: Optional[Dict[str, str]] = None
    # Env vars added to k8s env when building PhidataApps
    #   and running workflows
    k8s_env: Optional[Dict[str, str]] = None

    # -*- AWS parameters
    # Common aws params used by apps, resources and data assets
    aws_region: Optional[str] = None
    aws_profile: Optional[str] = None
    aws_config_file: Optional[str] = None
    aws_shared_credentials_file: Optional[str] = None
