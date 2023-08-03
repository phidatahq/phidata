from phi.utils.enum import ExtendedEnum


class ServiceType(ExtendedEnum):
    CLUSTER_IP = "ClusterIP"
    NODE_PORT = "NodePort"
    LOAD_BALANCER = "LoadBalancer"
