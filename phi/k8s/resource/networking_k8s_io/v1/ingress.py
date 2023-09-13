from typing import List, Optional, Union, Any

from kubernetes.client import NetworkingV1Api
from kubernetes.client.models.v1_ingress import V1Ingress
from kubernetes.client.models.v1_ingress_backend import V1IngressBackend
from kubernetes.client.models.v1_ingress_list import V1IngressList
from kubernetes.client.models.v1_ingress_rule import V1IngressRule
from kubernetes.client.models.v1_ingress_spec import V1IngressSpec
from kubernetes.client.models.v1_ingress_tls import V1IngressTLS
from kubernetes.client.models.v1_status import V1Status

from phi.k8s.api_client import K8sApiClient
from phi.k8s.resource.base import K8sResource, K8sObject
from phi.utils.log import logger


class ServiceBackendPort(K8sObject):
    """
    Reference:
    - https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.23/#servicebackendport-v1-networking-k8s-io
    """

    resource_type: str = "ServiceBackendPort"

    number: int
    name: Optional[str] = None


class IngressServiceBackend(K8sObject):
    """
    Reference:
    - https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.23/#ingressbackend-v1-networking-k8s-io
    """

    resource_type: str = "IngressServiceBackend"

    service_name: str
    service_port: Union[int, str]


class IngressBackend(K8sObject):
    """
    Reference:
    - https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.23/#ingressbackend-v1-networking-k8s-io
    """

    resource_type: str = "IngressBackend"

    service: Optional[V1IngressBackend] = None
    resource: Optional[Any] = None


class HTTPIngressPath(K8sObject):
    """
    Reference:
    - https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.23/#httpingresspath-v1-networking-k8s-io
    """

    resource_type: str = "HTTPIngressPath"

    path: Optional[str] = None
    path_type: Optional[str] = None
    backend: IngressBackend


class HTTPIngressRuleValue(K8sObject):
    """
    Reference:
    - https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.23/#httpingressrulevalue-v1-networking-k8s-io
    """

    resource_type: str = "HTTPIngressRuleValue"

    paths: List[HTTPIngressPath]


class IngressRule(K8sObject):
    """
    Reference:
    - https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.23/#ingressrule-v1-networking-k8s-io
    """

    resource_type: str = "IngressRule"

    host: Optional[str] = None
    http: Optional[HTTPIngressRuleValue] = None


class IngressSpec(K8sObject):
    """
    Reference:
    - https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.23/#ingressspec-v1-core
    """

    resource_type: str = "IngressSpec"

    # DefaultBackend is the backend that should handle requests that don't match any rule.
    # If Rules are not specified, DefaultBackend must be specified.
    # If DefaultBackend is not set, the handling of requests that do not match any of
    # the rules will be up to the Ingress controller.
    default_backend: Optional[V1IngressBackend] = None
    # IngressClassName is the name of the IngressClass cluster resource.
    # The associated IngressClass defines which controller will implement the resource.
    # This replaces the deprecated `kubernetes.io/ingress.class` annotation.
    # For backwards compatibility, when that annotation is set, it must be given precedence over this field.
    ingress_class_name: Optional[str] = None
    # A list of host rules used to configure the Ingress. If unspecified, or no rule matches,
    # all traffic is sent to the default backend.
    rules: Optional[List[V1IngressRule]] = None
    # TLS configuration. The Ingress only supports a single TLS port, 443.
    # If multiple members of this list specify different hosts, they will be multiplexed on the
    # same port according to the hostname specified through the SNI TLS extension, if the ingress controller
    # fulfilling the ingress supports SNI.
    tls: Optional[List[V1IngressTLS]] = None

    def get_k8s_object(self) -> V1IngressSpec:
        # Return a V1IngressSpec object
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_ingress_spec.py

        _v1_ingress_spec = V1IngressSpec(
            default_backend=self.default_backend,
            ingress_class_name=self.ingress_class_name,
            rules=self.rules,
            tls=self.tls,
        )
        return _v1_ingress_spec


