from pathlib import Path
from typing import Optional, Dict, Any, List, Union

from phidata.app.aws_app import AwsApp, AwsAppArgs
from phidata.app.base_app import WorkspaceVolumeType
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


class DjangoAppArgs(AwsAppArgs, DockerAppArgs, K8sAppArgs):
    # -*- Django Configuration
    # Use NGINX to serve static file
    enable_nginx: bool = False
    nginx_image: Optional[Any] = None
    nginx_image_name: str = "phidata/django-nginx"
    nginx_image_tag: str = "latest"
    nginx_container_port: int = 80


class DjangoApp(AwsApp, DockerApp, K8sApp):
    def __init__(
        self,
        name: str = "django",
        version: str = "1",
        enabled: bool = True,
        # -*- Image Configuration,
        # Image can be provided as a DockerImage object or as image_name:image_tag
        image: Optional[Any] = None,
        image_name: str = "phidata/django",
        image_tag: str = "4.2.2",
        entrypoint: Optional[Union[str, List[str]]] = None,
        command: Union[str, List[str]] = "python manage.py runserver 0.0.0.0:8000",
        # -*- Django Configuration,
        # Use NGINX to serve static file,
        enable_nginx: bool = False,
        nginx_image: Optional[Any] = None,
        nginx_image_name: str = "phidata/django-nginx",
        nginx_image_tag: str = "latest",
        nginx_container_port: int = 80,
        # -*- Debug Mode
        debug_mode: bool = False,
        # -*- Python Configuration,
        # Install python dependencies using a requirements.txt file,
        install_requirements: bool = False,
        # Path to the requirements.txt file relative to the workspace_root,
        requirements_file: str = "requirements.txt",
        # Set the PYTHONPATH env var,
        set_python_path: bool = False,
        # Manually provide the PYTHONPATH,
        python_path: Optional[str] = None,
        # Add paths to the PYTHONPATH env var,
        # If python_path is provided, this value is ignored,
        add_python_paths: Optional[List[str]] = None,
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
        # -*- Container Ports,
        # Open a container port if open_container_port=True,
        open_container_port: bool = True,
        # Port number on the container,
        container_port: int = 8000,
        # Port name (only used by the K8sContainer),
        container_port_name: str = "http",
        # Host port to map to the container port,
        container_host_port: int = 8000,
        # -*- Workspace Volume,
        # Mount the workspace directory on the container,
        mount_workspace: bool = False,
        workspace_volume_name: Optional[str] = None,
        workspace_volume_type: Optional[WorkspaceVolumeType] = None,
        # Path to mount the workspace volume inside the container,
        workspace_dir_container_path: str = "/usr/local/app",
        # Add the workspace name to the container path,
        add_workspace_name_to_container_path: bool = False,
        # -*- If workspace_volume_type=WorkspaceVolumeType.HostPath,
        # Mount workspace_dir to workspace_dir_container_path,
        # If None, use the workspace_root,
        workspace_dir: Optional[str] = None,
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
        # -*- Pod Configuration,
        pod_name: Optional[str] = None,
        pod_annotations: Optional[Dict[str, str]] = None,
        pod_node_selector: Optional[Dict[str, str]] = None,
        # -*- Secret Configuration,
        secret_name: Optional[str] = None,
        # -*- Configmap Configuration,
        configmap_name: Optional[str] = None,
        # -*- Deployment Configuration,
        replicas: int = 1,
        deploy_name: Optional[str] = None,
        # Type: ImagePullPolicy,
        image_pull_policy: Optional[Any] = None,
        # Type: RestartPolicy,
        deploy_restart_policy: Optional[Any] = None,
        deploy_labels: Optional[Dict[str, Any]] = None,
        termination_grace_period_seconds: Optional[int] = None,
        # Key to spread the pods across a topology,
        topology_spread_key: Optional[str] = None,
        # The degree to which pods may be unevenly distributed,
        topology_spread_max_skew: Optional[int] = None,
        # How to deal with a pod if it doesn't satisfy the spread constraint.,
        topology_spread_when_unsatisfiable: Optional[str] = None,
        # -*- Service Configuration,
        create_service: bool = False,
        service_name: Optional[str] = None,
        # Type: ServiceType,
        service_type: Optional[Any] = None,
        # The port exposed by the service.,
        service_port: int = 8000,
        # The node_port exposed by the service if service_type = ServiceType.NODE_PORT,
        service_node_port: Optional[int] = None,
        # The target_port is the port to access on the pods targeted by the service.,
        # It can be the port number or port name on the pod.,
        service_target_port: Optional[Union[str, int]] = None,
        # Extra ports exposed by the webserver service. Type: List[CreatePort],
        service_ports: Optional[List[Any]] = None,
        service_labels: Optional[Dict[str, Any]] = None,
        service_annotations: Optional[Dict[str, str]] = None,
        # If ServiceType == ServiceType.LoadBalancer,
        service_health_check_node_port: Optional[int] = None,
        service_internal_traffic_policy: Optional[str] = None,
        service_load_balancer_class: Optional[str] = None,
        service_load_balancer_ip: Optional[str] = None,
        service_load_balancer_source_ranges: Optional[List[str]] = None,
        service_allocate_load_balancer_node_ports: Optional[bool] = None,
        # -*- Ingress Configuration,
        create_ingress: bool = False,
        ingress_name: Optional[str] = None,
        ingress_annotations: Optional[Dict[str, str]] = None,
        # -*- RBAC Configuration,
        use_rbac: bool = False,
        # Create a Namespace with name ns_name & default values,
        ns_name: Optional[str] = None,
        # or Provide the full Namespace definition,
        # Type: CreateNamespace,
        namespace: Optional[Any] = None,
        # Create a ServiceAccount with name sa_name & default values,
        sa_name: Optional[str] = None,
        # or Provide the full ServiceAccount definition,
        # Type: CreateServiceAccount,
        service_account: Optional[Any] = None,
        # Create a ClusterRole with name cr_name & default values,
        cr_name: Optional[str] = None,
        # or Provide the full ClusterRole definition,
        # Type: CreateClusterRole,
        cluster_role: Optional[Any] = None,
        # Create a ClusterRoleBinding with name crb_name & default values,
        crb_name: Optional[str] = None,
        # or Provide the full ClusterRoleBinding definition,
        # Type: CreateClusterRoleBinding,
        cluster_role_binding: Optional[Any] = None,
        # -*- AWS Configuration,
        aws_subnets: Optional[List[str]] = None,
        aws_security_groups: Optional[List[Any]] = None,
        # -*- ECS Configuration,
        ecs_cluster: Optional[Any] = None,
        # If ecs_cluster is None, create a new cluster with ecs_cluster_name,
        ecs_cluster_name: Optional[str] = None,
        ecs_launch_type: str = "FARGATE",
        ecs_task_cpu: str = "1024",
        ecs_task_memory: str = "2048",
        ecs_service_count: int = 1,
        assign_public_ip: bool = True,
        ecs_enable_exec: bool = True,
        # -*- LoadBalancer Configuration,
        load_balancer: Optional[Any] = None,
        listener: Optional[Any] = None,
        # Create a load balancer if load_balancer is None,
        create_load_balancer: bool = False,
        # HTTP or HTTPS,
        load_balancer_protocol: str = "HTTP",
        load_balancer_security_groups: Optional[List[Any]] = None,
        # Default 80 for HTTP and 443 for HTTPS,
        load_balancer_port: Optional[int] = None,
        load_balancer_certificate: Optional[Any] = None,
        load_balancer_certificate_arn: Optional[str] = None,
        # -*- TargetGroup Configuration,
        target_group: Optional[Any] = None,
        # HTTP or HTTPS,
        target_group_protocol: str = "HTTP",
        # Default 80 for HTTP and 443 for HTTPS,
        target_group_port: Optional[int] = None,
        target_group_type: str = "ip",
        health_check_protocol: Optional[str] = None,
        health_check_port: Optional[str] = None,
        health_check_enabled: Optional[bool] = None,
        health_check_path: Optional[str] = None,
        health_check_interval_seconds: Optional[int] = None,
        health_check_timeout_seconds: Optional[int] = None,
        healthy_threshold_count: Optional[int] = None,
        unhealthy_threshold_count: Optional[int] = None,
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
            self.args: DjangoAppArgs = DjangoAppArgs(
                name=name,
                version=version,
                enabled=enabled,
                image=image,
                image_name=image_name,
                image_tag=image_tag,
                entrypoint=entrypoint,
                command=command,
                enable_nginx=enable_nginx,
                nginx_image=nginx_image,
                nginx_image_name=nginx_image_name,
                nginx_image_tag=nginx_image_tag,
                nginx_container_port=nginx_container_port,
                debug_mode=debug_mode,
                install_requirements=install_requirements,
                requirements_file=requirements_file,
                set_python_path=set_python_path,
                python_path=python_path,
                add_python_paths=add_python_paths,
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
                workspace_dir_container_path=workspace_dir_container_path,
                add_workspace_name_to_container_path=add_workspace_name_to_container_path,
                workspace_dir=workspace_dir,
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
                pod_name=pod_name,
                pod_annotations=pod_annotations,
                pod_node_selector=pod_node_selector,
                secret_name=secret_name,
                configmap_name=configmap_name,
                replicas=replicas,
                deploy_name=deploy_name,
                image_pull_policy=image_pull_policy,
                deploy_restart_policy=deploy_restart_policy,
                deploy_labels=deploy_labels,
                termination_grace_period_seconds=termination_grace_period_seconds,
                topology_spread_key=topology_spread_key,
                topology_spread_max_skew=topology_spread_max_skew,
                topology_spread_when_unsatisfiable=topology_spread_when_unsatisfiable,
                create_service=create_service,
                service_name=service_name,
                service_type=service_type,
                service_port=service_port,
                service_node_port=service_node_port,
                service_target_port=service_target_port,
                service_ports=service_ports,
                service_labels=service_labels,
                service_annotations=service_annotations,
                service_health_check_node_port=service_health_check_node_port,
                service_internal_traffic_policy=service_internal_traffic_policy,
                service_load_balancer_class=service_load_balancer_class,
                service_load_balancer_ip=service_load_balancer_ip,
                service_load_balancer_source_ranges=service_load_balancer_source_ranges,
                service_allocate_load_balancer_node_ports=service_allocate_load_balancer_node_ports,
                create_ingress=create_ingress,
                ingress_name=ingress_name,
                ingress_annotations=ingress_annotations,
                use_rbac=use_rbac,
                ns_name=ns_name,
                namespace=namespace,
                sa_name=sa_name,
                service_account=service_account,
                cr_name=cr_name,
                cluster_role=cluster_role,
                crb_name=crb_name,
                cluster_role_binding=cluster_role_binding,
                aws_subnets=aws_subnets,
                aws_security_groups=aws_security_groups,
                ecs_cluster=ecs_cluster,
                ecs_cluster_name=ecs_cluster_name,
                ecs_launch_type=ecs_launch_type,
                ecs_task_cpu=ecs_task_cpu,
                ecs_task_memory=ecs_task_memory,
                ecs_service_count=ecs_service_count,
                assign_public_ip=assign_public_ip,
                ecs_enable_exec=ecs_enable_exec,
                load_balancer=load_balancer,
                listener=listener,
                create_load_balancer=create_load_balancer,
                load_balancer_protocol=load_balancer_protocol,
                load_balancer_security_groups=load_balancer_security_groups,
                load_balancer_port=load_balancer_port,
                load_balancer_certificate=load_balancer_certificate,
                load_balancer_certificate_arn=load_balancer_certificate_arn,
                target_group=target_group,
                target_group_protocol=target_group_protocol,
                target_group_port=target_group_port,
                target_group_type=target_group_type,
                health_check_protocol=health_check_protocol,
                health_check_port=health_check_port,
                health_check_enabled=health_check_enabled,
                health_check_path=health_check_path,
                health_check_interval_seconds=health_check_interval_seconds,
                health_check_timeout_seconds=health_check_timeout_seconds,
                healthy_threshold_count=healthy_threshold_count,
                unhealthy_threshold_count=unhealthy_threshold_count,
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
            AcmCertificate,
            SecurityGroup,
        )
        from phidata.utils.common import get_default_volume_name

        # -*- Build Container Paths
        container_paths: Optional[ContainerPathContext] = self.build_container_paths()
        if container_paths is None:
            raise Exception("Could not build Container Paths")
        logger.debug(f"ContainerPaths: {container_paths.json(indent=2)}")

        workspace_name = container_paths.workspace_name
        logger.debug(f"Building AwsResourceGroup: {self.app_name} for {workspace_name}")

        # -*- Build Security Groups
        security_groups: Optional[List[SecurityGroup]] = self.build_security_groups()

        # -*- Build ECS cluster
        ecs_cluster: Optional[EcsCluster] = self.build_ecs_cluster()

        # -*- Build Load Balancer
        load_balancer: Optional[LoadBalancer] = self.build_load_balancer()

        # -*- Build Target Group
        target_group: Optional[TargetGroup] = self.build_target_group()
        if (
            self.args.enable_nginx
            and self.args.target_group is None
            and self.args.target_group_port is None
        ):
            if target_group is not None:
                target_group.port = self.args.nginx_container_port
            else:
                logger.error(f"TargetGroup for {self.app_name} is None")

        # -*- Build Listener
        listener: Optional[Listener] = self.build_listener(
            load_balancer=load_balancer, target_group=target_group
        )

        # -*- Build ECSContainer
        ecs_container: Optional[EcsContainer] = self.build_ecs_container(
            container_paths=container_paths
        )

        nginx_container: Optional[EcsContainer] = None
        nginx_shared_volume: Optional[EcsVolume] = None
        # -*- Add Nginx Container
        if self.args.enable_nginx and ecs_container is not None:
            nginx_container_name = f"{self.app_name}-nginx"
            nginx_shared_volume = EcsVolume(name=get_default_volume_name(self.app_name))
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
                environment=ecs_container.environment,
                log_configuration={
                    "logDriver": "awslogs",
                    "options": {
                        "awslogs-group": self.app_name,
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
                linux_parameters=ecs_container.linux_parameters,
                env_from_secrets=ecs_container.env_from_secrets,
                save_output=ecs_container.save_output,
                resource_dir=ecs_container.resource_dir,
                skip_create=ecs_container.skip_create,
                skip_delete=ecs_container.skip_delete,
                wait_for_creation=ecs_container.wait_for_creation,
                wait_for_deletion=ecs_container.wait_for_deletion,
            )

            # Add shared volume to ecs_container
            ecs_container.mount_points = nginx_container.mount_points

        # -*- Build ECS Task Definition
        ecs_task_definition: Optional[
            EcsTaskDefinition
        ] = self.build_ecs_task_definition(ecs_container=ecs_container)
        # Add nginx_container to ecs_task_definition
        if self.args.enable_nginx:
            if ecs_task_definition is not None:
                if nginx_container is not None:
                    if ecs_task_definition.containers:
                        ecs_task_definition.containers.append(nginx_container)
                    else:
                        logger.error("TaskDefinition.containers is None")
                else:
                    logger.error("nginx_container is None")
                if nginx_shared_volume:
                    ecs_task_definition.volumes = [nginx_shared_volume]
            else:
                logger.error(f"TaskDefinition for {self.app_name} is None")

        # -*- Build ECS Service
        ecs_service: Optional[EcsService] = self.build_ecs_service(
            ecs_cluster=ecs_cluster,
            ecs_task_definition=ecs_task_definition,
            target_group=target_group,
            ecs_container=ecs_container,
        )
        # Set nginx_container as target_container
        if self.args.enable_nginx:
            if ecs_service is not None:
                if nginx_container is not None:
                    ecs_service.target_container_name = nginx_container.name
                    ecs_service.target_container_port = self.args.nginx_container_port
                else:
                    logger.error("nginx_container is None")
            else:
                logger.error(f"EcsService for {self.app_name} is None")

        # -*- Create AwsResourceGroup
        return AwsResourceGroup(
            name=self.app_name,
            enabled=self.enabled,
            ecs_clusters=[ecs_cluster],
            ecs_task_definitions=[ecs_task_definition],
            ecs_services=[ecs_service],
            load_balancers=[load_balancer],
            target_groups=[target_group],
            listeners=[listener],
            security_groups=security_groups,
        )
