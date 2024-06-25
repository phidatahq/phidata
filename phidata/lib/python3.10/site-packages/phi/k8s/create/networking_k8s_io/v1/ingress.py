from typing import Dict, List, Optional

from phi.k8s.create.base import CreateK8sResource
from phi.k8s.enums.api_version import ApiVersion
from phi.k8s.enums.kind import Kind
from phi.k8s.create.common.labels import create_component_labels_dict
from phi.k8s.resource.networking_k8s_io.v1.ingress import (
    Ingress,
    IngressSpec,
    V1IngressBackend,
    V1IngressTLS,
    V1IngressRule,
)
from phi.k8s.resource.meta.v1.object_meta import ObjectMeta


class CreateIngress(CreateK8sResource):
    ingress_name: str
    app_name: str
    namespace: Optional[str] = None
    service_account_name: Optional[str] = None
    rules: Optional[List[V1IngressRule]] = None
    ingress_class_name: Optional[str] = None
    default_backend: Optional[V1IngressBackend] = None
    tls: Optional[List[V1IngressTLS]] = None
    labels: Optional[Dict[str, str]] = None
    annotations: Optional[Dict[str, str]] = None

    def _create(self) -> Ingress:
        """Creates an Ingress resource"""
        ingress_name = self.ingress_name
        # logger.debug(f"Init Service resource: {ingress_name}")

        ingress_labels = create_component_labels_dict(
            component_name=ingress_name,
            app_name=self.app_name,
            labels=self.labels,
        )

        ingress = Ingress(
            name=ingress_name,
            api_version=ApiVersion.NETWORKING_V1,
            kind=Kind.INGRESS,
            metadata=ObjectMeta(
                name=ingress_name,
                namespace=self.namespace,
                labels=ingress_labels,
                annotations=self.annotations,
            ),
            spec=IngressSpec(
                default_backend=self.default_backend,
                ingress_class_name=self.ingress_class_name,
                rules=self.rules,
                tls=self.tls,
            ),
        )

        # logger.debug(
        #     f"Ingress {ingress_name}:\n{ingress.json(exclude_defaults=True, indent=2)}"
        # )
        return ingress
