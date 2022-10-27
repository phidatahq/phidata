from typing import List, Optional

from pydantic import validator

from phidata.app.phidata_app import PhidataApp
from phidata.app.databox import default_databox_name
from phidata.infra.base import InfraArgs
from phidata.infra.docker.resource.image import DockerImage
from phidata.infra.docker.resource.container import DockerContainer
from phidata.infra.docker.resource.volume import DockerVolume
from phidata.infra.docker.resource.group import DockerResourceGroup


class DockerArgs(InfraArgs):
    network: str = "phi"
    # configure the DockerClient
    # URL to the Docker server. For example, unix:///var/run/docker.sock or tcp://127.0.0.1:1234.
    # when None, phidata use DockerClient.from_env()
    base_url: Optional[str] = None
    apps: Optional[List[PhidataApp]] = None
    # default resources
    images: Optional[List[DockerImage]] = None
    containers: Optional[List[DockerContainer]] = None
    volumes: Optional[List[DockerVolume]] = None
    # additional resource groups
    resources: Optional[List[DockerResourceGroup]] = None
    databox_name: str = default_databox_name

    @validator("apps")
    def apps_are_valid(cls, apps):
        if apps is not None:
            for _app in apps:
                if not isinstance(_app, PhidataApp):
                    raise TypeError("App not of type PhidataApp: {}".format(_app))
        return apps

    def default_resources_available(self) -> bool:
        return (
            self.images is not None
            or self.containers is not None
            or self.volumes is not None
        )
