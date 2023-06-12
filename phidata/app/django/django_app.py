from pathlib import Path
from typing import Optional, Dict, Any, List, Union

from phidata.app.phidata_app import PhidataApp, PhidataAppArgs, WorkspaceVolumeType
from phidata.utils.log import logger


class DjangoAppArgs(PhidataAppArgs):
    # -*- ECS configuration
    ecs_cluster: Optional[Any] = None
    ecs_launch_type: str = "FARGATE"
    ecs_task_cpu: str = "256"
    ecs_task_memory: str = "512"
    ecs_service_count: int = 1
    assign_public_ip: bool = True
    ecs_enable_exec: bool = True

    # -*- LoadBalancer configuration
    enable_load_balancer: bool = True
    # Change to load_balancer
    elb: Optional[Any] = None
    # Default 80 for HTTP and 443 for HTTPS
    lb_port: Optional[int] = None
    # HTTP or HTTPS
    lb_protocol: str = "HTTP"
    lb_certificate_arn: Optional[str] = None

    # -*- TargetGroup configuration
    # Default 80 for HTTP and 443 for HTTPS
    target_group_port: Optional[int] = None
    # HTTP or HTTPS
    target_group_protocol: str = "HTTP"
    health_check_protocol: Optional[str] = None
    health_check_port: Optional[str] = None
    health_check_enabled: Optional[bool] = None
    health_check_path: Optional[str] = None
    health_check_interval_seconds: Optional[int] = None
    health_check_timeout_seconds: Optional[int] = None
    healthy_threshold_count: Optional[int] = None
    unhealthy_threshold_count: Optional[int] = None

    # Add NGINX to serve static file
    enable_nginx: bool = False
    nginx_image: Optional[Any] = None
    nginx_image_name: str = "phidata/django-nginx"
    nginx_image_tag: str = "latest"
    nginx_container_port: int = 80


