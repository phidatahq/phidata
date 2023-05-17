from pathlib import Path
from typing import Optional, Dict, Any, List, Union

from phidata.app.phidata_app import PhidataApp, PhidataAppArgs, WorkspaceVolumeType
from phidata.utils.log import logger


class StreamlitAppArgs(PhidataAppArgs):
    pass


class StreamlitApp(PhidataApp):
    def __init__(
        self,
        name: str = "streamlit-app",
        version: str = "1",
        enabled: bool = True,
        # -*- Image Configuration,
        # Image can be provided as a DockerImage object or as image_name:image_tag
        image: Optional[Any] = None,
        image_name: str = "phidata/streamlit",
        image_tag: str = "latest",
        entrypoint: Optional[Union[str, List]] = None,
        command: Optional[Union[str, List]] = "app start",
        # Install python dependencies using a requirements.txt file,
        install_requirements: bool = False,
        # Path to the requirements.txt file relative to the workspace_root,
        requirements_file: str = "requirements.txt",
        # -*- Debug Mode
        debug_mode: bool = False,
        # -*- Container Configuration,
        container_name: Optional[str] = None,
        # Overwrite the PYTHONPATH env var,
        # which is usually set to the workspace_root_container_path,
        python_path: Optional[str] = None,
        # Add to the PYTHONPATH env var. If python_path is set, this is ignored
        # Does not overwrite the PYTHONPATH env var - adds to it.
        add_python_path: Optional[str] = None,
        # Add labels to the container,
        container_labels: Optional[Dict[str, Any]] = None,
        # Container env passed to the PhidataApp,
        # Add env variables to container env,
        env: Optional[Dict[str, Any]] = None,
        # Read env variables from a file in yaml format,
        env_file: Optional[Path] = None,
        # Container secrets,
        # Add secret variables to container env,
        secrets: Optional[Dict[str, Any]] = None,
        # Read secret variables from a file in yaml format,
        secrets_file: Optional[Path] = None,
        # Read secret variables from AWS Secrets,
        aws_secrets: Optional[Any] = None,
        # Container ports,
        # Open a container port if open_container_port=True,
        open_container_port: bool = True,
        # Port number on the container,
        container_port: int = 9095,
        # Port name: Only used by the K8sContainer,
        container_port_name: str = "http",
        # Host port: Only used by the DockerContainer,
        container_host_port: int = 9095,
        # Container volumes,
        # Mount the workspace directory on the container,
        mount_workspace: bool = False,
        workspace_volume_name: Optional[str] = None,
        workspace_volume_type: Optional[WorkspaceVolumeType] = None,
        # Path to mount the workspace volume inside the container,
        workspace_volume_container_path: str = "/usr/local/server",
        # How to mount the workspace volume,
        # Option 1: Mount the workspace from the host machine,
        # If None, use the workspace_root_path,
        # Note: This is the default on DockerContainers. We assume that DockerContainers,
        # are running locally on the user's machine so the local workspace_root_path,
        # is mounted to the workspace_volume_container_path,
        workspace_volume_host_path: Optional[str] = None,
        # Option 2: Load the workspace from git using a git-sync sidecar container,
        # This the default on K8sContainers.,
        create_git_sync_sidecar: bool = False,
        # Required to create an initial copy of the workspace,
        create_git_sync_init_container: bool = True,
        git_sync_image_name: str = "k8s.gcr.io/git-sync",
        git_sync_image_tag: str = "v3.1.1",
        git_sync_repo: Optional[str] = None,
        git_sync_branch: Optional[str] = None,
        git_sync_wait: int = 1,
        # -*- Docker configuration,
        # Run container in the background and return a Container object.,
        container_detach: bool = True,
        # Enable auto-removal of the container on daemon side when the container’s process exits.,
        container_auto_remove: bool = True,
        # Remove the container when it has finished running. Default: True.,
        container_remove: bool = True,
        # Username or UID to run commands as inside the container.,
        container_user: Optional[Union[str, int]] = None,
        # Keep STDIN open even if not attached.,
        container_stdin_open: bool = True,
        container_tty: bool = True,
        # Specify a test to perform to check that the container is healthy.,
        container_healthcheck: Optional[Dict[str, Any]] = None,
        # Optional hostname for the container.,
        container_hostname: Optional[str] = None,
        # Platform in the format os[/arch[/variant]].,
        container_platform: Optional[str] = None,
        # Path to the working directory.,
        container_working_dir: Optional[str] = None,
        # Restart the container when it exits. Configured as a dictionary with keys:,
        # Name: One of on-failure, or always.,
        # MaximumRetryCount: Number of times to restart the container on failure.,
        # For example: {"Name": "on-failure", "MaximumRetryCount": 5},
        container_restart_policy_docker: Optional[Dict[str, Any]] = None,
        # Add volumes to DockerContainer,
        # container_volumes is a dictionary which adds the volumes to mount,
        # inside the container. The key is either the host path or a volume name,,
        # and the value is a dictionary with 2 keys:,
        #   bind - The path to mount the volume inside the container,
        #   mode - Either rw to mount the volume read/write, or ro to mount it read-only.,
        # For example:,
        # {,
        #   '/home/user1/': {'bind': '/mnt/vol2', 'mode': 'rw'},,
        #   '/var/www': {'bind': '/mnt/vol1', 'mode': 'ro'},
        # },
        container_volumes_docker: Optional[Dict[str, dict]] = None,
        # Add ports to DockerContainer,
        # The keys of the dictionary are the ports to bind inside the container,,
        # either as an integer or a string in the form port/protocol, where the protocol is either tcp, udp.,
        # The values of the dictionary are the corresponding ports to open on the host, which can be either:,
        #   - The port number, as an integer.,
        #       For example, {'2222/tcp': 3333} will expose port 2222 inside the container as port 3333 on the host.,
        #   - None, to assign a random host port. For example, {'2222/tcp': None}.,
        #   - A tuple of (address, port) if you want to specify the host interface.,
        #       For example, {'1111/tcp': ('127.0.0.1', 1111)}.,
        #   - A list of integers, if you want to bind multiple host ports to a single container port.,
        #       For example, {'1111/tcp': [1234, 4567]}.,
        container_ports_docker: Optional[Dict[str, Any]] = None,
        # Other args,
        print_env_on_load: bool = False,
        skip_create: bool = False,
        skip_read: bool = False,
        skip_update: bool = False,
        recreate_on_update: bool = False,
        skip_delete: bool = False,
        wait_for_creation: bool = True,
        wait_for_update: bool = True,
        wait_for_deletion: bool = True,
        waiter_delay: int = 30,
        waiter_max_attempts: int = 50,
        # If True, skip resource creation if active resources with the same name exist.,
        use_cache: bool = True,
        **kwargs,
    ):
        super().__init__()
        try:
            self.args: StreamlitAppArgs = StreamlitAppArgs(
            name=name,
            version=version,
            enabled=enabled,
            image=image,
            image_name=image_name,
            image_tag=image_tag,
            entrypoint=entrypoint,
            command=command,
            install_requirements=install_requirements,
            requirements_file=requirements_file,
            debug_mode=debug_mode,
            container_name=container_name,
            python_path=python_path,
            add_python_path=add_python_path,
            container_labels=container_labels,
            env=env,
            env_file=env_file,
            secrets=secrets,
            secrets_file=secrets_file,
            aws_secrets=aws_secrets,
            open_container_port=open_container_port,
            container_port=container_port,
            container_port_name=container_port_name,
            container_host_port=container_host_port,
            mount_workspace=mount_workspace,
            workspace_volume_name=workspace_volume_name,
            workspace_volume_type=workspace_volume_type,
            workspace_volume_container_path=workspace_volume_container_path,
            workspace_volume_host_path=workspace_volume_host_path,
            create_git_sync_sidecar=create_git_sync_sidecar,
            create_git_sync_init_container=create_git_sync_init_container,
            git_sync_image_name=git_sync_image_name,
            git_sync_image_tag=git_sync_image_tag,
            git_sync_repo=git_sync_repo,
            git_sync_branch=git_sync_branch,
            git_sync_wait=git_sync_wait,
            container_detach=container_detach,
            container_auto_remove=container_auto_remove,
            container_remove=container_remove,
            container_user=container_user,
            container_stdin_open=container_stdin_open,
            container_tty=container_tty,
            container_healthcheck=container_healthcheck,
            container_hostname=container_hostname,
            container_platform=container_platform,
            container_working_dir=container_working_dir,
            container_restart_policy_docker=container_restart_policy_docker,
            container_volumes_docker=container_volumes_docker,
            container_ports_docker=container_ports_docker,
            print_env_on_load=print_env_on_load,
            skip_create=skip_create,
            skip_read=skip_read,
            skip_update=skip_update,
            recreate_on_update=recreate_on_update,
            skip_delete=skip_delete,
            wait_for_creation=wait_for_creation,
            wait_for_update=wait_for_update,
            wait_for_deletion=wait_for_deletion,
            waiter_delay=waiter_delay,
            waiter_max_attempts=waiter_max_attempts,
            use_cache=use_cache,
            **kwargs,
        )
        except Exception as e:
            logger.error(f"Args for {self.name} are not valid")
            raise

    ######################################################
    ## Docker Resources
    ######################################################

    def get_docker_rg(self, docker_build_context: Any) -> Optional[Any]:
        from phidata.docker.resource.group import (
            DockerNetwork,
            DockerContainer,
            DockerResourceGroup,
            DockerBuildContext,
        )
        from phidata.types.context import ContainerPathContext

        app_name = self.args.name

        if self.workspace_root_path is None:
            raise Exception("Invalid workspace_root_path")
        workspace_name = self.workspace_root_path.stem

        logger.debug(f"Building DockerResourceGroup: {app_name} for {workspace_name}")

        if docker_build_context is None or not isinstance(
            docker_build_context, DockerBuildContext
        ):
            raise Exception(f"Invalid DockerBuildContext: {type(docker_build_context)}")

        container_paths: Optional[ContainerPathContext] = self.get_container_paths(
            add_ws_name_to_ws_root=False
        )
        if container_paths is None:
            raise Exception("Invalid ContainerPathContext")
        logger.debug(f"ContainerPaths: {container_paths.json(indent=2)}")

        # Get Container Environment
        container_env: Dict[str, str] = self.get_docker_container_env(
            container_paths=container_paths
        )

        # Get Container Volumes
        container_volumes = self.get_docker_container_volumes(
            container_paths=container_paths
        )

        # Get Container Ports
        container_ports: Dict[str, int] = self.get_docker_container_ports()

        # -*- Create Docker Container
        docker_container = DockerContainer(
            name=self.get_container_name(),
            image=self.get_image_str(),
            entrypoint=self.args.entrypoint,
            command=self.args.command,
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
            restart_policy=self.get_container_restart_policy_docker(),
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
            name=app_name,
            enabled=self.args.enabled,
            network=DockerNetwork(name=docker_build_context.network),
            containers=[docker_container],
            images=[self.args.image] if self.args.image else None,
        )
        return docker_rg

    def init_docker_resource_groups(self, docker_build_context: Any) -> None:
        docker_rg = self.get_docker_rg(docker_build_context)
        if docker_rg is not None:
            from collections import OrderedDict

            if self.docker_resource_groups is None:
                self.docker_resource_groups = OrderedDict()
            self.docker_resource_groups[docker_rg.name] = docker_rg

