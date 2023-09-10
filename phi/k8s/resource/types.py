from collections import OrderedDict
from typing import Dict, List, Type, Union

from phi.k8s.resource.apiextensions_k8s_io.v1.custom_object import CustomObject
from phi.k8s.resource.apiextensions_k8s_io.v1.custom_resource_definition import CustomResourceDefinition
from phi.k8s.resource.apps.v1.deployment import Deployment
from phi.k8s.resource.core.v1.config_map import ConfigMap
from phi.k8s.resource.core.v1.container import Container
from phi.k8s.resource.core.v1.namespace import Namespace
from phi.k8s.resource.core.v1.persistent_volume import PersistentVolume
from phi.k8s.resource.core.v1.persistent_volume_claim import PersistentVolumeClaim
from phi.k8s.resource.core.v1.pod import Pod
from phi.k8s.resource.core.v1.secret import Secret
from phi.k8s.resource.core.v1.service import Service
from phi.k8s.resource.core.v1.service_account import ServiceAccount
from phi.k8s.resource.base import K8sResource, K8sObject
from phi.k8s.resource.rbac_authorization_k8s_io.v1.cluste_role_binding import ClusterRoleBinding
from phi.k8s.resource.rbac_authorization_k8s_io.v1.cluster_role import ClusterRole
from phi.k8s.resource.storage_k8s_io.v1.storage_class import StorageClass

# Use this as a type for an object which can hold any K8sResource
K8sResourceType = Union[
    Namespace,
    Secret,
    ConfigMap,
    StorageClass,
    PersistentVolume,
    PersistentVolumeClaim,
    ServiceAccount,
    ClusterRole,
    ClusterRoleBinding,
    # Role,
    # RoleBinding,
    Service,
    Pod,
    Deployment,
    # Ingress,
    CustomResourceDefinition,
    CustomObject,
    Container,
]

# Use this as an ordered list to iterate over all K8sResource Classes
# This list is the order in which resources should be installed as well.
# Copied from https://github.com/helm/helm/blob/release-2.10/pkg/tiller/kind_sorter.go#L29
K8sResourceTypeList: List[Type[Union[K8sResource, K8sObject]]] = [
    Namespace,
    ServiceAccount,
    StorageClass,
    Secret,
    ConfigMap,
    PersistentVolume,
    PersistentVolumeClaim,
    ClusterRole,
    ClusterRoleBinding,
    # Role,
    # RoleBinding,
    Pod,
    Deployment,
    Container,
    Service,
    # Ingress,
    CustomResourceDefinition,
    CustomObject,
]

# Map K8s resource alias' to their type
_k8s_resource_type_names: Dict[str, Type[Union[K8sResource, K8sObject]]] = {
    k8s_type.__name__.lower(): k8s_type for k8s_type in K8sResourceTypeList
}
_k8s_resource_type_aliases: Dict[str, Type[Union[K8sResource, K8sObject]]] = {
    "crd": CustomResourceDefinition,
    "ns": Namespace,
    "cm": ConfigMap,
    "sc": StorageClass,
    "pvc": PersistentVolumeClaim,
    "sa": ServiceAccount,
    "cr": ClusterRole,
    "crb": ClusterRoleBinding,
    "svc": Service,
    "deploy": Deployment,
}

K8sResourceAliasToTypeMap: Dict[str, Type[Union[K8sResource, K8sObject]]] = dict(
    **_k8s_resource_type_names, **_k8s_resource_type_aliases
)

# Maps each K8sResource to an install weight
# lower weight K8sResource(s) get installed first
# i.e. Namespace is installed first, then Secret... and so on
K8sResourceInstallOrder: Dict[str, int] = OrderedDict(
    {resource_type.__name__: idx for idx, resource_type in enumerate(K8sResourceTypeList, start=1)}
)
