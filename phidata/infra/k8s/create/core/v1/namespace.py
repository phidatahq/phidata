from typing import Dict, Optional, List

from pydantic import BaseModel

from phidata.infra.k8s.enums.api_version import ApiVersion
from phidata.infra.k8s.enums.kind import Kind
from phidata.infra.k8s.resource.core.v1.namespace import Namespace, NamespaceSpec
from phidata.infra.k8s.create.common.labels import create_component_labels_dict
from phidata.infra.k8s.resource.meta.v1.object_meta import ObjectMeta
from phidata.utils.common import get_default_ns_name
from phidata.utils.log import logger


class CreateNamespace(BaseModel):
    ns: str
    app_name: str
    # Finalizers is an opaque list of values that must be empty to permanently remove object from storage.
    # More info: https://kubernetes.io/docs/tasks/administer-cluster/namespaces/
    finalizers: Optional[List[str]] = None
    labels: Optional[Dict[str, str]] = None

    def create(self) -> Optional[Namespace]:

        ns_name = self.ns if self.ns else get_default_ns_name(self.app_name)
        logger.debug(f"Init Namespace resource: {ns_name}")

        ns_labels = create_component_labels_dict(
            component_name=ns_name,
            app_name=self.app_name,
            labels=self.labels,
        )
        ns_spec = NamespaceSpec(finalizers=self.finalizers) if self.finalizers else None
        ns = Namespace(
            api_version=ApiVersion.CORE_V1,
            kind=Kind.NAMESPACE,
            metadata=ObjectMeta(
                name=ns_name,
                labels=ns_labels,
            ),
            spec=ns_spec,
        )
        return ns