class Ingress(K8sResource):
    """
    References:
    - Docs: https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.23/#ingress-v1-networking-k8s-io
    - Type: https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_ingress.py
    """

    resource_type: str = "Ingress"

    spec: IngressSpec

    # List of attributes to include in the K8s manifest
    fields_for_k8s_manifest: List[str] = ["spec"]

    def get_k8s_object(self) -> V1Ingress:
        """Creates a body for this Ingress"""

        # Return a V1Ingress object to create a ClusterRole
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_ingress.py
        _v1_ingress = V1Ingress(
            api_version=self.api_version.value,
            kind=self.kind.value,
            metadata=self.metadata.get_k8s_object(),
            spec=self.spec.get_k8s_object(),
        )
        return _v1_ingress

    @staticmethod
    def get_from_cluster(
        k8s_client: K8sApiClient, namespace: Optional[str] = None, **kwargs
    ) -> Optional[List[V1Ingress]]:
        """Reads Ingress from K8s cluster.

        Args:
            k8s_client: K8sApiClient for the cluster
            namespace: Namespace to use.
        """
        networking_v1_api: NetworkingV1Api = k8s_client.networking_v1_api
        ingress_list: Optional[V1IngressList] = None
        if namespace:
            logger.debug(f"Getting ingress for ns: {namespace}")
            ingress_list = networking_v1_api.list_namespaced_ingress(namespace=namespace)
        else:
            logger.debug("Getting ingress for all namespaces")
            ingress_list = networking_v1_api.list_ingress_for_all_namespaces()

        ingress: Optional[List[V1Ingress]] = None
        if ingress_list:
            ingress = ingress_list.items
        logger.debug(f"ingress: {ingress}")
        logger.debug(f"ingress type: {type(ingress)}")
        return ingress

    def _create(self, k8s_client: K8sApiClient) -> bool:
        networking_v1_api: NetworkingV1Api = k8s_client.networking_v1_api
        k8s_object: V1Ingress = self.get_k8s_object()
        namespace = self.get_namespace()

        logger.debug("Creating: {}".format(self.get_resource_name()))
        v1_ingress: V1Ingress = networking_v1_api.create_namespaced_ingress(
            namespace=namespace,
            body=k8s_object,
            async_req=self.async_req,
            pretty=self.pretty,
        )
        logger.debug("Created: {}".format(v1_ingress))
        if v1_ingress.metadata.creation_timestamp is not None:
            logger.debug("Ingress Created")
            self.active_resource = v1_ingress
            return True
        logger.error("Ingress could not be created")
        return False

    def _read(self, k8s_client: K8sApiClient) -> Optional[V1Ingress]:
        """Returns the "Active" Ingress from the cluster"""

        namespace = self.get_namespace()
        active_resource: Optional[V1Ingress] = None
        active_resources: Optional[List[V1Ingress]] = self.get_from_cluster(
            k8s_client=k8s_client,
            namespace=namespace,
        )
        logger.debug(f"Active Resources: {active_resources}")
        if active_resources is None:
            return None

        active_resources_dict = {_ingress.metadata.name: _ingress for _ingress in active_resources}

        ingress_name = self.get_resource_name()
        if ingress_name in active_resources_dict:
            active_resource = active_resources_dict[ingress_name]
            self.active_resource = active_resource
            logger.debug(f"Found active {ingress_name}")
        return active_resource

    def _update(self, k8s_client: K8sApiClient) -> bool:
        networking_v1_api: NetworkingV1Api = k8s_client.networking_v1_api
        ingress_name = self.get_resource_name()
        k8s_object: V1Ingress = self.get_k8s_object()
        namespace = self.get_namespace()

        logger.debug("Updating: {}".format(ingress_name))
        v1_ingress: V1Ingress = networking_v1_api.patch_namespaced_ingress(
            name=ingress_name,
            namespace=namespace,
            body=k8s_object,
            async_req=self.async_req,
            pretty=self.pretty,
        )
        # logger.debug("Updated:\n{}".format(pformat(v1_ingress.to_dict(), indent=2)))
        if v1_ingress.metadata.creation_timestamp is not None:
            logger.debug("Ingress Updated")
            self.active_resource = v1_ingress
            return True
        logger.error("Ingress could not be updated")
        return False

    def _delete(self, k8s_client: K8sApiClient) -> bool:
        networking_v1_api: NetworkingV1Api = k8s_client.networking_v1_api
        ingress_name = self.get_resource_name()
        namespace = self.get_namespace()

        logger.debug("Deleting: {}".format(ingress_name))
        self.active_resource = None
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_status.py
        delete_status: V1Status = networking_v1_api.delete_namespaced_ingress(
            name=ingress_name,
            namespace=namespace,
            async_req=self.async_req,
            pretty=self.pretty,
        )
        logger.debug("delete_status: {}".format(delete_status.status))
        if delete_status.status == "Success":
            logger.debug("Ingress Deleted")
            return True
        logger.error("Ingress could not be deleted")
        return False
