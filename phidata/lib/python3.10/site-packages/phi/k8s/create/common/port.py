from typing import Optional, Union

from pydantic import BaseModel

from phi.k8s.enums.protocol import Protocol


class CreatePort(BaseModel):
    """
    Reference:
    - https://matthewpalmer.net/kubernetes-app-developer/articles/kubernetes-ports-targetport-nodeport-service.html
    """

    # If specified, this must be an IANA_SVC_NAME and unique within the pod.
    # Each named port in a pod must have a unique name.
    # Name for the port that can be referred to by services.
    name: Optional[str] = None
    # Number of port to expose on the pod's IP address. This must be a valid port number, 0 < x < 65536.
    # This is port the application is running on the container
    container_port: int
    ## If the deployment running this container is exposed by a service
    # The service_port is the port that will be exposed by that service.
    service_port: Optional[int] = None
    # The target_port is the port to access on the pods targeted by the service.
    # It can be the port number or port name on the pod. usually the same as self.name
    target_port: Optional[Union[str, int]] = None
    # When using a service of type: NodePort or LoadBalancer
    # This is the port on each node on which this service is exposed
    node_port: Optional[int] = None
    protocol: Optional[Protocol] = None
    # host_ip: Optional[str] = None
    # Number of port to expose on the host.
    # If specified, this must be a valid port number, 0 < x < 65536.
    # Most containers do not need this.
    # host_port: Optional[int] = None
