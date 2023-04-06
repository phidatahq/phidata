from pathlib import Path

from phidata.app.superset import (
    SupersetInit,
    SupersetWebserver,
    SupersetWorker,
    SupersetWorkerBeat,
    ImagePullPolicy,
)
from phidata.app.group import AppGroup
from phidata.app.postgres import PostgresDb, PostgresVolumeType
from phidata.app.redis import Redis, RedisVolumeType

from workspace.prd.superset.aws_resources import (
    use_rds,
    use_elasticache,
    prd_superset_rds_db,
    prd_superset_db_volume,
    prd_superset_redis_volume,
    prd_superset_redis_cluster,
)
from workspace.prd.aws_resources import (
    services_ng_label,
    topology_spread_key,
    topology_spread_max_skew,
    topology_spread_when_unsatisfiable,
    workers_ng_label,
)
from workspace.prd.images import prd_superset_image
from workspace.settings import ws_settings

#
# -*- Superset Kubernetes resources
#

# -*- Superset db: A postgres instance to use as the database for superset
prd_superset_db = PostgresDb(
    name="ss-db",
    volume_type=PostgresVolumeType.AWS_EBS,
    ebs_volume=prd_superset_db_volume,
    secrets_file=ws_settings.ws_root.joinpath(
        "workspace/secrets/prd_superset_db_secrets.yml"
    ),
    pod_node_selector=services_ng_label,
)

# -*- Superset redis: A redis instance to use as the celery backend for superset
prd_superset_redis = Redis(
    name="ss-redis",
    volume_type=RedisVolumeType.AWS_EBS,
    ebs_volume=prd_superset_redis_volume,
    command=["redis-server", "--save", "60", "1"],
    pod_node_selector=services_ng_label,
)

# -*- Settings
# waits for superset-db to be ready before starting app
wait_for_db: bool = True
# waits for superset-redis to be ready before starting app
wait_for_redis: bool = True
# Mount the ws_repo using git-sync
mount_workspace: bool = False
# Create a git-sync sidecar
create_git_sync_sidecar: bool = False
# Read env variables from env/prd_superset_env.yml
prd_superset_env_file: Path = ws_settings.ws_root.joinpath(
    "workspace/env/prd_superset_env.yml"
)
# Read secrets from secrets/prd_superset_secrets.yml
prd_superset_secrets_file: Path = ws_settings.ws_root.joinpath(
    "workspace/secrets/prd_superset_secrets.yml"
)

# -*- Database configuration
db_user = (
    prd_superset_rds_db.get_master_username()
    if use_rds
    else prd_superset_db.get_db_user()
)
db_password = (
    prd_superset_rds_db.get_master_user_password()
    if use_rds
    else prd_superset_db.get_db_password()
)
db_schema = (
    prd_superset_rds_db.get_db_name() if use_rds else prd_superset_db.get_db_schema()
)
db_dialect = "postgresql"
# NOTE: Add DATABASE_HOST & DATABASE_PORT env variables to secrets for RDS
db_host = None if use_rds else prd_superset_db.get_db_host_k8s()
db_port = None if use_rds else prd_superset_db.get_db_port_k8s()

# -*- Redis configuration
redis_password = (
    prd_superset_redis_cluster.get_auth_token()
    if use_elasticache
    else prd_superset_redis.get_db_password()
)
redis_driver = "rediss" if redis_password else "redis"
# NOTE: Add REDIS_HOST & REDIS_PORT env variables to secrets
redis_host = None if use_elasticache else prd_superset_redis.get_db_host_k8s()
redis_port = None if use_elasticache else prd_superset_redis.get_db_port_k8s()

# -*- Superset webserver
prd_superset_ws = SupersetWebserver(
    replicas=2,
    image_name=prd_superset_image.name,
    image_tag=prd_superset_image.tag,
    wait_for_db=wait_for_db,
    db_user=db_user,
    db_password=db_password,
    db_schema=db_schema,
    db_dialect=db_dialect,
    db_host=db_host,
    db_port=db_port,
    wait_for_redis=wait_for_redis,
    redis_password=redis_password,
    redis_driver=redis_driver,
    redis_host=redis_host,
    redis_port=redis_port,
    mount_workspace=mount_workspace,
    create_git_sync_sidecar=create_git_sync_sidecar,
    git_sync_repo=ws_settings.ws_repo,
    git_sync_branch=ws_settings.prd_branch,
    env_file=prd_superset_env_file,
    secrets_file=prd_superset_secrets_file,
    image_pull_policy=ImagePullPolicy.ALWAYS,
    use_cache=ws_settings.use_cache,
    pod_node_selector=services_ng_label,
    topology_spread_key=topology_spread_key,
    topology_spread_max_skew=topology_spread_max_skew,
    topology_spread_when_unsatisfiable=topology_spread_when_unsatisfiable,
)

