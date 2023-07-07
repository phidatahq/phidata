from pathlib import Path
from typing import Optional, Dict, Any, List, Union

from phidata.app.aws_app import AwsApp, AwsAppArgs
from phidata.app.docker_app import DockerApp, DockerAppArgs
from phidata.app.k8s_app import (
    K8sApp,
    K8sAppArgs,
    ImagePullPolicy,
    RestartPolicy,
    ServiceType,
)
from phidata.types.context import ContainerPathContext
from phidata.utils.log import logger


class QdrantArgs(AwsAppArgs, DockerAppArgs, K8sAppArgs):
    # -*- Qdrant Volume
    qdrant_volume_name: Optional[str] = None
    # Path to mount the qdrant volume inside the container
    qdrant_storage_container_path: str = "/qdrant/storage"
    # Mount local qdrant storage directory to the container
    mount_qdrant_storage: bool = False
    # Path to the qdrant storage directory
    qdrant_storage_dir: str = "storage/qdrant"


class Qdrant(AwsApp, DockerApp, K8sApp):
    def __init__(
        self,
        name: str = "qdrant",
        version: str = "1",
        enabled: bool = True,
        # -*- Image Configuration,
        # Image can be provided as a DockerImage object or as image_name:image_tag
        image: Optional[Any] = None,
        image_name: str = "qdrant/qdrant",
        image_tag: str = "v1.3.1",
        entrypoint: Optional[Union[str, List[str]]] = None,
        command: Optional[Union[str, List]] = None,
        # -*- Debug Mode
        debug_mode: bool = False,
        # -*- Container Environment,
        # Add env variables to container,
        env: Optional[Dict[str, Any]] = None,
        # Read env variables from a file in yaml format,
        env_file: Optional[Path] = None,
        # Add secret variables to container,
        secrets: Optional[Dict[str, Any]] = None,
        # Read secret variables from a file in yaml format,
        secrets_file: Optional[Path] = None,
        # Read secret variables from AWS Secrets,
        aws_secrets: Optional[Any] = None,
        # -*- Qdrant Volume,
        qdrant_volume_name: Optional[str] = None,
        # Path to mount the qdrant volume inside the container,
        qdrant_storage_container_path: str = "/qdrant/storage",
        # Mount local qdrant storage directory to the container,
        mount_qdrant_storage: bool = False,
        # Path to the qdrant storage directory,
        qdrant_storage_dir: str = "storage/qdrant",
        # -*- Container Ports,
        # Open a container port if open_container_port=True,
        open_container_port: bool = True,
        # Port number on the container,
        container_port: int = 6333,
        # Port name (only used by the K8sContainer),
        container_port_name: str = "http",
        # Host port to map to the container port,
        container_host_port: int = 6333,
        # -*- Container Configuration,
        container_name: Optional[str] = None,
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
        # Return logs from STDOUT when container_detach=False.,
        container_stdout: Optional[bool] = True,
        # Return logs from STDERR when container_detach=False.,
        container_stderr: Optional[bool] = True,
        container_tty: bool = True,
        # Specify a test to perform to check that the container is healthy.,
        container_healthcheck: Optional[Dict[str, Any]] = None,
        # Optional hostname for the container.,
        container_hostname: Optional[str] = None,
        # Platform in the format os[/arch[/variant]].,
        container_platform: Optional[str] = None,
        # Path to the working directory.,
        container_working_dir: Optional[str] = None,
        # Add labels to the container,
        container_labels: Optional[Dict[str, str]] = None,
        # Restart the container when it exits. Configured as a dictionary with keys:,
        # Name: One of on-failure, or always.,
        # MaximumRetryCount: Number of times to restart the container on failure.,
        # For example: {"Name": "on-failure", "MaximumRetryCount": 5},
        container_restart_policy: Optional[Dict[str, Any]] = None,
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
        container_volumes: Optional[Dict[str, dict]] = None,
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
        container_ports: Optional[Dict[str, Any]] = None,
        # -*- AWS Configuration,
        aws_subnets: Optional[List[str]] = None,
        aws_security_groups: Optional[List[Any]] = None,
        # -*- ECS Configuration,
        ecs_cluster: Optional[Any] = None,
        ecs_launch_type: str = "FARGATE",
        ecs_task_cpu: str = "2048",
        ecs_task_memory: str = "4095",
        ecs_service_count: int = 1,
        assign_public_ip: bool = False,
        ecs_enable_exec: bool = True,
        #  -*- Resource Control,
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
        #  -*- Save Resources to output directory,
        # If True, save the resources to files,
        save_output: bool = False,
        # The resource directory for the output files,
        resource_dir: Optional[str] = None,
        # Skip creation if resource with the same name is active,
        use_cache: bool = True,
        #  -*- Other args,
        print_env_on_load: bool = False,
        # Extra kwargs used to capture additional args,
        **extra_kwargs,
    ):
        super().__init__()
        try:
            self.args: QdrantArgs = QdrantArgs(
                name=name,
                version=version,
                enabled=enabled,
                image=image,
                image_name=image_name,
                image_tag=image_tag,
                entrypoint=entrypoint,
                command=command,
                debug_mode=debug_mode,
                env=env,
                env_file=env_file,
                secrets=secrets,
                secrets_file=secrets_file,
                aws_secrets=aws_secrets,
                qdrant_volume_name=qdrant_volume_name,
                qdrant_storage_container_path=qdrant_storage_container_path,
                mount_qdrant_storage=mount_qdrant_storage,
                qdrant_storage_dir=qdrant_storage_dir,
                open_container_port=open_container_port,
                container_port=container_port,
                container_port_name=container_port_name,
                container_host_port=container_host_port,
                container_name=container_name,
                container_detach=container_detach,
                container_auto_remove=container_auto_remove,
                container_remove=container_remove,
                container_user=container_user,
                container_stdin_open=container_stdin_open,
                container_stdout=container_stdout,
                container_stderr=container_stderr,
                container_tty=container_tty,
                container_healthcheck=container_healthcheck,
                container_hostname=container_hostname,
                container_platform=container_platform,
                container_working_dir=container_working_dir,
                container_labels=container_labels,
                container_restart_policy=container_restart_policy,
                container_volumes=container_volumes,
                container_ports=container_ports,
                aws_subnets=aws_subnets,
                aws_security_groups=aws_security_groups,
                ecs_cluster=ecs_cluster,
                ecs_launch_type=ecs_launch_type,
                ecs_task_cpu=ecs_task_cpu,
                ecs_task_memory=ecs_task_memory,
                ecs_service_count=ecs_service_count,
                assign_public_ip=assign_public_ip,
                ecs_enable_exec=ecs_enable_exec,
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
                save_output=save_output,
                resource_dir=resource_dir,
                use_cache=use_cache,
                print_env_on_load=print_env_on_load,
                **extra_kwargs,
            )
        except Exception as e:
            logger.error(f"Args for {self.name} are not valid: {e}")
            raise

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

        # Create a volume for Qdrant Storage
        qdrant_storage_host = self.args.qdrant_volume_name or get_default_volume_name(
            self.app_name
        )

        # If mount_qdrant_storage is True, mount the qdrant_storage_dir to the container
        if self.args.mount_qdrant_storage:
            qdrant_storage_host = str(
                self.workspace_root_path.joinpath(self.args.qdrant_storage_dir)
            )

        logger.debug(f"Mounting: {qdrant_storage_host}")
        logger.debug(f"\tto: {self.args.qdrant_storage_container_path}")
        container_volumes[qdrant_storage_host] = {
            "bind": self.args.qdrant_storage_container_path,
            "mode": "rw",
        }
        return container_volumes
