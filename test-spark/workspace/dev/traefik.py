from phidata.docker.resource.container import DockerContainer
from phidata.docker.resource.group import DockerResourceGroup

from workspace.settings import ws_settings

#
# -*- Traefik Docker resources
#

# Traefik router
traefik_container = DockerContainer(
    name="traefik",
    image="traefik:v2.9",
    command=[
        # reference: https://doc.traefik.io/traefik/routing/entrypoints/#configuration-examples
        "--entryPoints.http.address=:80",
        # reference: https://doc.traefik.io/traefik/routing/providers/docker/
        "--providers.docker=true",
        # reference: https://doc.traefik.io/traefik/providers/docker/#endpoint
        "--providers.docker.endpoint=unix:///var/run/docker.sock",
        # reference: https://doc.traefik.io/traefik/providers/docker/#network
        f"--providers.docker.network={ws_settings.ws_name}",
        # reference: https://doc.traefik.io/traefik/operations/api/#configuration
        "--api=true",
        "--api.insecure=true",
        "--log.level=info",
    ],
    detach=True,
    # Serve the traefik dashboard on traefik.dp
    labels={
        "traefik.http.routers.api.rule": "Host(`traefik.dp`)",
        "traefik.http.routers.api.service": "api@internal",
    },
    network=ws_settings.ws_name,
    ports={
        "80": "80",
        "8080": "8380",
    },
    volumes=[
        "/var/run/docker.sock:/var/run/docker.sock:ro",
    ],
    use_cache=ws_settings.use_cache,
)

dev_traefik_resources = DockerResourceGroup(
    name="traefik",
    enabled=ws_settings.dev_traefik_enabled,
    containers=[traefik_container],
)
