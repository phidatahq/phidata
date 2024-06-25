from typing import Optional, Dict, List, Any, Union

from phi.k8s.app.base import (
    K8sApp,
    AppVolumeType,
    ContainerContext,
    ServiceType,  # noqa: F401
    RestartPolicy,  # noqa: F401
    ImagePullPolicy,  # noqa: F401
)


class Jupyter(K8sApp):
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

    # -*- Service Configuration
    create_service: bool = True

    # -*- Workspace Configuration
    # Path to the parent directory of the workspace inside the container
    # When using git-sync, the git repo is cloned inside this directory
    #   i.e. this is the parent directory of the workspace
    workspace_parent_dir_container_path: str = "/usr/local/workspace"

    # -*- Jupyter Configuration
    # Absolute path to JUPYTER_CONFIG_FILE
    # Used to set the JUPYTER_CONFIG_FILE env var and is added to the command using `--config`
    # Defaults to /jupyter_lab_config.py which is added in the "phidata/jupyter" image
    jupyter_config_file: str = "/jupyter_lab_config.py"
    # Absolute path to the notebook directory
    notebook_dir: Optional[str] = None

    # -*- Jupyter Volume
    # Create a volume for jupyter storage
    create_volume: bool = True
    volume_type: AppVolumeType = AppVolumeType.EmptyDir
    # Path to mount the volume inside the container
    # should be the parent directory of pgdata defined above
    volume_container_path: str = "/mnt"
    # -*- If volume_type is AwsEbs
    ebs_volume: Optional[Any] = None
    # Add NodeSelectors to Pods, so they are scheduled in the same region and zone as the ebs_volume
    schedule_pods_in_ebs_topology: bool = True

    def get_container_env(self, container_context: ContainerContext) -> Dict[str, str]:
        container_env: Dict[str, str] = super().get_container_env(container_context=container_context)

        if self.jupyter_config_file is not None:
            container_env["JUPYTER_CONFIG_FILE"] = self.jupyter_config_file

        return container_env

    def get_container_args(self) -> Optional[List[str]]:
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
