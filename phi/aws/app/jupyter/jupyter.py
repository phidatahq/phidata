from typing import Optional, Union, List, Dict

from phi.aws.app.base import AwsApp, ContainerContext, AwsBuildContext  # noqa: F401


class Jupyter(AwsApp):
    # -*- App Name
    name: str = "jupyter"

    # -*- Image Configuration
    image_name: str = "phidata/jupyter"
    image_tag: str = "4.0.5"
    command: Optional[Union[str, List[str]]] = "jupyter lab"

    # -*- App Ports
    # Open a container port if open_port=True
    open_port: bool = True
    # Port number on the container
    container_port: int = 8888

    # -*- Workspace Configuration
    # Path to the workspace directory inside the container
    workspace_dir_container_path: str = "/jupyter"

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

    def get_container_env(self, container_context: ContainerContext, build_context: AwsBuildContext) -> Dict[str, str]:
        container_env: Dict[str, str] = super().get_container_env(
            container_context=container_context, build_context=build_context
        )

        if self.jupyter_config_file is not None:
            container_env["JUPYTER_CONFIG_FILE"] = self.jupyter_config_file

        return container_env

    def get_container_command(self) -> Optional[List[str]]:
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
            container_context: Optional[ContainerContext] = self.get_container_context()
            if container_context is not None and container_context.workspace_root is not None:
                container_cmd.append(f"--notebook-dir={str(container_context.workspace_root)}")
        else:
            container_cmd.append(f"--notebook-dir={str(self.notebook_dir)}")
        return container_cmd
