from typing import List, Optional

from pydantic import BaseModel

from phi.docker.resource.network import DockerNetwork
from phi.docker.resource.image import DockerImage
from phi.docker.resource.container import DockerContainer
from phi.docker.resource.volume import DockerVolume


class DockerResourceGroup(BaseModel):
    """The DockerResourceGroup class contains the instructions to manage docker resources"""

    name: str = "default"
    enabled: bool = True

    # Deprecated. DO NOT USE
    weight: int = 100

    network: Optional[DockerNetwork] = None
    images: Optional[List[DockerImage]] = None
    containers: Optional[List[DockerContainer]] = None
    # secrets: Optional[List[DockerSecret]] = None
    volumes: Optional[List[DockerVolume]] = None


class DockerBuildContext(BaseModel):
    """This class is used to store default information when creating a DockerResourceGroup"""

    network: str
