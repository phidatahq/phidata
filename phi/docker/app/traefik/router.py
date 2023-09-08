from typing import Optional, Union, List

from phi.docker.app.base import DockerApp, ContainerContext  # noqa: F401


class TraefikRouter(DockerApp):
    # -*- App Name
    name: str = "traefik"

    # -*- Image Configuration
    image_name: str = "traefik"
    image_tag: str = "v2.10"
    command: Optional[Union[str, List[str]]] = "uvicorn main:app --reload"

    # -*- App Ports
    # Open a container port if open_port=True
    open_port: bool = True
    port_number: int = 8000

    # -*- Traefik Configuration
    # Enable Access Logs
    access_logs: bool = True
    # Traefik config file on the host
    traefik_config_file: Optional[str] = None
    # Traefik config file on the container
    traefik_config_file_container_path: str = "/etc/traefik/traefik.yaml"

    # -*- Dashboard Configuration
    dashboard_key: str = "dashboard"
    dashboard_enabled: bool = False
    dashboard_routes: Optional[List[dict]] = None
    dashboard_container_port: int = 8080
    # The dashboard is gated behind a user:password, which is generated using
    #   htpasswd -nb user password
    # You can provide the "users:password" list as a dashboard_auth_users param
    # or as DASHBOARD_AUTH_USERS in the secrets_file
    # Using the secrets_file is recommended
    dashboard_auth_users: Optional[str] = None
    insecure_api_access: bool = False

    def get_dashboard_auth_users(self) -> Optional[str]:
        return self.dashboard_auth_users or self.get_secret_from_file("DASHBOARD_AUTH_USERS")
