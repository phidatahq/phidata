from phidata.app.group import AppGroup
from phidata.app.traefik import IngressRoute, ServiceType, LoadBalancerProvider

from workspace.prd.aws_resources import (
    prd_acm_certificate,  # noqa: F401
    services_ng_label,
    topology_spread_key,
    topology_spread_max_skew,
    topology_spread_when_unsatisfiable,
)
from workspace.prd.airflow.k8s_apps import prd_airflow_flower, prd_airflow_ws
from workspace.prd.jupyter.jupyter_lab import prd_jupyter
from workspace.prd.superset.k8s_apps import prd_superset_ws
from workspace.k8s.whoami import whoami_port, whoami_service
from workspace.settings import ws_settings

#
# -*- Traefik Kubernetes resources
#
# Traefik Ingress: For routing web requests within the EKS cluster
routes = [
    {
        "match": f"Host(`whoami.{ws_settings.prd_domain}`)",
        "kind": "Rule",
        "services": [
            {
                "name": whoami_service.service_name,
                "port": whoami_port.service_port,
            }
        ],
    },
]

if ws_settings.prd_airflow_enabled:
    routes.append(
        {
            "match": f"Host(`airflow.{ws_settings.prd_domain}`)",
            "kind": "Rule",
            "services": [
                {
                    "name": prd_airflow_ws.get_ws_service_name(),
                    "port": prd_airflow_ws.get_ws_service_port(),
                }
            ],
        }
    )
    routes.append(
        {
            "match": f"Host(`flower.{ws_settings.prd_domain}`)",
            "kind": "Rule",
            "services": [
                {
                    "name": prd_airflow_flower.get_flower_service_name(),
                    "port": prd_airflow_flower.get_flower_service_port(),
                }
            ],
        }
    )

if ws_settings.prd_superset_enabled:
    routes.append(
        {
            "match": f"Host(`superset.{ws_settings.prd_domain}`)",
            "kind": "Rule",
            "services": [
                {
                    "name": prd_superset_ws.get_app_service_name(),
                    "port": prd_superset_ws.get_app_service_port(),
                }
            ],
        }
    )

if ws_settings.prd_jupyter_enabled:
    routes.append(
        {
            "match": f"Host(`jupyter.{ws_settings.prd_domain}`)",
            "kind": "Rule",
            "services": [
                {
                    "name": prd_jupyter.get_app_service_name(),
                    "port": prd_jupyter.get_app_service_port(),
                }
            ],
        }
    )

traefik_ingress_route = IngressRoute(
    replicas=3,
    name="traefik",
    web_enabled=True,
    web_routes=routes,
    # -*-
    # Uncomment the following lines to enable HTTPS
    # Use ACM certificate to enable HTTPS
    # websecure_enabled=True,
    # websecure_routes=routes,
    # forward_web_to_websecure=True,
    # Read ACM certificate from a summary file and add the certificate ARN to the service_annotations
    # acm_certificate_summary_file=prd_acm_certificate.certificate_summary_file,
    # -*-
    # Use a LoadBalancer service
    service_type=ServiceType.LOAD_BALANCER,
    # Use AWS LoadBalancer
    load_balancer_provider=LoadBalancerProvider.AWS,
    # Uncomment to use an internal LoadBalancer
    # load_balancer_scheme="internal",
    # Uncomment to use custom subnets for the LoadBalancer
    # load_balancer_subnets=ws_settings.subnet_ids,
    # Use a Network LoadBalancer
    use_nlb=True,
    # Enable traefik dashboard
    dashboard_enabled=True,
    # Serve traefik dashboard at traefik.prd_domain
    domain_name=ws_settings.prd_domain,
    # The dashboard is gated behind a user:password, which is generated using the cmd:
    #   htpasswd -nb user password
    # You can provide the "users:password" list as DASHBOARD_AUTH_USERS in the secrets_file
    secrets_file=ws_settings.ws_root.joinpath(
        "workspace/secrets/prd_traefik_secrets.yml"
    ),
    use_cache=ws_settings.use_cache,
    pod_node_selector=services_ng_label,
    topology_spread_key=topology_spread_key,
    topology_spread_max_skew=topology_spread_max_skew,
    topology_spread_when_unsatisfiable=topology_spread_when_unsatisfiable,
)

prd_traefik_apps = AppGroup(
    name="traefik",
    enabled=ws_settings.prd_traefik_enabled,
    apps=[traefik_ingress_route],
)
