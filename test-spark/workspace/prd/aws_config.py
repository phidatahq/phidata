from phidata.aws.config import AwsConfig

from workspace.prd.airflow.aws_resources import prd_airflow_aws_resources
from workspace.prd.aws_resources import prd_aws_resources
from workspace.prd.jupyter.jupyter_lab import prd_jupyter_aws_resources
from workspace.prd.postgres import prd_postgres_aws_resources
from workspace.prd.superset.aws_resources import prd_superset_aws_resources
from workspace.settings import ws_settings

#
# -*- Define production AWS resources using the AwsConfig
#
prd_aws_config = AwsConfig(
    env=ws_settings.prd_env,
    resources=[
        prd_aws_resources,
        prd_airflow_aws_resources,
        prd_postgres_aws_resources,
        prd_superset_aws_resources,
        prd_jupyter_aws_resources,
    ],
)
