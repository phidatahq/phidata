from typing import Optional, Union, List, Dict

from phi.docker.app.base import DockerApp, ContainerContext  # noqa: F401


class Jupyter(DockerApp):
    # -*- App Name
    name: str = "jupyter"

    # -*- Image Configuration
    image_name: str = "phidata/jupyter"
    image_tag: str = "4.0.5"
    command: Optional[Union[str, List[str]]] = "jupyter lab"

    # -*- App Ports
    # Open a container port if open_port=True
    open_port: bool = True
    port_number: int = 8888

    # -*- Workspace Configuration
    # Path to the workspace directory inside the container
    workspace_dir_container_path: str = "/jupyter"
    # Mount the workspace directory from host machine to the container
    mount_workspace: bool = False

    # -*- Resources Volume
    # Mount a read-only directory from host machine to the container
    mount_resources: bool = False
    # Resources directory relative to the workspace_root
    resources_dir: str = "workspace/jupyter/resources"

    # -*- Jupyter Configuration
    # Absolute path to JUPYTER_CONFIG_FILE
    # Used to set the JUPYTER_CONFIG_FILE env var and is added to the command using `--config`
    # Defaults to /jupyter_lab_config.py which is added in the "phidata/jupyter" image
    jupyter_config_file: str = "/jupyter_lab_config.py"
    # Absolute path to the notebook directory
    # Defaults to the workspace_root if mount_workspace = True else "/"
    notebook_dir: Optional[str] = None

    def get_container_env(self, container_context: ContainerContext) -> Dict[str, str]:
        container_env: Dict[str, str] = super().get_container_env(container_context=container_context)

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
            if self.mount_workspace:
                container_context: Optional[ContainerContext] = self.get_container_context()
                if container_context is not None and container_context.workspace_root is not None:
                    container_cmd.append(f"--notebook-dir={str(container_context.workspace_root)}")
            else:
                container_cmd.append("--notebook-dir=/")
        else:
            container_cmd.append(f"--notebook-dir={str(self.notebook_dir)}")
        return container_cmd