# -*- Superset init
superset_init_enabled = True  # Mark as False after first run
prd_superset_init = SupersetInit(
    enabled=superset_init_enabled,
    image_name=prd_superset_image.name,
    image_tag=prd_superset_image.tag,
    wait_for_db=wait_for_db,
    db_user=db_user,
    db_password=db_password,
    db_schema=db_schema,
    db_dialect=db_dialect,
    db_host=db_host,
    db_port=db_port,
    wait_for_redis=wait_for_redis,
    redis_password=redis_password,
    redis_driver=redis_driver,
    redis_host=redis_host,
    redis_port=redis_port,
    mount_workspace=mount_workspace,
    create_git_sync_sidecar=create_git_sync_sidecar,
    git_sync_repo=ws_settings.ws_repo,
    git_sync_branch=ws_settings.prd_branch,
    env_file=prd_superset_env_file,
    secrets_file=prd_superset_secrets_file,
    image_pull_policy=ImagePullPolicy.ALWAYS,
    use_cache=ws_settings.use_cache,
    pod_node_selector=workers_ng_label,
    topology_spread_key=topology_spread_key,
    topology_spread_max_skew=topology_spread_max_skew,
    topology_spread_when_unsatisfiable=topology_spread_when_unsatisfiable,
)

# -*- Superset worker
prd_superset_worker = SupersetWorker(
    replicas=1,
    image_name=prd_superset_image.name,
    image_tag=prd_superset_image.tag,
    wait_for_db=wait_for_db,
    db_user=db_user,
    db_password=db_password,
    db_schema=db_schema,
    db_dialect=db_dialect,
    db_host=db_host,
    db_port=db_port,
    wait_for_redis=wait_for_redis,
    redis_password=redis_password,
    redis_driver=redis_driver,
    redis_host=redis_host,
    redis_port=redis_port,
    mount_workspace=mount_workspace,
    create_git_sync_sidecar=create_git_sync_sidecar,
    git_sync_repo=ws_settings.ws_repo,
    git_sync_branch=ws_settings.prd_branch,
    env_file=prd_superset_env_file,
    secrets_file=prd_superset_secrets_file,
    image_pull_policy=ImagePullPolicy.ALWAYS,
    use_cache=ws_settings.use_cache,
    pod_node_selector=workers_ng_label,
    topology_spread_key=topology_spread_key,
    topology_spread_max_skew=topology_spread_max_skew,
    topology_spread_when_unsatisfiable=topology_spread_when_unsatisfiable,
)

# -*- Superset worker beat
prd_superset_worker_beat = SupersetWorkerBeat(
    replicas=1,
    image_name=prd_superset_image.name,
    image_tag=prd_superset_image.tag,
    wait_for_db=wait_for_db,
    db_user=db_user,
    db_password=db_password,
    db_schema=db_schema,
    db_dialect=db_dialect,
    db_host=db_host,
    db_port=db_port,
    wait_for_redis=wait_for_redis,
    redis_password=redis_password,
    redis_driver=redis_driver,
    redis_host=redis_host,
    redis_port=redis_port,
    mount_workspace=mount_workspace,
    create_git_sync_sidecar=create_git_sync_sidecar,
    git_sync_repo=ws_settings.ws_repo,
    git_sync_branch=ws_settings.prd_branch,
    env_file=prd_superset_env_file,
    secrets_file=prd_superset_secrets_file,
    image_pull_policy=ImagePullPolicy.ALWAYS,
    use_cache=ws_settings.use_cache,
    pod_node_selector=workers_ng_label,
    topology_spread_key=topology_spread_key,
    topology_spread_max_skew=topology_spread_max_skew,
    topology_spread_when_unsatisfiable=topology_spread_when_unsatisfiable,
)

prd_superset_apps = AppGroup(
    name="superset",
    enabled=ws_settings.prd_superset_enabled,
    apps=[
        prd_superset_db,
        prd_superset_redis,
        prd_superset_ws,
        prd_superset_init,
        prd_superset_worker,
        prd_superset_worker_beat,
    ],
)
