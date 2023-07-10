from typing import Optional, Dict, Any, Union, List

from phi.infra.app.base import InfraApp, WorkspaceVolumeType, AppVolumeType  # noqa: F401
from phi.infra.app.context import ContainerContext
from phi.docker.app.context import DockerBuildContext
from phi.utils.log import logger


class DockerApp(InfraApp):
    # -*- App Volume
    # Create a volume for container storage
    create_volume: bool = False
    # If volume_host_path is provided, mount this directory relative to the workspace_root
    # from host machine to container
    volume_dir: Optional[str] = None
    # Otherwise, mount a volume named volume_name to the container
    # If volume_name is not provided, use {app-name}-volume
    volume_name: Optional[str] = None
    # Path to mount the volume inside the container
    volume_container_path: str = "/mnt/app"

    # -*- Resources Volume
    # Mount a read-only directory from host machine to the container
    mount_resources: bool = False
    # Resources directory relative to the workspace_root
    resources_dir: str = "workspace/resources"
    # Path to mount the resources_dir
    resources_dir_container_path: str = "/mnt/resources"

    # -*- Container Configuration
    container_name: Optional[str] = None
    container_labels: Optional[Dict[str, str]] = None
    # Run container in the background and return a Container object
    container_detach: bool = True
    # Enable auto-removal of the container on daemon side when the container’s process exits
    container_auto_remove: bool = True
    # Remove the container when it has finished running. Default: True
    container_remove: bool = True
    # Username or UID to run commands as inside the container
    container_user: Optional[Union[str, int]] = None
    # Keep STDIN open even if not attached
    container_stdin_open: bool = True
    # Return logs from STDOUT when container_detach=False
    container_stdout: Optional[bool] = True
    # Return logs from STDERR when container_detach=False
    container_stderr: Optional[bool] = True
    container_tty: bool = True
    # Specify a test to perform to check that the container is healthy
    container_healthcheck: Optional[Dict[str, Any]] = None
    # Optional hostname for the container
    container_hostname: Optional[str] = None
    # Platform in the format os[/arch[/variant]]
    container_platform: Optional[str] = None
    # Path to the working directory
    container_working_dir: Optional[str] = None
    # Restart the container when it exits. Configured as a dictionary with keys:
    # Name: One of on-failure, or always.
    # MaximumRetryCount: Number of times to restart the container on failure.
    # For example: {"Name": "on-failure", "MaximumRetryCount": 5}
    container_restart_policy: Optional[Dict[str, Any]] = None
    # Add volumes to DockerContainer
    # container_volumes is a dictionary which adds the volumes to mount
    # inside the container. The key is either the host path or a volume name,
    # and the value is a dictionary with 2 keys:
    #   bind - The path to mount the volume inside the container
    #   mode - Either rw to mount the volume read/write, or ro to mount it read-only.
    # For example:
    # {
    #   '/home/user1/': {'bind': '/mnt/vol2', 'mode': 'rw'},
    #   '/var/www': {'bind': '/mnt/vol1', 'mode': 'ro'}
    # }
    container_volumes: Optional[Dict[str, dict]] = None
    # Add ports to DockerContainer
    # The keys of the dictionary are the ports to bind inside the container,
    # either as an integer or a string in the form port/protocol, where the protocol is either tcp, udp.
    # The values of the dictionary are the corresponding ports to open on the host, which can be either:
    #   - The port number, as an integer.
    #     For example, {'2222/tcp': 3333} will expose port 2222 inside the container as port 3333 on the host.
    #   - None, to assign a random host port. For example, {'2222/tcp': None}.
    #   - A tuple of (address, port) if you want to specify the host interface.
    #     For example, {'1111/tcp': ('127.0.0.1', 1111)}.
    #   - A list of integers, if you want to bind multiple host ports to a single container port.
    #     For example, {'1111/tcp': [1234, 4567]}.
    container_ports: Optional[Dict[str, Any]] = None

    def get_container_name(self):
        return self.container_name or self.get_app_name()

    def build_container_env_docker(self, container_context: ContainerContext) -> Dict[str, str]:
        from phi.constants import (
            PYTHONPATH_ENV_VAR,
            PHI_RUNTIME_ENV_VAR,
            SCRIPTS_DIR_ENV_VAR,
            STORAGE_DIR_ENV_VAR,
            WORKFLOWS_DIR_ENV_VAR,
            WORKSPACE_ROOT_ENV_VAR,
            WORKSPACE_DIR_ENV_VAR,
            REQUIREMENTS_FILE_PATH_ENV_VAR,
        )

        # Container Environment
        container_env: Dict[str, str] = self.container_env or {}
        container_env.update(
            {
                PHI_RUNTIME_ENV_VAR: "docker",
                SCRIPTS_DIR_ENV_VAR: container_context.scripts_dir or "",
                STORAGE_DIR_ENV_VAR: container_context.storage_dir or "",
                WORKFLOWS_DIR_ENV_VAR: container_context.workflows_dir or "",
                WORKSPACE_DIR_ENV_VAR: container_context.workspace_dir or "",
                WORKSPACE_ROOT_ENV_VAR: container_context.workspace_root or "",
                "INSTALL_REQUIREMENTS": str(self.install_requirements),
                REQUIREMENTS_FILE_PATH_ENV_VAR: container_context.requirements_file or "",
                "MOUNT_WORKSPACE": str(self.mount_workspace),
                "MOUNT_RESOURCES": str(self.mount_resources),
                "RESOURCES_DIR_CONTAINER_PATH": str(self.resources_dir_container_path),
                "PRINT_ENV_ON_LOAD": str(self.print_env_on_load),
            }
        )

        if self.set_python_path:
            python_path = self.python_path
            if python_path is None:
                python_path = container_context.workspace_root
                if self.mount_resources and self.resources_dir_container_path is not None:
                    python_path = "{}:{}".format(python_path, self.resources_dir_container_path)
                if self.add_python_paths is not None:
                    python_path = "{}:{}".format(python_path, ":".join(self.add_python_paths))
            if python_path is not None:
                container_env[PYTHONPATH_ENV_VAR] = python_path

        # Set aws region and profile
        self.set_aws_env_vars(env_dict=container_env)

        # Update the container env using env_file
        env_data_from_file = self.get_env_file_data()
        if env_data_from_file is not None:
            container_env.update({k: str(v) for k, v in env_data_from_file.items() if v is not None})

        # Update the container env using secrets_file
        secret_data_from_file = self.get_secret_file_data()
        if secret_data_from_file is not None:
            container_env.update({k: str(v) for k, v in secret_data_from_file.items() if v is not None})

        # Update the container env with user provided env_vars
        # this overwrites any existing variables with the same key
        if self.env_vars is not None and isinstance(self.env_vars, dict):
            container_env.update({k: str(v) for k, v in self.env_vars.items() if v is not None})

        # logger.debug("Container Environment: {}".format(container_env))
        return container_env

    def build_container_volumes_docker(self, container_context: ContainerContext) -> Dict[str, dict]:
        from phi.utils.defaults import get_default_volume_name

        if self.workspace_root is None:
            logger.error("Invalid workspace_root")
            return {}

        # container_volumes is a dictionary which configures the volumes to mount
        # inside the container. The key is either the host path or a volume name,
        # and the value is a dictionary with 2 keys:
        #   bind - The path to mount the volume inside the container
        #   mode - Either rw to mount the volume read/write, or ro to mount it read-only.
        # For example:
        # {
        #   '/home/user1/': {'bind': '/mnt/vol2', 'mode': 'rw'},
        #   '/var/www': {'bind': '/mnt/vol1', 'mode': 'ro'}
        # }
        container_volumes = self.container_volumes or {}

        # Create Workspace Volume
        if self.mount_workspace:
            workspace_volume_container_path_str = container_context.workspace_root
            if self.workspace_volume_type is None or self.workspace_volume_type == WorkspaceVolumeType.HostPath:
                workspace_volume_host_path = str(self.workspace_root)
                logger.debug(f"Mounting: {workspace_volume_host_path}")
                logger.debug(f"      to: {workspace_volume_container_path_str}")
                container_volumes[workspace_volume_host_path] = {
                    "bind": workspace_volume_container_path_str,
                    "mode": "rw",
                }
            elif self.workspace_volume_type == WorkspaceVolumeType.EmptyDir:
                workspace_volume_name = self.workspace_volume_name
                if workspace_volume_name is None:
                    workspace_volume_name = get_default_volume_name(container_context.workspace_name or "ws")
                logger.debug(f"Mounting: {workspace_volume_name}")
                logger.debug(f"      to: {workspace_volume_container_path_str}")
                container_volumes[workspace_volume_name] = {
                    "bind": workspace_volume_container_path_str,
                    "mode": "rw",
                }
            else:
                logger.error(f"{self.workspace_volume_type.value} not supported")

        # Create App Volume
        if self.create_volume:
            volume_host = self.volume_name or get_default_volume_name(self.get_app_name())
            if self.volume_dir is not None:
                volume_host = str(self.workspace_root.joinpath(self.volume_dir))
            logger.debug(f"Mounting: {volume_host}")
            logger.debug(f"\tto: {self.volume_container_path}")
            container_volumes[volume_host] = {
                "bind": self.volume_container_path,
                "mode": "rw",
            }

        # Create Resources Volume
        if self.mount_resources:
            resources_dir_path = str(self.workspace_root.joinpath(self.resources_dir))
            logger.debug(f"Mounting: {resources_dir_path}")
            logger.debug(f"      to: {self.resources_dir_container_path}")
            container_volumes[resources_dir_path] = {
                "bind": self.resources_dir_container_path,
                "mode": "ro",
            }

        return container_volumes

    def build_container_ports_docker(self) -> Dict[str, int]:
        # container_ports is a dictionary which configures the ports to bind
        # inside the container. The key is the port to bind inside the container
        #   either as an integer or a string in the form port/protocol
        # and the value is the corresponding port to open on the host.
        # For example:
        #   {'2222/tcp': 3333} will expose port 2222 inside the container as port 3333 on the host.
        container_ports: Dict[str, int] = self.container_ports or {}

        if self.open_container_port:
            container_ports[str(self.container_port)] = self.host_port

        return container_ports

    def build_container_command_docker(self) -> Optional[List[str]]:
        if isinstance(self.command, str):
            return self.command.strip().split(" ")
        return self.command

    def build_resources(self, build_context: DockerBuildContext) -> Optional[Any]:
        from phi.docker.resource.base import DockerResource
        from phi.docker.resource.network import DockerNetwork
        from phi.docker.resource.container import DockerContainer

        logger.debug(f"------------ Building {self.get_app_name()} ------------")
        # -*- Build Container Paths
        container_context: Optional[ContainerContext] = self.build_container_context()
        if container_context is None:
            raise Exception("Could not build ContainerContext")
        logger.debug(f"ContainerContext: {container_context.model_dump_json(indent=2)}")

        # -*- Build Container Environment
        container_env: Dict[str, str] = self.build_container_env_docker(container_context=container_context)

        # -*- Build Container Volumes
        container_volumes = self.build_container_volumes_docker(container_context=container_context)

        # -*- Build Container Ports
        container_ports: Dict[str, int] = self.build_container_ports_docker()

        # -*- Build Container Command
        container_cmd: Optional[List[str]] = self.build_container_command_docker()
        if container_cmd:
            logger.debug("Command: {}".format(" ".join(container_cmd)))

        # -*- Create DockerContainer
        docker_container = DockerContainer(
            name=self.get_container_name(),
            image=self.get_image_str(),
            entrypoint=self.entrypoint,
            command=" ".join(container_cmd) if container_cmd is not None else None,
            detach=self.container_detach,
            auto_remove=self.container_auto_remove if not self.debug_mode else False,
            remove=self.container_remove if not self.debug_mode else False,
            healthcheck=self.container_healthcheck,
            hostname=self.container_hostname,
            labels=self.container_labels,
            environment=container_env,
            network=build_context.network,
            platform=self.container_platform,
            ports=container_ports if len(container_ports) > 0 else None,
            restart_policy=self.container_restart_policy,
            stdin_open=self.container_stdin_open,
            stderr=self.container_stderr,
            stdout=self.container_stdout,
            tty=self.container_tty,
            user=self.container_user,
            volumes=container_volumes if len(container_volumes) > 0 else None,
            working_dir=self.container_working_dir,
            use_cache=self.use_cache,
        )

        # -*- Create app_resources list
        app_resources: List[DockerResource] = []
        if self.image:
            app_resources.append(self.image)
        app_resources.extend(
            [
                DockerNetwork(name=build_context.network),
                docker_container,
            ]
        )

        logger.debug(f"------------ {self.get_app_name()} Built ------------")
        return app_resources
