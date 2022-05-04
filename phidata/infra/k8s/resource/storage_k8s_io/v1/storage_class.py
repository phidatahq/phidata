from typing import Dict, List, Optional

from kubernetes.client import StorageV1Api
from kubernetes.client.models.v1_status import V1Status
from kubernetes.client.models.v1_storage_class import V1StorageClass
from kubernetes.client.models.v1_storage_class_list import V1StorageClassList
from pydantic import Field

from phidata.infra.k8s.api_client import K8sApiClient
from phidata.infra.k8s.resource.base import K8sResource
from phidata.utils.cli_console import print_info
from phidata.utils.log import logger


class StorageClass(K8sResource):
    """
    References:
        * Doc: https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.23/#storageclass-v1-storage-k8s-io
        * Type: https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_storage_class.py
    """

    resource_type: str = "StorageClass"

    # AllowVolumeExpansion shows whether the storage class allow volume expand
    allow_volume_expansion: Optional[str] = Field(None, alias="allowVolumeExpansion")
    # Dynamically provisioned PersistentVolumes of this storage class are created with these mountOptions,
    # e.g. ["ro", "soft"]. Not validated - mount of the PVs will simply fail if one is invalid.
    mount_options: Optional[List[str]] = Field(None, alias="mountOptions")
    # Parameters holds the parameters for the provisioner that should create volumes of this storage class.
    parameters: Dict[str, str]
    # Provisioner indicates the type of the provisioner.
    provisioner: str
    # Dynamically provisioned PersistentVolumes of this storage class are created with this reclaimPolicy.
    # Defaults to Delete.
    reclaim_policy: Optional[str] = Field(None, alias="reclaimPolicy")
    # VolumeBindingMode indicates how PersistentVolumeClaims should be provisioned and bound.
    # When unset, VolumeBindingImmediate is used.
    # This field is only honored by servers that enable the VolumeScheduling feature.
    volume_binding_mode: Optional[str] = Field(None, alias="volumeBindingMode")

    # List of attributes to include in the K8s manifest
    fields_for_k8s_manifest: List[str] = [
        "allow_volume_expansion",
        "mount_options",
        "parameters",
        "provisioner",
        "reclaim_policy",
        "volume_binding_mode",
    ]

    def get_k8s_object(self) -> V1StorageClass:
        """Creates a body for this StorageClass"""

        # Return a V1StorageClass object to create a StorageClass
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_storage_class.py
        _v1_storage_class = V1StorageClass(
            allow_volume_expansion=self.allow_volume_expansion,
            api_version=self.api_version,
            kind=self.kind,
            metadata=self.metadata.get_k8s_object(),
            mount_options=self.mount_options,
            provisioner=self.provisioner,
            parameters=self.parameters,
            reclaim_policy=self.reclaim_policy,
            volume_binding_mode=self.volume_binding_mode,
        )
        return _v1_storage_class

    @staticmethod
    def get_from_cluster(
        k8s_client: K8sApiClient, namespace: Optional[str] = None, **kwargs
    ) -> Optional[List[V1StorageClass]]:
        """Reads StorageClasses from K8s cluster.

        Args:
            k8s_client: K8sApiClient for the cluster
            namespace: Namespace to use.
        """
        storage_v1_api: StorageV1Api = k8s_client.storage_v1_api
        sc_list: Optional[V1StorageClassList] = storage_v1_api.list_storage_class()
        scs: Optional[List[V1StorageClass]] = None
        if sc_list:
            scs = sc_list.items
            # logger.debug(f"scs: {scs}")
            # logger.debug(f"scs type: {type(scs)}")
        return scs

    def _create(self, k8s_client: K8sApiClient) -> bool:

        storage_v1_api: StorageV1Api = k8s_client.storage_v1_api
        k8s_object: V1StorageClass = self.get_k8s_object()

        logger.debug("Creating: {}".format(self.get_resource_name()))
        v1_storage_class: V1StorageClass = storage_v1_api.create_storage_class(
            body=k8s_object,
            async_req=self.async_req,
            pretty=self.pretty,
        )
        # logger.debug("Created: {}".format(v1_storage_class))
        if v1_storage_class.metadata.creation_timestamp is not None:
            logger.debug("StorageClass Created")
            self.active_resource = v1_storage_class
            self.active_resource_class = V1StorageClass
            return True
        logger.error("StorageClass could not be created")
        return False

    def _read(self, k8s_client: K8sApiClient) -> Optional[V1StorageClass]:
        """Returns the "Active" StorageClass from the cluster"""

        active_resource: Optional[V1StorageClass] = None
        active_resources: Optional[List[V1StorageClass]] = self.get_from_cluster(
            k8s_client=k8s_client,
        )
        # logger.debug(f"Active Resources: {active_resources}")
        if active_resources is None:
            return None

        active_resources_dict = {_sc.metadata.name: _sc for _sc in active_resources}

        sc_name = self.get_resource_name()
        if sc_name in active_resources_dict:
            active_resource = active_resources_dict[sc_name]
            self.active_resource = active_resource
            self.active_resource_class = V1StorageClass
            logger.debug(f"Found active {sc_name}")
        return active_resource

    def _update(self, k8s_client: K8sApiClient) -> bool:

        storage_v1_api: StorageV1Api = k8s_client.storage_v1_api
        sc_name = self.get_resource_name()
        k8s_object: V1StorageClass = self.get_k8s_object()

        logger.debug("Updating: {}".format(sc_name))
        v1_storage_class: V1StorageClass = storage_v1_api.patch_storage_class(
            name=sc_name,
            body=k8s_object,
            async_req=self.async_req,
            pretty=self.pretty,
        )
        # logger.debug("Updated:\n{}".format(pformat(v1_storage_class.to_dict(), indent=2)))
        if v1_storage_class.metadata.creation_timestamp is not None:
            logger.debug("StorageClass Updated")
            self.active_resource = v1_storage_class
            self.active_resource_class = V1StorageClass
            return True
        logger.error("StorageClass could not be updated")
        return False

    def _delete(self, k8s_client: K8sApiClient) -> bool:

        storage_v1_api: StorageV1Api = k8s_client.storage_v1_api
        sc_name = self.get_resource_name()

        logger.debug("Deleting: {}".format(sc_name))
        self.active_resource = None
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_status.py
        delete_status: V1Status = storage_v1_api.delete_storage_class(
            name=sc_name,
            async_req=self.async_req,
            pretty=self.pretty,
        )
        logger.debug("delete_status: {}".format(delete_status.status))
        if delete_status.status == "Success":
            logger.debug("StorageClass Deleted")
            return True
        logger.error("StorageClass could not be deleted")
        return False
