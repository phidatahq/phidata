from typing import Optional, Any, Dict

from phidata.aws.api_client import AwsApiClient
from phidata.aws.resource.base import AwsResource
from phidata.utils.cli_console import print_info, print_error, print_warning
from phidata.utils.log import logger


class SecurityGroup(AwsResource):
    """
    https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2/securitygroup/index.html
    https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2/client/create_security_group.html
    """

    resource_type = "SecurityGroup"
    service_name = "ec2"

    # Security Group id
    id: str

    description: Optional[str] = None
    group_name: Optional[str] = None
    vpc_id: Optional[str] = None
    tag_specifications: Optional[list] = None
    dry_run: Optional[bool] = None

    ip_permissions: Optional[list] = None
    cidr_ip: Optional[str] = None
    from_port: Optional[int] = None
    to_port: Optional[int] = None
    ip_protocol: Optional[str] = None
    source_security_group_name: Optional[str] = None
    source_security_group_owner_id: Optional[str] = None

    def get_resource_name(self) -> Optional[str]:
        return self.id

    def get_vpc_id(self, aws_client: Optional[AwsApiClient] = None) -> Optional[str]:
        # logger.debug(f"Reading {self.get_resource_type()}: {self.get_resource_name()}")

        from botocore.exceptions import ClientError

        client: AwsApiClient = aws_client or self.get_aws_client()
        service_resource = self.get_service_resource(client)
        try:
            subnet = service_resource.Subnet(self.id)
            vpc_id = subnet.vpc_id
            logger.debug(f"VPC ID for {self.id}: {vpc_id}")
            return vpc_id
        except ClientError as ce:
            logger.debug(f"ClientError: {ce}")
        except Exception as e:
            print_error(f"Error reading {self.get_resource_type()}: {e}")
        return None

    def _create(self, aws_client: AwsApiClient) -> bool:
        """Creates the SecurityGroup

        Args:
            aws_client: The AwsApiClient for the current Security group
        """
        print_info(f"Creating {self.get_resource_type()}: {self.get_resource_name()}")

        # Step 1: Build Security group configuration
        # Add name as a tag because Security groups do not have names

        # create a dict of args which are not null, otherwise aws type validation fails
        not_null_args: Dict[str, Any] = {}
        if self.encrypted:
            not_null_args["Encrypted"] = self.encrypted
        if self.description:
            not_null_args["Description"] = self.description
        if self.group_name:
            not_null_args["GroupName"] = self.group_name
        if self.vpc_id:
            not_null_args["VpcId"] = self.vpc_id
        if self.tag_specifications:
            not_null_args["TagSpecifications"] = self.tag_specifications
        if self.dry_run:
            not_null_args["DryRun"] = self.dry_run


        # Step 2: Create Security group
        service_resource = self.get_service_resource(aws_client)
        try:
            created_resource = service_resource.create_security_group(
                **not_null_args,
            )
            logger.debug(f"SecurityGroup: {created_resource}")

            # Validate Security group creation
            self.group_id = created_resource.group_id
            if self.group_id is not None:
                print_info(f"SecurityGroup created: {self.name}")
                self.active_resource = created_resource
                return True
        except Exception as e:
            print_error(f"{self.get_resource_type()} could not be created.")
            print_error(e)
        return False

    def _read(self, aws_client: AwsApiClient) -> Optional[Any]:
        """Read SecurityGroup"""
        from botocore.exceptions import ClientError

        logger.debug(f"Reading {self.get_resource_type()}: {self.get_resource_name()}")
        service_client = self.get_service_client(aws_client)
        try:
            describe_response = service_client.describe_security_groups(
            )
            logger.debug(f"SecurityGroup: {describe_response}")
            resource = describe_response.get("SecurityGroup", None)
            if resource is not None:
                # compare the task definition with the current state
                # if there is a difference, create a new task definition
                # TODO: fix the task_definition_up_to_date function
                # if self.task_definition_up_to_date(task_definition=resource):
                self.active_resource = resource
        except ClientError as ce:
            logger.debug(f"ClientError: {ce}")
        except Exception as e:
            print_error(f"Error reading {self.get_resource_type()}.")
            print_error(e)
        return self.active_resource

    def _delete(self, aws_client: AwsApiClient) -> bool:
        """Deletes the SecurityGroup

        Args:
            aws_client: The AwsApiClient for the current security_group
        """
        print_info(f"Deleting {self.get_resource_type()}: {self.get_resource_name()}")

        self.active_resource = None
        try:
            security_group = self._read(aws_client)
            logger.debug(f"SecurityGroup: {security_group}")
            if security_group is None:
                logger.warning(f"No {self.get_resource_type()} to delete")
                return True

            # delete security_group
            security_group.delete()
            print_info(f"SecurityGroup deleted: {self.name}")
            return True
        except Exception as e:
            print_error(f"{self.get_resource_type()} could not be deleted.")
            print_error("Please try again or delete resources manually.")
            print_error(e)
        return False

    def authorize_egress(self, aws_client: AwsApiClient) -> bool:

        # create a dict of args which are not null, otherwise aws type validation fails
        not_null_args: Dict[str, Any] = {}
        if self.dry_run:
            not_null_args["DryRun"] = self.dry_run
        if self.ip_permissions:
            not_null_args["IpPermissions"] = self.ip_permissions
        if self.tag_specifications:
            not_null_args["TagSpecifications"] = self.tag_specifications
        if self.cidr_ip:
            not_null_args["CidrIp"] = self.cidr_ip
        if self.from_port:
            not_null_args["FromPort"] = self.from_port
        if self.to_port:
            not_null_args["ToPort"] = self.to_port
        if self.ip_protocol:
            not_null_args["IpProtocol"] = self.ip_protocol
        if self.source_security_group_name:
            not_null_args["SourceSecurityGroupName"] = self.source_security_group_name
        if self.source_security_group_owner_id:
            not_null_args["SourceSecurityGroupOwnerId"] = self.source_security_group_owner_id

        service_resource = self.get_service_resource(aws_client)
        try:
            created_resource = service_resource.authorize_egress(
                **not_null_args,
            )
            logger.debug(f"SecurityGroup: {created_resource}")

            # Validate AuthorizeEgress
            if created_resource.Return:
                print_info(f"SecurityGroup created: {self.name}")
                self.active_resource = created_resource
                return True
        except Exception as e:
            print_error(f"{self.get_resource_type()} could not be created.")
            print_error(e)
        return False

    def authorize_ingress(self, aws_client: AwsApiClient) -> bool:

        # create a dict of args which are not null, otherwise aws type validation fails
        not_null_args: Dict[str, Any] = {}
        if self.cidr_ip:
            not_null_args["CidrIp"] = self.cidr_ip
        if self.from_port:
            not_null_args["FromPort"] = self.from_port
        if self.group_name:
            not_null_args["GroupName"] = self.group_name
        if self.ip_permissions:
            not_null_args["IpPermissions"] = self.ip_permissions
        if self.ip_protocol:
            not_null_args["IpProtocol"] = self.ip_protocol
        if self.source_security_group_name:
            not_null_args["SourceSecurityGroupName"] = self.source_security_group_name
        if self.source_security_group_owner_id:
            not_null_args["SourceSecurityGroupOwnerId"] = self.source_security_group_owner_id
        if self.to_port:
            not_null_args["ToPort"] = self.to_port
        if self.dry_run:
            not_null_args["DryRun"] = self.dry_run
        if self.tag_specifications:
            not_null_args["TagSpecifications"] = self.tag_specifications

        service_resource = self.get_service_resource(aws_client)
        try:
            created_resource = service_resource.authorize_ingress(
                **not_null_args,
            )
            logger.debug(f"SecurityGroup: {created_resource}")

            # Validate AuthorizeIngress
            if created_resource.Return:
                print_info(f"SecurityGroup created: {self.name}")
                self.active_resource = created_resource
                return True
        except Exception as e:
            print_error(f"{self.get_resource_type()} could not be created.")
            print_error(e)
        return False
