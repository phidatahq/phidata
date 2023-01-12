from pathlib import Path
from typing import Optional, Dict, Union

from phidata.base import PhidataBaseArgs


class InfraArgs(PhidataBaseArgs):
    env: Optional[str] = None

    # -*- Path parameters
    # Path to the workspace root directory
    workspace_root_path: Optional[Path] = None
    # Path to the workspace config file
    workspace_config_file_path: Optional[Path] = None
    # Path to important directories relative to the workspace_root
    # These directories are joined to the workspace_root_path
    #   to build paths depending on the environments (local, docker, k8s)
    # defaults are set by WorkspaceConfig.__init__()
    meta_dir: Optional[str] = None
    notebooks_dir: Optional[str] = None
    products_dir: Optional[str] = None
    scripts_dir: Optional[str] = None
    storage_dir: Optional[str] = None
    workflows_dir: Optional[str] = None
    workspace_config_dir: Optional[str] = None

    # -*- Environment parameters
    # Env vars added to local env
    local_env: Optional[Dict[str, str]] = None
    # Load local env using env file
    local_env_file: Optional[Union[str, Path]] = None
    # Env vars added to docker env
    docker_env: Optional[Dict[str, str]] = None
    # Load docker env using env file
    docker_env_file: Optional[Union[str, Path]] = None
    # Env vars added to k8s env
    k8s_env: Optional[Dict[str, str]] = None
    # Load k8s env using env file
    k8s_env_file: Optional[Union[str, Path]] = None

    # -*- AWS parameters
    # Common aws params used by apps, resources and data assets
    aws_region: Optional[str] = None
    aws_profile: Optional[str] = None
    aws_config_file: Optional[str] = None
    aws_shared_credentials_file: Optional[str] = None

    # -*- `phi` cli parameters
    # Set to True if `phi` should continue creating
    # resources after a resource creation has failed
    continue_on_create_failure: Optional[bool] = None
    # Set to True if `phi` should continue deleting
    # resources after a resource deleting has failed
    # Defaults to True because we normally want to continue deleting
    continue_on_delete_failure: Optional[bool] = None
    # Set to True if `phi` should continue patching
    # resources after a resource patch has failed
    continue_on_patch_failure: Optional[bool] = None
