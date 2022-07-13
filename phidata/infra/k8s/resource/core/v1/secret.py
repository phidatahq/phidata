from typing import Any, Dict, List, Optional

from kubernetes.client import CoreV1Api
from kubernetes.client.models.v1_secret import V1Secret
from kubernetes.client.models.v1_secret_list import V1SecretList
from kubernetes.client.models.v1_status import V1Status
from pydantic import Field

from phidata.infra.k8s.api_client import K8sApiClient
from phidata.infra.k8s.resource.base import K8sResource
from phidata.utils.cli_console import print_info
from phidata.utils.log import logger


class Secret(K8sResource):
    """
    References:
        * Doc: https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.23/#secret-v1-core
        * Type: https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_secret.py
    """

    resource_type: str = "Secret"

    type: str
    data: Optional[Dict[str, str]] = None
    string_data: Optional[Dict[str, str]] = Field(None, alias="stringData")

    # List of attributes to include in the K8s manifest
    fields_for_k8s_manifest: List[str] = ["type", "data", "string_data"]

    def get_k8s_object(self) -> V1Secret:
        """Creates a body for this Secret"""

        # Return a V1Secret object to create a ClusterRole
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_secret.py
        _v1_secret = V1Secret(
            api_version=self.api_version,
            kind=self.kind,
            metadata=self.metadata.get_k8s_object(),
            data=self.data,
            string_data=self.string_data,
            type=self.type,
        )
        return _v1_secret

    @staticmethod
    def get_from_cluster(
        k8s_client: K8sApiClient, namespace: Optional[str] = None, **kwargs: str
    ) -> Optional[List[V1Secret]]:
        """Reads Secrets from K8s cluster.

        Args:
            k8s_client: K8sApiClient for the cluster
            namespace: Namespace to use.
        """
        core_v1_api: CoreV1Api = k8s_client.core_v1_api
        secret_list: Optional[V1SecretList] = None
        if namespace:
            # logger.debug(f"Getting Secrets for ns: {namespace}")
            secret_list = core_v1_api.list_namespaced_secret(namespace=namespace)
        else:
            # logger.debug("Getting Secrets for all namespaces")
            secret_list = core_v1_api.list_secret_for_all_namespaces()

        secrets: Optional[List[V1Secret]] = None
        if secret_list:
            secrets = secret_list.items
        # logger.debug(f"secrets: {secrets}")
        # logger.debug(f"secrets type: {type(secrets)}")
        return secrets

    def _create(self, k8s_client: K8sApiClient) -> bool:

        core_v1_api: CoreV1Api = k8s_client.core_v1_api
        k8s_object: V1Secret = self.get_k8s_object()
        namespace = self.get_namespace()

        logger.debug("Creating: {}".format(self.get_resource_name()))
        v1_secret: V1Secret = core_v1_api.create_namespaced_secret(
            namespace=namespace,
            body=k8s_object,
            async_req=self.async_req,
            pretty=self.pretty,
        )
        # logger.debug("Created: {}".format(v1_secret))
        if v1_secret.metadata.creation_timestamp is not None:
            logger.debug("Secret Created")
            self.active_resource = v1_secret
            self.active_resource_class = V1Secret
            return True
        logger.error("Secret could not be created")
        return False

    def _read(self, k8s_client: K8sApiClient) -> Optional[V1Secret]:
        """Returns the "Active" Secret from the cluster"""

        namespace = self.get_namespace()
        active_resource: Optional[V1Secret] = None
        active_resources: Optional[List[V1Secret]] = self.get_from_cluster(
            k8s_client=k8s_client,
            namespace=namespace,
        )
        # logger.debug(f"active_resources: {active_resources}")
        if active_resources is None:
            return None

        active_resources_dict = {
            _secret.metadata.name: _secret for _secret in active_resources
        }

        secret_name = self.get_resource_name()
        if secret_name in active_resources_dict:
            active_resource = active_resources_dict[secret_name]
            self.active_resource = active_resource
            self.active_resource_class = V1Secret
            logger.debug(f"Found active {secret_name}")
        return active_resource

    def _update(self, k8s_client: K8sApiClient) -> bool:

        core_v1_api: CoreV1Api = k8s_client.core_v1_api
        secret_name = self.get_resource_name()
        k8s_object: V1Secret = self.get_k8s_object()
        namespace = self.get_namespace()

        logger.debug("Updating: {}".format(secret_name))
        v1_secret: V1Secret = core_v1_api.patch_namespaced_secret(
            name=secret_name,
            namespace=namespace,
            body=k8s_object,
            async_req=self.async_req,
            pretty=self.pretty,
        )
        # logger.debug("Updated:\n{}".format(pformat(v1_secret.to_dict(), indent=2)))
        if v1_secret.metadata.creation_timestamp is not None:
            logger.debug("Secret Updated")
            self.active_resource = v1_secret
            self.active_resource_class = V1Secret
            return True
        logger.error("Secret could not be updated")
        return False

    def _delete(self, k8s_client: K8sApiClient) -> bool:

        core_v1_api: CoreV1Api = k8s_client.core_v1_api
        secret_name = self.get_resource_name()
        namespace = self.get_namespace()

        logger.debug("Deleting: {}".format(secret_name))
        self.active_resource = None
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_status.py
        delete_status: V1Status = core_v1_api.delete_namespaced_secret(
            name=secret_name,
            namespace=namespace,
            async_req=self.async_req,
            pretty=self.pretty,
        )
        logger.debug("delete_status: {}".format(delete_status.status))
        if delete_status.status == "Success":
            logger.debug("Secret Deleted")
            return True
        logger.error("Secret could not be deleted")
        return False
