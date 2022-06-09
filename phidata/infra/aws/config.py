from typing import Optional, List, Union

from phidata.infra.base import InfraConfig
from phidata.infra.aws.args import AwsArgs
from phidata.infra.aws.manager import AwsManager
from phidata.infra.aws.resource.group import AwsResourceGroup
from phidata.utils.log import logger


class AwsConfig(InfraConfig):
    def __init__(
        self,
        env: Optional[str] = "prd",
        version: Optional[str] = None,
        enabled: bool = True,
        # AwsResourceGroups to deploy
        resources: Optional[Union[AwsResourceGroup, List[AwsResourceGroup]]] = None,
        # Resources dir where aws manifests are stored
        resources_dir: str = "aws",
        # Aws params for this Config
        # Override the aws params from WorkspaceConfig if provided
        aws_region: Optional[str] = None,
        aws_profile: Optional[str] = None,
        aws_config_file: Optional[str] = None,
        aws_shared_credentials_file: Optional[str] = None,
    ):
        super().__init__()
        _resources: Optional[List[AwsResourceGroup]] = None
        if isinstance(resources, AwsResourceGroup):
            _resources = [resources]
        elif isinstance(resources, list):
            _resources = resources
        else:
            raise TypeError(
                "AwsConfig.resources should be AwsResourceGroup or List[AwsResourceGroup]"
            )

        try:
            self.args: AwsArgs = AwsArgs(
                env=env,
                version=version,
                enabled=enabled,
                resources=_resources,
                resources_dir=resources_dir,
                aws_region=aws_region,
                aws_profile=aws_profile,
                aws_config_file=aws_config_file,
                aws_shared_credentials_file=aws_shared_credentials_file,
            )
        except Exception as e:
            logger.error(f"Args for {self.__class__.__name__} are not valid")
            raise

    @property
    def resources(self) -> Optional[List[AwsResourceGroup]]:
        return self.args.resources if self.args else None

    @property
    def resources_dir(self) -> Optional[str]:
        return self.args.resources_dir if self.args else None

    @resources_dir.setter
    def resources_dir(self, resources_dir: str) -> None:
        if self.args is not None and resources_dir is not None:
            self.args.resources_dir = resources_dir

    def is_valid(self) -> bool:
        return True

    def get_aws_manager(self) -> Optional[AwsManager]:
        return AwsManager(aws_args=self.args)
