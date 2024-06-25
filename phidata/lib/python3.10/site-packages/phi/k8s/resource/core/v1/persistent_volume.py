from typing import List, Optional, Dict
from typing_extensions import Literal

from pydantic import Field, field_serializer

from kubernetes.client import CoreV1Api
from kubernetes.client.models.v1_persistent_volume import V1PersistentVolume
from kubernetes.client.models.v1_persistent_volume_list import V1PersistentVolumeList
from kubernetes.client.models.v1_persistent_volume_spec import V1PersistentVolumeSpec
from kubernetes.client.models.v1_status import V1Status

from phi.k8s.api_client import K8sApiClient
from phi.k8s.enums.pv import PVAccessMode
from phi.k8s.resource.base import K8sResource, K8sObject
from phi.k8s.resource.core.v1.volume_source import (
    GcePersistentDiskVolumeSource,
    LocalVolumeSource,
    HostPathVolumeSource,
    NFSVolumeSource,
    ClaimRef,
)
from phi.k8s.resource.core.v1.volume_node_affinity import VolumeNodeAffinity
from phi.utils.log import logger


class PersistentVolumeSpec(K8sObject):
    """
    Reference:
    - https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.23/#persistentvolumeclaim-v1-core
    """

    resource_type: str = "PersistentVolumeSpec"

    # AccessModes contains all ways the volume can be mounted.
    # More info: https://kubernetes.io/docs/concepts/storage/persistent-volumes#access-modes
    access_modes: List[PVAccessMode] = Field(..., alias="accessModes")
    # A description of the persistent volume's resources and capacity.
    # More info: https://kubernetes.io/docs/concepts/storage/persistent-volumes#capacity
    capacity: Optional[Dict[str, str]] = None
    # A list of mount options, e.g. ["ro", "soft"]. Not validated - mount will simply fail if one is invalid.
    # More info: https://kubernetes.io/docs/concepts/storage/persistent-volumes/#mount-options
    mount_options: Optional[List[str]] = Field(None, alias="mountOptions")
    # NodeAffinity defines constraints that limit what nodes this volume can be accessed from.
    # This field influences the scheduling of pods that use this volume.
    node_affinity: Optional[VolumeNodeAffinity] = Field(None, alias="nodeAffinity")
    # What happens to a persistent volume when released from its claim.
    # Valid options are Retain (default for manually created PersistentVolumes)
    #   Delete (default for dynamically provisioned PersistentVolumes)
    #   Recycle (deprecated). Recycle must be supported by the volume plugin underlying this PersistentVolume.
    # More info: https://kubernetes.io/docs/concepts/storage/persistent-volumes#reclaiming
    # Possible enum values:
    #   - `"Delete"` means the volume will be deleted from Kubernetes on release from its claim.
    #   - `"Recycle"` means the volume will be recycled back into the pool of unbound persistent volumes
    #           on release from its claim.
    #   - `"Retain"` means the volume will be left in its current phase (Released) for manual reclamation
    #           by the administrator.
    #   The default policy is Retain.
    persistent_volume_reclaim_policy: Optional[Literal["Delete", "Recycle", "Retain"]] = Field(
        None, alias="persistentVolumeReclaimPolicy"
    )
    # Name of StorageClass to which this persistent volume belongs.
    # Empty value means that this volume does not belong to any StorageClass.
    storage_class_name: Optional[str] = Field(None, alias="storageClassName")
    # volumeMode defines if a volume is intended to be used with a formatted filesystem or to remain in raw block state.
    # Value of Filesystem is implied when not included in spec.
    volume_mode: Optional[str] = Field(None, alias="volumeMode")

    ## Volume Sources
    # Local represents directly-attached storage with node affinity
    local: Optional[LocalVolumeSource] = None
    # HostPath represents a directory on the host. Provisioned by a developer or tester.
    # This is useful for single-node development and testing only!
    # On-host storage is not supported in any way and WILL NOT WORK in a multi-node cluster.
    # More info: https://kubernetes.io/docs/concepts/storage/volumes#hostpath
    host_path: Optional[HostPathVolumeSource] = Field(None, alias="hostPath")
    # GCEPersistentDisk represents a GCE Disk resource that is attached to a
    # kubelet's host machine and then exposed to the pod. Provisioned by an admin.
    # More info: https://kubernetes.io/docs/concepts/storage/volumes#gcepersistentdisk
    gce_persistent_disk: Optional[GcePersistentDiskVolumeSource] = Field(None, alias="gcePersistentDisk")
    # NFS represents an NFS mount on the host. Provisioned by an admin.
    # More info: https://kubernetes.io/docs/concepts/storage/volumes#nfs
    nfs: Optional[NFSVolumeSource] = None

    # ClaimRef is part of a bi-directional binding between PersistentVolume and PersistentVolumeClaim.
    # Expected to be non-nil when bound. claim.VolumeName is the authoritative bind between PV and PVC.
    # More info: https://kubernetes.io/docs/concepts/storage/persistent-volumes#binding
    claim_ref: Optional[ClaimRef] = Field(None, alias="claimRef")

    @field_serializer("access_modes")
    def get_access_modes_value(self, v) -> List[str]:
        return [access_mode.value for access_mode in v]

    def get_k8s_object(
        self,
    ) -> V1PersistentVolumeSpec:
        # Return a V1PersistentVolumeSpec object
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_persistent_volume_spec.py
        _v1_persistent_volume_spec = V1PersistentVolumeSpec(
            access_modes=[access_mode.value for access_mode in self.access_modes],
            capacity=self.capacity,
            mount_options=self.mount_options,
            persistent_volume_reclaim_policy=self.persistent_volume_reclaim_policy,
            storage_class_name=self.storage_class_name,
            volume_mode=self.volume_mode,
            local=self.local.get_k8s_object() if self.local else None,
            host_path=self.host_path.get_k8s_object() if self.host_path else None,
            nfs=self.nfs.get_k8s_object() if self.nfs else None,
            claim_ref=self.claim_ref.get_k8s_object() if self.claim_ref else None,
            gce_persistent_disk=self.gce_persistent_disk.get_k8s_object() if self.gce_persistent_disk else None,
            node_affinity=self.node_affinity.get_k8s_object() if self.node_affinity else None,
        )
        return _v1_persistent_volume_spec


