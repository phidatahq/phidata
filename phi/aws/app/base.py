from typing import Optional, Dict, Any, Union, List

from phi.infra.app.base import InfraApp, WorkspaceVolumeType, AppVolumeType  # noqa: F401
from phi.infra.app.context import ContainerContext
from phi.utils.log import logger


class AwsApp(InfraApp):
    # -*- Aws Configuration
    # List of subnets: str or Subnet
    aws_subnets: Optional[List[Any]] = None
    # List of security groups: str or SecurityGroup
    aws_security_groups: Optional[List[Any]] = None

    # -*- ECS Configuration
    ecs_cluster: Optional[Any] = None
    # If ecs_cluster is None, create a new cluster with name: ecs_cluster_name
    ecs_cluster_name: Optional[str] = None
    ecs_launch_type: str = "FARGATE"
    ecs_task_cpu: str = "1024"
    ecs_task_memory: str = "2048"
    ecs_service_count: int = 1
    assign_public_ip: Optional[bool] = None
    ecs_enable_exec: bool = True

    # -*- LoadBalancer Configuration
    load_balancer: Optional[Any] = None
    listener: Optional[Any] = None
    # Create a load balancer if load_balancer is None
    create_load_balancer: bool = False
    # HTTP or HTTPS
    load_balancer_protocol: str = "HTTP"
    # Security groups for the load balancer: str or SecurityGroup
    load_balancer_security_groups: Optional[List[Any]] = None
    # Default is 80 for HTTP and 443 for HTTPS
    load_balancer_port: Optional[int] = None
    load_balancer_certificate: Optional[Any] = None
    load_balancer_certificate_arn: Optional[str] = None

    # -*- TargetGroup Configuration
    target_group: Optional[Any] = None
    # HTTP or HTTPS
    target_group_protocol: str = "HTTP"
    # Default 80 for HTTP and 443 for HTTPS
    target_group_port: Optional[int] = None
    target_group_type: str = "ip"
    health_check_protocol: Optional[str] = None
    health_check_port: Optional[str] = None
    health_check_enabled: Optional[bool] = None
    health_check_path: Optional[str] = None
    health_check_interval_seconds: Optional[int] = None
    health_check_timeout_seconds: Optional[int] = None
    healthy_threshold_count: Optional[int] = None
    unhealthy_threshold_count: Optional[int] = None

    def build_container_env_ecs(self, container_context: ContainerContext) -> Dict[str, str]:
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
                PHI_RUNTIME_ENV_VAR: "ecs",
                SCRIPTS_DIR_ENV_VAR: container_context.scripts_dir or "",
                STORAGE_DIR_ENV_VAR: container_context.storage_dir or "",
                WORKFLOWS_DIR_ENV_VAR: container_context.workflows_dir or "",
                WORKSPACE_DIR_ENV_VAR: container_context.workspace_dir or "",
                WORKSPACE_ROOT_ENV_VAR: container_context.workspace_root or "",
                "INSTALL_REQUIREMENTS": str(self.install_requirements),
                REQUIREMENTS_FILE_PATH_ENV_VAR: container_context.requirements_file or "",
                "MOUNT_WORKSPACE": str(self.mount_workspace),
                "PRINT_ENV_ON_LOAD": str(self.print_env_on_load),
            }
        )

        if self.set_python_path:
            python_path = self.python_path
            if python_path is None:
                python_path = container_context.workspace_root
                if self.add_python_paths is not None:
                    python_path = "{}:{}".format(python_path, ":".join(self.add_python_paths))
            if python_path is not None:
                container_env[PYTHONPATH_ENV_VAR] = python_path

        # Set aws region and profile
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
        if self.envenv_vars is not None and isinstance(self.envenv_vars, dict):
            container_env.update(
                {k: v for k, v in self.env_vars.items() if v is not None}
            )

        # logger.debug("Container Environment: {}".format(container_env))
        return container_env

    def build_security_groups(self) -> Optional[List[Any]]:
        from phi.aws.resource.ec2.security_group import SecurityGroup

        security_groups: List[SecurityGroup] = []
        if self.args.load_balancer_security_groups is not None:
            for lb_sg in self.args.load_balancer_security_groups:
                if isinstance(lb_sg, SecurityGroup):
                    security_groups.append(lb_sg)
        if self.args.aws_security_groups is not None:
            for sg in self.args.aws_security_groups:
                if isinstance(sg, SecurityGroup):
                    security_groups.append(sg)

        return security_groups if len(security_groups) > 0 else None

    def build_ecs_cluster(self) -> Optional[Any]:
        from phi.aws.resource.ecs.cluster import EcsCluster

        if self.args.ecs_cluster is None:
            return EcsCluster(
                name=f"{self.app_name}-cluster",
                ecs_cluster_name=self.args.ecs_cluster_name or self.app_name,
                capacity_providers=[self.args.ecs_launch_type],
                save_output=self.args.save_output,
                resource_dir=self.args.resource_dir or self.app_name,
                skip_create=self.args.skip_create,
                skip_delete=self.args.skip_delete,
                wait_for_creation=self.args.wait_for_creation,
                wait_for_deletion=self.args.wait_for_deletion,
            )
        elif isinstance(self.args.ecs_cluster, EcsCluster):
            return self.args.ecs_cluster
        else:
            raise Exception(
                f"Invalid ECSCluster: {self.args.ecs_cluster} - Must be of type EcsCluster"
            )

    def build_load_balancer(self) -> Optional[Any]:
        from phi.aws.resource.elb.load_balancer import LoadBalancer

        if self.args.load_balancer is None and self.args.create_load_balancer:
            if self.args.load_balancer_protocol not in ["HTTP", "HTTPS"]:
                raise Exception(
                    "Load Balancer Protocol must be one of: HTTP, HTTPS. "
                    f"Got: {self.args.load_balancer_protocol}"
                )
            return LoadBalancer(
                name=f"{self.app_name}-lb",
                subnets=self.args.aws_subnets,
                security_groups=self.args.load_balancer_security_groups
                or self.args.aws_security_groups,
                protocol=self.args.load_balancer_protocol,
                save_output=self.args.save_output,
                resource_dir=self.args.resource_dir or self.app_name,
                skip_create=self.args.skip_create,
                skip_delete=self.args.skip_delete,
                wait_for_creation=self.args.wait_for_creation,
                wait_for_deletion=self.args.wait_for_deletion,
            )
        elif isinstance(self.args.load_balancer, LoadBalancer):
            return self.args.load_balancer
        else:
            raise Exception(
                f"Invalid LoadBalancer: {self.args.load_balancer} - Must be of type LoadBalancer"
            )

    def build_target_group(self) -> Optional[Any]:
        from phi.aws.resource.elb.target_group import TargetGroup

        if self.args.target_group is None and self.args.create_load_balancer:
            if self.args.target_group_protocol not in ["HTTP", "HTTPS"]:
                raise Exception(
                    "Target Group Protocol must be one of: HTTP, HTTPS. "
                    f"Got: {self.args.target_group_protocol}"
                )
            return TargetGroup(
                name=f"{self.app_name}-tg",
                port=self.args.target_group_port or self.container_port,
                protocol=self.args.target_group_protocol,
                subnets=self.args.aws_subnets,
                target_type=self.args.target_group_type,
                health_check_protocol=self.args.health_check_protocol,
                health_check_port=self.args.health_check_port,
                health_check_enabled=self.args.health_check_enabled,
                health_check_path=self.args.health_check_path,
                health_check_interval_seconds=self.args.health_check_interval_seconds,
                health_check_timeout_seconds=self.args.health_check_timeout_seconds,
                healthy_threshold_count=self.args.healthy_threshold_count,
                unhealthy_threshold_count=self.args.unhealthy_threshold_count,
                save_output=self.args.save_output,
                resource_dir=self.args.resource_dir or self.app_name,
                skip_create=self.args.skip_create,
                skip_delete=self.args.skip_delete,
                wait_for_creation=self.args.wait_for_creation,
                wait_for_deletion=self.args.wait_for_deletion,
            )
        elif isinstance(self.args.target_group, TargetGroup):
            return self.args.target_group
        else:
            raise Exception(
                f"Invalid TargetGroup: {self.args.target_group} - Must be of type TargetGroup"
            )

    def build_listener(self, load_balancer: Any, target_group: Any) -> Optional[Any]:
        from phi.aws.resource.elb.listener import Listener

        if self.args.listener is None and self.args.create_load_balancer:
            listener = Listener(
                name=f"{self.app_name}-listener",
                load_balancer=load_balancer,
                target_group=target_group,
                save_output=self.args.save_output,
                resource_dir=self.args.resource_dir or self.app_name,
                skip_create=self.args.skip_create,
                skip_delete=self.args.skip_delete,
                wait_for_creation=self.args.wait_for_creation,
                wait_for_deletion=self.args.wait_for_deletion,
            )
            if self.args.load_balancer_certificate_arn is not None:
                listener.certificates = [
                    {"CertificateArn": self.args.load_balancer_certificate_arn}
                ]
            if self.args.load_balancer_certificate is not None:
                listener.acm_certificates = [self.args.load_balancer_certificate]
            return listener
        elif isinstance(self.args.listener, Listener):
            return self.args.listener
        else:
            raise Exception(
                f"Invalid Listener: {self.args.listener} - Must be of type Listener"
            )

    def build_container_command_aws(self) -> Optional[List[str]]:
        if isinstance(self.args.command, str):
            return self.args.command.strip().split(" ")
        return self.args.command

    def build_ecs_container(
        self, container_paths: ContainerPathContext
    ) -> Optional[Any]:
        from phi.aws.resource.ecs.container import EcsContainer

        # -*- Build Container Environment
        container_env: Dict[str, str] = self.build_container_env_ecs(
            container_paths=container_paths
        )

        # -*- Build Container Command
        container_cmd: Optional[List[str]] = self.build_container_command_aws()
        if container_cmd:
            logger.debug("Command: {}".format(" ".join(container_cmd)))

        return EcsContainer(
            name=self.app_name,
            image=self.get_image_str(),
            port_mappings=[{"containerPort": self.container_port}],
            command=container_cmd,
            essential=True,
            environment=[{"name": k, "value": v} for k, v in container_env.items()],
            log_configuration={
                "logDriver": "awslogs",
                "options": {
                    "awslogs-group": self.app_name,
                    "awslogs-region": self.aws_region,
                    "awslogs-create-group": "true",
                    "awslogs-stream-prefix": self.app_name,
                },
            },
            linux_parameters={"initProcessEnabled": True},
            env_from_secrets=self.args.aws_secrets,
            save_output=self.args.save_output,
            resource_dir=self.args.resource_dir or self.app_name,
            skip_create=self.args.skip_create,
            skip_delete=self.args.skip_delete,
            wait_for_creation=self.args.wait_for_creation,
            wait_for_deletion=self.args.wait_for_deletion,
        )

    def build_ecs_task_definition(self, ecs_container: Any) -> Optional[Any]:
        from phi.aws.resource.ecs.task_definition import EcsTaskDefinition

        return EcsTaskDefinition(
            name=f"{self.app_name}-td",
            family=self.app_name,
            network_mode="awsvpc",
            cpu=self.args.ecs_task_cpu,
            memory=self.args.ecs_task_memory,
            containers=[ecs_container],
            requires_compatibilities=[self.args.ecs_launch_type],
            add_ecs_exec_policy=self.args.ecs_enable_exec,
            add_ecs_secret_policy=True,
            save_output=self.args.save_output,
            resource_dir=self.args.resource_dir or self.app_name,
            skip_create=self.args.skip_create,
            skip_delete=self.args.skip_delete,
            wait_for_creation=self.args.wait_for_creation,
            wait_for_deletion=self.args.wait_for_deletion,
        )

    def build_ecs_service(
        self,
        ecs_cluster: Any,
        ecs_task_definition: Any,
        target_group: Any,
        ecs_container: Any,
    ) -> Optional[Any]:
        from phi.aws.resource.ecs.service import EcsService

        return EcsService(
            name=f"{self.app_name}-service",
            desired_count=self.args.ecs_service_count,
            launch_type=self.args.ecs_launch_type,
            cluster=ecs_cluster,
            task_definition=ecs_task_definition,
            target_group=target_group,
            target_container_name=ecs_container.name,
            target_container_port=self.container_port,
            subnets=self.args.aws_subnets,
            security_groups=self.args.aws_security_groups,
            assign_public_ip=self.args.assign_public_ip,
            # Force delete the service.
            force_delete=True,
            # Force a new deployment of the service on update.
            force_new_deployment=True,
            enable_execute_command=self.args.ecs_enable_exec,
            save_output=self.args.save_output,
            resource_dir=self.args.resource_dir or self.app_name,
            skip_create=self.args.skip_create,
            skip_delete=self.args.skip_delete,
            wait_for_creation=self.args.wait_for_creation,
            wait_for_deletion=self.args.wait_for_deletion,
        )

    def build_resources(self, build_context: Any) -> Optional[Any]:
        from phi.aws.resource.group import (
            AwsResourceGroup,
            EcsCluster,
            EcsContainer,
            EcsTaskDefinition,
            EcsService,
            LoadBalancer,
            TargetGroup,
            Listener,
            AcmCertificate,
            SecurityGroup,
        )
        from phi.aws.app.context import AwsBuildContext

        logger.debug(f"------------ Building {self.get_app_name()} ------------")
        # -*- Build ContainerContext
        container_context: Optional[ContainerContext] = self.build_container_context()
        if container_context is None:
            raise Exception("Could not build ContainerContext")
        logger.debug(f"ContainerContext: {container_context.model_dump_json(indent=2)}")

        if build_context is None or not isinstance(build_context, AwsBuildContext):
            logger.error("build_context not a AwsBuildContext")
            return None

        # -*- Build Security Groups
        security_groups: Optional[List[SecurityGroup]] = self.build_security_groups()

        # -*- Build ECS cluster
        ecs_cluster: Optional[EcsCluster] = self.build_ecs_cluster()

        # -*- Build Load Balancer
        load_balancer: Optional[LoadBalancer] = self.build_load_balancer()

        # -*- Build Target Group
        target_group: Optional[TargetGroup] = self.build_target_group()

        # -*- Build Listener
        listener: Optional[Listener] = self.build_listener(
            load_balancer=load_balancer, target_group=target_group
        )

        # -*- Build ECSContainer
        ecs_container: Optional[EcsContainer] = self.build_ecs_container(
            container_context=container_context
        )

        # -*- Build ECS Task Definition
        ecs_task_definition: Optional[
            EcsTaskDefinition
        ] = self.build_ecs_task_definition(ecs_container=ecs_container)

        # -*- Build ECS Service
        ecs_service: Optional[EcsService] = self.build_ecs_service(
            ecs_cluster=ecs_cluster,
            ecs_task_definition=ecs_task_definition,
            target_group=target_group,
            ecs_container=ecs_container,
        )

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

        # -*- Create app_resources list
        app_resources: List[AwsResource] = []
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
