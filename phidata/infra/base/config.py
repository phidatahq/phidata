from os import environ, getenv
from pathlib import Path
from typing import Optional, Dict, Union

from phidata.base import PhidataBase
from phidata.infra.base.args import InfraArgs
from phidata.utils.env_file import read_env_from_file
from phidata.utils.log import logger


class InfraConfig(PhidataBase):
    """Base Class for all phidata infra configs"""

    def __init__(self) -> None:
        super().__init__()
        self.args: Optional[InfraArgs] = None

    @property
    def env(self) -> Optional[str]:
        return self.args.env if self.args else None

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
    def meta_dir(self) -> Optional[str]:
        return self.args.meta_dir if self.args else None

    @meta_dir.setter
    def meta_dir(self, meta_dir: str) -> None:
        if self.args is not None and meta_dir is not None:
            self.args.meta_dir = meta_dir

    @property
    def notebooks_dir(self) -> Optional[str]:
        return self.args.notebooks_dir if self.args else None

    @notebooks_dir.setter
    def notebooks_dir(self, notebooks_dir: str) -> None:
        if self.args is not None and notebooks_dir is not None:
            self.args.notebooks_dir = notebooks_dir

    @property
    def products_dir(self) -> Optional[str]:
        return self.args.products_dir if self.args else None

    @products_dir.setter
    def products_dir(self, products_dir: str) -> None:
        if self.args is not None and products_dir is not None:
            self.args.products_dir = products_dir

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
    def workflows_dir(self) -> Optional[str]:
        return self.args.workflows_dir if self.args else None

    @workflows_dir.setter
    def workflows_dir(self, workflows_dir: str) -> None:
        if self.args is not None and workflows_dir is not None:
            self.args.workflows_dir = workflows_dir

    @property
    def workspace_config_dir(self) -> Optional[str]:
        return self.args.workspace_config_dir if self.args else None

    @workspace_config_dir.setter
    def workspace_config_dir(self, workspace_config_dir: str) -> None:
        if self.args is not None and workspace_config_dir is not None:
            self.args.workspace_config_dir = workspace_config_dir

    @property
    def local_env(self) -> Optional[Dict[str, str]]:
        if self.args is None:
            return None

        local_env: Dict[str, str] = {}

        # If self.args.local_env is available add that local_env
        if self.args.local_env is not None:
            local_env.update(self.args.local_env)

        # Then, read env from local_env_file
        if self.args.local_env_file is not None:
            local_env_file = self.args.local_env_file
            local_env_file_path: Optional[Path] = None
            if isinstance(local_env_file, str):
                if self.workspace_root_path is None:
                    logger.error(f"workspace_root_path is None")
                    return local_env
                if self.workspace_config_dir is None:
                    logger.error(f"workspace_config_dir is None")
                    return local_env

                local_env_file_path = self.workspace_root_path.joinpath(
                    self.workspace_config_dir
                ).joinpath(local_env_file)
            elif isinstance(local_env_file, Path):
                local_env_file_path = local_env_file

            local_env_from_file = read_env_from_file(local_env_file_path)
            if local_env_from_file:
                local_env.update(local_env_from_file)

        return local_env

    @local_env.setter
    def local_env(self, local_env: Dict[str, str]) -> None:
        if self.args is not None and local_env is not None:
            self.args.local_env = local_env

    @property
    def local_env_file(self) -> Optional[Union[str, Path]]:
        return self.args.local_env_file if self.args else None

    @local_env_file.setter
    def local_env_file(self, local_env_file: Union[str, Path]) -> None:
        if self.args is not None and local_env_file is not None:
            self.args.local_env_file = local_env_file

    @property
    def docker_env(self) -> Optional[Dict[str, str]]:
        return self.args.docker_env if self.args else None

    @docker_env.setter
    def docker_env(self, docker_env: Dict[str, str]) -> None:
        if self.args is not None and docker_env is not None:
            self.args.docker_env = docker_env

    @property
    def docker_env_file(self) -> Optional[Union[str, Path]]:
        return self.args.docker_env_file if self.args else None

    @docker_env_file.setter
    def docker_env_file(self, docker_env_file: Union[str, Path]) -> None:
        if self.args is not None and docker_env_file is not None:
            self.args.docker_env_file = docker_env_file

    @property
    def k8s_env(self) -> Optional[Dict[str, str]]:
        return self.args.k8s_env if self.args else None

    @k8s_env.setter
    def k8s_env(self, k8s_env: Dict[str, str]) -> None:
        if self.args is not None and k8s_env is not None:
            self.args.k8s_env = k8s_env

    @property
    def k8s_env_file(self) -> Optional[Union[str, Path]]:
        return self.args.k8s_env_file if self.args else None

    @k8s_env_file.setter
    def k8s_env_file(self, k8s_env_file: Union[str, Path]) -> None:
        if self.args is not None and k8s_env_file is not None:
            self.args.k8s_env_file = k8s_env_file

    @property
    def aws_region(self) -> Optional[str]:
        if self.args is None:
            return None

        # If self.args.aws_region is available return that
        if self.args.aws_region is not None:
            return self.args.aws_region

        # Get aws_region from env
        aws_region = getenv("AWS_DEFAULT_REGION", None)
        if aws_region is not None:
            self.args.aws_region = aws_region
            return self.args.aws_region

        # Get aws_region from local_env
        local_env: Optional[Dict[str, str]] = self.local_env
        if local_env is not None:
            aws_region = local_env.get("AWS_DEFAULT_REGION", None)
            if aws_region is not None:
                self.args.aws_region = aws_region
                return self.args.aws_region

        return None

    @aws_region.setter
    def aws_region(self, aws_region: str) -> None:
        if self.args is not None and aws_region is not None:
            self.args.aws_region = aws_region

    @property
    def aws_profile(self) -> Optional[str]:
        if self.args is None:
            return None

        # If self.args.aws_profile is available return that
        if self.args.aws_profile is not None:
            return self.args.aws_profile

        # Get aws_profile from env
        aws_profile = getenv("AWS_PROFILE", None)
        if aws_profile is not None:
            self.args.aws_profile = aws_profile
            return self.args.aws_profile

        # Get aws_profile from local_env
        local_env: Optional[Dict[str, str]] = self.local_env
        if local_env is not None:
            aws_profile = local_env.get("AWS_PROFILE", None)
            if aws_profile is not None:
                self.args.aws_profile = aws_profile
                return self.args.aws_profile

        return None

    @aws_profile.setter
    def aws_profile(self, aws_profile: str) -> None:
        if self.args is not None and aws_profile is not None:
            self.args.aws_profile = aws_profile

    @property
    def aws_config_file(self) -> Optional[str]:
        if self.args is None:
            return None

        # If self.args.aws_config_file is available return that
        if self.args.aws_config_file is not None:
            return self.args.aws_config_file

        # Get aws_config_file from env
        aws_config_file = getenv("AWS_CONFIG_FILE", None)
        if aws_config_file is not None:
            self.args.aws_config_file = aws_config_file
            return self.args.aws_config_file

        # Get aws_config_file from local_env
        local_env: Optional[Dict[str, str]] = self.local_env
        if local_env is not None:
            aws_config_file = local_env.get("AWS_CONFIG_FILE", None)
            if aws_config_file is not None:
                self.args.aws_config_file = aws_config_file
                return self.args.aws_config_file

        return None

    @aws_config_file.setter
    def aws_config_file(self, aws_config_file: str) -> None:
        if self.args is not None and aws_config_file is not None:
            self.args.aws_config_file = aws_config_file

    @property
    def aws_shared_credentials_file(self) -> Optional[str]:
        if self.args is None:
            return None

        # If self.args.aws_shared_credentials_file is available return that
        if self.args.aws_shared_credentials_file is not None:
            return self.args.aws_shared_credentials_file

        # Get aws_shared_credentials_file from env
        aws_shared_credentials_file = getenv("AWS_SHARED_CREDENTIALS_FILE", None)
        if aws_shared_credentials_file is not None:
            self.args.aws_shared_credentials_file = aws_shared_credentials_file
            return self.args.aws_shared_credentials_file

        # Get aws_shared_credentials_file from local_env
        local_env: Optional[Dict[str, str]] = self.local_env
        if local_env is not None:
            aws_shared_credentials_file = local_env.get(
                "AWS_SHARED_CREDENTIALS_FILE", None
            )
            if aws_shared_credentials_file is not None:
                self.args.aws_shared_credentials_file = aws_shared_credentials_file
                return self.args.aws_shared_credentials_file

        return None

    @aws_shared_credentials_file.setter
    def aws_shared_credentials_file(self, aws_shared_credentials_file: str) -> None:
        if self.args is not None and aws_shared_credentials_file is not None:
            self.args.aws_shared_credentials_file = aws_shared_credentials_file

    def is_valid(self) -> bool:
        """
        This function is implemented by each subclass
        and called before the config is used
        """
        logger.debug(f"@is_valid not defined for {self.__class__.__name__}")
        return True

    def set_local_env(self) -> bool:
        local_env: Optional[Dict[str, str]] = self.local_env
        if local_env is not None:
            environ.update(local_env)

        from phidata.constants import (
            NOTEBOOKS_DIR_ENV_VAR,
            PRODUCTS_DIR_ENV_VAR,
            META_DIR_ENV_VAR,
            STORAGE_DIR_ENV_VAR,
            SCRIPTS_DIR_ENV_VAR,
            WORKFLOWS_DIR_ENV_VAR,
            WORKSPACE_ROOT_ENV_VAR,
            WORKSPACE_CONFIG_DIR_ENV_VAR,
            WORKSPACE_CONFIG_FILE_ENV_VAR,
        )

        if self.workspace_config_file_path is not None:
            environ[WORKSPACE_CONFIG_FILE_ENV_VAR] = str(
                self.workspace_config_file_path
            )

        workspace_root_path = self.workspace_root_path
        if workspace_root_path is not None:
            environ[WORKSPACE_ROOT_ENV_VAR] = str(workspace_root_path)

            if self.workspace_config_dir is not None:
                workspace_config_dir = workspace_root_path.joinpath(
                    self.workspace_config_dir
                )
                environ[WORKSPACE_CONFIG_DIR_ENV_VAR] = str(workspace_config_dir)

            if self.workflows_dir is not None:
                workflows_dir = workspace_root_path.joinpath(self.workflows_dir)
                environ[WORKFLOWS_DIR_ENV_VAR] = str(workflows_dir)

            if self.meta_dir is not None:
                meta_dir = workspace_root_path.joinpath(self.meta_dir)
                environ[META_DIR_ENV_VAR] = str(meta_dir)

            if self.notebooks_dir is not None:
                notebooks_dir = workspace_root_path.joinpath(self.notebooks_dir)
                environ[NOTEBOOKS_DIR_ENV_VAR] = str(notebooks_dir)

            if self.products_dir is not None:
                products_dir = workspace_root_path.joinpath(self.products_dir)
                environ[PRODUCTS_DIR_ENV_VAR] = str(products_dir)

            if self.scripts_dir is not None:
                scripts_dir = workspace_root_path.joinpath(self.scripts_dir)
                environ[SCRIPTS_DIR_ENV_VAR] = str(scripts_dir)

            if self.storage_dir is not None:
                storage_dir = workspace_root_path.joinpath(self.storage_dir)
                environ[STORAGE_DIR_ENV_VAR] = str(storage_dir)

            return True

        return False

    @property
    def continue_on_create_failure(self) -> Optional[bool]:
        return self.args.continue_on_create_failure if self.args else False

    @continue_on_create_failure.setter
    def continue_on_create_failure(self, continue_on_create_failure: bool) -> None:
        if self.args is not None and continue_on_create_failure is not None:
            self.args.continue_on_create_failure = continue_on_create_failure

    @property
    def continue_on_delete_failure(self) -> Optional[bool]:
        return self.args.continue_on_delete_failure if self.args else False

    @continue_on_delete_failure.setter
    def continue_on_delete_failure(self, continue_on_delete_failure: bool) -> None:
        if self.args is not None and continue_on_delete_failure is not None:
            self.args.continue_on_delete_failure = continue_on_delete_failure

    @property
    def continue_on_patch_failure(self) -> Optional[bool]:
        return self.args.continue_on_patch_failure if self.args else False

    @continue_on_patch_failure.setter
    def continue_on_patch_failure(self, continue_on_patch_failure: bool) -> None:
        if self.args is not None and continue_on_patch_failure is not None:
            self.args.continue_on_patch_failure = continue_on_patch_failure
