from typing import Optional, Any, Dict, List

from phidata.aws.api_client import AwsApiClient
from phidata.aws.resource.base import AwsResource
from phidata.utils.cli_console import print_info, print_error, print_warning
from phidata.utils.log import logger


class LoadBalancer(AwsResource):
    """
    https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/elbv2.html
    """

    resource_type = "LoadBalancer"
    service_name = "elbv2"

    # Name of the Load Balancer.
    name: str
    subnets: Optional[List[str]] = None
    subnet_mappings: Optional[List[Dict[str, str]]] = None
    security_groups: Optional[List[str]] = None
    scheme: Optional[str] = None
    tags: Optional[List[Dict[str, str]]] = None
    type: Optional[str] = None
    ip_address_type: Optional[str] = None
    customer_owned_ipv_4_pool: Optional[str] = None

    # Target Group
    protocol: Optional[str] = None
    protocol_version: str
    port: int
    vpc_id: Optional[str] = None
    health_check_protocol: Optional[str] = None
    health_check_port: Optional[str] = None
    health_check_enabled: Optional[str] = None
    health_check_path: Optional[str] = None
    health_check_interval_seconds: int
    health_check_timeout_seconds: int
    healthy_threshold_count: int
    unhealthy_threshold_count: int
    matcher: Optional[Dict[str, str]] = None
    target_type: Optional[str] = None
    tags: Optional[List[Dict[str, str]]] = None
    ip_address_type: Optional[str] = None

    def _create(self, aws_client: AwsApiClient) -> bool:
        """Creates the Load Balancer

        Args:
            aws_client: The AwsApiClient for the current Load Balancer
        """
        print_info(f"Creating {self.get_resource_type()}: {self.get_resource_name()}")

        # create a dict of args which are not null, otherwise aws type validation fails
        not_null_args: Dict[str, Any] = {}
        if self.subnets is not None:
            not_null_args["Subnets"] = self.subnets
        if self.subnet_mappings is not None:
            not_null_args["SubnetMappings"] = self.subnet_mappings
        if self.security_groups is not None:
            not_null_args["SecurityGroups"] = self.security_groups
        if self.scheme is not None:
            not_null_args["Scheme"] = self.scheme
        if self.tags is not None:
            not_null_args["tags"] = self.tags
        if self.type is not None:
            not_null_args["Type"] = self.type
        if self.ip_address_type is not None:
            not_null_args["IpAddressType"] = self.ip_address_type
        if self.customer_owned_ipv_4_pool is not None:
            not_null_args["CustomerOwnedIpv4Pool"] = self.customer_owned_ipv_4_pool

        # Create LoadBalancer
        service_client = self.get_service_client(aws_client)
        try:
            create_response = service_client.create_load_balancer(
                Name=self.name,
                **not_null_args,
            )
            logger.debug(f"Response: {create_response}")
            resource_dict = create_response.get("LoadBalancers", {})

            # Validate resource creation
            if resource_dict is not None:
                print_info(f"LoadBalancer created: {self.get_resource_name()}")
                self.active_resource = create_response
                return True
        except Exception as e:
            print_error(f"{self.get_resource_type()} could not be created.")
            print_error(e)
        return False

    def _read(self, aws_client: AwsApiClient) -> Optional[Any]:
        """Returns the LoadBalancer

        Args:
            aws_client: The AwsApiClient for the current LoadBalancer
        """
        logger.debug(f"Reading {self.get_resource_type()}: {self.get_resource_name()}")

        from botocore.exceptions import ClientError

        service_client = self.get_service_client(aws_client)
        try:
            describe_response = service_client.describe_load_balancers(
                Names=[self.name]
            )
            logger.debug(f"LoadBalancers: {describe_response}")
            resource_list = describe_response.get("LoadBalancers", None)

            if resource_list is not None and isinstance(resource_list, list):
                self.active_resource = resource_list[0]
        except ClientError as ce:
            logger.debug(f"ClientError: {ce}")
        except Exception as e:
            print_error(f"Error reading {self.get_resource_type()}.")
            print_error(e)
        return self.active_resource

    def _delete(self, aws_client: AwsApiClient) -> bool:
        """Deletes the LoadBalancer

        Args:
            aws_client: The AwsApiClient for the current LoadBalancer
        """
        print_info(f"Deleting {self.get_resource_type()}: {self.get_resource_name()}")

        service_client = self.get_service_client(aws_client)
        self.active_resource = None

        try:
            delete_response = service_client.delete_load_balancer(
                LoadBalancerArn=self.get_arn
            )
            logger.debug(f"LoadBalancer: {delete_response}")
            print_info(
                f"{self.get_resource_type()}: {self.get_resource_name()} deleted"
            )
            return True
        except Exception as e:
            print_error(f"{self.get_resource_type()} could not be deleted.")
            print_error("Please try again or delete resources manually.")
            print_error(e)
        return False

    def get_arn(self, aws_client: AwsApiClient) -> Optional[str]:
        lb = self._read(aws_client)
        if lb is None:
            return None
        lb_arn = lb.get("LoadBalancerArn", None)
        return lb_arn


    def _create_tg(self, aws_client: AwsApiClient) -> bool:
        """Creates the Target Group

        Args:
            aws_client: The AwsApiClient for the current Target Group
        """
        print_info(f"Creating {self.get_resource_type()}: {self.get_resource_name()}")

        # create a dict of args which are not null, otherwise aws type validation fails
        not_null_args: Dict[str, Any] = {}
        if self.protocol is not None:
            not_null_args["Protocol"] = self.protocol
        if self.protocol_version is not None:
            not_null_args["ProtocolVersion"] = self.protocol_version
        if self.port is not None:
            not_null_args["Port"] = self.port
        if self.vpc_id is not None:
            not_null_args["VpcId"] = self.vpc_id
        if self.health_check_protocol is not None:
            not_null_args["HealthCheckProtocol"] = self.health_check_protocol
        if self.health_check_port is not None:
            not_null_args["HealthCheckPort"] = self.health_check_port
        if self.health_check_enabled is not None:
            not_null_args["HealthCheckEnabled"] = self.health_check_enabled
        if self.health_check_path is not None:
            not_null_args["HealthCheckPath"] = self.health_check_path
        if self.health_check_interval_seconds is not None:
            not_null_args["HealthCheckIntervalSeconds"] = self.health_check_interval_seconds
        if self.health_check_timeout_seconds is not None:
            not_null_args["HealthCheckTimeoutSeconds"] = self.health_check_timeout_seconds
        if self.healthy_threshold_count is not None:
            not_null_args["HealthyThresholdCount"] = self.healthy_threshold_count
        if self.unhealthy_threshold_count is not None:
            not_null_args["UnhealthyThresholdCount"] = self.unhealthy_threshold_count
        if self.matcher is not None:
            not_null_args["Matcher"] = self.matcher
        if self.target_type is not None:
            not_null_args["TargetType"] = self.target_type
        if self.tags is not None:
            not_null_args["Tags"] = self.tags
        if self.ip_address_type is not None:
            not_null_args["IpAddressType"] = self.ip_address_type

        # Create TargetGroup
        service_client = self.get_service_client(aws_client)
        try:
            create_response = service_client.create_target_group(
                Name=self.name,
                **not_null_args,
            )
            logger.debug(f"Response: {create_response}")
            resource_dict = create_response.get("TargetGroup", {})

            # Validate resource creation
            if resource_dict is not None:
                print_info(f"TargetGroup created: {self.get_resource_name()}")
                self.active_resource = create_response
                return True
        except Exception as e:
            print_error(f"{self.get_resource_type()} could not be created.")
            print_error(e)
        return False

    def _read_tg(self, aws_client: AwsApiClient) -> Optional[Any]:
        """Returns the TargetGroup

        Args:
            aws_client: The AwsApiClient for the current TargetGroup
        """
        logger.debug(f"Reading {self.get_resource_type()}: {self.get_resource_name()}")

        from botocore.exceptions import ClientError

        service_client = self.get_service_client(aws_client)
        try:
            describe_response = service_client.describe_target_groups(
                Names=[self.name]
            )
            logger.debug(f"TargetGroup: {describe_response}")
            resource_list = describe_response.get("TargetGroup", None)

            if resource_list is not None and isinstance(resource_list, list):
                self.active_resource = resource_list[0]
        except ClientError as ce:
            logger.debug(f"ClientError: {ce}")
        except Exception as e:
            print_error(f"Error reading {self.get_resource_type()}.")
            print_error(e)
        return self.active_resource

    def _delete_tg(self, aws_client: AwsApiClient) -> bool:
        """Deletes the TargetGroup

        Args:
            aws_client: The AwsApiClient for the current TargetGroup
        """
        print_info(f"Deleting {self.get_resource_type()}: {self.get_resource_name()}")

        service_client = self.get_service_client(aws_client)
        self.active_resource = None

        try:
            delete_response = service_client.delete_target_group(
                TargetGroupArn=self.get_arn
            )
            logger.debug(f"TargetGroup: {delete_response}")
            print_info(
                f"{self.get_resource_type()}: {self.get_resource_name()} deleted"
            )
            return True
        except Exception as e:
            print_error(f"{self.get_resource_type()} could not be deleted.")
            print_error("Please try again or delete resources manually.")
            print_error(e)
        return False

    def _update_tg(self, aws_client: AwsApiClient) -> bool:
        """Update EcsService"""
        print_info(f"Updating {self.get_resource_type()}: {self.get_resource_name()}")

        # create a dict of args which are not null, otherwise aws type validation fails
        not_null_args: Dict[str, Any] = {}
        if self.target_group_arn is not None:
            not_null_args["TargetGroupArn"] = self.target_group_arn
        if self.protocol is not None:
            not_null_args["Protocol"] = self.protocol
        if self.health_check_protocol is not None:
            not_null_args["HealthCheckProtocol"] = self.health_check_protocol
        if self.health_check_port is not None:
            not_null_args["HealthCheckPort"] = self.health_check_port
        if self.health_check_enabled is not None:
            not_null_args["HealthCheckEnabled"] = self.health_check_enabled
        if self.health_check_path is not None:
            not_null_args["HealthCheckPath"] = self.health_check_path
        if self.health_check_interval_seconds is not None:
            not_null_args["HealthCheckIntervalSeconds"] = self.health_check_interval_seconds
        if self.health_check_timeout_seconds is not None:
            not_null_args["HealthCheckTimeoutSeconds"] = self.health_check_timeout_seconds
        if self.healthy_threshold_count is not None:
            not_null_args["HealthyThresholdCount"] = self.healthy_threshold_count
        if self.unhealthy_threshold_count is not None:
            not_null_args["UnhealthyThresholdCount"] = self.unhealthy_threshold_count
        if self.matcher is not None:
            not_null_args["Matcher"] = self.matcher

        service_client = self.get_service_client(aws_client)
        try:
            create_response = service_client.modify_target_group(
                Name=self.name,
                **not_null_args,
            )
            logger.debug(f"Response: {create_response}")
            resource_dict = create_response.get("LoadBalancers", {})

            # Validate resource creation
            if resource_dict is not None:
                print_info(f"LoadBalancer created: {self.get_resource_name()}")
                self.active_resource = create_response
                return True
        except Exception as e:
            print_error(f"{self.get_resource_type()} could not be created.")
            print_error(e)
        return False
