from typing import Dict, List, Optional, Union
from typing_extensions import Literal

from phi.k8s.create.core.v1.container import CreateContainer
from phi.k8s.create.core.v1.volume import CreateVolume
from phi.k8s.create.base import CreateK8sResource
from phi.k8s.enums.api_version import ApiVersion
from phi.k8s.enums.kind import Kind
from phi.k8s.enums.restart_policy import RestartPolicy
from phi.k8s.resource.apps.v1.deployment import (
    Deployment,
    DeploymentSpec,
    LabelSelector,
    PodTemplateSpec,
)
from phi.k8s.resource.core.v1.container import Container
from phi.k8s.resource.core.v1.pod_spec import PodSpec
from phi.k8s.resource.core.v1.volume import Volume
from phi.k8s.resource.core.v1.topology_spread_constraints import (
    TopologySpreadConstraint,
)
from phi.k8s.create.common.labels import create_component_labels_dict
from phi.k8s.resource.meta.v1.object_meta import ObjectMeta


class CreateDeployment(CreateK8sResource):
    deploy_name: str
    pod_name: str
    app_name: str
    namespace: Optional[str] = None
    service_account_name: Optional[str] = None
    replicas: Optional[int] = 1
    containers: List[CreateContainer]
    init_containers: Optional[List[CreateContainer]] = None
    pod_node_selector: Optional[Dict[str, str]] = None
    restart_policy: RestartPolicy = RestartPolicy.ALWAYS
    termination_grace_period_seconds: Optional[int] = None
    volumes: Optional[List[CreateVolume]] = None
    labels: Optional[Dict[str, str]] = None
    pod_annotations: Optional[Dict[str, str]] = None
    topology_spread_key: Optional[str] = None
    topology_spread_max_skew: Optional[int] = None
    topology_spread_when_unsatisfiable: Optional[Union[str, Literal["DoNotSchedule", "ScheduleAnyway"]]] = None
    # If True, recreate the resource on update
    # Used for deployments with EBS volumes
    recreate_on_update: bool = False

    def _create(self) -> Deployment:
        """Creates the Deployment resource"""

        deploy_name = self.deploy_name
        # logger.debug(f"Init Deployment resource: {deploy_name}")

        deploy_labels = create_component_labels_dict(
            component_name=deploy_name,
            app_name=self.app_name,
            labels=self.labels,
        )

        pod_name = self.pod_name
        pod_labels = create_component_labels_dict(
            component_name=pod_name,
            app_name=self.app_name,
            labels=self.labels,
        )

        containers: List[Container] = []
        for cc in self.containers:
            container = cc.create()
            if container is not None and isinstance(container, Container):
                containers.append(container)

        init_containers: Optional[List[Container]] = None
        if self.init_containers is not None:
            init_containers = []
            for ic in self.init_containers:
                _init_container = ic.create()
                if _init_container is not None and isinstance(_init_container, Container):
                    init_containers.append(_init_container)

        topology_spread_constraints: Optional[List[TopologySpreadConstraint]] = None
        if self.topology_spread_key is not None:
            topology_spread_constraints = [
                TopologySpreadConstraint(
                    topology_key=self.topology_spread_key,
                    max_skew=self.topology_spread_max_skew,
                    when_unsatisfiable=self.topology_spread_when_unsatisfiable,
                    label_selector=LabelSelector(match_labels=pod_labels),
                )
            ]

        volumes: Optional[List[Volume]] = None
        if self.volumes:
            volumes = []
            for cv in self.volumes:
                volume = cv.create()
                if volume and isinstance(volume, Volume):
                    volumes.append(volume)

        deployment = Deployment(
            name=deploy_name,
            api_version=ApiVersion.APPS_V1,
            kind=Kind.DEPLOYMENT,
            metadata=ObjectMeta(
                name=deploy_name,
                namespace=self.namespace,
                labels=deploy_labels,
            ),
            spec=DeploymentSpec(
                replicas=self.replicas,
                selector=LabelSelector(match_labels=pod_labels),
                template=PodTemplateSpec(
                    # TODO: fix this
                    metadata=ObjectMeta(
                        name=pod_name,
                        namespace=self.namespace,
                        labels=pod_labels,
                        annotations=self.pod_annotations,
                    ),
                    spec=PodSpec(
                        init_containers=init_containers,
                        node_selector=self.pod_node_selector,
                        service_account_name=self.service_account_name,
                        restart_policy=self.restart_policy,
                        containers=containers,
                        termination_grace_period_seconds=self.termination_grace_period_seconds,
                        topology_spread_constraints=topology_spread_constraints,
                        volumes=volumes,
                    ),
                ),
            ),
            recreate_on_update=self.recreate_on_update,
        )

        # logger.debug(
        #     f"Deployment {deploy_name}:\n{deployment.json(exclude_defaults=True, indent=2)}"
        # )
        return deployment
