from pathlib import Path

from phidata.app.group import AppGroup
from phidata.app.postgres import PostgresDb
from phidata.app.redis import Redis
from phidata.app.superset import SupersetInit, SupersetWebserver
from phidata.docker.resource.image import DockerImage

from workspace.settings import ws_settings

#
# -*- Superset Docker resources
#

# Superset db: A postgres instance to use as the database for superset
dev_superset_db = PostgresDb(
    name=f"superset-db-{ws_settings.ws_name}",
    db_user="superset",
    db_password="superset",
    db_schema="superset",
    # Connect to this db on port 8340
    container_host_port=8340,
)

# Superset redis: A redis instance to use as the celery backend for superset
dev_superset_redis = Redis(
    name=f"superset-redis-{ws_settings.ws_name}",
    command=["redis-server", "--save", "60", "1", "--loglevel", "debug"],
    container_host_port=8341,
)

# -*- Settings
# waits for superset-db to be ready before starting app
wait_for_db: bool = True
# waits for superset-redis to be ready before starting app
wait_for_redis: bool = True
# Mount the resources dir using a docker volume
mount_resources: bool = True
dev_superset_resources: str = "workspace/dev/superset/resources"
# Read env variables from env/dev_superset_env.yml
dev_superset_env_file: Path = ws_settings.ws_root.joinpath(
    "workspace/env/dev_superset_env.yml"
)
# Read secrets from secrets/dev_superset_secrets.yml
dev_superset_secrets_file: Path = ws_settings.ws_root.joinpath(
    "workspace/secrets/dev_superset_secrets.yml"
)

# -*- Superset image
dev_superset_image = DockerImage(
    name=f"{ws_settings.image_repo}/superset-{ws_settings.image_suffix}",
    tag=ws_settings.dev_env,
    enabled=ws_settings.build_images,
    path=str(ws_settings.ws_root),
    dockerfile="workspace/dev/images/superset.Dockerfile",
    pull=ws_settings.force_pull_images,
    push_image=ws_settings.push_images,
    skip_docker_cache=ws_settings.skip_image_cache,
    use_cache=ws_settings.use_cache,
)

# Superset webserver
dev_superset_ws = SupersetWebserver(
    image=dev_superset_image,
    db_app=dev_superset_db,
    wait_for_db=wait_for_db,
    redis_app=dev_superset_redis,
    wait_for_redis=wait_for_redis,
    mount_resources=mount_resources,
    resources_dir=dev_superset_resources,
    env_file=dev_superset_env_file,
    secrets_file=dev_superset_secrets_file,
    use_cache=ws_settings.use_cache,
    # Access the superset webserver on http://localhost:8410
    app_host_port=8410,
    # Run the superset webserver on superset.dp
    container_labels={
        "traefik.enable": "true",
        "traefik.http.routers.superset-ws.entrypoints": "http",
        "traefik.http.routers.superset-ws.rule": "Host(`superset.dp`)",
        # point the traefik loadbalancer to the app_port on the container
        "traefik.http.services.superset-ws.loadbalancer.server.port": "8088",
    },
)

# Superset init
dev_superset_init = SupersetInit(
    enabled=True,  # Mark as False after first run
    image=dev_superset_image,
    db_app=dev_superset_db,
    wait_for_db=wait_for_db,
    redis_app=dev_superset_redis,
    wait_for_redis=wait_for_redis,
    mount_resources=mount_resources,
    resources_dir=dev_superset_resources,
    env_file=dev_superset_env_file,
    secrets_file=dev_superset_secrets_file,
    use_cache=ws_settings.use_cache,
    load_examples=False,
)

dev_superset_apps = AppGroup(
    name="superset",
    enabled=ws_settings.dev_superset_enabled,
    apps=[
        dev_superset_db,
        dev_superset_redis,
        dev_superset_ws,
        dev_superset_init,
    ],
)
