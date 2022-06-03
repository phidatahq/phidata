from typing import Dict, List, Optional, Union

from kubernetes.client import CoreV1Api
from kubernetes.client.models.v1_service import V1Service
from kubernetes.client.models.v1_service_list import V1ServiceList
from kubernetes.client.models.v1_service_port import V1ServicePort
from kubernetes.client.models.v1_service_spec import V1ServiceSpec
from kubernetes.client.models.v1_status import V1Status
from pydantic import Field

from phidata.infra.k8s.api_client import K8sApiClient
from phidata.infra.k8s.resource.base import K8sResource, K8sObject
from phidata.infra.k8s.enums.protocol import Protocol
from phidata.infra.k8s.enums.service_type import ServiceType
from phidata.utils.cli_console import print_info
from phidata.utils.log import logger


class ServicePort(K8sObject):
    """
    * Docs: https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.23/#serviceport-v1-core
    * Type: https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_service_port.py
    """

    resource_type: str = "ServicePort"

    # The name of this port within the service. This must be a DNS_LABEL.
    # All ports within a ServiceSpec must have unique names.
    # When considering the endpoints for a Service, this must match the 'name' field in the EndpointPort.
    # Optional if only one ServicePort is defined on this service.
    name: Optional[str] = None
    # The port on each node on which this service is exposed when type is NodePort or LoadBalancer.
    # Usually assigned by the system. If a value is specified, in-range, and not in use it will be used,
    # otherwise the operation will fail.
    # If not specified, a port will be allocated if this Service requires one.
    # If this field is specified when creating a Service which does not need it, creation will fail.
    # More info: https://kubernetes.io/docs/concepts/services-networking/service/#type-nodeport
    node_port: Optional[int] = Field(None, alias="nodePort")
    # The port that will be exposed by this service.
    port: int
    # The IP protocol for this port.
    # Supports "TCP", "UDP", and "SCTP". Default is TCP.
    protocol: Optional[Protocol] = None
    # Number or name of the port to access on the pods targeted by the service.
    # Number must be in the range 1 to 65535. Name must be an IANA_SVC_NAME.
    # If this is a string, it will be looked up as a named port in the target Pod's container ports.
    # If this is not specified, the value of the 'port' field is used (an identity map).
    # This field is ignored for services with clusterIP=None, and should be omitted or set equal to the 'port' field.
    # More info: https://kubernetes.io/docs/concepts/services-networking/service/#defining-a-service
    target_port: Optional[Union[str, int]] = Field(None, alias="targetPort")
    # The application protocol for this port. This field follows standard Kubernetes label syntax.
    app_protocol: Optional[str] = Field(None, alias="appProtocol")

    def get_k8s_object(self) -> V1ServicePort:

        # logger.info(f"Building {self.get_resource_type()} : {self.get_resource_name()}")

        target_port_int: Optional[int] = None
        if isinstance(self.target_port, int):
            target_port_int = self.target_port
        elif isinstance(self.target_port, str):
            try:
                target_port_int = int(self.target_port)
            except ValueError:
                pass

        target_port = target_port_int or self.target_port
        # logger.info(f"target_port         : {type(self.target_port)} | {self.target_port}")
        # logger.info(f"target_port updated : {type(target_port)} | {target_port}")

        # Return a V1ServicePort object
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_service_port.py
        _v1_service_port = V1ServicePort(
            name=self.name,
            node_port=self.node_port,
            port=self.port,
            protocol=self.protocol,
            target_port=target_port,
            app_protocol=self.app_protocol,
        )
        return _v1_service_port


