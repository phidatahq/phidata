from typing import List, Optional

from kubernetes.client import CoreV1Api
from kubernetes.client.models.v1_persistent_volume_claim import V1PersistentVolumeClaim
from kubernetes.client.models.v1_persistent_volume_claim_list import (
    V1PersistentVolumeClaimList,
)
from kubernetes.client.models.v1_persistent_volume_claim_spec import (
    V1PersistentVolumeClaimSpec,
)
from kubernetes.client.models.v1_status import V1Status
from pydantic import Field

from phidata.infra.k8s.api_client import K8sApiClient
from phidata.infra.k8s.enums.pv import PVAccessMode
from phidata.infra.k8s.resource.base import K8sResource, K8sObject
from phidata.infra.k8s.resource.core.v1.resource_requirements import (
    ResourceRequirements,
)
from phidata.utils.log import logger


class PersistentVolumeClaimSpec(K8sObject):
    """
    # https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.23/#persistentvolumeclaim-v1-core
    """

    resource_type: str = "PersistentVolumeClaimSpec"

    access_modes: List[PVAccessMode] = Field(..., alias="accessModes")
    resources: ResourceRequirements
    storage_class_name: str = Field(..., alias="storageClassName")

    def get_k8s_object(
        self,
    ) -> V1PersistentVolumeClaimSpec:

        # Return a V1PersistentVolumeClaimSpec object
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_persistent_volume_claim_spec.py
        _v1_persistent_volume_claim_spec = V1PersistentVolumeClaimSpec(
            access_modes=self.access_modes,
            resources=self.resources.get_k8s_object(),
            storage_class_name=self.storage_class_name,
        )
        return _v1_persistent_volume_claim_spec