class PersistentVolume(K8sResource):
    """
    A PersistentVolume (PV) is a piece of storage in the cluster that has been provisioned by an administrator
    or dynamically provisioned using Storage Classes.

    In Kubernetes, each container can read and write to its own, isolated filesystem.
    But, data on that filesystem will be destroyed when the container is restarted.
    To solve this, Kubernetes has volumes.
    Volumes let your pod write to a filesystem that exists as long as the pod exists.
    Volumes also let you share data between containers in the same pod.
    But, data in that volume will be destroyed when the pod is restarted.
    To solve this, Kubernetes has persistent volumes.
    Persistent volumes are long-term storage in your Kubernetes cluster.
    Persistent volumes exist beyond containers, pods, and nodes.

    A pod uses a persistent volume claim to to get read and write access to the persistent volume.

    References:
        * Docs:
            https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.23/#persistentvolume-v1-core
            https://kubernetes.io/docs/concepts/storage/persistent-volumes/
        * Type: https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_persistent_volume.py
    """

    resource_type: str = "PersistentVolume"

    spec: PersistentVolumeSpec

    # List of attributes to include in the K8s manifest
    fields_for_k8s_manifest: List[str] = ["spec"]

    def get_k8s_object(self) -> V1PersistentVolume:
        """Creates a body for this PVC"""

        # Return a V1PersistentVolume object to create a ClusterRole
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_persistent_volume.py
        _v1_persistent_volume = V1PersistentVolume(
            api_version=self.api_version.value,
            kind=self.kind.value,
            metadata=self.metadata.get_k8s_object(),
            spec=self.spec.get_k8s_object(),
        )
        return _v1_persistent_volume

    @staticmethod
    def get_from_cluster(
        k8s_client: K8sApiClient, namespace: Optional[str] = None, **kwargs
    ) -> Optional[List[V1PersistentVolume]]:
        """Reads PVCs from K8s cluster.

        Args:
            k8s_client: K8sApiClient for the cluster
            namespace: NOT USED.
        """
        core_v1_api: CoreV1Api = k8s_client.core_v1_api
        pv_list: Optional[V1PersistentVolumeList] = core_v1_api.list_persistent_volume(**kwargs)
        pvs: Optional[List[V1PersistentVolume]] = None
        if pv_list:
            pvs = pv_list.items
            logger.debug(f"pvs: {pvs}")
            logger.debug(f"pvs type: {type(pvs)}")
        return pvs

    def _create(self, k8s_client: K8sApiClient) -> bool:
        core_v1_api: CoreV1Api = k8s_client.core_v1_api
        k8s_object: V1PersistentVolume = self.get_k8s_object()

        logger.debug("Creating: {}".format(self.get_resource_name()))
        v1_persistent_volume: V1PersistentVolume = core_v1_api.create_persistent_volume(
            body=k8s_object,
            async_req=self.async_req,
            pretty=self.pretty,
        )
        # logger.debug("Created: {}".format(v1_persistent_volume))
        if v1_persistent_volume.metadata.creation_timestamp is not None:
            logger.debug("PV Created")
            self.active_resource = v1_persistent_volume  # logger.debug(f"Init
            return True
        logger.error("PV could not be created")
        return False

    def _read(self, k8s_client: K8sApiClient) -> Optional[V1PersistentVolume]:
        """Returns the "Active" PVC from the cluster"""

        active_resource: Optional[V1PersistentVolume] = None
        active_resources: Optional[List[V1PersistentVolume]] = self.get_from_cluster(
            k8s_client=k8s_client,
        )
        # logger.debug(f"Active Resources: {active_resources}")
        if active_resources is None:
            return None

        active_resources_dict = {_pv.metadata.name: _pv for _pv in active_resources}

        pv_name = self.get_resource_name()
        if pv_name in active_resources_dict:
            active_resource = active_resources_dict[pv_name]
            self.active_resource = active_resource  # logger.debug(f"Init
            logger.debug(f"Found active {pv_name}")
        return active_resource

    def _update(self, k8s_client: K8sApiClient) -> bool:
        core_v1_api: CoreV1Api = k8s_client.core_v1_api
        pv_name = self.get_resource_name()
        k8s_object: V1PersistentVolume = self.get_k8s_object()

        logger.debug("Updating: {}".format(pv_name))
        v1_persistent_volume: V1PersistentVolume = core_v1_api.patch_persistent_volume(
            name=pv_name,
            body=k8s_object,
            async_req=self.async_req,
            pretty=self.pretty,
        )
        # logger.debug("Updated:\n{}".format(pformat(v1_persistent_volume.to_dict(), indent=2)))
        if v1_persistent_volume.metadata.creation_timestamp is not None:
            logger.debug("PV Updated")
            self.active_resource = v1_persistent_volume  # logger.debug(f"Init
            return True
        logger.error("PV could not be updated")
        return False

    def _delete(self, k8s_client: K8sApiClient) -> bool:
        core_v1_api: CoreV1Api = k8s_client.core_v1_api
        pv_name = self.get_resource_name()

        logger.debug("Deleting: {}".format(pv_name))
        self.active_resource = None
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_status.py
        delete_status: V1Status = core_v1_api.delete_persistent_volume(
            name=pv_name,
            async_req=self.async_req,
            pretty=self.pretty,
        )
        # logger.debug("delete_status: {}".format(pformat(delete_status, indent=2)))
        if delete_status.status == "Success":
            logger.debug("PV Deleted")
            return True
        logger.error("PV could not be deleted")
        return False
