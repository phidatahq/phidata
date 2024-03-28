from typing import Optional, Dict, List, Any

from phi.k8s.app.base import (
    K8sApp,
    AppVolumeType,  # noqa: F401
    ContainerContext,  # noqa: F401
    ServiceType,
    RestartPolicy,  # noqa: F401
    ImagePullPolicy,  # noqa: F401
    LoadBalancerProvider,  # noqa: F401
)
from phi.k8s.app.traefik.crds import ingressroute_crd, middleware_crd
from phi.utils.log import logger


class TraefikRouter(K8sApp):
    # -*- App Name
    name: str = "traefik"

    # -*- Image Configuration
    image_name: str = "traefik"
    image_tag: str = "v2.10"

    # -*- RBAC Configuration
    # Create a ServiceAccount, ClusterRole, and ClusterRoleBinding
    create_rbac: bool = True

    # -*- Install traefik CRDs
    # See: https://doc.traefik.io/traefik/providers/kubernetes-crd/#configuration-requirements
    install_crds: bool = False

    # -*- Traefik Configuration
    domain_name: Optional[str] = None
    # Enable Access Logs
    access_logs: bool = True
    # Traefik config file on the host
    traefik_config_file: Optional[str] = None
    # Traefik config file on the container
    traefik_config_file_container_path: str = "/etc/traefik/traefik.yaml"

    # -*- HTTP Configuration
    http_enabled: bool = False
    http_routes: Optional[List[dict]] = None
    http_container_port: int = 80
    http_service_port: int = 80
    http_node_port: Optional[int] = None
    http_key: str = "http"
    http_ingress_name: str = "http-ingress"
    forward_http_to_https: bool = False
    enable_http_proxy_protocol: bool = False
    enable_http_forward_headers: bool = False

    # -*- HTTPS Configuration
    https_enabled: bool = False
    https_routes: Optional[List[dict]] = None
    https_container_port: int = 443
    https_service_port: int = 443
    https_node_port: Optional[int] = None
    https_key: str = "https"
    https_ingress_name: str = "https-ingress"
    enable_https_proxy_protocol: bool = False
    enable_https_forward_headers: bool = False
    add_headers: Optional[Dict[str, dict]] = None

    # -*- Dashboard Configuration
    dashboard_enabled: bool = False
    dashboard_routes: Optional[List[dict]] = None
    dashboard_container_port: int = 8080
    dashboard_service_port: int = 8080
    dashboard_node_port: Optional[int] = None
    dashboard_key: str = "dashboard"
    dashboard_ingress_name: str = "dashboard-ingress"
    # The dashboard is gated behind a user:password, which is generated using
    #   htpasswd -nb user password
    # You can provide the "users:password" list as a dashboard_auth_users param
    # or as DASHBOARD_AUTH_USERS in the secrets_file
    # Using the secrets_file is recommended
    dashboard_auth_users: Optional[str] = None
    insecure_api_access: bool = False

    # -*- Service Configuration
    create_service: bool = True

    def get_dashboard_auth_users(self) -> Optional[str]:
        return self.dashboard_auth_users or self.get_secret_from_file("DASHBOARD_AUTH_USERS")

    def get_ingress_rules(self) -> List[Any]:
        from kubernetes.client.models.v1_ingress_rule import V1IngressRule
        from kubernetes.client.models.v1_ingress_backend import V1IngressBackend
        from kubernetes.client.models.v1_ingress_service_backend import V1IngressServiceBackend
        from kubernetes.client.models.v1_http_ingress_path import V1HTTPIngressPath
        from kubernetes.client.models.v1_http_ingress_rule_value import V1HTTPIngressRuleValue
        from kubernetes.client.models.v1_service_port import V1ServicePort

        ingress_rules = [
            V1IngressRule(
                http=V1HTTPIngressRuleValue(
                    paths=[
                        V1HTTPIngressPath(
                            path="/",
                            path_type="Prefix",
                            backend=V1IngressBackend(
                                service=V1IngressServiceBackend(
                                    name=self.get_service_name(),
                                    port=V1ServicePort(
                                        name=self.https_key if self.https_enabled else self.http_key,
                                        port=self.https_service_port if self.https_enabled else self.http_service_port,
                                    ),
                                )
                            ),
                        ),
                    ]
                ),
            )
        ]
        if self.dashboard_enabled:
            ingress_rules[0].http.paths.append(
                V1HTTPIngressPath(
                    path="/",
                    path_type="Prefix",
                    backend=V1IngressBackend(
                        service=V1IngressServiceBackend(
                            name=self.get_service_name(),
                            port=V1ServicePort(
                                name=self.dashboard_key,
                                port=self.dashboard_service_port,
                            ),
                        )
                    ),
                )
            )
        return ingress_rules

    def get_cr_policy_rules(self) -> List[Any]:
        from phi.k8s.create.rbac_authorization_k8s_io.v1.cluster_role import (
            PolicyRule,
        )

        return [
            PolicyRule(
                api_groups=[""],
                resources=["services", "endpoints", "secrets"],
                verbs=["get", "list", "watch"],
            ),
            PolicyRule(
                api_groups=["extensions", "networking.k8s.io"],
                resources=["ingresses", "ingressclasses"],
                verbs=["get", "list", "watch"],
            ),
            PolicyRule(
                api_groups=["extensions", "networking.k8s.io"],
                resources=["ingresses/status"],
                verbs=["update"],
            ),
            PolicyRule(
                api_groups=["traefik.io", "traefik.containo.us"],
                resources=[
                    "middlewares",
                    "middlewaretcps",
                    "ingressroutes",
                    "traefikservices",
                    "ingressroutetcps",
                    "ingressrouteudps",
                    "tlsoptions",
                    "tlsstores",
                    "serverstransports",
                ],
                verbs=["get", "list", "watch"],
            ),
        ]

    def get_container_args(self) -> Optional[List[str]]:
        if self.command is not None:
            if isinstance(self.command, str):
                return self.command.strip().split(" ")
            return self.command

        container_args = ["--providers.kubernetescrd"]

        if self.access_logs:
            container_args.append("--accesslog")

        if self.http_enabled:
            container_args.append(f"--entrypoints.{self.http_key}.Address=:{self.http_service_port}")
            if self.enable_http_proxy_protocol:
                container_args.append(f"--entrypoints.{self.http_key}.proxyProtocol.insecure=true")
            if self.enable_http_forward_headers:
                container_args.append(f"--entrypoints.{self.http_key}.forwardedHeaders.insecure=true")

        if self.https_enabled:
            container_args.append(f"--entrypoints.{self.https_key}.Address=:{self.https_service_port}")
            if self.enable_https_proxy_protocol:
                container_args.append(f"--entrypoints.{self.https_key}.proxyProtocol.insecure=true")
            if self.enable_https_forward_headers:
                container_args.append(f"--entrypoints.{self.https_key}.forwardedHeaders.insecure=true")
            if self.forward_http_to_https:
                container_args.extend(
                    [
                        f"--entrypoints.{self.http_key}.http.redirections.entryPoint.to={self.https_key}",
                        f"--entrypoints.{self.http_key}.http.redirections.entryPoint.scheme=https",
                    ]
                )

        if self.dashboard_enabled:
            container_args.append("--api=true")
            container_args.append("--api.dashboard=true")
            if self.insecure_api_access:
                container_args.append("--api.insecure")

        return container_args

    def get_secrets(self) -> List[Any]:
        return self.add_secrets or []

    def get_ports(self) -> List[Any]:
        from phi.k8s.create.common.port import CreatePort

        ports: List[CreatePort] = self.add_ports or []

        if self.http_enabled:
            web_port = CreatePort(
                name=self.http_key,
                container_port=self.http_container_port,
                service_port=self.http_service_port,
                target_port=self.http_key,
            )
            if (
                self.service_type in (ServiceType.NODE_PORT, ServiceType.LOAD_BALANCER)
                and self.http_node_port is not None
            ):
                web_port.node_port = self.http_node_port
            ports.append(web_port)

        if self.https_enabled:
            websecure_port = CreatePort(
                name=self.https_key,
                container_port=self.https_container_port,
                service_port=self.https_service_port,
                target_port=self.https_key,
            )
            if (
                self.service_type in (ServiceType.NODE_PORT, ServiceType.LOAD_BALANCER)
                and self.https_node_port is not None
            ):
                websecure_port.node_port = self.https_node_port
            ports.append(websecure_port)

        if self.dashboard_enabled:
            dashboard_port = CreatePort(
                name=self.dashboard_key,
                container_port=self.dashboard_container_port,
                service_port=self.dashboard_service_port,
                target_port=self.dashboard_key,
            )
            if (
                self.service_type in (ServiceType.NODE_PORT, ServiceType.LOAD_BALANCER)
                and self.dashboard_node_port is not None
            ):
                dashboard_port.node_port = self.dashboard_node_port
            ports.append(dashboard_port)

        return ports

    def add_app_resources(self, namespace: str, service_account_name: Optional[str]) -> List[Any]:
        from phi.k8s.create.apiextensions_k8s_io.v1.custom_object import CreateCustomObject

        app_resources = self.add_resources or []

        if self.http_enabled:
            http_ingressroute = CreateCustomObject(
                name=self.http_ingress_name,
                crd=ingressroute_crd,
                spec={
                    "entryPoints": [self.http_key],
                    "routes": self.http_routes,
                },
                app_name=self.get_app_name(),
                namespace=namespace,
            )
            app_resources.append(http_ingressroute)
            logger.debug(f"Added IngressRoute: {http_ingressroute.name}")

        if self.https_enabled:
            https_ingressroute = CreateCustomObject(
                name=self.https_ingress_name,
                crd=ingressroute_crd,
                spec={
                    "entryPoints": [self.https_key],
                    "routes": self.https_routes,
                },
                app_name=self.get_app_name(),
                namespace=namespace,
            )
            app_resources.append(https_ingressroute)
            logger.debug(f"Added IngressRoute: {https_ingressroute.name}")

        if self.add_headers:
            headers_middleware = CreateCustomObject(
                name="header-middleware",
                crd=middleware_crd,
                spec={
                    "headers": self.add_headers,
                },
                app_name=self.get_app_name(),
                namespace=namespace,
            )
            app_resources.append(headers_middleware)
            logger.debug(f"Added Middleware: {headers_middleware.name}")

        if self.dashboard_enabled:
            # create dashboard_auth_middleware if auth provided
            # ref: https://doc.traefik.io/traefik/operations/api/#configuration
            dashboard_auth_middleware = None
            dashboard_auth_users = self.get_dashboard_auth_users()
            if dashboard_auth_users is not None:
                from phi.k8s.create.core.v1.secret import CreateSecret

                dashboard_auth_secret = CreateSecret(
                    secret_name="dashboard-auth-secret",
                    app_name=self.get_app_name(),
                    namespace=namespace,
                    string_data={"users": dashboard_auth_users},
                )
                app_resources.append(dashboard_auth_secret)
                logger.debug(f"Added Secret: {dashboard_auth_secret.secret_name}")

                dashboard_auth_middleware = CreateCustomObject(
                    name="dashboard-auth-middleware",
                    crd=middleware_crd,
                    spec={"basicAuth": {"secret": dashboard_auth_secret.secret_name}},
                    app_name=self.get_app_name(),
                    namespace=namespace,
                )
                app_resources.append(dashboard_auth_middleware)
                logger.debug(f"Added Middleware: {dashboard_auth_middleware.name}")

            dashboard_routes = self.dashboard_routes
            # use default dashboard routes
            if dashboard_routes is None:
                # domain must be provided
                if self.domain_name is not None:
                    dashboard_routes = [
                        {
                            "kind": "Rule",
                            "match": f"Host(`traefik.{self.domain_name}`)",
                            "middlewares": [
                                {
                                    "name": dashboard_auth_middleware.name,
                                    "namespace": namespace,
                                },
                            ]
                            if dashboard_auth_middleware is not None
                            else [],
                            "services": [
                                {
                                    "kind": "TraefikService",
                                    "name": "api@internal",
                                }
                            ],
                        },
                    ]

            dashboard_ingressroute = CreateCustomObject(
                name=self.dashboard_ingress_name,
                crd=ingressroute_crd,
                spec={
                    "routes": dashboard_routes,
                },
                app_name=self.get_app_name(),
                namespace=namespace,
            )
            app_resources.append(dashboard_ingressroute)
            logger.debug(f"Added IngressRoute: {dashboard_ingressroute.name}")

        if self.install_crds:
            from phi.k8s.resource.yaml import YamlResource

            if self.yaml_resources is None:
                self.yaml_resources = []
            self.yaml_resources.append(
                YamlResource(
                    name="traefik-crds",
                    url="https://raw.githubusercontent.com/traefik/traefik/v2.10/docs/content/reference/dynamic-configuration/kubernetes-crd-definition-v1.yml",
                )
            )
            logger.debug("Added CRD yaml")

        return app_resources
