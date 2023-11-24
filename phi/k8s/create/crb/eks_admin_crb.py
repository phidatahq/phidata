from typing import Dict, List, Optional

from phi.k8s.enums.api_group import ApiGroup
from phi.k8s.enums.api_version import ApiVersion
from phi.k8s.enums.kind import Kind
from phi.k8s.resource.rbac_authorization_k8s_io.v1.cluste_role_binding import (
    Subject,
    RoleRef,
    ClusterRoleBinding,
)
from phi.k8s.create.common.labels import create_component_labels_dict
from phi.k8s.resource.meta.v1.object_meta import ObjectMeta
from phi.utils.log import logger


def create_eks_admin_crb(
    name: str = "eks-admin-crb",
    cluster_role: str = "cluster-admin",
    users: Optional[List[str]] = None,
    groups: Optional[List[str]] = None,
    service_accounts: Optional[List[str]] = None,
    app_name: str = "eks-admin",
    labels: Optional[Dict[str, str]] = None,
    skip_create: bool = False,
    skip_delete: bool = False,
) -> Optional[ClusterRoleBinding]:
    crb_labels = create_component_labels_dict(
        component_name=name,
        app_name=app_name,
        labels=labels,
    )

    subjects: List[Subject] = []
    if service_accounts is not None and isinstance(service_accounts, list):
        for sa in service_accounts:
            subjects.append(Subject(kind=Kind.SERVICEACCOUNT, name=sa))
    if users is not None and isinstance(users, list):
        for user in users:
            subjects.append(Subject(kind=Kind.USER, name=user))
    if groups is not None and isinstance(groups, list):
        for group in groups:
            subjects.append(Subject(kind=Kind.GROUP, name=group))

    if len(subjects) == 0:
        logger.error(f"No subjects for ClusterRoleBinding: {name}")
        return None

    return ClusterRoleBinding(
        name=name,
        api_version=ApiVersion.RBAC_AUTH_V1,
        kind=Kind.CLUSTERROLEBINDING,
        metadata=ObjectMeta(
            name=name,
            labels=crb_labels,
        ),
        role_ref=RoleRef(
            api_group=ApiGroup.RBAC_AUTH,
            kind=Kind.CLUSTERROLE,
            name=cluster_role,
        ),
        subjects=subjects,
        skip_create=skip_create,
        skip_delete=skip_delete,
    )
