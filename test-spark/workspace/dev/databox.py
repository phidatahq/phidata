from phidata.app.databox import Databox
from phidata.docker.resource.image import DockerImage

from workspace.dev.airflow.docker_resources import (
    dev_airflow_env,
    dev_airflow_env_file,
    dev_airflow_secrets_file,
)
from workspace.dev.postgres import dev_postgres_airflow_connections
from workspace.settings import ws_settings

#
# -*- Databox Docker resources
#

# -*- Databox image
dev_databox_image = DockerImage(
    name=f"{ws_settings.image_repo}/databox-{ws_settings.image_suffix}",
    tag=ws_settings.dev_env,
    enabled=ws_settings.build_images,
    path=str(ws_settings.ws_root),
    dockerfile="workspace/dev/images/databox.Dockerfile",
    pull=ws_settings.force_pull_images,
    push_image=ws_settings.push_images,
    skip_docker_cache=ws_settings.skip_image_cache,
    use_cache=ws_settings.use_cache,
)

# Databox
dev_databox = Databox(
    enabled=ws_settings.dev_databox_enabled,
    image=dev_databox_image,
    mount_workspace=True,
    env=dev_airflow_env,
    env_file=dev_airflow_env_file,
    secrets_file=dev_airflow_secrets_file,
    use_cache=ws_settings.use_cache,
    db_connections=dev_postgres_airflow_connections,
    # Access the databox airflow webserver on http://localhost:8390
    airflow_standalone_host_port=8390,
    # Mark as false after first run
    # Init airflow db on container start -- mark as false after first run
    init_airflow_db=True,
    # Upgrade the airflow db on container start -- mark as false after first run
    upgrade_airflow_db=True,
    # Creates airflow user: admin, pass: admin -- mark as false after first run
    create_airflow_admin_user=True,
    # Run the airflow webserver on airflow.dp
    container_labels={
        "traefik.enable": "true",
        "traefik.http.routers.databox.entrypoints": "http",
        "traefik.http.routers.databox.rule": "Host(`databox.dp`)",
        # point the traefik loadbalancer to the webserver_port on the container
        "traefik.http.services.databox.loadbalancer.server.port": "8080",
    },
)
