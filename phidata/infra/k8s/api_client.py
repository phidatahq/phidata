from pathlib import Path
from typing import Optional

import kubernetes

from phidata.infra.base.api_client import InfraApiClient
from phidata.infra.k8s.exceptions import K8sApiClientException
from phidata.utils.cli_console import print_error
from phidata.utils.log import logger


class K8sApiClient(InfraApiClient):
    """
    This class is a wrapper around the kubernetes clients to use with a K8sWorker
    """

    def __init__(
        self,
        context: Optional[str] = None,
        kubeconfig_path: Optional[Path] = None,
    ):

        super().__init__()
        # logger.debug(f"Creating K8sApiClient")
        # Cluster configuration
        self.context: Optional[str] = context
        self.kubeconfig_path: Optional[Path] = kubeconfig_path
        self.configuration: Optional[kubernetes.client.Configuration] = None

        # kubernetes API clients
        self._api_client: Optional[kubernetes.client.ApiClient] = None
        self._apps_v1_api: Optional[kubernetes.client.AppsV1Api] = None
        self._core_v1_api: Optional[kubernetes.client.CoreV1Api] = None
        self._rbac_auth_v1_api: Optional[
            kubernetes.client.RbacAuthorizationV1Api
        ] = None
        self._storage_v1_api: Optional[kubernetes.client.StorageV1Api] = None
        self._apiextensions_v1_api: Optional[
            kubernetes.client.ApiextensionsV1Api
        ] = None
        self._custom_objects_api: Optional[kubernetes.client.CustomObjectsApi] = None

        logger.debug(f"**-+-** K8sApiClient created")

    def is_initialized(self) -> bool:
        if self.api_client is not None:
            return True
        return False

    def create_api_client(self) -> kubernetes.client.ApiClient:
        """Create a kubernetes.client.ApiClient"""

        logger.debug("Creating kubernetes.client.ApiClient")
        api_client = None
        try:
            self.configuration = kubernetes.client.Configuration()
            try:
                kubernetes.config.load_kube_config(
                    client_configuration=self.configuration, context=self.context
                )
            except kubernetes.config.ConfigException as config_exc:
                # Usually because the context is not in the kubeconfig
                kubernetes.config.load_kube_config(
                    client_configuration=self.configuration
                )
            logger.debug(f"\thost: {self.configuration.host}")
            api_client = kubernetes.client.ApiClient(self.configuration)
            # logger.debug(f"\tApiClient: {api_client}")
        except Exception as e:
            print_error(e)
        if api_client is None:
            raise K8sApiClientException("Failed creating Kubernetes ApiClient")
        return api_client

    ######################################################
    ## K8s APIs as properties
    # APIs are lazy-initialized when needed
    ######################################################

    @property
    def api_client(self) -> kubernetes.client.ApiClient:
        if self._api_client is None:
            self._api_client = self.create_api_client()
        return self._api_client

    @property
    def apps_v1_api(self) -> kubernetes.client.AppsV1Api:
        if self._apps_v1_api is None:
            self._apps_v1_api = kubernetes.client.AppsV1Api(self.api_client)
        return self._apps_v1_api

    @property
    def core_v1_api(self) -> kubernetes.client.CoreV1Api:
        if self._core_v1_api is None:
            self._core_v1_api = kubernetes.client.CoreV1Api(self.api_client)
        return self._core_v1_api

    @property
    def rbac_auth_v1_api(self) -> kubernetes.client.RbacAuthorizationV1Api:
        if self._rbac_auth_v1_api is None:
            self._rbac_auth_v1_api = kubernetes.client.RbacAuthorizationV1Api(
                self.api_client
            )
        return self._rbac_auth_v1_api

    @property
    def storage_v1_api(self) -> kubernetes.client.StorageV1Api:
        if self._storage_v1_api is None:
            self._storage_v1_api = kubernetes.client.StorageV1Api(self.api_client)
        return self._storage_v1_api

    @property
    def apiextensions_v1_api(self) -> kubernetes.client.ApiextensionsV1Api:
        if self._apiextensions_v1_api is None:
            self._apiextensions_v1_api = kubernetes.client.ApiextensionsV1Api(
                self.api_client
            )
        return self._apiextensions_v1_api

    @property
    def custom_objects_api(self) -> kubernetes.client.CustomObjectsApi:
        if self._custom_objects_api is None:
            self._custom_objects_api = kubernetes.client.CustomObjectsApi(
                self.api_client
            )
        return self._custom_objects_api
