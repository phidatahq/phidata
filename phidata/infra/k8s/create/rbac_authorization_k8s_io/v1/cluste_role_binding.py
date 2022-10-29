from typing import Dict, List, Optional

from pydantic import BaseModel

from phidata.infra.k8s.enums.api_group import ApiGroup
from phidata.infra.k8s.enums.api_version import ApiVersion
from phidata.infra.k8s.enums.kind import Kind
from phidata.infra.k8s.resource.rbac_authorization_k8s_io.v1.cluste_role_binding import (
    Subject,
    RoleRef,
    ClusterRoleBinding,
)
from phidata.infra.k8s.create.common.labels import create_component_labels_dict
from phidata.infra.k8s.resource.meta.v1.object_meta import ObjectMeta
from phidata.utils.log import logger


class CreateClusterRoleBinding(BaseModel):
    crb_name: str
    cr_name: str
    service_account_name: str
    app_name: str
    namespace: str
    labels: Optional[Dict[str, str]] = None

    def create(self) -> ClusterRoleBinding:
        """Creates the ClusterRoleBinding resource"""

        crb_name = self.crb_name
        logger.debug(f"Init ClusterRoleBinding resource: {crb_name}")

        sa_name = self.service_account_name
        subjects: List[Subject] = [
            Subject(kind=Kind.SERVICEACCOUNT, name=sa_name, namespace=self.namespace)
        ]
        cr_name = self.cr_name

        crb_labels = create_component_labels_dict(
            component_name=crb_name,
            app_name=self.app_name,
            labels=self.labels,
        )
        crb = ClusterRoleBinding(
            api_version=ApiVersion.RBAC_AUTH_V1,
            kind=Kind.CLUSTERROLEBINDING,
            metadata=ObjectMeta(
                name=crb_name,
                labels=crb_labels,
            ),
            role_ref=RoleRef(
                api_group=ApiGroup.RBAC_AUTH,
                kind=Kind.CLUSTERROLE,
                name=cr_name,
            ),
            subjects=subjects,
        )
        return crb
