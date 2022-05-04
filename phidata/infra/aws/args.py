from typing import Optional

from phidata.infra.aws.resource.group import AwsResourceGroup
from phidata.infra.base import InfraArgs
from phidata.infra.k8s.args import K8sArgs


class AwsArgs(InfraArgs):
    resources: Optional[AwsResourceGroup] = None
    resources_dir: str = "aws"

    # AWS configuration for this env
    # Use aws config from WorkspaceConfig if not provided
    aws_region: Optional[str] = None
    aws_profile: Optional[str] = None
    aws_config_file: Optional[str] = None
    aws_shared_credentials_file: Optional[str] = None
