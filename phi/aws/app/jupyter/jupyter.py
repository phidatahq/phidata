from typing import Optional, Union, List, Dict, Any

from pydantic import field_validator, Field
from pydantic_core.core_schema import FieldValidationInfo

from phi.aws.app.base import AwsApp, WorkspaceVolumeType, AppVolumeType, ContainerContext  # noqa: F401


class Jupyter(AwsApp):
    # -*- App Name
    name: str = "jupyter"

    # -*- Image Configuration
    image_name: str = "phidata/jupyter"
    image_tag: str = "3.6.3"
    command: Optional[Union[str, List[str]]] = "jupyter lab"

    # -*- App Ports
    # Open a container port if open_container_port=True
    open_container_port: bool = True
    # Port number on the container
    container_port: int = 8888

    # -*- ECS Configuration
    ecs_task_cpu: str = "1024"
    ecs_task_memory: str = "2048"
    ecs_service_count: int = 1
    assign_public_ip: Optional[bool] = True

    # -*- Jupyter Configuration
    # Absolute path to JUPYTER_CONFIG_FILE
    # Used to set the JUPYTER_CONFIG_FILE env var and is added to the command using `--config`
    # Defaults to /resources/jupyter_lab_config.py which is added in the "phidata/jupyter" image
    jupyter_config_file: str = "/resources/jupyter_lab_config.py"
    # Absolute path to the notebook directory,
    # Defaults to the workspace_root if mount_workspace = True else "/",
    notebook_dir: Optional[str] = None

    # Set validate_default=True so update_container_env is always called
    container_env: Optional[Dict[str, Any]] = Field(None, validate_default=True)

    @field_validator("container_env", mode="before")
    def update_container_env(cls, v, info: FieldValidationInfo):
        jupyter_config_file = info.data.get("jupyter_config_file", None)
        if jupyter_config_file is not None:
            v = v or {}
            v["JUPYTER_CONFIG_FILE"] = jupyter_config_file

        return v

    def build_container_command_docker(self) -> Optional[List[str]]:
        container_cmd: List[str]
        if isinstance(self.command, str):
            container_cmd = self.command.split(" ")
        elif isinstance(self.command, list):
            container_cmd = self.command
        else:
            container_cmd = ["jupyter", "lab"]

        if self.jupyter_config_file is not None:
            container_cmd.append(f"--config={str(self.jupyter_config_file)}")

        if self.notebook_dir is None:
            if self.mount_workspace:
                container_context: Optional[ContainerContext] = self.build_container_context()
                if container_context is not None and container_context.workspace_root is not None:
                    container_cmd.append(f"--notebook-dir={str(container_context.workspace_root)}")
            else:
                container_cmd.append("--notebook-dir=/")
        else:
            container_cmd.append(f"--notebook-dir={str(self.notebook_dir)}")
        return container_cmd
