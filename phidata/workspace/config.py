from typing import Optional, List, Dict
from typing_extensions import Literal

from phidata.infra.base import InfraConfig, InfraArgs
from phidata.infra.docker.config import DockerConfig
from phidata.infra.k8s.config import K8sConfig
from phidata.infra.aws.config import AwsConfig
from phidata.utils.cli_console import print_error


class WorkspaceConfigArgs(InfraArgs):
    # default env for phi ws up/down
    default_env: Optional[Literal["dev", "stg", "prd"]] = None
    # default config for phi ws up/down
    default_config: Optional[str] = None

    docker: Optional[List[DockerConfig]] = None
    k8s: Optional[List[K8sConfig]] = None
    # AWS configuration per env
    aws: Optional[List[AwsConfig]] = None
    # Common aws configuration used by resources and data assets
    # this is passed down to each aws config and set in the local_env
    aws_region: Optional[str] = None
    aws_profile: Optional[str] = None
    aws_config_file: Optional[str] = None
    aws_shared_credentials_file: Optional[str] = None

    # Path to important directories relative to the workspace_root
    # These directories are joined to the workspace_root dir
    #   to build paths depending on the environments (local, docker, k8s)
    # defaults are set by WorkspaceConfig.__init__()
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
        # default env for phi ws up/down
        default_env: Optional[Literal["dev", "stg", "prd"]] = None,
        # default config for phi ws up/down
        default_config: Optional[str] = None,
        docker: Optional[List[DockerConfig]] = None,
        k8s: Optional[List[K8sConfig]] = None,
        # AWS configuration per env
        aws: Optional[List[AwsConfig]] = None,
        # Common aws configuration used by resources and data assets
        # this is passed down to each aws config and set in the local_env
        aws_region: Optional[str] = None,
        aws_profile: Optional[str] = None,
        aws_config_file: Optional[str] = None,
        aws_shared_credentials_file: Optional[str] = None,
        # src_dir is the dir containing the products directory.
        src_dir: str = "data",
        # path to important directories relative to the workspace_root
        scripts_dir: Optional[str] = None,
        storage_dir: Optional[str] = None,
        meta_dir: Optional[str] = None,
        # path to important directories relative to the
        # workspace_root/src_dir
        products_dir: Optional[str] = None,
        notebooks_dir: Optional[str] = None,
        workspace_config_dir: Optional[str] = None,
        # Env vars added to local env when running workflows
        local_env: Optional[Dict[str, str]] = None,
        # Env vars added to docker env when running workflows
        docker_env: Optional[Dict[str, str]] = None,
        # Env vars added to k8s env when running workflows
        k8s_env: Optional[Dict[str, str]] = None,
    ):
        super().__init__()
        scripts_dir_clean = scripts_dir if scripts_dir else f"scripts"
        storage_dir_clean = storage_dir if storage_dir else f"storage"
        meta_dir_clean = meta_dir if meta_dir else f"meta"
        products_dir_clean = products_dir if products_dir else f"{src_dir}/products"
        notebooks_dir_clean = notebooks_dir if notebooks_dir else f"{src_dir}/notebooks"
        workspace_config_dir_clean = (
            workspace_config_dir if workspace_config_dir else f"{src_dir}/workspace"
        )

        try:
            self.args: WorkspaceConfigArgs = WorkspaceConfigArgs(
                version=version,
                enabled=enabled,
                default_env=default_env,
                default_config=default_config,
                docker=docker,
                k8s=k8s,
                aws=aws,
                aws_region=aws_region,
                aws_profile=aws_profile,
                aws_config_file=aws_config_file,
                aws_shared_credentials_file=aws_shared_credentials_file,
                scripts_dir=scripts_dir_clean,
                storage_dir=storage_dir_clean,
                meta_dir=meta_dir_clean,
                products_dir=products_dir_clean,
                notebooks_dir=notebooks_dir_clean,
                workspace_config_dir=workspace_config_dir_clean,
                local_env=local_env,
                docker_env=docker_env,
                k8s_env=k8s_env,
            )
        except Exception as e:
            print_error(f"Args for {self.__class__.__name__} are not valid")
            raise

    @property
    def default_env(self) -> Optional[Literal["dev", "stg", "prd"]]:
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

    @property
    def aws_region(self) -> Optional[str]:
        return self.args.aws_region if self.args else None

    @property
    def aws_profile(self) -> Optional[str]:
        return self.args.aws_profile if self.args else None

    @property
    def aws_config_file(self) -> Optional[str]:
        return self.args.aws_config_file if self.args else None

    @property
    def aws_shared_credentials_file(self) -> Optional[str]:
        return self.args.aws_shared_credentials_file if self.args else None

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