class DjangoApp(PhidataApp):
    def __init__(
        self,
        name: str = "django-app",
        version: str = "1",
        enabled: bool = True,
        # -*- Image Configuration,
        # Image can be provided as a DockerImage object or as image_name:image_tag
        image: Optional[Any] = None,
        image_name: str = "phidata/django-app",
        image_tag: str = "latest",
        entrypoint: Optional[str] = None,
        command: Optional[str] = "python manage.py runserver 0.0.0.0:8000",
        # Install python dependencies using a requirements.txt file,
        install_requirements: bool = False,
        # Path to the requirements.txt file relative to the workspace_root,
        requirements_file: str = "requirements.txt",
        # -*- Debug Mode
        debug_mode: bool = False,
        # Overwrite the PYTHONPATH env var, default: False
        set_python_path: bool = False,
        # Set the python_path, default: workspace_volume_container_path,
        python_path: Optional[str] = None,
        # Add to the PYTHONPATH env var. If python_path is set, this is ignored,
        add_python_path: Optional[str] = None,
        # Add env variables to container env,
        env: Optional[Dict[str, Any]] = None,
        # Read env variables from a file in yaml format,
        env_file: Optional[Path] = None,
        # Add secret variables to container env,
        secrets: Optional[Dict[str, Any]] = None,
        # Read secret variables from a file in yaml format,
        secrets_file: Optional[Path] = None,
        # Read secret variables from AWS Secrets,
        aws_secrets: Optional[Any] = None,
        # -*- Container Configuration,
        container_name: Optional[str] = None,
        # Open a container port if open_container_port=True,
        open_container_port: bool = True,
        # Port number on the container,
        container_port: int = 8000,
        # Port name: Only used by the K8sContainer,
        container_port_name: str = "http",
        # Host port: Only used by the DockerContainer,
        container_host_port: int = 8000,
        # Mount the workspace directory on the container,
        mount_workspace: bool = False,
        workspace_volume_name: Optional[str] = None,
        workspace_volume_type: Optional[WorkspaceVolumeType] = None,
        # Path to mount the workspace volume inside the container,
        workspace_volume_container_path: str = "/usr/local/app",
        # Mount the workspace from the host machine,
        # If None, use the workspace_root_path,
        workspace_volume_host_path: Optional[str] = None,
        # Add labels to the container,
        container_labels: Optional[Dict[str, Any]] = None,
        # Run container in the background and return a Container object,
        container_detach: bool = True,
        # Enable auto-removal of the container on daemon side when the container’s process exits,
        container_auto_remove: bool = True,
        # Remove the container when it has finished running. Default: True,
        container_remove: bool = True,
        # Username or UID to run commands as inside the container,
        container_user: Optional[Union[str, int]] = None,
        # Keep STDIN open even if not attached.,
        container_stdin_open: bool = True,
        # Return logs from STDOUT when container_detach=False,
        container_stdout: Optional[bool] = True,
        # Return logs from STDERR when container_detach=False,
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
        # -*- ECS configuration,
        ecs_cluster: Optional[Any] = None,
        ecs_launch_type: str = "FARGATE",
        ecs_task_cpu: str = "256",
        ecs_task_memory: str = "512",
        ecs_service_count: int = 1,
        assign_public_ip: bool = True,
        ecs_enable_exec: bool = True,
        # -*- LoadBalancer configuration,
        enable_load_balancer: bool = True,
        # Change to load_balancer,
        elb: Optional[Any] = None,
        # Default 80 for HTTP and 443 for HTTPS,
        lb_port: Optional[int] = None,
        # HTTP or HTTPS,
        lb_protocol: str = "HTTP",
        lb_certificate_arn: Optional[str] = None,
        # -*- TargetGroup configuration,
        # Default 80 for HTTP and 443 for HTTPS,
        target_group_port: Optional[str] = None,
        # HTTP or HTTPS,
        target_group_protocol: str = "HTTP",
        health_check_protocol: Optional[str] = None,
        health_check_port: Optional[str] = None,
        health_check_enabled: Optional[bool] = None,
        health_check_path: Optional[str] = None,
        health_check_interval_seconds: Optional[int] = None,
        health_check_timeout_seconds: Optional[int] = None,
        healthy_threshold_count: Optional[int] = None,
        unhealthy_threshold_count: Optional[int] = None,
        # Add NGINX to serve static file
        enable_nginx: bool = False,
        nginx_image: Optional[Any] = None,
        nginx_image_name: str = "phidata/django-nginx",
        nginx_image_tag: str = "latest",
        # -*- AWS configuration
        aws_subnets: Optional[List[str]] = None,
        aws_security_groups: Optional[List[Any]] = None,
        # Other args,
        print_env_on_load: bool = False,
        skip_create: bool = False,
        skip_read: bool = False,
        skip_update: bool = False,
        recreate_on_update: bool = False,
        skip_delete: bool = False,
        wait_for_create: bool = True,
        wait_for_update: bool = True,
        wait_for_delete: bool = True,
        waiter_delay: int = 30,
        waiter_max_attempts: int = 50,
        # If True, skip resource creation if active resources with the same name exist.,
        use_cache: bool = True,
        **kwargs,
    ):
        super().__init__()
        try:
            self.args: DjangoAppArgs = DjangoAppArgs(
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
                set_python_path=set_python_path,
                python_path=python_path,
                add_python_path=add_python_path,
                env=env,
                env_file=env_file,
                secrets=secrets,
                secrets_file=secrets_file,
                aws_secrets=aws_secrets,
                container_name=container_name,
                open_container_port=open_container_port,
                container_port=container_port,
                container_port_name=container_port_name,
                container_host_port=container_host_port,
                mount_workspace=mount_workspace,
                workspace_volume_name=workspace_volume_name,
                workspace_volume_type=workspace_volume_type,
                workspace_volume_container_path=workspace_volume_container_path,
                workspace_volume_host_path=workspace_volume_host_path,
                container_labels=container_labels,
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
                container_restart_policy_docker=container_restart_policy_docker,
                container_volumes_docker=container_volumes_docker,
                container_ports_docker=container_ports_docker,
                ecs_cluster=ecs_cluster,
                ecs_launch_type=ecs_launch_type,
                ecs_task_cpu=ecs_task_cpu,
                ecs_task_memory=ecs_task_memory,
                ecs_service_count=ecs_service_count,
                assign_public_ip=assign_public_ip,
                ecs_enable_exec=ecs_enable_exec,
                enable_load_balancer=enable_load_balancer,
                elb=elb,
                lb_port=lb_port,
                lb_protocol=lb_protocol,
                lb_certificate_arn=lb_certificate_arn,
                target_group_port=target_group_port,
                target_group_protocol=target_group_protocol,
                health_check_protocol=health_check_protocol,
                health_check_port=health_check_port,
                health_check_enabled=health_check_enabled,
                health_check_path=health_check_path,
                health_check_interval_seconds=health_check_interval_seconds,
                health_check_timeout_seconds=health_check_timeout_seconds,
                healthy_threshold_count=healthy_threshold_count,
                unhealthy_threshold_count=unhealthy_threshold_count,
                enable_nginx=enable_nginx,
                nginx_image=nginx_image,
                nginx_image_name=nginx_image_name,
                nginx_image_tag=nginx_image_tag,
                aws_subnets=aws_subnets,
                aws_security_groups=aws_security_groups,
                print_env_on_load=print_env_on_load,
                skip_create=skip_create,
                skip_read=skip_read,
                skip_update=skip_update,
                recreate_on_update=recreate_on_update,
                skip_delete=skip_delete,
                wait_for_creation=wait_for_create,
                wait_for_update=wait_for_update,
                wait_for_deletion=wait_for_delete,
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

    ######################################################
    ## Aws Resources
    ######################################################

    def get_aws_rg(self, aws_build_context: Any) -> Optional[Any]:
        from phidata.docker.resource.image import DockerImage
        from phidata.aws.resource.group import (
            AwsResourceGroup,
            EcsCluster,
            EcsContainer,
            EcsTaskDefinition,
            EcsService,
            EcsVolume,
            LoadBalancer,
            TargetGroup,
            Listener,
            Subnet,
        )
        from phidata.types.context import ContainerPathContext
        from phidata.utils.common import get_default_volume_name

        app_name = self.name

        if self.workspace_root_path is None:
            raise Exception("Invalid workspace_root_path")
        workspace_name = self.workspace_root_path.stem

        logger.debug(f"Building AwsResourceGroup: {app_name} for {workspace_name}")

        container_paths: Optional[ContainerPathContext] = self.get_container_paths(
            add_ws_name_to_ws_root=False
        )
        if container_paths is None:
            raise Exception("Invalid ContainerPathContext")
        logger.debug(f"ContainerPaths: {container_paths.json(indent=2)}")

        # Get Container Environment
        container_env: Dict[str, str] = self.get_ecs_container_env(
            container_paths=container_paths
        )

        # -*- Create ECS cluster
        ecs_cluster = self.args.ecs_cluster
        if ecs_cluster is None:
            ecs_cluster = EcsCluster(
                name=f"{app_name}-cluster",
                ecs_cluster_name=app_name,
                capacity_providers=[self.args.ecs_launch_type],
                skip_create=self.args.skip_create,
                skip_delete=self.args.skip_delete,
                wait_for_creation=self.args.wait_for_creation,
                wait_for_deletion=self.args.wait_for_deletion,
            )

        # -*- Create Load Balancer
        load_balancer = self.args.elb
        if load_balancer is None:
            load_balancer = LoadBalancer(
                name=f"{app_name}-lb",
                subnets=self.args.aws_subnets,
                security_groups=self.args.aws_security_groups,
                protocol=self.args.lb_protocol,
                skip_create=self.args.skip_create,
                skip_delete=self.args.skip_delete,
                wait_for_creation=self.args.wait_for_creation,
                wait_for_deletion=self.args.wait_for_deletion,
            )

        # Get VPC ID from subnets
        vpc_ids = set()
        vpc_id = None
        if self.args.aws_subnets is not None:
            for subnet in self.args.aws_subnets:
                _vpc = Subnet(id=subnet).get_vpc_id()
                vpc_ids.add(_vpc)
                if len(vpc_ids) != 1:
                    raise ValueError("Subnets must be in the same VPC")
            vpc_id = vpc_ids.pop() if len(vpc_ids) == 1 else None

        # -*- Create Target Group
        tg_port = self.args.target_group_port
        if tg_port is None:
            tg_port = (
                self.args.nginx_container_port
                if self.args.enable_nginx
                else self.get_container_port()
            )
        target_group = TargetGroup(
            name=f"{app_name}-tg",
            port=tg_port,
            protocol=self.args.target_group_protocol,
            vpc_id=vpc_id,
            health_check_protocol=self.args.health_check_protocol,
            health_check_port=self.args.health_check_port,
            health_check_enabled=self.args.health_check_enabled,
            health_check_path=self.args.health_check_path,
            health_check_interval_seconds=self.args.health_check_interval_seconds,
            health_check_timeout_seconds=self.args.health_check_timeout_seconds,
            healthy_threshold_count=self.args.healthy_threshold_count,
            unhealthy_threshold_count=self.args.unhealthy_threshold_count,
            target_type="ip",
            skip_create=self.args.skip_create,
            skip_delete=self.args.skip_delete,
            wait_for_creation=self.args.wait_for_creation,
            wait_for_deletion=self.args.wait_for_deletion,
        )

        # -*- Create Listener
        lb_port = self.args.lb_port
        if lb_port is None:
            lb_port = 443 if self.args.lb_protocol == "HTTPS" else 80
        listener = Listener(
            name=f"{app_name}-listener",
            protocol=self.args.lb_protocol,
            port=lb_port,
            load_balancer=load_balancer,
            target_group=target_group,
            skip_create=self.args.skip_create,
            skip_delete=self.args.skip_delete,
            wait_for_creation=self.args.wait_for_creation,
            wait_for_deletion=self.args.wait_for_deletion,
        )
        if self.args.lb_certificate_arn is not None:
            listener.certificates = [{"CertificateArn": self.args.lb_certificate_arn}]

        # -*- Create ECS Containers
        container_command: List = []
        if isinstance(self.args.command, list):
            container_command = self.args.command
        elif isinstance(self.args.command, str):
            container_command = self.args.command.strip().split()
        else:
            logger.error(f"Invalid command: {self.args.command}")
        django_container = EcsContainer(
            name=app_name,
            image=self.get_image_str(),
            essential=True,
            port_mappings=[{"containerPort": self.get_container_port()}],
            command=container_command,
            environment=[{"name": k, "value": v} for k, v in container_env.items()],
            log_configuration={
                "logDriver": "awslogs",
                "options": {
                    "awslogs-group": app_name,
                    "awslogs-region": self.aws_region,
                    "awslogs-create-group": "true",
                    "awslogs-stream-prefix": app_name,
                },
            },
            linux_parameters={"initProcessEnabled": True},
            skip_create=self.args.skip_create,
            skip_delete=self.args.skip_delete,
            wait_for_creation=self.args.wait_for_creation,
            wait_for_deletion=self.args.wait_for_deletion,
        )
        nginx_container = None
        nginx_shared_volume = None
        if self.args.enable_nginx:
            nginx_container_name = f"{app_name}-nginx"
            nginx_shared_volume = EcsVolume(name=get_default_volume_name(app_name))
            nginx_image_str = (
                f"{self.args.nginx_image_name}:{self.args.nginx_image_tag}"
            )
            if self.args.nginx_image and isinstance(self.args.nginx_image, DockerImage):
                nginx_image_str = self.args.nginx_image.get_image_str()
            nginx_container = EcsContainer(
                name=nginx_container_name,
                image=nginx_image_str,
                essential=True,
                port_mappings=[{"containerPort": self.args.nginx_container_port}],
                environment=[{"name": k, "value": v} for k, v in container_env.items()],
                log_configuration={
                    "logDriver": "awslogs",
                    "options": {
                        "awslogs-group": app_name,
                        "awslogs-region": self.aws_region,
                        "awslogs-create-group": "true",
                        "awslogs-stream-prefix": nginx_container_name,
                    },
                },
                mount_points=[
                    {
                        "sourceVolume": nginx_shared_volume.name,
                        "containerPath": container_paths.workspace_root,
                    }
                ],
                linux_parameters={"initProcessEnabled": True},
                skip_create=self.args.skip_create,
                skip_delete=self.args.skip_delete,
                wait_for_creation=self.args.wait_for_creation,
                wait_for_deletion=self.args.wait_for_deletion,
            )
            if django_container:
                django_container.mount_points = [
                    {
                        "sourceVolume": nginx_shared_volume.name,
                        "containerPath": container_paths.workspace_root,
                    }
                ]
            else:
                logger.error("Could not add volume to django_container")

        # -*- Create ECS Task Definition
        ecs_task_definition = EcsTaskDefinition(
            name=f"{app_name}-td",
            family=app_name,
            network_mode="awsvpc",
            cpu=self.args.ecs_task_cpu,
            memory=self.args.ecs_task_memory,
            containers=[django_container],
            requires_compatibilities=[self.args.ecs_launch_type],
            add_ecs_exec_policy=self.args.ecs_enable_exec,
            skip_create=self.args.skip_create,
            skip_delete=self.args.skip_delete,
            wait_for_creation=self.args.wait_for_creation,
            wait_for_deletion=self.args.wait_for_deletion,
        )
        if self.args.enable_nginx:
            if nginx_container:
                if ecs_task_definition.containers:
                    ecs_task_definition.containers.append(nginx_container)
                else:
                    logger.error("ecs_task_definition.containers None")
            else:
                logger.error("nginx_container None")
            if nginx_shared_volume:
                ecs_task_definition.volumes = [nginx_shared_volume]

        aws_vpc_config: Dict[str, Any] = {}
        if self.args.aws_subnets is not None:
            aws_vpc_config["subnets"] = self.args.aws_subnets
        if self.args.aws_security_groups is not None:
            aws_vpc_config["securityGroups"] = self.args.aws_security_groups
        if self.args.assign_public_ip:
            aws_vpc_config["assignPublicIp"] = "ENABLED"

        # -*- Create ECS Service
        ecs_service = EcsService(
            name=f"{app_name}-service",
            desired_count=self.args.ecs_service_count,
            launch_type=self.args.ecs_launch_type,
            cluster=ecs_cluster,
            task_definition=ecs_task_definition,
            target_group=target_group,
            target_container_name=nginx_container.name
            if self.args.enable_nginx and nginx_container
            else django_container.name,
            target_container_port=self.args.nginx_container_port
            if self.args.enable_nginx
            else self.get_container_port(),
            network_configuration={"awsvpcConfiguration": aws_vpc_config},
            # Force delete the service.
            force_delete=True,
            # Force a new deployment of the service on update.
            force_new_deployment=True,
            enable_execute_command=self.args.ecs_enable_exec,
            skip_create=self.args.skip_create,
            skip_delete=self.args.skip_delete,
            wait_for_creation=self.args.wait_for_creation,
            wait_for_deletion=self.args.wait_for_deletion,
        )

        # -*- Create AwsResourceGroup
        return AwsResourceGroup(
            name=app_name,
            enabled=self.enabled,
            ecs_clusters=[ecs_cluster],
            ecs_task_definitions=[ecs_task_definition],
            ecs_services=[ecs_service],
            load_balancers=[load_balancer],
            target_groups=[target_group],
            listeners=[listener],
        )

    def init_aws_resource_groups(self, aws_build_context: Any) -> None:
        aws_rg = self.get_aws_rg(aws_build_context)
        if aws_rg is not None:
            from collections import OrderedDict

            if self.aws_resource_groups is None:
                self.aws_resource_groups = OrderedDict()
            self.aws_resource_groups[aws_rg.name] = aws_rg
