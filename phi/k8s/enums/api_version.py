from phi.utils.enum import ExtendedEnum


class ApiVersion(str, ExtendedEnum):
    CORE_V1 = "v1"
    APPS_V1 = "apps/v1"
    RBAC_AUTH_V1 = "rbac.authorization.k8s.io/v1"
    STORAGE_V1 = "storage.k8s.io/v1"
    APIEXTENSIONS_V1 = "apiextensions.k8s.io/v1"
    NETWORKING_V1 = "networking.k8s.io/v1"
    CLIENT_AUTHENTICATION_V1ALPHA1 = "client.authentication.k8s.io/v1alpha1"
    CLIENT_AUTHENTICATION_V1BETA1 = "client.authentication.k8s.io/v1beta1"
    # CRDs for Traefik
    TRAEFIK_CONTAINO_US_V1ALPHA1 = "traefik.containo.us/v1alpha1"
    NA = "NA"
