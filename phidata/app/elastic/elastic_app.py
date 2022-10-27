from collections import OrderedDict
from typing import Optional, List

from phidata.app.phidata_app import PhidataApp, PhidataAppArgs
from phidata.infra.docker.resource.group import (
    DockerResourceGroup,
    DockerBuildContext,
)
from phidata.infra.k8s.create.group import CreateK8sResourceGroup
from phidata.infra.k8s.resource.group import (
    K8sResourceGroup,
    K8sBuildContext,
)
from phidata.utils.cli_console import print_error
from phidata.utils.log import logger


class ElasticAppArgs(PhidataAppArgs):
    name: str = "elastic"
    version: str = "1"
    enabled: bool = True
    docker_resource_groups: Optional[List[DockerResourceGroup]] = None
    k8s_resource_groups: Optional[List[K8sResourceGroup]] = None
    create_k8s_resource_groups: Optional[List[CreateK8sResourceGroup]] = None


class ElasticApp(PhidataApp):
    def __init__(
        self,
        name: str = "elastic",
        version: str = "1",
        enabled: bool = True,
        docker_resource_groups: Optional[List[DockerResourceGroup]] = None,
        k8s_resource_groups: Optional[List[K8sResourceGroup]] = None,
        create_k8s_resource_groups: Optional[List[CreateK8sResourceGroup]] = None,
    ):

        super().__init__()
        try:
            self.args: ElasticAppArgs = ElasticAppArgs(
                name=name,
                version=version,
                enabled=enabled,
                docker_resource_groups=docker_resource_groups,
                k8s_resource_groups=k8s_resource_groups,
                create_k8s_resource_groups=create_k8s_resource_groups,
            )
        except Exception as e:
            logger.error(f"Args for {self.__class__.__name__} are not valid")
            raise

    def init_docker_resource_groups(
        self, docker_build_context: DockerBuildContext
    ) -> None:
        if self.args.docker_resource_groups is not None:
            self.docker_resource_groups = OrderedDict()
            for docker_rg in self.args.docker_resource_groups:
                if docker_rg is not None and isinstance(docker_rg, DockerResourceGroup):
                    self.docker_resource_groups[docker_rg.name] = docker_rg
                else:
                    print_error(
                        "+------+ DockerResourceGroup invalid: {}".format(docker_rg)
                    )

    def init_k8s_resource_groups(self, k8s_build_context: K8sBuildContext) -> None:
        # first check if the k8s_resource_groups are provided
        if self.args.k8s_resource_groups is not None:
            self.k8s_resource_groups = OrderedDict()
            for k8s_rg in self.args.k8s_resource_groups:
                if k8s_rg is not None and isinstance(k8s_rg, K8sResourceGroup):
                    self.k8s_resource_groups[k8s_rg.name] = k8s_rg
                else:
                    print_error(
                        "+------+ K8sResourceGroup invalid: {}".format(k8s_rg.name)
                    )
        # second check if the create_k8s_resource_groups are provided
        elif self.args.create_k8s_resource_groups is not None:
            self.k8s_resource_groups = OrderedDict()
            for create_k8s_rg in self.args.create_k8s_resource_groups:
                if create_k8s_rg is not None and isinstance(
                    create_k8s_rg, CreateK8sResourceGroup
                ):
                    _k8s_rg = create_k8s_rg.create()
                    if _k8s_rg is not None:
                        self.k8s_resource_groups[create_k8s_rg.name] = _k8s_rg
                else:
                    print_error(
                        "+------+ K8sResourceGroup invalid: {}".format(
                            create_k8s_rg.name
                        )
                    )
