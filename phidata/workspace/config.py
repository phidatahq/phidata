from pathlib import Path
from typing import Optional, List, Dict, Union, Any

from phidata.infra.base import InfraConfig, InfraArgs
from phidata.utils.log import logger


class WorkspaceConfigArgs(InfraArgs):
    # default env for phi ws ... commands
    default_env: Optional[str] = None
    # default config for phi ws ... commands
    default_config: Optional[str] = None

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
        # Env vars added to local env
        local_env: Optional[Dict[str, str]] = None,
        # Load local env using env file
        local_env_file: Optional[Union[str, Path]] = None,
        # Env vars added to docker env
        docker_env: Optional[Dict[str, str]] = None,
        # Load docker env using env file
        docker_env_file: Optional[Union[str, Path]] = None,
        # Env vars added to k8s env
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

    @property
    def default_config(self) -> Optional[str]:
        return self.args.default_config if self.args else None

    @property
    def docker(self) -> Optional[List[Any]]:
        return self.args.docker if self.args else None

    @property
    def k8s(self) -> Optional[List[Any]]:
        return self.args.k8s if self.args else None

    @property
    def aws(self) -> Optional[List[Any]]:
        return self.args.aws if self.args else None

    def is_valid(self) -> bool:
        if self.docker is not None:
            from phidata.infra.docker.config import DockerConfig

            if not isinstance(self.docker, list):
                raise ValueError("docker should be a list")
            for dc in self.docker:
                if not isinstance(dc, DockerConfig):
                    raise ValueError(f"Invalid DockerConfig: {dc}")

        if self.k8s is not None:
            from phidata.infra.k8s.config import K8sConfig

            if not isinstance(self.k8s, list):
                raise ValueError("k8s should be a list")
            for kc in self.k8s:
                if not isinstance(kc, K8sConfig):
                    raise ValueError(f"Invalid K8sConfig: {kc}")

        if self.aws is not None:
            from phidata.infra.aws.config import AwsConfig

            if not isinstance(self.aws, list):
                raise ValueError("aws should be a list")
            for awsc in self.aws:
                if not isinstance(awsc, AwsConfig):
                    raise ValueError(f"Invalid AwsConfig: {awsc}")
        return True
