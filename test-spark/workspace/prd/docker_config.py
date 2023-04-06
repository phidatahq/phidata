from phidata.docker.config import DockerConfig

from workspace.prd.images import prd_images
from workspace.settings import ws_settings

#
# -*- Define production Docker resources using the DockerConfig
#
prd_docker_config = DockerConfig(
    env=ws_settings.prd_env,
    network=ws_settings.ws_name,
    images=prd_images,
)
