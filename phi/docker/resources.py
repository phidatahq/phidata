from typing import List, Optional

from phi.docker.app.base import DockerApp
from phi.docker.resource.base import DockerResource
from phi.infra.resource_group import InfraResourceGroup


class DockerResources(InfraResourceGroup):
    network: str = "bridge"
    # URL for the Docker server. For example, unix:///var/run/docker.sock or tcp://127.0.0.1:1234
    base_url: Optional[str] = None

    apps: Optional[List[DockerApp]] = None
    resources: Optional[List[DockerResource]] = None
