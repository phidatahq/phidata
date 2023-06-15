from typing import Optional, List, Union

from phidata.app.base_app import BaseApp
from phidata.app.phidata_app import PhidataApp
from phidata.aws.resource.group import AwsResourceGroup
from phidata.infra.args import InfraArgs


class AwsArgs(InfraArgs):
    apps: Optional[List[Union[BaseApp, PhidataApp]]] = None

    # AwsResourceGroups to deploy
    resources: Optional[List[AwsResourceGroup]] = None
    # Resources dir where aws manifests are stored
    resources_dir: str = "aws"
