from pathlib import Path
from typing import Optional, Dict
from typing_extensions import Literal

from phidata.infra.base.args import InfraArgs
from phidata.utils.log import logger


class InfraConfig:
    """Base Class for all phidata infra configs"""

    def __init__(self) -> None:
        self.args: Optional[InfraArgs] = None

    @property
    def name(self) -> str:
        if self.args and self.args.name:
            return self.args.name
        return self.__class__.__name__.lower()

    @property
    def env(self) -> Optional[Literal["dev", "stg", "prd"]]:
        return self.args.env if self.args else None

    @property
    def version(self) -> Optional[str]:
        return self.args.version if self.args else None

    @property
    def enabled(self) -> bool:
        return self.args.enabled if self.args else False

    @property
    def workspace_root_path(self) -> Optional[Path]:
        return self.args.workspace_root_path if self.args else None

    @workspace_root_path.setter
    def workspace_root_path(self, workspace_root_path: Path) -> None:
        if self.args is not None and workspace_root_path is not None:
            self.args.workspace_root_path = workspace_root_path

    @property
    def workspace_config_file_path(self) -> Optional[Path]:
        return self.args.workspace_config_file_path if self.args else None

    @workspace_config_file_path.setter
    def workspace_config_file_path(self, workspace_config_file_path: Path) -> None:
        if self.args is not None and workspace_config_file_path is not None:
            self.args.workspace_config_file_path = workspace_config_file_path

    @property
    def scripts_dir(self) -> Optional[str]:
        return self.args.scripts_dir if self.args else None

    @scripts_dir.setter
    def scripts_dir(self, scripts_dir: str) -> None:
        if self.args is not None and scripts_dir is not None:
            self.args.scripts_dir = scripts_dir

    @property
    def storage_dir(self) -> Optional[str]:
        return self.args.storage_dir if self.args else None

    @storage_dir.setter
    def storage_dir(self, storage_dir: str) -> None:
        if self.args is not None and storage_dir is not None:
            self.args.storage_dir = storage_dir

    @property
    def meta_dir(self) -> Optional[str]:
        return self.args.meta_dir if self.args else None

    @meta_dir.setter
    def meta_dir(self, meta_dir: str) -> None:
        if self.args is not None and meta_dir is not None:
            self.args.meta_dir = meta_dir

    @property
    def products_dir(self) -> Optional[str]:
        return self.args.products_dir if self.args else None

    @products_dir.setter
    def products_dir(self, products_dir: str) -> None:
        if self.args is not None and products_dir is not None:
            self.args.products_dir = products_dir

    @property
    def notebooks_dir(self) -> Optional[str]:
        return self.args.notebooks_dir if self.args else None

    @notebooks_dir.setter
    def notebooks_dir(self, notebooks_dir: str) -> None:
        if self.args is not None and notebooks_dir is not None:
            self.args.notebooks_dir = notebooks_dir

    @property
    def workspace_config_dir(self) -> Optional[str]:
        return self.args.workspace_config_dir if self.args else None

    @workspace_config_dir.setter
    def workspace_config_dir(self, workspace_config_dir: str) -> None:
        if self.args is not None and workspace_config_dir is not None:
            self.args.workspace_config_dir = workspace_config_dir

    @property
    def local_env(self) -> Optional[Dict[str, str]]:
        return self.args.local_env if self.args else None

    @local_env.setter
    def local_env(self, local_env: Dict[str, str]) -> None:
        if self.args is not None and local_env is not None:
            self.args.local_env = local_env

    @property
    def docker_env(self) -> Optional[Dict[str, str]]:
        return self.args.docker_env if self.args else None

    @docker_env.setter
    def docker_env(self, docker_env: Dict[str, str]) -> None:
        if self.args is not None and docker_env is not None:
            self.args.docker_env = docker_env

    @property
    def k8s_env(self) -> Optional[Dict[str, str]]:
        return self.args.k8s_env if self.args else None

    @k8s_env.setter
    def k8s_env(self, k8s_env: Dict[str, str]) -> None:
        if self.args is not None and k8s_env is not None:
            self.args.k8s_env = k8s_env

    def is_valid(self) -> bool:
        logger.debug(f"@is_valid not defined for {self.__class__.__name__}")
        # each subclass should implement this function
        return True
