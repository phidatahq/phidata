from phidata.aws.config import AwsConfig

from workspace.dev.aws_resources import dev_aws_resources
from workspace.settings import ws_settings

#
# -*- Define dev AWS resources using the AwsConfig
#
dev_aws_config = AwsConfig(
    env=ws_settings.dev_env,
    resources=[dev_aws_resources],
)
