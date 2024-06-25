from typing import Dict, List, Optional

from phi.k8s.create.base import CreateK8sResource
from phi.k8s.enums.api_version import ApiVersion
from phi.k8s.enums.kind import Kind
from phi.k8s.resource.rbac_authorization_k8s_io.v1.cluster_role import (
    ClusterRole,
    PolicyRule,
)
from phi.k8s.create.common.labels import create_component_labels_dict
from phi.k8s.resource.meta.v1.object_meta import ObjectMeta


class CreateClusterRole(CreateK8sResource):
    cr_name: str
    app_name: str
    rules: Optional[List[PolicyRule]] = None
    namespace: Optional[str] = None
    labels: Optional[Dict[str, str]] = None

    def _create(self) -> ClusterRole:
        """Creates the ClusterRole resource"""

        cr_name = self.cr_name
        # logger.debug(f"Init ClusterRole resource: {cr_name}")

        cr_labels = create_component_labels_dict(
            component_name=cr_name,
            app_name=self.app_name,
            labels=self.labels,
        )

        cr_rules: List[PolicyRule] = (
            self.rules if self.rules else [PolicyRule(api_groups=["*"], resources=["*"], verbs=["*"])]
        )

        cr = ClusterRole(
            name=cr_name,
            api_version=ApiVersion.RBAC_AUTH_V1,
            kind=Kind.CLUSTERROLE,
            metadata=ObjectMeta(
                name=cr_name,
                namespace=self.namespace,
                labels=cr_labels,
            ),
            rules=cr_rules,
        )
        return cr
