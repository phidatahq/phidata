from typing import Optional, List

from phidata.infra.args import InfraArgs
from phidata.aws.resource.group import AwsResourceGroup


class AwsArgs(InfraArgs):
    # AwsResourceGroups to deploy
    resources: Optional[List[AwsResourceGroup]] = None
    # Resources dir where aws manifests are stored
    resources_dir: str = "aws"
