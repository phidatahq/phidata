# import datetime
# from typing import Any, Dict, List, Optional
#
# import google.auth.transport.requests as google_auth_requests
# from google.cloud import container_v1
# from google.oauth2 import service_account
#
# import phidata.infra.k8s.enums as k8s_enums
# from phidata.infra.k8s.resource.kubeconfig import (
#     KubeconfigCluster,
#     KubeconfigUser,
#     KubeconfigUserConfig,
#     KubeconfigAuthConfig,
#     KubeconfigAuthProvider,
#     KubeconfigContext,
#     KubeconfigContextSpec,
#     Kubeconfig,
#     KubeconfigClusterConfig,
# )
# from phidata.utils.log import logger
#
#
# def _create_kubeconfig_cluster(
#     cluster_name: str, cluster_endpoint: str, cluster_ca_certificate: str
# ) -> KubeconfigCluster:
#     _cluster = KubeconfigCluster(
#         name=cluster_name,
#         cluster=KubeconfigClusterConfig(
#             server="https://{}".format(cluster_endpoint),
#             certificate_authority_data=cluster_ca_certificate,
#             # "insecure-skip-tls-verify": True,
#         ),
#     )
#     return _cluster
#
#
# def _create_kubeconfig_user(
#     auth_provider_name: str,
#     user_name: str,
#     access_token: str,
#     expiry: datetime.datetime,
# ) -> KubeconfigUser:
#     _user = KubeconfigUser(
#         name=user_name,
#         user=KubeconfigUserConfig(
#             auth_provider=KubeconfigAuthProvider(
#                 name=auth_provider_name,
#                 config=KubeconfigAuthConfig(
#                     access_token=access_token,
#                     expiry=expiry,
#                 ),
#             )
#         ),
#     )
#     return _user
#
#
# def _create_kubeconfig_context(
#     context_name: str, user_name: str, cluster_name: str, namespace: str
# ) -> KubeconfigContext:
#     _context = KubeconfigContext(
#         name=context_name,
#         context=KubeconfigContextSpec(
#             cluster=cluster_name,
#             user=user_name,
#             namespace=namespace,
#         ),
#     )
#     return _context
#
#
# def create_kubeconfig_resource_for_gke_cluster(
#     gke_cluster_gcp: container_v1.types.Cluster,
#     credentials: service_account.Credentials,
#     namespace_name: str,
#     context_name: str,
# ) -> Optional[Kubeconfig]:
#     """Creates the kubeconfig for a given cluster.
#
#     TODO:
#         * Learn more about kubeconfig - no idea what the fuck im doing here
#         * Figure out if there is a better way to generate a kubeconfig
#         * Add doc
#         * Add Error Handling
#         * Change input from container_v1.types.Cluster to resource.GKEClusterOutput
#     References:
#         * https://kubernetes.io/docs/concepts/configuration/organize-cluster-access-kubeconfig/
#         * https://kubernetes.io/docs/tasks/access-application-cluster/configure-access-multiple-clusters/
#         * https://godoc.org/k8s.io/client-go/tools/clientcmd/api#Config
#         * https://unofficial-kubernetes.readthedocs.io/en/latest/concepts/cluster-administration/authenticate-across-clusters-kubeconfig/
#     """
#
#     kubeconfig: Optional[Kubeconfig] = None
#     if gke_cluster_gcp and credentials:
#         try:
#             cluster_name = gke_cluster_gcp.name
#         except Exception as e:
#             logger.exception(f"Cannot parse GKEClusterSchema {gke_cluster_gcp}", e)
#             return None
#
#         logger.debug(f"Creating kubeconfig for {cluster_name}")
#         http_request = google_auth_requests.Request()
#         logger.debug("Refreshing credentials")
#         credentials.refresh(http_request)
#         logger.debug("Credentials refreshed")
#
#         # logger.debug(f"service_account_email: {credentials.service_account_email}")
#         # logger.debug(f"project_id: {credentials.project_id}")
#         # logger.debug(f"requires_scopes: {credentials.requires_scopes}")
#         # logger.debug(f"signer: {credentials.signer}")
#         # logger.debug(f"signer_email: {credentials.signer_email}")
#         # logger.debug(f"valid: {credentials.valid}")
#         # logger.debug(f"expired: {credentials.expired}")
#         # logger.debug(f"token: {credentials.token}")
#         # logger.debug(f"expiry: {credentials.expiry}")
#         # logger.debug(f"expiry type: {type(credentials.expiry)}")
#         # logger.debug(f"_credentials: {credentials}")
#         # logger.debug(f"gke_cluster_gcp: {gke_cluster_gcp}")
#
#         try:
#             # Cluster details for the kubeconfig
#             cluster_endpoint = gke_cluster_gcp.endpoint
#             cluster_ca_certificate = gke_cluster_gcp.master_auth.cluster_ca_certificate
#
#             # UserSchema details for the kubeconfig
#             service_account_email = credentials.service_account_email
#             access_token = credentials.token
#             expiry = credentials.expiry
#         except Exception as e:
#             logger.exception(f"Cannot Parse GKEClusterSchema {gke_cluster_gcp}", e)
#             return None
#
#         kubeconfig_cluster: KubeconfigCluster = _create_kubeconfig_cluster(
#             cluster_name, cluster_endpoint, cluster_ca_certificate
#         )
#         kubeconfig_user: KubeconfigUser = _create_kubeconfig_user(
#             "gcp", service_account_email, access_token, expiry
#         )
#         kubeconfig_context: KubeconfigContext = _create_kubeconfig_context(
#             context_name, service_account_email, cluster_name, namespace_name
#         )
#
#         kubeconfig = Kubeconfig(
#             api_version=k8s_enums.ApiVersion.CORE_V1,
#             kind=k8s_enums.Kind.CONFIG,
#             clusters=[kubeconfig_cluster],
#             users=[kubeconfig_user],
#             contexts=[kubeconfig_context],
#             current_context=context_name,
#         )
#
#     return kubeconfig
