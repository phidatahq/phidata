from phi.utils.enum import ExtendedEnum


class ServiceType(str, ExtendedEnum):
    CLUSTER_IP = "ClusterIP"
    NODE_PORT = "NodePort"
    LOAD_BALANCER = "LoadBalancer"
    EXTERNAL_NAME = "ExternalName"