class ServiceSpec(K8sObject):
    """
    # https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.23/#servicespec-v1-core
    """

    resource_type: str = "ServiceSpec"

    # type determines how the Service is exposed.
    # Defaults to ClusterIP. Valid options are ExternalName, ClusterIP, NodePort, and LoadBalancer.
    # "ClusterIP" allocates a cluster-internal IP address for load-balancing to endpoints.
    #   Endpoints are determined by the selector or if that is not specified,
    #   by manual construction of an Endpoints object or EndpointSlice objects.
    #   If clusterIP is "None", no virtual IP is allocated and the endpoints
    #   are published as a set of endpoints rather than a virtual IP.
    # "NodePort" builds on ClusterIP and allocates a port on every node which
    #   routes to the same endpoints as the clusterIP.
    # "LoadBalancer" builds on NodePort and creates an external load-balancer (if supported in the current cloud)
    #   which routes to the same endpoints as the clusterIP.
    # "ExternalName" aliases this service to the specified externalName.
    # Several other fields do not apply to ExternalName services.
    # More info: https://kubernetes.io/docs/concepts/services-networking/service/#publishing-services-service-types
    # Possible enum values:
    #   - `"ClusterIP"` means a service will only be accessible inside the cluster, via the cluster IP.
    #   - `"ExternalName"` means a service consists of only a reference to an external name
    #       that kubedns or equivalent will return as a CNAME record, with no exposing or proxying of any pods involved.
    #   - `"LoadBalancer"` means a service will be exposed via an external load balancer
    #   - `"NodePort"` means a service will be exposed on one port of every node, in addition to 'ClusterIP' type.
    type: Optional[ServiceType] = None
    ## type == ClusterIP
    # clusterIP is the IP address of the service and is usually assigned randomly.
    # If an address is specified manually, is in-range (as per system configuration), and is not in use,
    # it will be allocated to the service; otherwise creation of the service will fail
    cluster_ip: Optional[str] = Field(None, alias="clusterIP")
    # ClusterIPs is a list of IP addresses assigned to this service, and are usually assigned randomly
    cluster_ips: Optional[List[str]] = Field(None, alias="clusterIPs")
    ## type == ExternalName
    # externalIPs is a list of IP addresses for which nodes in the cluster will also accept traffic for this service.
    # These IPs are not managed by Kubernetes. The user is responsible for ensuring that traffic arrives at a node
    # with this IP. An example is external load-balancers that are not part of the Kubernetes system.
    external_ips: Optional[List[str]] = Field(None, alias="externalIPs")
    # externalName is the external reference that discovery mechanisms will return as an alias for this
    # service (e.g. a DNS CNAME record). No proxying will be involved.
    # Must be a lowercase RFC-1123 hostname (https://tools.ietf.org/html/rfc1123) and requires
    # `type` to be "ExternalName".
    external_name: Optional[str] = Field(None, alias="externalName")
    # externalTrafficPolicy denotes if this Service desires to route external traffic to node-local or cluster-wide endpoints.
    # "Local" preserves the client source IP and avoids a second hop for LoadBalancer and Nodeport type services,
    #   but risks potentially imbalanced traffic spreading.
    # "Cluster" obscures the client source IP and may cause a second hop to another node, but should have good overall load-spreading.
    # Possible enum values:
    #   - `"Cluster"` specifies node-global (legacy) behavior.
    #   - `"Local"` specifies node-local endpoints behavior.
    external_traffic_policy: Optional[str] = Field(None, alias="externalTrafficPolicy")
    ## type == LoadBalancer
    # healthCheckNodePort specifies the healthcheck nodePort for the service.
    # This only applies when type is set to LoadBalancer and externalTrafficPolicy is set to Local.
    health_check_node_port: Optional[int] = Field(None, alias="healthCheckNodePort")
    # InternalTrafficPolicy specifies if the cluster internal traffic should be routed to all endpoints or node-local endpoints only.
    # "Cluster" routes internal traffic to a Service to all endpoints.
    # "Local" routes traffic to node-local endpoints only, traffic is dropped if no node-local endpoints are ready.
    # The default value is "Cluster".
    internal_taffic_policy: Optional[str] = Field(None, alias="internalTrafficPolicy")
    # loadBalancerClass is the class of the load balancer implementation this Service belongs to.
    # If specified, the value of this field must be a label-style identifier, with an optional prefix,
    # e.g. "internal-vip" or "example.com/internal-vip". Unprefixed names are reserved for end-users.
    # This field can only be set when the Service type is 'LoadBalancer'.
    # If not set, the default load balancer implementation is used
    load_balancer_class: Optional[str] = Field(None, alias="loadBalancerClass")
    # Only applies to Service Type: LoadBalancer
    # LoadBalancer will get created with the IP specified in this field. This feature depends on
    # whether the underlying cloud-provider supports specifying the loadBalancerIP when a load balancer is created.
    # This field will be ignored if the cloud-provider does not support the feature.
    load_balancer_ip: Optional[str] = Field(None, alias="loadBalancerIP")
    # If specified and supported by the platform, this will restrict traffic through the cloud-provider load-balancer
    # will be restricted to the specified client IPs. This field will be ignored if the cloud-provider does not support.
    # More info: https://kubernetes.io/docs/tasks/access-application-cluster/create-external-load-balancer/
    load_balancer_source_ranges: Optional[List[str]] = Field(
        None, alias="loadBalancerSourceRanges"
    )
    # allocateLoadBalancerNodePorts defines if NodePorts will be automatically allocated for services
    # with type LoadBalancer. Default is "true". It may be set to "false" if the cluster load-balancer
    # does not rely on NodePorts.
    allocate_load_balancer_node_ports: Optional[bool] = Field(
        None, alias="allocateLoadBalancerNodePorts"
    )

    # The list of ports that are exposed by this service.
    # More info: https://kubernetes.io/docs/concepts/services-networking/service/#virtual-ips-and-service-proxies
    ports: List[ServicePort]
    publish_not_ready_addresses: Optional[bool] = Field(
        None, alias="publishNotReadyAddresses"
    )
    # Route service traffic to pods with label keys and values matching this selector.
    # If empty or not present, the service is assumed to have an external process managing its endpoints,
    # which Kubernetes will not modify. Only applies to types ClusterIP, NodePort, and LoadBalancer.
    # Ignored if type is ExternalName. More info: https://kubernetes.io/docs/concepts/services-networking/service/
    selector: Dict[str, str]
    # Supports "ClientIP" and "None". Used to maintain session affinity.
    # Enable client IP based session affinity. Must be ClientIP or None. Defaults to None.
    session_affinity: Optional[str] = Field(None, alias="sessionAffinity")
    # sessionAffinityConfig contains the configurations of session affinity.
    # session_affinity_config: Optional[SessionAffinityConfig] = Field(None, alias="sessionAffinityConfig")

    def get_k8s_object(self) -> V1ServiceSpec:

        # Return a V1ServiceSpec object
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_service_spec.py
        _ports: Optional[List[V1ServicePort]] = None
        if self.ports:
            _ports = []
            for _port in self.ports:
                _ports.append(_port.get_k8s_object())

        _v1_service_spec = V1ServiceSpec(
            type=self.type,
            allocate_load_balancer_node_ports=self.allocate_load_balancer_node_ports,
            cluster_ip=self.cluster_ip,
            cluster_i_ps=self.cluster_ips,
            external_i_ps=self.external_ips,
            external_name=self.external_name,
            external_traffic_policy=self.external_traffic_policy,
            health_check_node_port=self.health_check_node_port,
            internal_traffic_policy=self.internal_taffic_policy,
            load_balancer_class=self.load_balancer_class,
            load_balancer_ip=self.load_balancer_ip,
            load_balancer_source_ranges=self.load_balancer_source_ranges,
            ports=_ports,
            publish_not_ready_addresses=self.publish_not_ready_addresses,
            selector=self.selector,
            session_affinity=self.session_affinity,
            # ip_families=self.ip_families,
            # ip_family_policy=self.ip_family_policy,
            # session_affinity_config=self.session_affinity_config,
        )
        return _v1_service_spec


