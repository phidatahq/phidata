from typing import List, Optional, Dict

from pydantic import BaseModel

from phidata.infra.k8s.resource.apiextensions_k8s_io.v1.custom_object import (
    CustomObject,
)
from phidata.infra.k8s.resource.apiextensions_k8s_io.v1.custom_resource_definition import (
    CustomResourceDefinition,
)
from phidata.infra.k8s.resource.apps.v1.deployment import Deployment
from phidata.infra.k8s.resource.core.v1.config_map import ConfigMap
from phidata.infra.k8s.resource.core.v1.namespace import Namespace
from phidata.infra.k8s.resource.core.v1.secret import Secret
from phidata.infra.k8s.resource.core.v1.service import Service
from phidata.infra.k8s.resource.core.v1.service_account import ServiceAccount
from phidata.infra.k8s.resource.rbac_authorization_k8s_io.v1.cluste_role_binding import (
    ClusterRoleBinding,
)
from phidata.infra.k8s.resource.rbac_authorization_k8s_io.v1.cluster_role import (
    ClusterRole,
)
from phidata.infra.k8s.resource.storage_k8s_io.v1.storage_class import StorageClass


class K8sResourceGroup(BaseModel):
    """The K8sResourceGroup class contains the instructions to manage K8s resources"""

    name: str
    enabled: bool = True

    # The weight variable controls how this is resource group is deployed to a cluster
    # relative to other resource groups.

    # Within each resource group, different types of resources are
    # deployed in a predefined order (eg: ns first, then sa and so on..)
    # but we can also add an order to how to deploy different resource groups.
    # (Eg if we want to deploy a resource group with just storage_class (s) before all other resources)

    # Weights 1-10 are reserved
    # Weight 100 is default.
    # ResourceGroups with weight 100 are the default resources.
    # Choose weight 11-99 to deploy a resource group before all the default resources.
    # Choose weight 101+ to deploy a resource group after all the default resources
    weight: int = 100
    ns: Optional[Namespace] = None
    sa: Optional[ServiceAccount] = None
    cr: Optional[ClusterRole] = None
    crb: Optional[ClusterRoleBinding] = None
    secrets: Optional[List[Secret]] = None
    config_maps: Optional[List[ConfigMap]] = None
    storage_classes: Optional[List[StorageClass]] = None
    services: Optional[List[Service]] = None
    deployments: Optional[List[Deployment]] = None
    custom_objects: Optional[List[CustomObject]] = None
    crds: Optional[List[CustomResourceDefinition]] = None


class K8sBuildContext(BaseModel):
    namespace: str = "default"
    context: Optional[str] = None
    service_account_name: Optional[str] = None
    labels: Optional[Dict[str, str]] = None
