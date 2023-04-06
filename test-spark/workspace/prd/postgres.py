from phidata.app.group import AppGroup
from phidata.app.postgres import PostgresDb, PostgresVolumeType
from phidata.aws.resource.group import AwsResourceGroup, EbsVolume

from workspace.prd.aws_resources import services_ng_label
from workspace.settings import ws_settings

# -*- Settings
db_id: str = "1"
# Do not create the resource when running `phi ws up`
skip_create: bool = False
# Do not delete the resource when running `phi ws down`
skip_delete: bool = False
# Wait for the resource to be created
wait_for_create: bool = True
# Wait for the resource to be deleted
wait_for_delete: bool = True

#
# -*- AWS resources
#
# -*- EbsVolumes
# EbsVolume for postgres db
prd_postgres_volume = EbsVolume(
    name=f"postgres-{db_id}-{ws_settings.prd_key}",
    size=32,
    availability_zone=ws_settings.aws_az1,
    tags=ws_settings.prd_tags,
    skip_create=skip_create,
    skip_delete=skip_delete,
    wait_for_creation=wait_for_create,
    wait_for_deletion=wait_for_delete,
)

prd_postgres_aws_resources = AwsResourceGroup(
    name=f"postgres-{db_id}",
    enabled=ws_settings.prd_postgres_enabled,
    volumes=[prd_postgres_volume],
)

#
# -*- Kubernetes resources
#
# Prd postgres: A postgres instance to use for production data
prd_postgres = PostgresDb(
    name=f"postgres-{db_id}",
    volume_type=PostgresVolumeType.AWS_EBS,
    ebs_volume=prd_postgres_volume,
    secrets_file=ws_settings.ws_root.joinpath(
        "workspace/secrets/prd_postgres_secrets.yml"
    ),
    pod_node_selector=services_ng_label,
)

prd_postgres_connection_id = "prd_postgres"
prd_postgres_airflow_connections = {
    prd_postgres_connection_id: prd_postgres.get_db_connection_url_k8s()
}

prd_postgres_apps = AppGroup(
    name="postgres",
    enabled=ws_settings.prd_postgres_enabled,
    apps=[prd_postgres],
)
