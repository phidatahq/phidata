from phi.utils.enum import ExtendedEnum


class ApiGroup(ExtendedEnum):
    CORE = ""
    APPS = "app"
    RBAC_AUTH = "rbac.authorization.k8s.io"
    STORAGE = "storage.k8s.io"
    APIEXTENSIONS = "apiextensions.k8s.io"
