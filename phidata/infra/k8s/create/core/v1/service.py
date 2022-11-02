from typing import Dict, List, Optional

from pydantic import BaseModel

from phidata.infra.k8s.create.apps.v1.deployment import CreateDeployment
from phidata.infra.k8s.create.common.port import CreatePort
from phidata.infra.k8s.enums.api_version import ApiVersion
from phidata.infra.k8s.enums.kind import Kind
from phidata.infra.k8s.enums.service_type import ServiceType
from phidata.infra.k8s.resource.core.v1.service import Service, ServicePort, ServiceSpec
from phidata.infra.k8s.create.common.labels import create_component_labels_dict
from phidata.infra.k8s.resource.meta.v1.object_meta import ObjectMeta
from phidata.utils.log import logger


class CreateService(BaseModel):
    service_name: str
    app_name: str
    namespace: Optional[str] = None
    service_account_name: Optional[str] = None
    service_type: Optional[ServiceType] = None
    # Deployment to expose using this service
    deployment: CreateDeployment
    # Ports to expose using this service
    ports: Optional[List[CreatePort]] = None
    ## type == ClusterIP
    cluster_ip: Optional[str] = None
    cluster_ips: Optional[List[str]] = None
    ## type == ExternalName
    external_ips: Optional[List[str]] = None
    external_name: Optional[str] = None
    external_traffic_policy: Optional[str] = None
    ## type == LoadBalancer
    health_check_node_port: Optional[int] = None
    internal_taffic_policy: Optional[str] = None
    load_balancer_class: Optional[str] = None
    load_balancer_ip: Optional[str] = None
    load_balancer_source_ranges: Optional[List[str]] = None
    allocate_load_balancer_node_ports: Optional[bool] = None
    labels: Optional[Dict[str, str]] = None
    annotations: Optional[Dict[str, str]] = None

    def create(self) -> Optional[Service]:
        """Creates a Service resource"""
        service_name = self.service_name
        logger.debug(f"Init Service resource: {service_name}")

        service_labels = create_component_labels_dict(
            component_name=service_name,
            app_name=self.app_name,
            labels=self.labels,
        )

        target_pod_name = self.deployment.pod_name
        target_pod_labels = create_component_labels_dict(
            component_name=target_pod_name,
            app_name=self.app_name,
            labels=self.labels,
        )

        service_ports: List[ServicePort] = []
        if self.ports:
            for _port in self.ports:
                # logger.debug(f"Creating ServicePort for {_port}")
                if _port.service_port is not None:
                    service_ports.append(
                        ServicePort(
                            name=_port.name,
                            port=_port.service_port,
                            node_port=_port.node_port,
                            protocol=_port.protocol,
                            target_port=_port.target_port,
                        )
                    )

        service = Service(
            api_version=ApiVersion.CORE_V1,
            kind=Kind.SERVICE,
            metadata=ObjectMeta(
                name=service_name,
                namespace=self.namespace,
                labels=service_labels,
                annotations=self.annotations,
            ),
            spec=ServiceSpec(
                type=self.service_type,
                cluster_ip=self.cluster_ip,
                cluster_ips=self.cluster_ips,
                external_ips=self.external_ips,
                external_name=self.external_name,
                external_traffic_policy=self.external_traffic_policy,
                health_check_node_port=self.health_check_node_port,
                internal_taffic_policy=self.internal_taffic_policy,
                load_balancer_class=self.load_balancer_class,
                load_balancer_ip=self.load_balancer_ip,
                load_balancer_source_ranges=self.load_balancer_source_ranges,
                allocate_load_balancer_node_ports=self.allocate_load_balancer_node_ports,
                ports=service_ports,
                selector=target_pod_labels,
            ),
        )

        # logger.debug(
        #     f"Service {service_name}:\n{service.json(exclude_defaults=True, indent=2)}"
        # )
        return service
