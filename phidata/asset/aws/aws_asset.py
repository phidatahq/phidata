from typing import Optional

from phidata.asset import DataAsset, DataAssetArgs
from phidata.constants import AWS_REGION_ENV_VAR, AWS_PROFILE_ENV_VAR
from phidata.utils.log import logger


class AwsAssetArgs(DataAssetArgs):
    # Aws variables added by WorkspaceConfig().__init__()
    aws_region: Optional[str] = None
    aws_profile: Optional[str] = None


class AwsAsset(DataAsset):
    def __init__(self) -> None:
        super().__init__()
        self.args: Optional[AwsAssetArgs] = None

    @property
    def aws_region(self) -> Optional[str]:
        # aws_asset not yet initialized
        if self.args is None:
            return None

        # use cached value if available
        if self.args.aws_region:
            return self.args.aws_region

        # logger.info(f"Loading {AWS_REGION_ENV_VAR} from env")
        import os

        aws_region_env = os.getenv(AWS_REGION_ENV_VAR)
        # logger.info(f"{AWS_REGION_ENV_VAR}: {aws_region_env}")
        if aws_region_env is not None:
            self.args.aws_region = aws_region_env
        return self.args.aws_region

    @aws_region.setter
    def aws_region(self, aws_region: str) -> None:
        if self.args is not None and aws_region is not None:
            self.args.aws_region = aws_region

    @property
    def aws_profile(self) -> Optional[str]:
        # aws_asset not yet initialized
        if self.args is None:
            return None

        # use cached value if available
        if self.args.aws_profile:
            return self.args.aws_profile

        # logger.info(f"Loading {AWS_PROFILE_ENV_VAR} from env")
        import os

        aws_profile_env = os.getenv(AWS_PROFILE_ENV_VAR)
        # logger.info(f"{AWS_PROFILE_ENV_VAR}: {aws_profile_env}")
        if aws_profile_env is not None:
            self.args.aws_profile = aws_profile_env
        return self.args.aws_profile

    @aws_profile.setter
    def aws_profile(self, aws_profile: str) -> None:
        if self.args is not None and aws_profile is not None:
            self.args.aws_profile = aws_profile
