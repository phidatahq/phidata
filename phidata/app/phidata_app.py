from pathlib import Path
from typing import Optional, Dict

from phidata.base import PhidataBase, PhidataBaseArgs
from phidata.infra.docker.resource.group import (
    DockerResourceGroup,
    DockerBuildContext,
)
from phidata.infra.k8s.resource.group import (
    K8sResourceGroup,
    K8sBuildContext,
)
from phidata.utils.log import logger


class PhidataAppArgs(PhidataBaseArgs):
    name: str

    # If True, skip resource creation if active resources with the same name exist.
    use_cache: bool = True
    # If True, log extra debug messages
    use_verbose_logs: bool = False

    # Populated during init_resources()
    # These are passed down from the WorkspaceConfig and each PhidataApp has access to them
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

    # Env vars added to docker env when building PhidataApps
    #   and running workflows
    docker_env: Optional[Dict[str, str]] = None
    # Env vars added to k8s env when building PhidataApps
    #   and running workflows
    k8s_env: Optional[Dict[str, str]] = None

    class Config:
        arbitrary_types_allowed = True


class PhidataApp(PhidataBase):
    """Base Class for all PhidataApps"""

    def __init__(self) -> None:
        super().__init__()
        self.args: Optional[PhidataAppArgs] = None
        self.docker_resource_groups: Optional[Dict[str, DockerResourceGroup]] = None
        self.k8s_resource_groups: Optional[Dict[str, K8sResourceGroup]] = None

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

    ######################################################
    ## DockerResourceGroup
    ######################################################

    def init_docker_resource_groups(
        self, docker_build_context: DockerBuildContext
    ) -> None:
        logger.debug(
            f"@init_docker_resource_groups not defined for {self.__class__.__name__}"
        )

    def get_docker_resource_groups(
        self, docker_build_context: DockerBuildContext
    ) -> Optional[Dict[str, DockerResourceGroup]]:
        if self.docker_resource_groups is None:
            self.init_docker_resource_groups(docker_build_context)
        # # Comment out in prod
        # if self.docker_resource_groups:
        #     logger.debug("DockerResourceGroups:")
        #     for rg_name, rg in self.docker_resource_groups.items():
        #         logger.debug(
        #             "{}: {}".format(rg_name, rg.json(exclude_none=True, indent=2))
        #         )
        return self.docker_resource_groups

    ######################################################
    ## K8sResourceGroup
    ######################################################

    def init_k8s_resource_groups(self, k8s_build_context: K8sBuildContext) -> None:
        logger.debug(
            f"@init_docker_resource_groups not defined for {self.__class__.__name__}"
        )

    def get_k8s_resource_groups(
        self, k8s_build_context: K8sBuildContext
    ) -> Optional[Dict[str, K8sResourceGroup]]:
        if self.k8s_resource_groups is None:
            self.init_k8s_resource_groups(k8s_build_context)
        # # Comment out in prod
        # if self.k8s_resource_groups:
        #     logger.debug("K8sResourceGroups:")
        #     for rg_name, rg in self.k8s_resource_groups.items():
        #         logger.debug(
        #             "{}:{}\n{}".format(rg_name, type(rg), rg)
        #         )
        return self.k8s_resource_groups
