from typing import Optional, Union, List, Dict, Any

from pydantic import field_validator, Field
from pydantic_core.core_schema import FieldValidationInfo

from phi.aws.app.base import AwsApp, WorkspaceVolumeType, ContainerContext  # noqa: F401


class Streamlit(AwsApp):
    # -*- App Name
    name: str = "streamlit"

    # -*- Image Configuration
    image_name: str = "phidata/streamlit"
    image_tag: str = "1.23"
    command: Optional[Union[str, List[str]]] = "streamlit hello"

    # -*- App Ports
    # Open a container port if open_port=True
    open_port: bool = True
    port_number: int = 8501

    # -*- ECS Configuration
    ecs_task_cpu: str = "1024"
    ecs_task_memory: str = "2048"
    ecs_service_count: int = 1
    assign_public_ip: Optional[bool] = True

    # -*- Streamlit Configuration
    # Server settings
    # Defaults to the port_number
    streamlit_server_port: Optional[int] = None
    streamlit_server_headless: bool = True
    streamlit_server_run_on_save: Optional[bool] = None
    streamlit_server_max_upload_size: Optional[bool] = None
    # Browser settings
    streamlit_browser_gather_usage_stats: Optional[bool] = None
    streamlit_browser_server_port: Optional[str] = None
    streamlit_browser_server_address: Optional[str] = None

    # Set validate_default=True so set_container_env is always called
    container_env: Optional[Dict[str, Any]] = Field(None, validate_default=True)

    @field_validator("container_env", mode="before")
    def set_container_env(cls, v, info: FieldValidationInfo):
        v = v or {}

        streamlit_server_port = info.data.get("streamlit_server_port")
        if streamlit_server_port is None:
            port_number = info.data.get("port_number")
            if port_number is not None:
                streamlit_server_port = port_number
        if streamlit_server_port is not None:
            v["STREAMLIT_SERVER_PORT"] = streamlit_server_port

        streamlit_server_headless = info.data.get("streamlit_server_headless")
        if streamlit_server_headless is not None:
            v["STREAMLIT_SERVER_HEADLESS"] = streamlit_server_headless

        streamlit_server_run_on_save = info.data.get("streamlit_server_run_on_save")
        if streamlit_server_run_on_save is not None:
            v["STREAMLIT_SERVER_RUN_ON_SAVE"] = streamlit_server_run_on_save

        streamlit_server_max_upload_size = info.data.get("streamlit_server_max_upload_size")
        if streamlit_server_max_upload_size is not None:
            v["STREAMLIT_SERVER_MAX_UPLOAD_SIZE"] = streamlit_server_max_upload_size

        streamlit_browser_gather_usage_stats = info.data.get("streamlit_browser_gather_usage_stats")
        if streamlit_browser_gather_usage_stats is not None:
            v["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = streamlit_browser_gather_usage_stats

        streamlit_browser_server_port = info.data.get("streamlit_browser_server_port")
        if streamlit_browser_server_port is not None:
            v["STREAMLIT_BROWSER_SERVER_PORT"] = streamlit_browser_server_port

        streamlit_browser_server_address = info.data.get("streamlit_browser_server_address")
        if streamlit_browser_server_address is not None:
            v["STREAMLIT_BROWSER_SERVER_ADDRESS"] = streamlit_browser_server_address

        return v
