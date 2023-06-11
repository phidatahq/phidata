from pathlib import Path
from typing import Optional, List, Dict, Union, Any

from phidata.infra.args import InfraArgs
from phidata.infra.config import InfraConfig
from phidata.workspace.settings import WorkspaceSettings
from phidata.utils.log import logger


class WorkspaceConfigArgs(InfraArgs):
    # default env for phi ws ... commands
    default_env: Optional[str] = None
    # default config for phi ws ... commands
    default_config: Optional[str] = None
    # A copy of the workspace settings
    ws_settings: Optional[WorkspaceSettings] = None

    # List of Docker configurations
    # Type: DockerConfig
    docker: Optional[List[Any]] = None
    # List of K8s configurations
    # Type: K8sConfig
    k8s: Optional[List[Any]] = None
    # List of AWS configurations
    # Type: AwsConfig
    aws: Optional[List[Any]] = None

    # Path to important directories relative to the workspace_root
    meta_dir: str
    notebooks_dir: str
    products_dir: str
    scripts_dir: str
    storage_dir: str
    workflows_dir: str
    workspace_config_dir: str


class WorkspaceConfig(InfraConfig):
    def __init__(
        self,
        version: Optional[str] = None,
        enabled: bool = True,
        # default env for phi ws ... commands
        default_env: Optional[str] = None,
        # default config for phi ws ... commands
        default_config: Optional[str] = None,
        ws_settings: Optional[WorkspaceSettings] = None,
        # List of Docker configurations
        # Type: DockerConfig
        docker: Optional[List[Any]] = None,
        # List of K8s configurations
        # Type: K8sConfig
        k8s: Optional[List[Any]] = None,
        # List of AWS configurations
        # Type: AwsConfig
        aws: Optional[List[Any]] = None,
        # Path to important directories relative to the workspace_root
        meta_dir: str = "meta",
        notebooks_dir: str = "notebooks",
        products_dir: str = "workflows",
        scripts_dir: str = "scripts",
        storage_dir: str = "storage",
        workflows_dir: str = "workflows",
        workspace_config_dir: str = "workspace",
        # -*- Environment parameters
        # NOTE: These are NOT used by the WorkspaceConfig
        # So cannot be used in the workspace files
        # Env vars added to local env when running workflows
        local_env: Optional[Dict[str, str]] = None,
        # Load local env using env file
        local_env_file: Optional[Union[str, Path]] = None,
        # Env vars added to docker env when running workflows
        docker_env: Optional[Dict[str, str]] = None,
        # Load docker env using env file
        docker_env_file: Optional[Union[str, Path]] = None,
        # Env vars added to k8s env when running workflows
        k8s_env: Optional[Dict[str, str]] = None,
        # Load k8s env using env file
        k8s_env_file: Optional[Union[str, Path]] = None,
        # -*- AWS parameters
        # Common aws params used by apps, resources and data assets
        aws_region: Optional[str] = None,
        aws_profile: Optional[str] = None,
        aws_config_file: Optional[str] = None,
        aws_shared_credentials_file: Optional[str] = None,
        # -*- `phi` cli parameters
        # Set to True if `phi` should continue creating
        # resources after a resource creation has failed
        continue_on_create_failure: bool = False,
        # Set to True if `phi` should continue deleting
        # resources after a resource deleting has failed
        # Defaults to True because we normally want to continue deleting
        continue_on_delete_failure: bool = True,
        # Set to True if `phi` should continue patching
        # resources after a resource patch has failed
        continue_on_patch_failure: bool = False,
    ):
        super().__init__()

        try:
            self.args: WorkspaceConfigArgs = WorkspaceConfigArgs(
                version=version,
                enabled=enabled,
                default_env=default_env,
                default_config=default_config,
                ws_settings=ws_settings,
                docker=docker,
                k8s=k8s,
                aws=aws,
                meta_dir=meta_dir,
                notebooks_dir=notebooks_dir,
                products_dir=products_dir,
                scripts_dir=scripts_dir,
                storage_dir=storage_dir,
                workflows_dir=workflows_dir,
                workspace_config_dir=workspace_config_dir,
                local_env=local_env,
                local_env_file=local_env_file,
                docker_env=docker_env,
                docker_env_file=docker_env_file,
                k8s_env=k8s_env,
                k8s_env_file=k8s_env_file,
                aws_region=aws_region,
                aws_profile=aws_profile,
                aws_config_file=aws_config_file,
                aws_shared_credentials_file=aws_shared_credentials_file,
                continue_on_create_failure=continue_on_create_failure,
                continue_on_delete_failure=continue_on_delete_failure,
                continue_on_patch_failure=continue_on_patch_failure,
            )
        except Exception as e:
            logger.error(f"Args for {self.__class__.__name__} are not valid")
            raise

    @property
    def default_env(self) -> Optional[str]:
        return self.args.default_env if self.args else None

    @default_env.setter
    def default_env(self, default_env: str) -> None:
        if self.args is not None and default_env is not None:
            self.args.default_env = default_env

    @property
    def default_config(self) -> Optional[str]:
        return self.args.default_config if self.args else None

    @default_config.setter
    def default_config(self, default_config: str) -> None:
        if self.args is not None and default_config is not None:
            self.args.default_config = default_config

    @property
    def ws_settings(self) -> Optional[WorkspaceSettings]:
        return self.args.ws_settings if self.args else None

    @ws_settings.setter
    def ws_settings(self, ws_settings: WorkspaceSettings) -> None:
        if self.args is not None and ws_settings is not None:
            self.args.ws_settings = ws_settings

    @property
    def docker(self) -> Optional[List[Any]]:
        return self.args.docker if self.args else None

    @docker.setter
    def docker(self, docker: Any) -> None:
        if self.args is not None and docker is not None:
            self.args.docker = docker

    @property
    def k8s(self) -> Optional[List[Any]]:
        return self.args.k8s if self.args else None

    @k8s.setter
    def k8s(self, k8s: Any) -> None:
        if self.args is not None and k8s is not None:
            self.args.k8s = k8s

    @property
    def aws(self) -> Optional[List[Any]]:
        return self.args.aws if self.args else None

    @aws.setter
    def aws(self, aws: Any) -> None:
        if self.args is not None and aws is not None:
            self.args.aws = aws

    def is_valid(self) -> bool:
        if self.docker is not None:
            from phidata.docker.config import DockerConfig

            if not isinstance(self.docker, list):
                raise ValueError("docker should be a list")
            for dc in self.docker:
                if not isinstance(dc, DockerConfig):
                    raise ValueError(f"Invalid DockerConfig: {dc}")

        if self.k8s is not None:
            from phidata.k8s.config import K8sConfig

            if not isinstance(self.k8s, list):
                raise ValueError("k8s should be a list")
            for kc in self.k8s:
                if not isinstance(kc, K8sConfig):
                    raise ValueError(f"Invalid K8sConfig: {kc}")

        if self.aws is not None:
            from phidata.aws.config import AwsConfig

            if not isinstance(self.aws, list):
                raise ValueError("aws should be a list")
            for awsc in self.aws:
                if not isinstance(awsc, AwsConfig):
                    raise ValueError(f"Invalid AwsConfig: {awsc}")
        return True

    @classmethod
    def from_file(cls, path: Path) -> "WorkspaceConfig":
        if not path.exists():
            raise FileNotFoundError(f"File {path} does not exist")
        if not path.is_file():
            raise ValueError(f"Path {path} is not a file")
        if not path.suffix == ".py":
            raise ValueError(f"File {path} is not a python file")

        ws_config = cls()
        logger.debug(f"--^^-- Building WorkspaceConfig from: {path}")
        ws_config.workspace_root_path = path.parent.resolve()
        workspace_config_objects = {}
        try:
            from phidata.utils.get_python_objects_from_module import (
                get_python_objects_from_module,
            )

            python_objects = get_python_objects_from_module(path)
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
            parent_dir = path.parent.name
            parent_parent_dir = path.parent.parent.name
            if parent_dir in ("resources", "tests") or parent_parent_dir in (
                "resources",
                "tests",
            ):
                pass
            else:
                logger.warning(f"Error in {path}: {e}")
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
                    ws_config.aws_shared_credentials_file = (
                        obj.aws_shared_credentials_file
                    )
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
        return ws_config