class Service(K8sResource):
    """A service resource exposes an application running on a set of Pods
    as a network service.

    References:
        * Docs:
            https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.23/#service-v1-core
            https://kubernetes.io/docs/concepts/services-networking/service/
        * Type: https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_service.py
    Notes:
        * The name of a Service object must be a valid DNS label name.
    """

    resource_type: str = "Service"

    spec: ServiceSpec

    # List of attributes to include in the K8s manifest
    fields_for_k8s_manifest: List[str] = ["spec"]

    def get_k8s_object(self) -> V1Service:
        """Creates a body for this Service"""

        # Return a V1Service object to create a ClusterRole
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_service.py
        _v1_service = V1Service(
            api_version=self.api_version,
            kind=self.kind,
            metadata=self.metadata.get_k8s_object(),
            spec=self.spec.get_k8s_object(),
        )
        return _v1_service

    @staticmethod
    def get_from_cluster(
        k8s_client: K8sApiClient, namespace: Optional[str] = None, **kwargs
    ) -> Optional[List[V1Service]]:
        """Reads Services from K8s cluster.

        Args:
            k8s_client: K8sApiClient for the cluster
            namespace: Namespace to use.
        """
        core_v1_api: CoreV1Api = k8s_client.core_v1_api
        svc_list: Optional[V1ServiceList] = None
        if namespace:
            # logger.debug(f"Getting services for ns: {namespace}")
            svc_list = core_v1_api.list_namespaced_service(namespace=namespace)
        else:
            # logger.debug("Getting services for all namespaces")
            svc_list = core_v1_api.list_service_for_all_namespaces()

        services: Optional[List[V1Service]] = None
        if svc_list:
            services = svc_list.items
        # logger.debug(f"services: {services}")
        # logger.debug(f"services type: {type(services)}")
        return services

    def _create(self, k8s_client: K8sApiClient) -> bool:

        core_v1_api: CoreV1Api = k8s_client.core_v1_api
        k8s_object: V1Service = self.get_k8s_object()
        namespace = self.get_namespace()

        logger.debug("Creating: {}".format(self.get_resource_name()))
        v1_service: V1Service = core_v1_api.create_namespaced_service(
            namespace=namespace,
            body=k8s_object,
            async_req=self.async_req,
            pretty=self.pretty,
        )
        # logger.debug("Created: {}".format(v1_service))
        if v1_service.metadata.creation_timestamp is not None:
            logger.debug("Service Created")
            self.active_resource = v1_service
            self.active_resource_class = V1Service
            return True
        logger.error("Service could not be created")
        return False

    def _read(self, k8s_client: K8sApiClient) -> Optional[V1Service]:
        """Returns the "Active" Service from the cluster"""

        namespace = self.get_namespace()
        active_resource: Optional[V1Service] = None
        active_resources: Optional[List[V1Service]] = self.get_from_cluster(
            k8s_client=k8s_client,
            namespace=namespace,
        )
        # logger.debug(f"Active Resources: {active_resources}")
        if active_resources is None:
            return None

        active_resources_dict = {
            _service.metadata.name: _service for _service in active_resources
        }

        svc_name = self.get_resource_name()
        if svc_name in active_resources_dict:
            active_resource = active_resources_dict[svc_name]
            self.active_resource = active_resource
            self.active_resource_class = V1Service
            logger.debug(f"Found active {svc_name}")
        return active_resource

    def _update(self, k8s_client: K8sApiClient) -> bool:

        core_v1_api: CoreV1Api = k8s_client.core_v1_api
        svc_name = self.get_resource_name()
        k8s_object: V1Service = self.get_k8s_object()
        namespace = self.get_namespace()

        logger.debug("Updating: {}".format(svc_name))
        v1_service: V1Service = core_v1_api.patch_namespaced_service(
            name=svc_name,
            namespace=namespace,
            body=k8s_object,
            async_req=self.async_req,
            pretty=self.pretty,
        )
        # logger.debug("Updated:\n{}".format(pformat(v1_service.to_dict(), indent=2)))
        if v1_service.metadata.creation_timestamp is not None:
            logger.debug("Service Updated")
            self.active_resource = v1_service
            self.active_resource_class = V1Service
            return True
        logger.error("Service could not be updated")
        return False

    def _delete(self, k8s_client: K8sApiClient) -> bool:

        core_v1_api: CoreV1Api = k8s_client.core_v1_api
        svc_name = self.get_resource_name()
        namespace = self.get_namespace()

        logger.debug("Deleting: {}".format(svc_name))
        self.active_resource = None
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_status.py
        delete_status: V1Status = core_v1_api.delete_namespaced_service(
            name=svc_name,
            namespace=namespace,
            async_req=self.async_req,
            pretty=self.pretty,
        )
        logger.debug("delete_status: {}".format(delete_status.status))
        if delete_status.status == "Success":
            logger.debug("Service Deleted")
            return True
        logger.error("Service could not be deleted")
        return False