class PersistentVolumeClaim(K8sResource):
    """
    A PersistentVolumeClaim (PVC) is a request for storage by a user.
    It is similar to a Pod. Pods consume node resources and PVCs consume PV resources.
    A PersistentVolume (PV) is a piece of storage in the cluster that has been provisioned
    by an administrator or dynamically provisioned using Storage Classes.
    With Pak8, we prefer to use Storage Classes, read more about Dynamic provisioning here: https://kubernetes.io/docs/concepts/storage/persistent-volumes/#dynamic

    References:
        * Docs:
            https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.23/#persistentvolumeclaim-v1-core
            https://kubernetes.io/docs/concepts/storage/persistent-volumes/
        * Type: https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_persistent_volume_claim.py
    """

    resource_type: str = "PersistentVolumeClaim"

    spec: PersistentVolumeClaimSpec

    # List of attributes to include in the K8s manifest
    fields_for_k8s_manifest: List[str] = ["spec"]

    def get_k8s_object(self) -> V1PersistentVolumeClaim:
        """Creates a body for this PVC"""

        # Return a V1PersistentVolumeClaim object to create a ClusterRole
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_persistent_volume_claim.py
        _v1_persistent_volume_claim = V1PersistentVolumeClaim(
            api_version=self.api_version,
            kind=self.kind,
            metadata=self.metadata.get_k8s_object(),
            spec=self.spec.get_k8s_object(),
        )
        return _v1_persistent_volume_claim

    @staticmethod
    def get_from_cluster(
        k8s_client: K8sApiClient, namespace: Optional[str] = None, **kwargs
    ) -> Optional[List[V1PersistentVolumeClaim]]:
        """Reads PVCs from K8s cluster.

        Args:
            k8s_client: K8sApiClient for the cluster
            namespace: Namespace to use.
        """
        core_v1_api: CoreV1Api = k8s_client.core_v1_api
        pvc_list: Optional[V1PersistentVolumeClaimList] = None
        if namespace:
            logger.debug(f"Getting PVCs for ns: {namespace}")
            pvc_list = core_v1_api.list_namespaced_persistent_volume_claim(
                namespace=namespace, **kwargs
            )
        else:
            logger.debug("Getting PVCs for all namespaces")
            pvc_list = core_v1_api.list_persistent_volume_claim_for_all_namespaces(
                **kwargs
            )

        pvcs: Optional[List[V1PersistentVolumeClaim]] = None
        if pvc_list:
            pvcs = pvc_list.items
        logger.debug(f"pvcs: {pvcs}")
        logger.debug(f"pvcs type: {type(pvcs)}")
        return pvcs

    def _create(self, k8s_client: K8sApiClient) -> bool:

        core_v1_api: CoreV1Api = k8s_client.core_v1_api
        k8s_object: V1PersistentVolumeClaim = self.get_k8s_object()
        namespace = self.get_namespace()

        logger.debug("Creating: {}".format(self.get_resource_name()))
        v1_persistent_volume_claim: V1PersistentVolumeClaim = (
            core_v1_api.create_namespaced_persistent_volume_claim(
                namespace=namespace, body=k8s_object
            )
        )
        # logger.debug("Created: {}".format(v1_persistent_volume_claim))
        if v1_persistent_volume_claim.metadata.creation_timestamp is not None:
            logger.debug("PVC Created")
            self.active_resource = v1_persistent_volume_claim
            self.active_resource_class = V1PersistentVolumeClaim
            return True
        logger.error("PVC could not be created")
        return False

    def _read(self, k8s_client: K8sApiClient) -> Optional[V1PersistentVolumeClaim]:
        """Returns the "Active" PVC from the cluster"""

        namespace = self.get_namespace()
        active_pvc: Optional[V1PersistentVolumeClaim] = None
        active_pvcs: Optional[List[V1PersistentVolumeClaim]] = self.get_from_cluster(
            k8s_client=k8s_client,
            namespace=namespace,
        )
        # logger.debug(f"active_pvcs: {active_pvcs}")
        if active_pvcs is None:
            return None

        _active_pvcs_dict = {_pvc.metadata.name: _pvc for _pvc in active_pvcs}

        pvc_name = self.get_resource_name()
        if pvc_name in _active_pvcs_dict:
            active_pvc = _active_pvcs_dict[pvc_name]
            self.active_resource = active_pvc
            self.active_resource_class = V1PersistentVolumeClaim
            # logger.debug(f"Found {pvc_name}")
        return active_pvc

    def _update(self, k8s_client: K8sApiClient) -> bool:

        core_v1_api: CoreV1Api = k8s_client.core_v1_api
        pvc_name = self.get_resource_name()
        k8s_object: V1PersistentVolumeClaim = self.get_k8s_object()
        namespace = self.get_namespace()

        logger.debug("Updating: {}".format(pvc_name))
        v1_persistent_volume_claim: V1PersistentVolumeClaim = (
            core_v1_api.patch_namespaced_persistent_volume_claim(
                name=pvc_name, namespace=namespace, body=k8s_object
            )
        )
        # logger.debug("Updated:\n{}".format(pformat(v1_persistent_volume_claim.to_dict(), indent=2)))
        if v1_persistent_volume_claim.metadata.creation_timestamp is not None:
            logger.debug("PVC Updated")
            self.active_resource = v1_persistent_volume_claim
            self.active_resource_class = V1PersistentVolumeClaim
            return True
        logger.error("PVC could not be updated")
        return False

    def _delete(self, k8s_client: K8sApiClient) -> bool:

        core_v1_api: CoreV1Api = k8s_client.core_v1_api
        pvc_name = self.get_resource_name()
        namespace = self.get_namespace()

        logger.debug("Deleting: {}".format(pvc_name))
        self.active_resource = None
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_status.py
        _delete_status: V1Status = (
            core_v1_api.delete_namespaced_persistent_volume_claim(
                name=pvc_name, namespace=namespace
            )
        )
        # logger.debug("_delete_status: {}".format(pformat(_delete_status, indent=2)))
        if _delete_status.status == "Success":
            logger.debug("PVC Deleted")
            return True
        logger.error("PVC could not be deleted")
        return False
