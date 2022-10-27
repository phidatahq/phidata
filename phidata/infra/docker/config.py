from typing import List, Optional

from phidata.app.phidata_app import PhidataApp
from phidata.app.databox import default_databox_name
from phidata.infra.base import InfraConfig
from phidata.infra.docker.args import DockerArgs
from phidata.infra.docker.manager import DockerManager
from phidata.infra.docker.resource.image import DockerImage
from phidata.infra.docker.resource.container import DockerContainer
from phidata.infra.docker.resource.volume import DockerVolume
from phidata.infra.docker.resource.group import DockerResourceGroup
from phidata.utils.log import logger


class DockerConfig(InfraConfig):
    def __init__(
        self,
        name: Optional[str] = None,
        env: Optional[str] = "dev",
        version: Optional[str] = None,
        enabled: bool = True,
        network: str = "phi",
        base_url: Optional[str] = None,
        apps: Optional[List[PhidataApp]] = None,
        images: Optional[List[DockerImage]] = None,
        containers: Optional[List[DockerContainer]] = None,
        volumes: Optional[List[DockerVolume]] = None,
        resources: Optional[List[DockerResourceGroup]] = None,
        databox: str = default_databox_name,
    ):
        super().__init__()
        try:
            self.args: DockerArgs = DockerArgs(
                name=name,
                env=env,
                version=version,
                enabled=enabled,
                network=network,
                base_url=base_url,
                apps=apps,
                images=images,
                containers=containers,
                volumes=volumes,
                resources=resources,
                databox_name=databox,
            )
        except Exception as e:
            raise

    @property
    def network(self) -> Optional[str]:
        return self.args.network if self.args else None

    @property
    def base_url(self) -> Optional[str]:
        return self.args.base_url if self.args else None

    @property
    def apps(self) -> Optional[List[PhidataApp]]:
        return self.args.apps if self.args else None

    @property
    def images(self) -> Optional[List[DockerImage]]:
        return self.args.images if self.args else None

    @property
    def containers(self) -> Optional[List[DockerContainer]]:
        return self.args.containers if self.args else None

    @property
    def volumes(self) -> Optional[List[DockerVolume]]:
        return self.args.volumes if self.args else None

    @property
    def resources(self) -> Optional[List[DockerResourceGroup]]:
        return self.args.resources if self.args else None

    @property
    def databox_name(self) -> Optional[str]:
        return self.args.databox_name if self.args else None

    def apps_are_valid(self) -> bool:
        if self.apps is None:
            return False
        for _app in self.apps:
            if not isinstance(_app, PhidataApp):
                raise TypeError("Invalid App: {}".format(_app))
        return True

    def resources_are_valid(self) -> bool:
        if self.resources is None:
            return False
        for _resource in self.resources:
            if not isinstance(_resource, DockerResourceGroup):
                raise TypeError("Invalid Resource: {}".format(_resource))
        return True

    def default_resources_are_valid(self) -> bool:
        if self.images is None and self.containers is None and self.volumes is None:
            return False
        return True

    def is_valid(self) -> bool:
        return (
            self.apps_are_valid()
            or self.resources_are_valid()
            or self.default_resources_are_valid()
        )

    def get_docker_manager(self) -> DockerManager:
        return DockerManager(docker_args=self.args)

    def get_app_by_name(self, app_name: str) -> Optional[PhidataApp]:

        if self.apps is None:
            return None

        for _app in self.apps:
            try:
                if app_name == _app.name:
                    return _app
            except Exception as e:
                logger.exception(e)
                continue
        return None
