from phi.utils.enum import ExtendedEnum


class Kind(str, ExtendedEnum):
    CLUSTERROLE = "ClusterRole"
    CLUSTERROLEBINDING = "ClusterRoleBinding"
    CONFIG = "Config"
    CONFIGMAP = "ConfigMap"
    CONTAINER = "Container"
    DEPLOYMENT = "Deployment"
    POD = "Pod"
    NAMESPACE = "Namespace"
    SERVICE = "Service"
    INGRESS = "Ingress"
    SERVICEACCOUNT = "ServiceAccount"
    SECRET = "Secret"
    PERSISTENTVOLUME = "PersistentVolume"
    PERSISTENTVOLUMECLAIM = "PersistentVolumeClaim"
    STORAGECLASS = "StorageClass"
    CUSTOMRESOURCEDEFINITION = "CustomResourceDefinition"
    # CRDs for Traefik
    INGRESSROUTE = "IngressRoute"
    INGRESSROUTETCP = "IngressRouteTCP"
    MIDDLEWARE = "Middleware"
    TLSOPTION = "TLSOption"
    USER = "User"
    GROUP = "Group"
    VOLUME = "Volume"
    YAML = "yaml"
