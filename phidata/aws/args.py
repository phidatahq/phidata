from typing import Optional, List

from phidata.infra.args import InfraArgs
from phidata.app.phidata_app import PhidataApp
from phidata.aws.resource.group import AwsResourceGroup


class AwsArgs(InfraArgs):
    apps: Optional[List[PhidataApp]] = None

    # AwsResourceGroups to deploy
    resources: Optional[List[AwsResourceGroup]] = None
    # Resources dir where aws manifests are stored
    resources_dir: str = "aws"
