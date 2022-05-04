from collections import OrderedDict

from phidata.app import PhidataApp, PhidataAppArgs
from phidata.infra.docker.resource.group import (
    DockerBuildContext,
)
from phidata.infra.k8s.resource.group import (
    K8sBuildContext,
)
from phidata.utils.log import logger


class AirbyteArgs(PhidataAppArgs):
    name: str = "airbyte"
    version: str = "1"
    enabled: bool = True


class Airbyte(PhidataApp):
    def __init__(
        self,
        name: str = "airbyte",
        version: str = "1",
        enabled: bool = True,
    ):

        super().__init__()
        try:
            self.args: AirbyteArgs = AirbyteArgs(
                name=name,
                version=version,
                enabled=enabled,
            )
        except Exception as e:
            logger.error(f"Args for {self.__class__.__name__} are not valid")
            raise

    def init_docker_resource_groups(
        self, docker_build_context: DockerBuildContext
    ) -> None:
        self.docker_resource_groups = OrderedDict()

    def init_k8s_resource_groups(self, k8s_build_context: K8sBuildContext) -> None:
        self.k8s_resource_groups = OrderedDict()
