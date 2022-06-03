from typing import List, Optional

from kubernetes.client import CoreV1Api
from kubernetes.client.models.v1_namespace import V1Namespace
from kubernetes.client.models.v1_namespace_spec import V1NamespaceSpec
from kubernetes.client.models.v1_namespace_list import V1NamespaceList
from kubernetes.client.models.v1_status import V1Status

from phidata.infra.k8s.api_client import K8sApiClient
from phidata.infra.k8s.resource.base import K8sResource, K8sObject
from phidata.utils.cli_console import print_info
from phidata.utils.log import logger


class NamespaceSpec(K8sObject):
    """
    # https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.23/#namespacespec-v1-core
    """

    resource_type: str = "NamespaceSpec"

    # Finalizers is an opaque list of values that must be empty to permanently remove object from storage.
    # More info: https://kubernetes.io/docs/tasks/administer-cluster/namespaces/
    finalizers: Optional[List[str]] = None

    def get_k8s_object(self) -> V1NamespaceSpec:

        # Return a V1NamespaceSpec object
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_namespace_spec.py
        _v1_namespace_spec = V1NamespaceSpec(
            finalizers=self.finalizers,
        )
        return _v1_namespace_spec


class Namespace(K8sResource):
    """
    Kubernetes supports multiple virtual clusters backed by the same physical cluster.
    These virtual clusters are called namespaces.
    References:
        * Docs:
            https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.23/#namespace-v1-core
            https://kubernetes.io/docs/concepts/overview/working-with-objects/namespaces/
        * Type: https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_namespace.py
    """

    resource_type: str = "Namespace"

    spec: Optional[NamespaceSpec] = None

    # List of attributes to include in the K8s manifest
    fields_for_k8s_manifest: List[str] = []

    def get_k8s_object(self) -> V1Namespace:
        """Creates a body for this Namespace"""

        # Return a V1Namespace object to create a ClusterRole
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_namespace.py
        _v1_namespace = V1Namespace(
            api_version=self.api_version,
            kind=self.kind,
            metadata=self.metadata.get_k8s_object(),
            spec=self.spec.get_k8s_object() if self.spec is not None else None,
        )
        return _v1_namespace

    @staticmethod
    def get_from_cluster(
        k8s_client: K8sApiClient, namespace: Optional[str] = None, **kwargs
    ) -> Optional[List[V1Namespace]]:
        """Reads Namespaces from K8s cluster.

        Args:
            k8s_client: K8sApiClient for the cluster
            namespace: Namespace to use.
        """
        core_v1_api: CoreV1Api = k8s_client.core_v1_api
        # logger.debug("Getting all Namespaces")
        ns_list: Optional[V1NamespaceList] = core_v1_api.list_namespace()

        namespaces: Optional[List[V1Namespace]] = None
        if ns_list:
            namespaces = [ns for ns in ns_list.items if ns.status.phase == "Active"]
        # logger.debug(f"namespaces: {namespaces}")
        # logger.debug(f"namespaces type: {type(namespaces)}")
        return namespaces

    def _create(self, k8s_client: K8sApiClient) -> bool:

        core_v1_api: CoreV1Api = k8s_client.core_v1_api
        k8s_object: V1Namespace = self.get_k8s_object()

        logger.debug("Creating: {}".format(self.get_resource_name()))
        v1_namespace: V1Namespace = core_v1_api.create_namespace(
            body=k8s_object,
            async_req=self.async_req,
            pretty=self.pretty,
        )
        logger.debug("Created: {}".format(v1_namespace))
        if v1_namespace.metadata.creation_timestamp is not None:
            logger.debug("Namespace Created")
            self.active_resource = v1_namespace
            self.active_resource_class = V1Namespace
            return True
        logger.error("Namespace could not be created")
        return False

    def _read(self, k8s_client: K8sApiClient) -> Optional[V1Namespace]:
        """Returns the "Active" Namespace from the cluster"""

        active_resource: Optional[V1Namespace] = None
        active_resources: Optional[List[V1Namespace]] = self.get_from_cluster(
            k8s_client=k8s_client,
        )
        # logger.debug(f"Active Resources: {active_resources}")
        if active_resources is None:
            return None

        active_resources_dict = {_ns.metadata.name: _ns for _ns in active_resources}

        ns_name = self.get_resource_name()
        if ns_name in active_resources_dict:
            active_resource = active_resources_dict[ns_name]
            self.active_resource = active_resource
            self.active_resource_class = V1Namespace
            logger.debug(f"Found active {ns_name}")
        return active_resource

    def _update(self, k8s_client: K8sApiClient) -> bool:

        core_v1_api: CoreV1Api = k8s_client.core_v1_api
        ns_name = self.get_resource_name()
        k8s_object: V1Namespace = self.get_k8s_object()

        logger.debug("Updating: {}".format(ns_name))
        v1_namespace: V1Namespace = core_v1_api.patch_namespace(
            name=ns_name,
            body=k8s_object,
            async_req=self.async_req,
            pretty=self.pretty,
        )
        # logger.debug("Updated:\n{}".format(pformat(v1_namespace.to_dict(), indent=2)))
        if v1_namespace.metadata.creation_timestamp is not None:
            logger.debug("Namespace Updated")
            self.active_resource = v1_namespace
            self.active_resource_class = V1Namespace
            return True
        logger.error("Namespace could not be updated")
        return False

    def _delete(self, k8s_client: K8sApiClient) -> bool:

        core_v1_api: CoreV1Api = k8s_client.core_v1_api
        ns_name = self.get_resource_name()

        logger.debug("Deleting: {}".format(ns_name))
        self.active_resource = None
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_status.py
        delete_status: V1Status = core_v1_api.delete_namespace(
            name=ns_name,
            async_req=self.async_req,
            pretty=self.pretty,
        )
        logger.debug("delete_status: {}".format(delete_status.status))
        if delete_status.status == "Success":
            logger.debug("Namespace Deleted")
            return True
        logger.error("Namespace could not be deleted")
        return False
