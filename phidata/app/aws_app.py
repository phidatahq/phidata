from typing import Optional, Any, List, Dict
from collections import OrderedDict

from phidata.app.base_app import BaseApp, BaseAppArgs
from phidata.types.context import ContainerPathContext
from phidata.utils.log import logger


class AwsAppArgs(BaseAppArgs):
    # -*- AWS Configuration
    # List of subnets: str or Subnet
    aws_subnets: Optional[List[Any]] = None
    # List of security groups: str or SecurityGroup
    aws_security_groups: Optional[List[Any]] = None

    # -*- ECS Configuration
    ecs_cluster: Optional[Any] = None
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
    load_balancer_security_groups: Optional[List[Any]] = None
    # Default 80 for HTTP and 443 for HTTPS
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


class AwsApp(BaseApp):
    def __init__(self) -> None:
        super().__init__()

        # Args for the AwsAppArgs, updated by the subclass
        self.args: AwsAppArgs = AwsAppArgs()

        # Dict of AwsResourceGroups
        # Type: Optional[Dict[str, AwsResourceGroup]]
        self.aws_resource_groups: Optional[Dict[str, Any]] = None

    @property
    def aws_subnets(self) -> Optional[List[Any]]:
        return self.args.aws_subnets

    @aws_subnets.setter
    def aws_subnets(self, aws_subnets: List[Any]) -> None:
        if self.args is not None and aws_subnets is not None:
            self.args.aws_subnets = aws_subnets

    @property
    def aws_security_groups(self) -> Optional[List[Any]]:
        return self.args.aws_security_groups

    @aws_security_groups.setter
    def aws_security_groups(self, aws_security_groups: List[Any]) -> None:
        if self.args is not None and aws_security_groups is not None:
            self.args.aws_security_groups = aws_security_groups

    @property
    def ecs_cluster(self) -> Optional[Any]:
        return self.args.ecs_cluster

    @ecs_cluster.setter
    def ecs_cluster(self, ecs_cluster: Any) -> None:
        if self.args is not None and ecs_cluster is not None:
            self.args.ecs_cluster = ecs_cluster

    @property
    def ecs_launch_type(self) -> Optional[str]:
        return self.args.ecs_launch_type

    @ecs_launch_type.setter
    def ecs_launch_type(self, ecs_launch_type: str) -> None:
        if self.args is not None and ecs_launch_type is not None:
            self.args.ecs_launch_type = ecs_launch_type

    @property
    def ecs_task_cpu(self) -> Optional[str]:
        return self.args.ecs_task_cpu

    @ecs_task_cpu.setter
    def ecs_task_cpu(self, ecs_task_cpu: str) -> None:
        if self.args is not None and ecs_task_cpu is not None:
            self.args.ecs_task_cpu = ecs_task_cpu

    @property
    def ecs_task_memory(self) -> Optional[str]:
        return self.args.ecs_task_memory

    @ecs_task_memory.setter
    def ecs_task_memory(self, ecs_task_memory: str) -> None:
        if self.args is not None and ecs_task_memory is not None:
            self.args.ecs_task_memory = ecs_task_memory

    @property
    def ecs_service_count(self) -> Optional[int]:
        return self.args.ecs_service_count

    @ecs_service_count.setter
    def ecs_service_count(self, ecs_service_count: int) -> None:
        if self.args is not None and ecs_service_count is not None:
            self.args.ecs_service_count = ecs_service_count

    @property
    def assign_public_ip(self) -> Optional[bool]:
        return self.args.assign_public_ip

    @assign_public_ip.setter
    def assign_public_ip(self, assign_public_ip: bool) -> None:
        if self.args is not None and assign_public_ip is not None:
            self.args.assign_public_ip = assign_public_ip

    @property
    def ecs_enable_exec(self) -> Optional[bool]:
        return self.args.ecs_enable_exec

    @ecs_enable_exec.setter
    def ecs_enable_exec(self, ecs_enable_exec: bool) -> None:
        if self.args is not None and ecs_enable_exec is not None:
            self.args.ecs_enable_exec = ecs_enable_exec

    @property
    def create_load_balancer(self) -> Optional[bool]:
        return self.args.create_load_balancer

    @create_load_balancer.setter
    def create_load_balancer(self, create_load_balancer: bool) -> None:
        if self.args is not None and create_load_balancer is not None:
            self.args.create_load_balancer = create_load_balancer

    @property
    def load_balancer(self) -> Optional[Any]:
        return self.args.load_balancer

    @load_balancer.setter
    def load_balancer(self, load_balancer: Any) -> None:
        if self.args is not None and load_balancer is not None:
            self.args.load_balancer = load_balancer

    @property
    def load_balancer_protocol(self) -> Optional[str]:
        return self.args.load_balancer_protocol

    @load_balancer_protocol.setter
    def load_balancer_protocol(self, load_balancer_protocol: str) -> None:
        if self.args is not None and load_balancer_protocol is not None:
            self.args.load_balancer_protocol = load_balancer_protocol

    @property
    def load_balancer_port(self) -> Optional[int]:
        return self.args.load_balancer_port

    @load_balancer_port.setter
    def load_balancer_port(self, load_balancer_port: int) -> None:
        if self.args is not None and load_balancer_port is not None:
            self.args.load_balancer_port = load_balancer_port

    @property
    def load_balancer_certificate_arn(self) -> Optional[str]:
        return self.args.load_balancer_certificate_arn

    @load_balancer_certificate_arn.setter
    def load_balancer_certificate_arn(self, load_balancer_certificate_arn: str) -> None:
        if self.args is not None and load_balancer_certificate_arn is not None:
            self.args.load_balancer_certificate_arn = load_balancer_certificate_arn

    def get_container_env_ecs(
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
                PHIDATA_RUNTIME_ENV_VAR: "ecs",
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
                "PRINT_ENV_ON_LOAD": str(self.args.print_env_on_load),
            }
        )

        if self.args.set_python_path:
            python_path = self.args.python_path
            if python_path is None:
                python_path = container_paths.workspace_root
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
                {k: v for k, v in self.args.env.items() if v is not None}
            )

        # logger.debug("Container Environment: {}".format(container_env))
        return container_env

    def get_container_command_aws(self) -> Optional[List[str]]:
        if isinstance(self.args.command, str):
            return self.args.command.split(" ")
        return self.args.command

    def get_aws_rg(
        self, aws_build_context: Any, defer_api_calls: bool = False
    ) -> Optional[Any]:
        from phidata.aws.resource.group import (
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

        # -*- Build Container Paths
        container_paths: Optional[ContainerPathContext] = self.get_container_paths()
        if container_paths is None:
            raise Exception("Could not build Container Paths")
        logger.debug(f"ContainerPaths: {container_paths.json(indent=2)}")

        app_name = self.name
        workspace_name = container_paths.workspace_name
        logger.debug(f"Building AwsResourceGroup: {app_name} for {workspace_name}")

        # -*- Build Container Environment
        container_env: Dict[str, str] = self.get_container_env_ecs(
            container_paths=container_paths
        )

        # -*- Create Security Groups
        security_groups: List[SecurityGroup] = []
        if self.args.aws_security_groups is not None:
            for sg in self.args.aws_security_groups:
                if isinstance(sg, SecurityGroup):
                    security_groups.append(sg)
        if self.args.load_balancer_security_groups is not None:
            for lb_sg in self.args.load_balancer_security_groups:
                if isinstance(lb_sg, SecurityGroup):
                    security_groups.append(lb_sg)

        # -*- Create ECS cluster
        ecs_cluster = self.args.ecs_cluster
        if ecs_cluster is None:
            ecs_cluster = EcsCluster(
                name=f"{app_name}-cluster",
                ecs_cluster_name=app_name,
                capacity_providers=[self.args.ecs_launch_type],
                save_output=self.args.save_output,
                resource_dir=self.args.resource_dir or app_name,
                skip_create=self.args.skip_create,
                skip_delete=self.args.skip_delete,
                wait_for_creation=self.args.wait_for_creation,
                wait_for_deletion=self.args.wait_for_deletion,
            )

        # -*- Create Load Balancer
        load_balancer = self.args.load_balancer
        if load_balancer is None and self.args.create_load_balancer:
            if self.args.load_balancer_protocol not in ["HTTP", "HTTPS"]:
                raise Exception(
                    "Load Balancer Protocol must be one of: HTTP, HTTPS. "
                    f"Got: {self.args.load_balancer_protocol}"
                )
            load_balancer_sgs = (
                self.args.load_balancer_security_groups or self.args.aws_security_groups
            )
            load_balancer = LoadBalancer(
                name=f"{app_name}-lb",
                subnets=self.args.aws_subnets,
                security_groups=load_balancer_sgs,
                protocol=self.args.load_balancer_protocol,
                save_output=self.args.save_output,
                resource_dir=self.args.resource_dir or app_name,
                skip_create=self.args.skip_create,
                skip_delete=self.args.skip_delete,
                wait_for_creation=self.args.wait_for_creation,
                wait_for_deletion=self.args.wait_for_deletion,
            )

        # -*- Create Target Group
        target_group = self.args.target_group
        if target_group is None and self.args.create_load_balancer:
            if self.args.target_group_protocol not in ["HTTP", "HTTPS"]:
                raise Exception(
                    "Target Group Protocol must be one of: HTTP, HTTPS. "
                    f"Got: {self.args.target_group_protocol}"
                )
            target_group = TargetGroup(
                name=f"{app_name}-tg",
                port=self.container_port,
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
                resource_dir=self.args.resource_dir or app_name,
                skip_create=self.args.skip_create,
                skip_delete=self.args.skip_delete,
                wait_for_creation=self.args.wait_for_creation,
                wait_for_deletion=self.args.wait_for_deletion,
            )

        # -*- Create Listener
        listener = self.args.listener
        if listener is None and self.args.create_load_balancer:
            listener = Listener(
                name=f"{app_name}-listener",
                load_balancer=load_balancer,
                target_group=target_group,
                save_output=self.args.save_output,
                resource_dir=self.args.resource_dir or app_name,
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

        # -*- Build Container Command
        container_cmd: Optional[List[str]] = self.get_container_command_aws()
        if container_cmd:
            logger.debug("Command: {}".format(" ".join(container_cmd)))

        # -*- Create ECS Container
        ecs_container = EcsContainer(
            name=app_name,
            image=self.get_image_str(),
            port_mappings=[{"containerPort": self.container_port}],
            command=container_cmd,
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
            env_from_secrets=self.args.aws_secrets,
            save_output=self.args.save_output,
            resource_dir=self.args.resource_dir or app_name,
            skip_create=self.args.skip_create,
            skip_delete=self.args.skip_delete,
            wait_for_creation=self.args.wait_for_creation,
            wait_for_deletion=self.args.wait_for_deletion,
        )

        # -*- Create ECS Task Definition
        ecs_task_definition = EcsTaskDefinition(
            name=f"{app_name}-td",
            family=app_name,
            network_mode="awsvpc",
            cpu=self.args.ecs_task_cpu,
            memory=self.args.ecs_task_memory,
            containers=[ecs_container],
            requires_compatibilities=[self.args.ecs_launch_type],
            add_ecs_exec_policy=True,
            add_ecs_secret_policy=True,
            save_output=self.args.save_output,
            resource_dir=self.args.resource_dir or app_name,
            skip_create=self.args.skip_create,
            skip_delete=self.args.skip_delete,
            wait_for_creation=self.args.wait_for_creation,
            wait_for_deletion=self.args.wait_for_deletion,
        )

        # -*- Create ECS Service
        ecs_service = EcsService(
            name=f"{app_name}-service",
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
            save_output=self.args.save_output,
            resource_dir=self.args.resource_dir or app_name,
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
            security_groups=security_groups if len(security_groups) > 0 else None,
        )

    def build_aws_resource_groups(
        self, aws_build_context: Any, defer_api_calls: bool = False
    ) -> None:
        aws_rg = self.get_aws_rg(aws_build_context)
        if aws_rg is not None:
            if self.aws_resource_groups is None:
                self.aws_resource_groups = OrderedDict()
            self.aws_resource_groups[aws_rg.name] = aws_rg

    def get_aws_resource_groups(
        self, aws_build_context: Any, defer_api_calls: bool = False
    ) -> Optional[Dict[str, Any]]:
        if self.aws_resource_groups is None:
            self.build_aws_resource_groups(aws_build_context)
        # # Comment out in production
        # if self.aws_resource_groups:
        #     logger.debug("AwsResourceGroups:")
        #     for rg_name, rg in self.aws_resource_groups.items():
        #         logger.debug(
        #             "{}:{}\n{}".format(rg_name, type(rg), rg)
        #         )
        return self.aws_resource_groups
