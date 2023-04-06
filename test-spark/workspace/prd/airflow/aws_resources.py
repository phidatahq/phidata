from phidata.aws.resource.group import (
    AwsResourceGroup,
    CacheCluster,
    CacheSubnetGroup,
    DbInstance,
    DbSubnetGroup,
    EbsVolume,
)

from workspace.prd.aws_resources import prd_eks_cluster
from workspace.settings import ws_settings

#
# -*- Airflow AWS resources
#

# -*- Settings
# Use RDS as database instead of running postgres on k8s
use_rds: bool = False
# Use ElastiCache as cache instead of running redis on k8s
use_elasticache: bool = False
# Do not create the resource when running `phi ws up`
skip_create: bool = False
# Do not delete the resource when running `phi ws down`
skip_delete: bool = False
# Wait for the resource to be created
wait_for_create: bool = True
# Wait for the resource to be deleted
wait_for_delete: bool = True

# -*- EbsVolumes for airflow database and cache
# NOTE: For production, use RDS and ElastiCache instead of running postgres/redis on k8s.
# EbsVolume for airflow-db
prd_airflow_db_volume = EbsVolume(
    name=f"airflow-db-{ws_settings.prd_key}",
    enabled=(not use_rds),
    size=32,
    tags=ws_settings.prd_tags,
    availability_zone=ws_settings.aws_az1,
    skip_create=skip_create,
    skip_delete=skip_delete,
    wait_for_creation=wait_for_create,
    wait_for_deletion=wait_for_delete,
)
# EbsVolume for airflow-redis
prd_airflow_redis_volume = EbsVolume(
    name=f"airflow-redis-{ws_settings.prd_key}",
    enabled=(not use_elasticache),
    size=16,
    tags=ws_settings.prd_tags,
    availability_zone=ws_settings.aws_az1,
    skip_create=skip_create,
    skip_delete=skip_delete,
    wait_for_creation=wait_for_create,
    wait_for_deletion=wait_for_delete,
)

# -*- RDS Database Subnet Group
prd_rds_subnet_group = DbSubnetGroup(
    name=f"{ws_settings.prd_key}-db-sg",
    enabled=use_rds,
    # subnet_ids=ws_settings.subnet_ids,
    vpc_stack=prd_eks_cluster.get_vpc_stack(),
    skip_create=skip_create,
    skip_delete=skip_delete,
    wait_for_creation=wait_for_create,
    wait_for_deletion=wait_for_delete,
)

# -*- Elasticache Subnet Group
prd_elasticache_subnet_group = CacheSubnetGroup(
    name=f"{ws_settings.prd_key}-cache-sg",
    enabled=use_elasticache,
    # subnet_ids=ws_settings.subnet_ids,
    vpc_stack=prd_eks_cluster.get_vpc_stack(),
    skip_create=skip_create,
    skip_delete=skip_delete,
    wait_for_creation=wait_for_create,
    wait_for_deletion=wait_for_delete,
)

# -*- RDS Database Instance
db_engine = "postgres"
prd_airflow_rds_db = DbInstance(
    name=f"airflow-db-{ws_settings.prd_key}",
    enabled=use_rds,
    engine=db_engine,
    engine_version="14.5",
    allocated_storage=100,
    # NOTE: For production, use a larger instance type.
    # Last checked price: $0.152 per hour = ~$110 per month
    db_instance_class="db.m6g.large",
    availability_zone=ws_settings.aws_az1,
    db_subnet_group=prd_rds_subnet_group,
    enable_performance_insights=True,
    vpc_security_group_ids=ws_settings.security_groups,
    secrets_file=ws_settings.ws_root.joinpath(
        "workspace/secrets/prd_airflow_db_secrets.yml"
    ),
    skip_create=skip_create,
    skip_delete=skip_delete,
    wait_for_creation=wait_for_create,
    wait_for_deletion=wait_for_delete,
)

# -*- Elasticache Redis Cluster
prd_airflow_redis_cluster = CacheCluster(
    name=f"airflow-cache-{ws_settings.prd_key}",
    enabled=use_elasticache,
    engine="redis",
    num_cache_nodes=1,
    # NOTE: For production, use a larger instance type.
    # Last checked price: $0.068 per hour = ~$50 per month
    cache_node_type="cache.t2.medium",
    security_group_ids=ws_settings.security_groups,
    cache_subnet_group=prd_elasticache_subnet_group,
    preferred_availability_zone=ws_settings.aws_az1,
    skip_create=skip_create,
    skip_delete=skip_delete,
    wait_for_creation=wait_for_create,
    wait_for_deletion=wait_for_delete,
)

prd_airflow_aws_resources = AwsResourceGroup(
    name="airflow",
    enabled=ws_settings.prd_airflow_enabled,
    db_instances=[prd_airflow_rds_db],
    db_subnet_groups=[prd_rds_subnet_group],
    cache_clusters=[prd_airflow_redis_cluster],
    cache_subnet_groups=[prd_elasticache_subnet_group],
    volumes=[prd_airflow_db_volume, prd_airflow_redis_volume],
)
