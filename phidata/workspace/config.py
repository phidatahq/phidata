from pathlib import Path
from typing import Optional, List, Dict, Union

from phidata.infra.base import InfraConfig, InfraArgs
from phidata.infra.docker.config import DockerConfig
from phidata.infra.k8s.config import K8sConfig
from phidata.infra.aws.config import AwsConfig
from phidata.utils.log import logger


class WorkspaceConfigArgs(InfraArgs):
    # default env for phi ws ... commands
    default_env: Optional[str] = None
    # default config for phi ws ... commands
    default_config: Optional[str] = None

    # List of Docker configurations
    docker: Optional[List[DockerConfig]] = None
    # List of K8s configurations
    k8s: Optional[List[K8sConfig]] = None
    # List of AWS configurations
    aws: Optional[List[AwsConfig]] = None

    # Path to important directories relative to the workspace_root
    # These are inherited from InfraArgs but are marked as `str`
    # in WorkspaceConfigArgs
    scripts_dir: str
    storage_dir: str
    meta_dir: str
    products_dir: str
    notebooks_dir: str
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
        # List of Docker configurationsdo
        docker: Optional[List[DockerConfig]] = None,
        # List of K8s configurations
        k8s: Optional[List[K8sConfig]] = None,
        # List of AWS configurations
        aws: Optional[List[AwsConfig]] = None,
        # Path to important directories relative to the workspace_root
        scripts_dir: Optional[str] = None,
        storage_dir: Optional[str] = None,
        meta_dir: Optional[str] = None,
        # src_dir is the top-level python package directory
        # it contains the products & notebooks directories
        # if products_dir == None, the default used is "{src_dir}/products"
        src_dir: str = "data",
        products_dir: Optional[str] = None,
        notebooks_dir: Optional[str] = None,
        workspace_config_dir: Optional[str] = None,
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
        scripts_dir_clean = scripts_dir or "scripts"
        storage_dir_clean = storage_dir or "storage"
        meta_dir_clean = meta_dir or "meta"
        products_dir_clean = products_dir or f"{src_dir}/products"
        notebooks_dir_clean = notebooks_dir or f"{src_dir}/notebooks"
        workspace_config_dir_clean = workspace_config_dir or "workspace"

        try:
            self.args: WorkspaceConfigArgs = WorkspaceConfigArgs(
                version=version,
                enabled=enabled,
                default_env=default_env,
                default_config=default_config,
                docker=docker,
                k8s=k8s,
                aws=aws,
                scripts_dir=scripts_dir_clean,
                storage_dir=storage_dir_clean,
                meta_dir=meta_dir_clean,
                products_dir=products_dir_clean,
                notebooks_dir=notebooks_dir_clean,
                workspace_config_dir=workspace_config_dir_clean,
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
    def docker(self) -> Optional[List[DockerConfig]]:
        return self.args.docker if self.args else None

    @property
    def k8s(self) -> Optional[List[K8sConfig]]:
        return self.args.k8s if self.args else None

    @property
    def aws(self) -> Optional[List[AwsConfig]]:
        return self.args.aws if self.args else None

    def is_valid(self) -> bool:
        if self.docker is not None:
            if not isinstance(self.docker, list):
                raise ValueError("docker should be a list")
            for dc in self.docker:
                if not isinstance(dc, DockerConfig):
                    raise ValueError(f"Invalid DockerConfig: {dc}")

        if self.k8s is not None:
            if not isinstance(self.k8s, list):
                raise ValueError("k8s should be a list")
            for kc in self.k8s:
                if not isinstance(kc, K8sConfig):
                    raise ValueError(f"Invalid K8sConfig: {kc}")

        if self.aws is not None:
            if not isinstance(self.aws, list):
                raise ValueError("aws should be a list")
            for awsc in self.aws:
                if not isinstance(awsc, AwsConfig):
                    raise ValueError(f"Invalid AwsConfig: {awsc}")
        return True
