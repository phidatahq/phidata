from typing import List, Optional, Dict, Any

from pydantic import BaseModel, ValidationError

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
from phidata.infra.k8s.resource.core.v1.persistent_volume import PersistentVolume
from phidata.infra.k8s.resource.core.v1.persistent_volume_claim import (
    PersistentVolumeClaim,
)
from phidata.infra.k8s.resource.rbac_authorization_k8s_io.v1.cluste_role_binding import (
    ClusterRoleBinding,
)
from phidata.infra.k8s.resource.rbac_authorization_k8s_io.v1.cluster_role import (
    ClusterRole,
)
from phidata.infra.k8s.resource.storage_k8s_io.v1.storage_class import StorageClass
from phidata.utils.log import logger


class K8sResourceGroup(BaseModel):
    """
    The K8sResourceGroup is a collection of K8s Resources acting as a single unit.

    1 PhidataApp normally produces 1 K8sResourceGroup
    but for complex Apps, 1 PhidataApp may produce > 1 K8sResourceGroup
    """

    # Name of this group aka name of the app
    name: str
    enabled: bool = True

    # The weight variable controls how this is group is deployed to a cluster
    # relative to other resource groups.

    # Within each resource group, different types of resources are
    # deployed in a predefined order (eg: ns first, then sa and so on ...)
    # but we can also add an order to how to deploy different resource groups.
    # Eg: if we want to deploy a resource group with databases before other resources

    # Weights 1-10 are reserved
    # Weight 100 is default.
    # ResourceGroups with weight 100 are the default resources.
    # Choose weight 11-99 to deploy a resource group before all the default resources.
    # Choose weight 101+ to deploy a resource group after all the default resources
    weight: int = 100

    ns: Optional[List[Namespace]] = None
    sa: Optional[List[ServiceAccount]] = None
    cr: Optional[List[ClusterRole]] = None
    crb: Optional[List[ClusterRoleBinding]] = None
    secrets: Optional[List[Secret]] = None
    config_maps: Optional[List[ConfigMap]] = None
    storage_classes: Optional[List[StorageClass]] = None
    services: Optional[List[Service]] = None
    deployments: Optional[List[Deployment]] = None
    custom_objects: Optional[List[CustomObject]] = None
    crds: Optional[List[CustomResourceDefinition]] = None
    pvs: Optional[List[PersistentVolume]] = None
    pvcs: Optional[List[PersistentVolumeClaim]] = None

    def add_manifest_to_group(self, manifest: Dict[str, Any]) -> bool:
        """
        Reads a k8s manifest dict and adds to the K8sResourceGroup
        """
        kind = manifest.get("kind", None)
        if kind is None:
            logger.error(f"Cannot parse manifest: {manifest}")
            return False

        logger.debug(f"Adding {kind} to {self.name}")

        try:
            ######################################################
            ## Parse Namespace
            ######################################################
            if kind == "Namespace":
                from phidata.infra.k8s.resource.core.v1.namespace import Namespace

                _ns_resource = Namespace(**manifest)
                if _ns_resource is not None:
                    if self.ns is None:
                        self.ns = []
                    self.ns.append(_ns_resource)
                logger.debug(
                    f"Parsed: {_ns_resource.get_resource_type()}: {_ns_resource.get_resource_name()}"
                )
            ######################################################
            ## Parse ServiceAccount
            ######################################################
            elif kind == "ServiceAccount":
                from phidata.infra.k8s.resource.core.v1.service_account import (
                    ServiceAccount,
                )

                _sa_resource = ServiceAccount(**manifest)
                if _sa_resource is not None:
                    if self.sa is None:
                        self.sa = []
                    self.sa.append(_sa_resource)
                logger.debug(
                    f"Parsed: {_sa_resource.get_resource_type()}: {_sa_resource.get_resource_name()}"
                )
            ######################################################
            ## Parse ClusterRole
            ######################################################
            elif kind == "ClusterRole":
                from phidata.infra.k8s.resource.rbac_authorization_k8s_io.v1.cluster_role import (
                    ClusterRole,
                )

                _cr_resource = ClusterRole(**manifest)
                if _cr_resource is not None:
                    if self.cr is None:
                        self.cr = []
                    self.cr.append(_cr_resource)
                logger.debug(
                    f"Parsed: {_cr_resource.get_resource_type()}: {_cr_resource.get_resource_name()}"
                )
            ######################################################
            ## Parse ClusterRoleBinding
            ######################################################
            elif kind == "ClusterRoleBinding":
                from phidata.infra.k8s.resource.rbac_authorization_k8s_io.v1.cluste_role_binding import (
                    ClusterRoleBinding,
                )

                _crb_resource = ClusterRoleBinding(**manifest)
                if _crb_resource is not None:
                    if self.crb is None:
                        self.crb = []
                    self.crb.append(_crb_resource)
                logger.debug(
                    f"Parsed: {_crb_resource.get_resource_type()}: {_crb_resource.get_resource_name()}"
                )
            ######################################################
            ## Parse Secrets
            ######################################################
            elif kind == "Secret":
                from phidata.infra.k8s.resource.core.v1.secret import Secret

                _secret_resource = Secret(**manifest)
                if _secret_resource is not None:
                    if self.secrets is None:
                        self.secrets = []
                    self.secrets.append(_secret_resource)
                logger.debug(
                    f"Parsed: {_secret_resource.get_resource_type()}: {_secret_resource.get_resource_name()}"
                )
            ######################################################
            ## Parse ConfigMaps
            ######################################################
            elif kind == "ConfigMap":
                from phidata.infra.k8s.resource.core.v1.config_map import ConfigMap

                _cm_resource = ConfigMap(**manifest)
                if _cm_resource is not None:
                    if self.config_maps is None:
                        self.config_maps = []
                    self.config_maps.append(_cm_resource)
                logger.debug(
                    f"Parsed: {_cm_resource.get_resource_type()}: {_cm_resource.get_resource_name()}"
                )
            ######################################################
            ## Parse StorageClasses
            ######################################################
            elif kind == "StorageClass":
                from phidata.infra.k8s.resource.storage_k8s_io.v1.storage_class import (
                    StorageClass,
                )

                _sc_resource = StorageClass(**manifest)
                if _sc_resource is not None:
                    if self.storage_classes is None:
                        self.storage_classes = []
                    self.storage_classes.append(_sc_resource)
                logger.debug(
                    f"Parsed: {_sc_resource.get_resource_type()}: {_sc_resource.get_resource_name()}"
                )
            ######################################################
            ## Parse Services
            ######################################################
            elif kind == "Service":
                from phidata.infra.k8s.resource.core.v1.service import Service

                _svc_resource = Service(**manifest)
                if _svc_resource is not None:
                    if self.services is None:
                        self.services = []
                    self.services.append(_svc_resource)
                logger.debug(
                    f"Parsed: {_svc_resource.get_resource_type()}: {_svc_resource.get_resource_name()}"
                )
            ######################################################
            ## Parse Deployments
            ######################################################
            elif kind == "Deployment":
                from phidata.infra.k8s.resource.apps.v1.deployment import Deployment

                _deploy_resource = Deployment(**manifest)
                if _deploy_resource is not None:
                    if self.deployments is None:
                        self.deployments = []
                    self.deployments.append(_deploy_resource)
                logger.debug(
                    f"Parsed: {_deploy_resource.get_resource_type()}: {_deploy_resource.get_resource_name()}"
                )
            ######################################################
            ## Parse CustomResourceDefinitions
            ######################################################
            if kind == "CustomResourceDefinition":
                from phidata.infra.k8s.resource.apiextensions_k8s_io.v1.custom_resource_definition import (
                    CustomResourceDefinition,
                )

                _crd_resource = CustomResourceDefinition(**manifest)
                if _crd_resource is not None:
                    if self.crds is None:
                        self.crds = []
                    self.crds.append(_crd_resource)
                logger.debug(
                    f"Parsed: {_crd_resource.get_resource_type()}: {_crd_resource.get_resource_name()}"
                )
            ######################################################
            ## Parse PersistentVolumes
            ######################################################
            elif kind == "PersistentVolume":
                from phidata.infra.k8s.resource.core.v1.persistent_volume import (
                    PersistentVolume,
                )

                _pv_resource = PersistentVolume(**manifest)
                if _pv_resource is not None:
                    if self.pvs is None:
                        self.pvs = []
                    self.pvs.append(_pv_resource)
                logger.debug(
                    f"Parsed: {_pv_resource.get_resource_type()}: {_pv_resource.get_resource_name()}"
                )
            ######################################################
            ## Parse PersistentVolumeClaim
            ######################################################
            elif kind == "PersistentVolumeClaim":
                from phidata.infra.k8s.resource.core.v1.persistent_volume_claim import (
                    PersistentVolumeClaim,
                )

                _pvcs_resource = PersistentVolumeClaim(**manifest)
                if _pvcs_resource is not None:
                    if self.pvcs is None:
                        self.pvcs = []
                    self.pvcs.append(_pvcs_resource)
                logger.debug(
                    f"Parsed: {_pvcs_resource.get_resource_type()}: {_pvcs_resource.get_resource_name()}"
                )
            ######################################################
            ## TODO: Parse CustomObjects
            ######################################################
            return True
        except ValidationError as validation_error:
            logger.warning(f"Could not parse manifest: {manifest}")
            logger.exception(validation_error)
            return False


class K8sBuildContext(BaseModel):
    namespace: str = "default"
    context: Optional[str] = None
    service_account_name: Optional[str] = None
    labels: Optional[Dict[str, str]] = None
