from typing import Optional, Any, List, Dict, Literal
from collections import OrderedDict

from phidata.app.base_app import BaseApp, BaseAppArgs


class AwsAppArgs(BaseAppArgs):
    # -*- AWS Configuration
    aws_subnets: Optional[List[str]] = None
    aws_security_groups: Optional[List[str]] = None

    # -*- ECS Configuration
    ecs_cluster: Optional[Any] = None
    ecs_launch_type: str = "FARGATE"
    ecs_task_cpu: str = "512"
    ecs_task_memory: str = "1024"
    ecs_service_count: int = 1
    assign_public_ip: bool = True
    ecs_enable_exec: bool = True

    # -*- LoadBalancer Configuration
    enable_load_balancer: bool = True
    load_balancer: Optional[Any] = None
    # HTTP or HTTPS
    load_balancer_protocol: str = "HTTP"
    # Default 80 for HTTP and 443 for HTTPS
    load_balancer_port: Optional[int] = None
    load_balancer_certificate_arn: Optional[str] = None

    # -*- TargetGroup Configuration
    # HTTP or HTTPS
    target_group_protocol: str = "HTTP"
    # Default 80 for HTTP and 443 for HTTPS
    target_group_port: Optional[int] = None
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
    def aws_subnets(self) -> Optional[List[str]]:
        return self.args.aws_subnets

    @aws_subnets.setter
    def aws_subnets(self, aws_subnets: List[str]) -> None:
        if self.args is not None and aws_subnets is not None:
            self.args.aws_subnets = aws_subnets

    @property
    def aws_security_groups(self) -> Optional[List[str]]:
        return self.args.aws_security_groups

    @aws_security_groups.setter
    def aws_security_groups(self, aws_security_groups: List[str]) -> None:
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
    def enable_load_balancer(self) -> Optional[bool]:
        return self.args.enable_load_balancer

    @enable_load_balancer.setter
    def enable_load_balancer(self, enable_load_balancer: bool) -> None:
        if self.args is not None and enable_load_balancer is not None:
            self.args.enable_load_balancer = enable_load_balancer

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

    def get_aws_rg(self, aws_build_context: Any) -> Optional[Any]:
        return None

    def build_aws_resource_groups(self, aws_build_context: Any) -> None:
        aws_rg = self.get_aws_rg(aws_build_context)
        if aws_rg is not None:
            if self.aws_resource_groups is None:
                self.aws_resource_groups = OrderedDict()
            self.aws_resource_groups[aws_rg.name] = aws_rg

    def get_aws_resource_groups(
        self, aws_build_context: Any
    ) -> Optional[Dict[str, Any]]:
        if self.aws_resource_groups is None:
            self.build_aws_resource_groups(aws_build_context)
        # # Comment out in production
        # if self.aws_resource_groups:
        #     logger.debug("K8sResourceGroups:")
        #     for rg_name, rg in self.aws_resource_groups.items():
        #         logger.debug(
        #             "{}:{}\n{}".format(rg_name, type(rg), rg)
        #         )
        return self.aws_resource_groups
