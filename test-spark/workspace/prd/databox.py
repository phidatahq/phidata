from phidata.app.databox import Databox

from workspace.prd.airflow.k8s_apps import (
    prd_airflow_env,
    prd_airflow_env_file,
    prd_airflow_secrets_file,
)
from workspace.prd.aws_resources import (
    topology_spread_key,
    topology_spread_max_skew,
    topology_spread_when_unsatisfiable,
    workers_ng_label,
)
from workspace.prd.images import prd_databox_image
from workspace.prd.postgres import prd_postgres_airflow_connections
from workspace.settings import ws_settings

#
# -*- Databox Kubernetes resources
#

# Databox
prd_databox = Databox(
    enabled=ws_settings.prd_databox_enabled,
    image=prd_databox_image,
    mount_workspace=True,
    create_git_sync_sidecar=True,
    git_sync_repo=ws_settings.ws_repo,
    git_sync_branch=ws_settings.prd_branch,
    env=prd_airflow_env,
    env_file=prd_airflow_env_file,
    secrets_file=prd_airflow_secrets_file,
    use_cache=ws_settings.use_cache,
    db_connections=prd_postgres_airflow_connections,
    pod_node_selector=workers_ng_label,
    topology_spread_key=topology_spread_key,
    topology_spread_max_skew=topology_spread_max_skew,
    topology_spread_when_unsatisfiable=topology_spread_when_unsatisfiable,
)
