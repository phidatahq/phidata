from typing import Optional, Union, List, Dict

from phi.k8s.app.base import (
    K8sApp,
    AppVolumeType,  # noqa: F401
    ContainerContext,
    ServiceType,  # noqa: F401
    RestartPolicy,  # noqa: F401
    ImagePullPolicy,  # noqa: F401
)


class FastApi(K8sApp):
    # -*- App Name
    name: str = "fastapi"

    # -*- Image Configuration
    image_name: str = "phidata/fastapi"
    image_tag: str = "0.104"
    command: Optional[Union[str, List[str]]] = "uvicorn main:app --reload"

    # -*- App Ports
    # Open a container port if open_port=True
    open_port: bool = True
    port_number: int = 8000

    # -*- Workspace Configuration
    # Path to the workspace directory inside the container
    workspace_dir_container_path: str = "/usr/local/app"

    # -*- Service Configuration
    create_service: bool = True
    # The port exposed by the service
    service_port: int = 8000

    # -*- Uvicorn Configuration
    uvicorn_host: str = "0.0.0.0"
    # Defaults to the port_number
    uvicorn_port: Optional[int] = None
    uvicorn_reload: Optional[bool] = None
    uvicorn_log_level: Optional[str] = None
    web_concurrency: Optional[int] = None

    def get_container_env(self, container_context: ContainerContext) -> Dict[str, str]:
        container_env: Dict[str, str] = super().get_container_env(container_context=container_context)

        if self.uvicorn_host is not None:
            container_env["UVICORN_HOST"] = self.uvicorn_host

        uvicorn_port = self.uvicorn_port
        if uvicorn_port is None:
            if self.port_number is not None:
                uvicorn_port = self.port_number
        if uvicorn_port is not None:
            container_env["UVICORN_PORT"] = str(uvicorn_port)

        if self.uvicorn_reload is not None:
            container_env["UVICORN_RELOAD"] = str(self.uvicorn_reload)

        if self.uvicorn_log_level is not None:
            container_env["UVICORN_LOG_LEVEL"] = self.uvicorn_log_level

        if self.web_concurrency is not None:
            container_env["WEB_CONCURRENCY"] = str(self.web_concurrency)

        return container_env
