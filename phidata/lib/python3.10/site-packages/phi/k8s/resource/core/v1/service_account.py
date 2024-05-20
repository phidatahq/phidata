from typing import List, Optional

from kubernetes.client import CoreV1Api
from kubernetes.client.models.v1_service_account import V1ServiceAccount
from kubernetes.client.models.v1_service_account_list import V1ServiceAccountList
from pydantic import Field

from phi.k8s.api_client import K8sApiClient
from phi.k8s.resource.core.v1.local_object_reference import (
    LocalObjectReference,
)
from phi.k8s.resource.core.v1.object_reference import ObjectReference
from phi.k8s.resource.base import K8sResource
from phi.utils.log import logger


class ServiceAccount(K8sResource):
    """A service account provides an identity for processes that run in a Pod.
    When you create a pod, if you do not specify a service account, it is automatically assigned the default
    service account in the same namespace.

    References:
    - Docs: https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.23/#serviceaccount-v1-core
    - Type: https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_service_account.py
    """

    resource_type: str = "ServiceAccount"

    # AutomountServiceAccountToken indicates whether pods running as this service account
    # should have an API token automatically mounted. Can be overridden at the pod level.
    automount_service_account_token: Optional[bool] = Field(None, alias="automountServiceAccountToken")
    # ImagePullSecrets is a list of references to secrets in the same namespace to use for pulling any images in pods
    # that reference this ServiceAccount. ImagePullSecrets are distinct from Secrets because Secrets can be mounted
    # in the pod, but ImagePullSecrets are only accessed by the kubelet.
    # More info: https://kubernetes.io/docs/concepts/containers/images/#specifying-imagepullsecrets-on-a-pod
    image_pull_secrets: Optional[List[LocalObjectReference]] = Field(None, alias="imagePullSecrets")
    # Secrets is the list of secrets allowed to be used by pods running using this ServiceAccount.
    # More info: https://kubernetes.io/docs/concepts/configuration/secret
    secrets: Optional[List[ObjectReference]] = None

    # List of attributes to include in the K8s manifest
    fields_for_k8s_manifest: List[str] = [
        "automount_service_account_token",
        "image_pull_secrets",
        "secrets",
    ]

    def get_k8s_object(self) -> V1ServiceAccount:
        """Creates a body for this ServiceAccount"""

        # Return a V1ServiceAccount object
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_service_account.py
        _image_pull_secrets = None
        if self.image_pull_secrets:
            _image_pull_secrets = []
            for ips in self.image_pull_secrets:
                _image_pull_secrets.append(ips.get_k8s_object())

        _secrets = None
        if self.secrets:
            _secrets = []
            for s in self.secrets:
                _secrets.append(s.get_k8s_object())

        _v1_service_account = V1ServiceAccount(
            api_version=self.api_version.value,
            kind=self.kind.value,
            metadata=self.metadata.get_k8s_object(),
            automount_service_account_token=self.automount_service_account_token,
            image_pull_secrets=_image_pull_secrets,
            secrets=_secrets,
        )
        return _v1_service_account

    @staticmethod
    def get_from_cluster(
        k8s_client: K8sApiClient, namespace: Optional[str] = None, **kwargs
    ) -> Optional[List[V1ServiceAccount]]:
        """Reads ServiceAccounts from K8s cluster.

        Args:
            k8s_client: K8sApiClient for the cluster
            namespace: Namespace to use.
        """
        core_v1_api: CoreV1Api = k8s_client.core_v1_api
        sa_list: Optional[V1ServiceAccountList] = None
        if namespace:
            # logger.debug(f"Getting SAs for ns: {namespace}")
            sa_list = core_v1_api.list_namespaced_service_account(namespace=namespace)
        else:
            # logger.debug("Getting SAs for all namespaces")
            sa_list = core_v1_api.list_service_account_for_all_namespaces()

        sas: Optional[List[V1ServiceAccount]] = None
        if sa_list:
            sas = sa_list.items
        # logger.debug(f"sas: {sas}")
        # logger.debug(f"sas type: {type(sas)}")

        return sas

    def _create(self, k8s_client: K8sApiClient) -> bool:
        core_v1_api: CoreV1Api = k8s_client.core_v1_api
        k8s_object: V1ServiceAccount = self.get_k8s_object()
        namespace = self.get_namespace()

        logger.debug("Creating: {}".format(self.get_resource_name()))
        v1_service_account: V1ServiceAccount = core_v1_api.create_namespaced_service_account(
            body=k8s_object,
            namespace=namespace,
            async_req=self.async_req,
            pretty=self.pretty,
        )
        # logger.debug("Created: {}".format(v1_service_account))
        if v1_service_account.metadata.creation_timestamp is not None:
            logger.debug("ServiceAccount Created")
            self.active_resource = v1_service_account
            return True
        logger.error("ServiceAccount could not be created")
        return False

    def _read(self, k8s_client: K8sApiClient) -> Optional[V1ServiceAccount]:
        """Returns the "Active" ServiceAccount from the cluster"""

        namespace = self.get_namespace()
        active_resource: Optional[V1ServiceAccount] = None
        active_resources: Optional[List[V1ServiceAccount]] = self.get_from_cluster(
            k8s_client=k8s_client,
            namespace=namespace,
        )
        # logger.debug(f"Active Resources: {active_resources}")
        if active_resources is None:
            return None

        active_resources_dict = {_sa.metadata.name: _sa for _sa in active_resources}

        sa_name = self.get_resource_name()
        if sa_name in active_resources_dict:
            active_resource = active_resources_dict[sa_name]
            self.active_resource = active_resource
            logger.debug(f"Found active {sa_name}")
        return active_resource

    def _update(self, k8s_client: K8sApiClient) -> bool:
        core_v1_api: CoreV1Api = k8s_client.core_v1_api
        sa_name = self.get_resource_name()
        k8s_object: V1ServiceAccount = self.get_k8s_object()
        namespace = self.get_namespace()
        logger.debug("Updating: {}".format(sa_name))

        v1_service_account: V1ServiceAccount = core_v1_api.patch_namespaced_service_account(
            name=sa_name,
            namespace=namespace,
            body=k8s_object,
            async_req=self.async_req,
            pretty=self.pretty,
        )
        # logger.debug("Updated:\n{}".format(pformat(v1_service_account.to_dict(), indent=2)))
        if v1_service_account.metadata.creation_timestamp is not None:
            logger.debug("ServiceAccount Updated")
            self.active_resource = v1_service_account
            return True
        logger.error("ServiceAccount could not be updated")
        return False

    def _delete(self, k8s_client: K8sApiClient) -> bool:
        core_v1_api: CoreV1Api = k8s_client.core_v1_api
        sa_name = self.get_resource_name()
        namespace = self.get_namespace()

        logger.debug("Deleting: {}".format(sa_name))
        self.active_resource = None
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_status.py
        delete_status: V1ServiceAccount = core_v1_api.delete_namespaced_service_account(
            name=sa_name,
            namespace=namespace,
            async_req=self.async_req,
            pretty=self.pretty,
        )
        # logger.debug("delete_status: {}".format(delete_status))
        # logger.debug("delete_status type: {}".format(type(delete_status)))
        # logger.debug("delete_status: {}".format(delete_status.status))
        # TODO: validate the delete status, this check is currently not accurate
        # it just checks if a V1ServiceAccount object was returned
        if delete_status is not None:
            logger.debug("ServiceAccount Deleted")
            return True
        logger.error("ServiceAccount could not be deleted")
        return False
