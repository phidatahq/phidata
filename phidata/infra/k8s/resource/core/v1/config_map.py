from typing import Any, Dict, List, Optional

from kubernetes.client import CoreV1Api
from kubernetes.client.models.v1_config_map import V1ConfigMap
from kubernetes.client.models.v1_config_map_list import V1ConfigMapList
from kubernetes.client.models.v1_status import V1Status

from phidata.infra.k8s.api_client import K8sApiClient
from phidata.infra.k8s.resource.base import K8sResource
from phidata.utils.cli_console import print_info
from phidata.utils.log import logger


class ConfigMap(K8sResource):
    """
    ConfigMaps allow you to decouple configuration artifacts from image content to keep containerized applications portable.
    In short, they store configs. For config variables which contain sensitive info, use Secrets.

    References:
        * Docs:
            https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.23/#configmap-v1-core
            https://kubernetes.io/docs/tasks/configure-pod-container/configure-pod-configmap/
        * Type: https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_config_map.py
    """

    resource_type: str = "ConfigMap"

    data: Dict[str, Any]

    # List of attributes to include in the K8s manifest
    fields_for_k8s_manifest: List[str] = ["data"]

    def get_k8s_object(self) -> V1ConfigMap:
        """Creates a body for this ConfigMap"""

        # Return a V1ConfigMap object to create a ClusterRole
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_config_map.py
        _v1_config_map = V1ConfigMap(
            api_version=self.api_version,
            kind=self.kind,
            metadata=self.metadata.get_k8s_object(),
            data=self.data,
        )
        return _v1_config_map

    @staticmethod
    def get_from_cluster(
        k8s_client: K8sApiClient, namespace: Optional[str] = None, **kwargs: str
    ) -> Optional[List[V1ConfigMap]]:
        """Reads ConfigMaps from K8s cluster.

        Args:
            k8s_client: K8sApiClient for the cluster
            namespace: Namespace to use.
        """
        core_v1_api: CoreV1Api = k8s_client.core_v1_api
        # logger.debug(f"core_v1_api: {core_v1_api}")
        cm_list: Optional[V1ConfigMapList] = None
        if namespace:
            # logger.debug(f"Getting CMs for ns: {namespace}")
            cm_list = core_v1_api.list_namespaced_config_map(namespace=namespace)
        else:
            # logger.debug("Getting CMs for all namespaces")
            cm_list = core_v1_api.list_config_map_for_all_namespaces()

        config_maps: Optional[List[V1ConfigMap]] = None
        if cm_list:
            config_maps = cm_list.items
        # logger.debug(f"config_maps: {config_maps}")
        # logger.debug(f"config_maps type: {type(config_maps)}")
        return config_maps

    def _create(self, k8s_client: K8sApiClient) -> bool:

        core_v1_api: CoreV1Api = k8s_client.core_v1_api
        # logger.debug(f"core_v1_api: {core_v1_api}")
        k8s_object: V1ConfigMap = self.get_k8s_object()
        # logger.debug(f"k8s_object: {k8s_object}")
        namespace = self.get_namespace()
        # logger.debug(f"namespace: {namespace}")

        logger.debug("Creating: {}".format(self.get_resource_name()))
        v1_config_map: V1ConfigMap = core_v1_api.create_namespaced_config_map(
            namespace=namespace,
            body=k8s_object,
            async_req=self.async_req,
            pretty=self.pretty,
        )
        # logger.debug("Created: {}".format(v1_config_map))
        if v1_config_map.metadata.creation_timestamp is not None:
            logger.debug("ConfigMap Created")
            self.active_resource = v1_config_map
            self.active_resource_class = V1ConfigMap
            return True
        logger.error("ConfigMap could not be created")
        return False

    def _read(self, k8s_client: K8sApiClient) -> Optional[V1ConfigMap]:
        """Returns the "Active" ConfigMap from the cluster"""

        namespace = self.get_namespace()
        active_resource: Optional[V1ConfigMap] = None
        active_resources: Optional[List[V1ConfigMap]] = self.get_from_cluster(
            k8s_client=k8s_client,
            namespace=namespace,
        )
        # logger.debug(f"active_resources: {active_resources}")
        if active_resources is None:
            return None

        active_resources_dict = {_cm.metadata.name: _cm for _cm in active_resources}

        cm_name = self.get_resource_name()
        if cm_name in active_resources_dict:
            active_resource = active_resources_dict[cm_name]
            self.active_resource = active_resource
            self.active_resource_class = V1ConfigMap
            logger.debug(f"Found active {cm_name}")
        return active_resource

    def _update(self, k8s_client: K8sApiClient) -> bool:

        core_v1_api: CoreV1Api = k8s_client.core_v1_api
        cm_name = self.get_resource_name()
        k8s_object: V1ConfigMap = self.get_k8s_object()
        namespace = self.get_namespace()

        logger.debug("Updating: {}".format(cm_name))
        v1_config_map: V1ConfigMap = core_v1_api.patch_namespaced_config_map(
            name=cm_name,
            namespace=namespace,
            body=k8s_object,
            async_req=self.async_req,
            pretty=self.pretty,
        )
        # logger.debug("Updated:\n{}".format(pformat(v1_config_map.to_dict(), indent=2)))
        if v1_config_map.metadata.creation_timestamp is not None:
            logger.debug("ConfigMap Updated")
            self.active_resource = v1_config_map
            self.active_resource_class = V1ConfigMap
            return True
        logger.error("ConfigMap could not be updated")
        return False

    def _delete(self, k8s_client: K8sApiClient) -> bool:

        core_v1_api: CoreV1Api = k8s_client.core_v1_api
        cm_name = self.get_resource_name()
        namespace = self.get_namespace()

        logger.debug("Deleting: {}".format(cm_name))
        self.active_resource = None
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_status.py
        delete_status: V1Status = core_v1_api.delete_namespaced_config_map(
            name=cm_name,
            namespace=namespace,
            async_req=self.async_req,
            pretty=self.pretty,
        )
        logger.debug("delete_status: {}".format(delete_status.status))
        if delete_status.status == "Success":
            logger.debug("ConfigMap Deleted")
            return True
        logger.error("ConfigMap could not be deleted")
        return False
