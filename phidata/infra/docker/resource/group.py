from typing import List, Optional

from pydantic import BaseModel

from phidata.infra.docker.resource.network import DockerNetwork
from phidata.infra.docker.resource.image import DockerImage
from phidata.infra.docker.resource.container import DockerContainer
from phidata.infra.docker.resource.volume import DockerVolume


class DockerResourceGroup(BaseModel):
    """The DockerResourceGroup class contains the instructions to manage docker resources"""

    name: str = "default"
    enabled: bool = True

    # The weight variable controls how this is resource group is deployed to a cluster
    # relative to other resource groups.

    # Within each resource group, the resources are deployed in a predefined order
    # eg: network first, then images, volumes, containers and so on..
    # But we can also add an order to how different resource groups are deployed relative to each other.
    # (Eg if we want to deploy a resource group with just storage_class (s) before all other resources)

    # Weights 1-10 are reserved
    # Weight 100 is default.
    # Choose weight 11-99 to deploy a resource group before all the default resources.
    # Choose weight 101+ to deploy a resource group after all the default resources
    weight: int = 100

    network: Optional[DockerNetwork] = None
    images: Optional[List[DockerImage]] = None
    containers: Optional[List[DockerContainer]] = None
    # secrets: Optional[List[DockerSecret]] = None
    volumes: Optional[List[DockerVolume]] = None


class DockerBuildContext(BaseModel):
    """This class is used to store default information when creating a DockerResourceGroup"""

    network: str
