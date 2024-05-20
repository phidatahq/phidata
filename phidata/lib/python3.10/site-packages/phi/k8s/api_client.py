from typing import Optional

try:
    import kubernetes
except ImportError:
    raise ImportError(
        "The `kubernetes` package is not installed. "
        "Install using `pip install kubernetes` or `pip install phidata[k8s]`."
    )

from phi.utils.log import logger


class K8sApiClient:
    def __init__(self, context: Optional[str] = None, kubeconfig_path: Optional[str] = None):
        super().__init__()

        self.context: Optional[str] = context
        self.kubeconfig_path: Optional[str] = kubeconfig_path
        self.configuration: Optional[kubernetes.client.Configuration] = None

        # kubernetes API clients
        self._api_client: Optional[kubernetes.client.ApiClient] = None
        self._apps_v1_api: Optional[kubernetes.client.AppsV1Api] = None
        self._core_v1_api: Optional[kubernetes.client.CoreV1Api] = None
        self._rbac_auth_v1_api: Optional[kubernetes.client.RbacAuthorizationV1Api] = None
        self._storage_v1_api: Optional[kubernetes.client.StorageV1Api] = None
        self._apiextensions_v1_api: Optional[kubernetes.client.ApiextensionsV1Api] = None
        self._networking_v1_api: Optional[kubernetes.client.NetworkingV1Api] = None
        self._custom_objects_api: Optional[kubernetes.client.CustomObjectsApi] = None
        logger.debug(f"**-+-** K8sApiClient created for {self.context}")

    def create_api_client(self) -> "kubernetes.client.ApiClient":
        """Create a kubernetes.client.ApiClient"""
        logger.debug("Creating kubernetes.client.ApiClient")
        try:
            self.configuration = kubernetes.client.Configuration()
            try:
                kubernetes.config.load_kube_config(
                    config_file=self.kubeconfig_path, client_configuration=self.configuration, context=self.context
                )
            except kubernetes.config.ConfigException:
                # Usually because the context is not in the kubeconfig
                kubernetes.config.load_kube_config(client_configuration=self.configuration)
            logger.debug(f"\thost: {self.configuration.host}")
            self._api_client = kubernetes.client.ApiClient(self.configuration)
            logger.debug(f"\tApiClient: {self._api_client}")
        except Exception as e:
            logger.error(e)

        if self._api_client is None:
            logger.error("Failed to create Kubernetes ApiClient")
            exit(0)
        return self._api_client

    ######################################################
    # K8s APIs are cached by the class
    ######################################################

    @property
    def api_client(self) -> "kubernetes.client.ApiClient":
        if self._api_client is None:
            self._api_client = self.create_api_client()
        return self._api_client

    @property
    def apps_v1_api(self) -> "kubernetes.client.AppsV1Api":
        if self._apps_v1_api is None:
            self._apps_v1_api = kubernetes.client.AppsV1Api(self.api_client)
        return self._apps_v1_api

    @property
    def core_v1_api(self) -> "kubernetes.client.CoreV1Api":
        if self._core_v1_api is None:
            self._core_v1_api = kubernetes.client.CoreV1Api(self.api_client)
        return self._core_v1_api

    @property
    def rbac_auth_v1_api(self) -> "kubernetes.client.RbacAuthorizationV1Api":
        if self._rbac_auth_v1_api is None:
            self._rbac_auth_v1_api = kubernetes.client.RbacAuthorizationV1Api(self.api_client)
        return self._rbac_auth_v1_api

    @property
    def storage_v1_api(self) -> "kubernetes.client.StorageV1Api":
        if self._storage_v1_api is None:
            self._storage_v1_api = kubernetes.client.StorageV1Api(self.api_client)
        return self._storage_v1_api

    @property
    def apiextensions_v1_api(self) -> "kubernetes.client.ApiextensionsV1Api":
        if self._apiextensions_v1_api is None:
            self._apiextensions_v1_api = kubernetes.client.ApiextensionsV1Api(self.api_client)
        return self._apiextensions_v1_api

    @property
    def networking_v1_api(self) -> "kubernetes.client.NetworkingV1Api":
        if self._networking_v1_api is None:
            self._networking_v1_api = kubernetes.client.NetworkingV1Api(self.api_client)
        return self._networking_v1_api

    @property
    def custom_objects_api(self) -> "kubernetes.client.CustomObjectsApi":
        if self._custom_objects_api is None:
            self._custom_objects_api = kubernetes.client.CustomObjectsApi(self.api_client)
        return self._custom_objects_api
