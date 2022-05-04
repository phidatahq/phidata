from typing import Optional
from typing_extensions import Literal

from phidata.infra.base import InfraConfig
from phidata.infra.aws.args import AwsArgs
from phidata.infra.aws.manager import AwsManager
from phidata.infra.aws.resource.group import AwsResourceGroup


class AwsConfig(InfraConfig):
    def __init__(
        self,
        name: Optional[str] = None,
        env: Optional[Literal["dev", "stg", "prd"]] = "prd",
        version: Optional[str] = None,
        enabled: bool = True,
        resources: Optional[AwsResourceGroup] = None,
        resources_dir: str = "aws",
        # AWS configuration for this env
        # Use aws config from WorkspaceConfig if not provided
        aws_region: Optional[str] = None,
        aws_profile: Optional[str] = None,
        aws_config_file: Optional[str] = None,
        aws_shared_credentials_file: Optional[str] = None,
    ):
        super().__init__()
        try:
            self.args: AwsArgs = AwsArgs(
                name=name,
                env=env,
                version=version,
                enabled=enabled,
                resources=resources,
                resources_dir=resources_dir,
                aws_region=aws_region,
                aws_profile=aws_profile,
                aws_config_file=aws_config_file,
                aws_shared_credentials_file=aws_shared_credentials_file,
            )
        except Exception as e:
            raise

    @property
    def resources(self) -> Optional[AwsResourceGroup]:
        return self.args.resources if self.args else None

    @property
    def resources_dir(self) -> Optional[str]:
        return self.args.resources_dir if self.args else None

    @resources_dir.setter
    def resources_dir(self, resources_dir: str) -> None:
        if self.args is not None and resources_dir is not None:
            self.args.resources_dir = resources_dir

    @property
    def aws_region(self) -> Optional[str]:
        return self.args.aws_region if self.args else None

    @aws_region.setter
    def aws_region(self, aws_region: str) -> None:
        if self.args is not None and aws_region is not None:
            self.args.aws_region = aws_region

    @property
    def aws_profile(self) -> Optional[str]:
        return self.args.aws_profile if self.args else None

    @aws_profile.setter
    def aws_profile(self, aws_profile: str) -> None:
        if self.args is not None and aws_profile is not None:
            self.args.aws_profile = aws_profile

    @property
    def aws_config_file(self) -> Optional[str]:
        return self.args.aws_config_file if self.args else None

    @aws_config_file.setter
    def aws_config_file(self, aws_config_file: str) -> None:
        if self.args is not None and aws_config_file is not None:
            self.args.aws_config_file = aws_config_file

    @property
    def aws_shared_credentials_file(self) -> Optional[str]:
        return self.args.aws_shared_credentials_file if self.args else None

    @aws_shared_credentials_file.setter
    def aws_shared_credentials_file(self, aws_shared_credentials_file: str) -> None:
        if self.args is not None and aws_shared_credentials_file is not None:
            self.args.aws_shared_credentials_file = aws_shared_credentials_file

    def resources_are_valid(self) -> bool:
        if self.resources is None:
            return True
        if not isinstance(self.resources, AwsResourceGroup):
            raise TypeError("Invalid AwsResourceGroup: {}".format(self.resources))
        return True

    def is_valid(self) -> bool:
        return self.resources_are_valid()

    def get_aws_manager(self) -> Optional[AwsManager]:
        return AwsManager(aws_args=self.args)
