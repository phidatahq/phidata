class K8sConfigException(Exception):
    pass


class K8sManagerException(Exception):
    pass


class K8sWorkerException(Exception):
    pass


class K8sArgsException(Exception):
    pass


class K8sApiClientException(Exception):
    pass


class K8sResourceCreationFailedException(Exception):
    pass


class StorageClassNotFoundException(Exception):
    pass


class KubeconfigInvalidException(Exception):
    pass
