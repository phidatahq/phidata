from typing import Optional, Dict, Any, Union, List
from collections import OrderedDict

from phidata.app.base_app import BaseApp, BaseAppArgs, WorkspaceVolumeType
from phidata.types.context import ContainerPathContext
from phidata.utils.log import logger


class DockerAppArgs(BaseAppArgs):
    # -*- Resources Volume
    # Mount a resources directory on the container
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
    #       For example, {'2222/tcp': 3333} will expose port 2222 inside the container as port 3333 on the host.
    #   - None, to assign a random host port. For example, {'2222/tcp': None}.
    #   - A tuple of (address, port) if you want to specify the host interface.
    #       For example, {'1111/tcp': ('127.0.0.1', 1111)}.
    #   - A list of integers, if you want to bind multiple host ports to a single container port.
    #       For example, {'1111/tcp': [1234, 4567]}.
    container_ports: Optional[Dict[str, Any]] = None


class DockerApp(BaseApp):
    def __init__(self) -> None:
        super().__init__()

        # Args for the AwsAppArgs, updated by the subclass
        self.args: DockerAppArgs = DockerAppArgs()

        # Dict of DockerResourceGroups
        # Type: Optional[Dict[str, DockerResourceGroup]]
        self.docker_resource_groups: Optional[Dict[str, Any]] = None

    @property
    def container_name(self) -> str:
        from phidata.utils.common import get_default_container_name

        return (
            self.args.container_name
            if self.args.container_name
            else get_default_container_name(self.name)
        )

    @container_name.setter
    def container_name(self, container_name: str) -> None:
        if self.args is not None and container_name is not None:
            self.args.container_name = container_name

    @property
    def container_restart_policy(self) -> Optional[Dict[str, Any]]:
        return self.args.container_restart_policy

    @container_restart_policy.setter
    def container_restart_policy(
        self, container_restart_policy: Dict[str, Any]
    ) -> None:
        if self.args is not None and container_restart_policy is not None:
            self.args.container_restart_policy = container_restart_policy

    def build_container_env_docker(
        self, container_paths: ContainerPathContext
    ) -> Dict[str, str]:
        from phidata.constants import (
            PYTHONPATH_ENV_VAR,
            PHIDATA_RUNTIME_ENV_VAR,
            SCRIPTS_DIR_ENV_VAR,
            STORAGE_DIR_ENV_VAR,
            META_DIR_ENV_VAR,
            PRODUCTS_DIR_ENV_VAR,
            NOTEBOOKS_DIR_ENV_VAR,
            WORKFLOWS_DIR_ENV_VAR,
            WORKSPACE_ROOT_ENV_VAR,
            WORKSPACE_CONFIG_DIR_ENV_VAR,
        )

        # Container Environment
        container_env: Dict[str, str] = self.container_env or {}
        container_env.update(
            {
                PHIDATA_RUNTIME_ENV_VAR: "docker",
                SCRIPTS_DIR_ENV_VAR: container_paths.scripts_dir or "",
                STORAGE_DIR_ENV_VAR: container_paths.storage_dir or "",
                META_DIR_ENV_VAR: container_paths.meta_dir or "",
                PRODUCTS_DIR_ENV_VAR: container_paths.products_dir or "",
                NOTEBOOKS_DIR_ENV_VAR: container_paths.notebooks_dir or "",
                WORKFLOWS_DIR_ENV_VAR: container_paths.workflows_dir or "",
                WORKSPACE_ROOT_ENV_VAR: container_paths.workspace_root or "",
                WORKSPACE_CONFIG_DIR_ENV_VAR: container_paths.workspace_config_dir
                or "",
                "INSTALL_REQUIREMENTS": str(self.args.install_requirements),
                "REQUIREMENTS_FILE_PATH": container_paths.requirements_file or "",
                "MOUNT_WORKSPACE": str(self.args.mount_workspace),
                "WORKSPACE_DIR_CONTAINER_PATH": str(
                    self.args.workspace_dir_container_path
                ),
                "MOUNT_RESOURCES": str(self.args.mount_resources),
                "RESOURCES_DIR_CONTAINER_PATH": str(
                    self.args.resources_dir_container_path
                ),
                "PRINT_ENV_ON_LOAD": str(self.args.print_env_on_load),
            }
        )

        if self.args.set_python_path:
            python_path = self.args.python_path
            if python_path is None:
                python_path = container_paths.workspace_root
                if (
                    self.args.mount_resources
                    and self.args.resources_dir_container_path is not None
                ):
                    python_path = "{}:{}".format(
                        python_path, self.args.resources_dir_container_path
                    )
                if self.args.add_python_paths is not None:
                    python_path = "{}:{}".format(
                        python_path, ":".join(self.args.add_python_paths)
                    )
            if python_path is not None:
                container_env[PYTHONPATH_ENV_VAR] = python_path

        # Set aws env vars
        self.set_aws_env_vars(env_dict=container_env)

        # Update the container env using env_file
        env_data_from_file = self.get_env_data()
        if env_data_from_file is not None:
            container_env.update(
                {k: str(v) for k, v in env_data_from_file.items() if v is not None}
            )

        # Update the container env using secrets_file
        secret_data_from_file = self.get_secret_data()
        if secret_data_from_file is not None:
            container_env.update(
                {k: str(v) for k, v in secret_data_from_file.items() if v is not None}
            )

        # Update the container env with user provided env
        # this overwrites any existing variables with the same key
        if self.args.env is not None and isinstance(self.args.env, dict):
            container_env.update(
                {k: str(v) for k, v in self.args.env.items() if v is not None}
            )

        # logger.debug("Container Environment: {}".format(container_env))
        return container_env

    def build_container_volumes_docker(
        self, container_paths: ContainerPathContext
    ) -> Dict[str, dict]:
        from phidata.utils.common import get_default_volume_name

        if self.workspace_root_path is None:
            logger.error("Invalid workspace_root_path")
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
        container_volumes = self.args.container_volumes or {}

        # Create a volume for the workspace dir
        if self.args.mount_workspace:
            workspace_volume_container_path_str = container_paths.workspace_root
            if (
                self.args.workspace_volume_type is None
                or self.args.workspace_volume_type == WorkspaceVolumeType.HostPath
            ):
                workspace_volume_host_path = self.args.workspace_dir or str(
                    self.workspace_root_path
                )
                logger.debug(f"Mounting: {workspace_volume_host_path}")
                logger.debug(f"\tto: {workspace_volume_container_path_str}")
                container_volumes[workspace_volume_host_path] = {
                    "bind": workspace_volume_container_path_str,
                    "mode": "rw",
                }
            elif self.args.workspace_volume_type == WorkspaceVolumeType.EmptyDir:
                workspace_volume_name = self.args.workspace_volume_name
                if workspace_volume_name is None:
                    workspace_volume_name = get_default_volume_name(
                        container_paths.workspace_name or "ws"
                    )
                logger.debug(f"Mounting: {workspace_volume_name}")
                logger.debug(f"\tto: {workspace_volume_container_path_str}")
                container_volumes[workspace_volume_name] = {
                    "bind": workspace_volume_container_path_str,
                    "mode": "rw",
                }
            else:
                logger.error(f"{self.args.workspace_volume_type.value} not supported")

        # Create a volume for the resources dir
        if self.args.mount_resources:
            resources_dir_path = str(
                self.workspace_root_path.joinpath(self.args.resources_dir)
            )
            logger.debug(f"Mounting: {resources_dir_path}")
            logger.debug(f"\tto: {self.args.resources_dir_container_path}")
            container_volumes[resources_dir_path] = {
                "bind": self.args.resources_dir_container_path,
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
        container_ports: Dict[str, int] = self.args.container_ports or {}

        if self.args.open_container_port:
            container_ports[
                str(self.args.container_port)
            ] = self.args.container_host_port

        return container_ports

    def build_container_command_docker(self) -> Optional[List[str]]:
        if isinstance(self.args.command, str):
            return self.args.command.strip().split(" ")
        return self.args.command

    def get_docker_rg(self, docker_build_context: Any) -> Optional[Any]:
        from phidata.docker.resource.group import (
            DockerNetwork,
            DockerContainer,
            DockerResourceGroup,
            DockerBuildContext,
        )

        # -*- Build Container Paths
        container_paths: Optional[ContainerPathContext] = self.build_container_paths()
        if container_paths is None:
            raise Exception("Could not build Container Paths")
        logger.debug(f"ContainerPaths: {container_paths.json(indent=2)}")

        workspace_name = container_paths.workspace_name
        logger.debug(
            f"Building DockerResourceGroup: {self.app_name} for {workspace_name}"
        )

        if docker_build_context is None or not isinstance(
            docker_build_context, DockerBuildContext
        ):
            logger.error("docker_build_context must be a DockerBuildContext")
            return None

        # -*- Build Container Environment
        container_env: Dict[str, str] = self.build_container_env_docker(
            container_paths=container_paths
        )

        # -*- Build Container Volumes
        container_volumes = self.build_container_volumes_docker(
            container_paths=container_paths
        )

        # -*- Build Container Ports
        container_ports: Dict[str, int] = self.build_container_ports_docker()

        # -*- Build Container Command
        container_cmd: Optional[List[str]] = self.build_container_command_docker()
        if container_cmd:
            logger.debug("Command: {}".format(" ".join(container_cmd)))

        # -*- Create DockerContainer
        docker_container = DockerContainer(
            name=self.container_name,
            image=self.get_image_str(),
            entrypoint=self.args.entrypoint,
            command=" ".join(container_cmd) if container_cmd is not None else None,
            detach=self.args.container_detach,
            auto_remove=self.args.container_auto_remove
            if not self.args.debug_mode
            else False,
            remove=self.args.container_remove if not self.args.debug_mode else False,
            healthcheck=self.args.container_healthcheck,
            hostname=self.args.container_hostname,
            labels=self.args.container_labels,
            environment=container_env,
            network=docker_build_context.network,
            platform=self.args.container_platform,
            ports=container_ports if len(container_ports) > 0 else None,
            restart_policy=self.container_restart_policy,
            stdin_open=self.args.container_stdin_open,
            stderr=self.args.container_stderr,
            stdout=self.args.container_stdout,
            tty=self.args.container_tty,
            user=self.args.container_user,
            volumes=container_volumes if len(container_volumes) > 0 else None,
            working_dir=self.args.container_working_dir,
            use_cache=self.args.use_cache,
        )

        docker_rg = DockerResourceGroup(
            name=self.app_name,
            enabled=self.args.enabled,
            network=DockerNetwork(name=docker_build_context.network),
            containers=[docker_container],
            images=[self.args.image] if self.args.image else None,
        )
        return docker_rg

    def build_docker_resource_groups(self, docker_build_context: Any) -> None:
        docker_rg = self.get_docker_rg(docker_build_context)
        if docker_rg is not None:
            if self.docker_resource_groups is None:
                self.docker_resource_groups = OrderedDict()
            self.docker_resource_groups[docker_rg.name] = docker_rg

    def get_docker_resource_groups(
        self, docker_build_context: Any
    ) -> Optional[Dict[str, Any]]:
        if self.docker_resource_groups is None:
            self.build_docker_resource_groups(docker_build_context)
        # Comment out in production
        # if self.docker_resource_groups:
        #     logger.debug("DockerResourceGroups:")
        #     for rg_name, rg in self.docker_resource_groups.items():
        #         logger.debug(
        #             "{}: {}".format(rg_name, rg.json(exclude_none=True, indent=2))
        #         )
        return self.docker_resource_groups
