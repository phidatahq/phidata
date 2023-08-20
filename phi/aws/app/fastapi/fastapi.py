from typing import Optional, Union, List, Dict, Any

from pydantic import field_validator, Field
from pydantic_core.core_schema import FieldValidationInfo


from phi.aws.app.base import AwsApp, WorkspaceVolumeType, ContainerContext  # noqa: F401


class FastApi(AwsApp):
    # -*- App Name
    name: str = "fastapi"

    # -*- Image Configuration
    image_name: str = "phidata/fastapi"
    image_tag: str = "0.96"
    command: Optional[Union[str, List[str]]] = "uvicorn main:app --reload --host 0.0.0.0 --port 9090"

    # -*- App Ports
    # Open a container port if open_port=True
    open_port: bool = True
    port_number: int = 8000

    # -*- ECS Configuration
    ecs_task_cpu: str = "1024"
    ecs_task_memory: str = "2048"
    ecs_service_count: int = 1
    assign_public_ip: Optional[bool] = True

    # -*- Uvicorn Configuration
    uvicorn_host: str = "0.0.0.0"
    # Defaults to the port_number
    uvicorn_port: Optional[int] = None
    uvicorn_reload: Optional[bool] = None
    uvicorn_log_level: Optional[str] = None
    web_concurrency: Optional[int] = None

    # Set validate_default=True so set_container_env is always called
    container_env: Optional[Dict[str, Any]] = Field(None, validate_default=True)

    @field_validator("container_env", mode="before")
    def set_container_env(cls, v, info: FieldValidationInfo):
        v = v or {}

        uvicorn_host = info.data.get("uvicorn_host")
        if uvicorn_host is not None:
            v["UVICORN_HOST"] = uvicorn_host

        uvicorn_port = info.data.get("uvicorn_port")
        if uvicorn_port is None:
            port_number = info.data.get("port_number")
            if port_number is not None:
                uvicorn_port = port_number
        if uvicorn_port is not None:
            v["UVICORN_PORT"] = uvicorn_port

        uvicorn_reload = info.data.get("uvicorn_reload")
        if uvicorn_reload is not None:
            v["UVICORN_RELOAD"] = uvicorn_reload

        uvicorn_log_level = info.data.get("uvicorn_log_level")
        if uvicorn_log_level is not None:
            v["UVICORN_LOG_LEVEL"] = uvicorn_log_level

        web_concurrency = info.data.get("web_concurrency")
        if web_concurrency is not None:
            v["WEB_CONCURRENCY"] = web_concurrency
        return v
