from phidata.app.group import AppGroup
from phidata.app.jupyter import ImagePullPolicy, JupyterLab
from phidata.aws.resource.group import AwsResourceGroup, EbsVolume

from workspace.prd.aws_resources import (
    topology_spread_key,
    topology_spread_max_skew,
    topology_spread_when_unsatisfiable,
    workers_ng_label,
)
from workspace.prd.images import prd_jupyter_image
from workspace.settings import ws_settings

# -*- Settings
lab_id: str = "1"
# Do not create the resource when running `phi ws up`
skip_create: bool = False
# Do not delete the resource when running `phi ws down`
skip_delete: bool = False
# Wait for the resource to be created
wait_for_create: bool = True
# Wait for the resource to be deleted
wait_for_delete: bool = True

#
# -*- Jupyter AWS resources
#
# -*- EbsVolumes
# EbsVolume for jupyterlab
prd_jupyter_ebs_volume = EbsVolume(
    name=f"jupyter-{lab_id}-{ws_settings.prd_key}",
    size=16,
    availability_zone=ws_settings.aws_az1,
    tags=ws_settings.prd_tags,
    skip_create=skip_create,
    skip_delete=skip_delete,
    wait_for_creation=wait_for_create,
    wait_for_deletion=wait_for_delete,
)

prd_jupyter_aws_resources = AwsResourceGroup(
    name=f"jupyter-{lab_id}",
    enabled=ws_settings.prd_jupyter_enabled,
    volumes=[prd_jupyter_ebs_volume],
)

#
# -*- Jupyter Kubernetes resources
#
# JupyterLab
prd_jupyter = JupyterLab(
    name=f"jupyter-{lab_id}",
    image_name=prd_jupyter_image.name,
    image_tag=prd_jupyter_image.tag,
    mount_ebs_volume=True,
    ebs_volume=prd_jupyter_ebs_volume,
    # The jupyter_lab_config is mounted when creating the image
    jupyter_config_file="/usr/local/jupyter/jupyter_lab_config.py",
    # Read env variables from env/prd_jupyter_env.yml
    env_file=ws_settings.ws_root.joinpath("workspace/env/prd_jupyter_env.yml"),
    # Read secrets from secrets/prd_jupyter_secrets.yml
    secrets_file=ws_settings.ws_root.joinpath(
        "workspace/secrets/prd_jupyter_secrets.yml"
    ),
    image_pull_policy=ImagePullPolicy.ALWAYS,
    use_cache=ws_settings.use_cache,
    pod_node_selector=workers_ng_label,
    topology_spread_key=topology_spread_key,
    topology_spread_max_skew=topology_spread_max_skew,
    topology_spread_when_unsatisfiable=topology_spread_when_unsatisfiable,
)

prd_jupyter_apps = AppGroup(
    name=f"jupyter-{lab_id}",
    enabled=ws_settings.prd_jupyter_enabled,
    apps=[prd_jupyter],
)
