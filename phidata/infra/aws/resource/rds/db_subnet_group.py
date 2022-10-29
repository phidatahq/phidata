from typing import Optional, Any, Dict, List

from phidata.infra.aws.api_client import AwsApiClient
from phidata.infra.aws.resource.base import AwsResource
from phidata.infra.aws.resource.cloudformation.stack import CloudFormationStack
from phidata.utils.cli_console import print_info, print_error
from phidata.utils.log import logger


class DbSubnetGroup(AwsResource):
    """
    # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/rds.html#RDS.Client.create_db_subnet_group

    Creates a new DB subnet group. DB subnet groups must contain at least one subnet in at least
    two AZs in the Amazon Web Services Region.
    """

    resource_type = "DbSubnetGroup"
    service_name = "rds"

    # The name for the DB subnet group. This value is stored as a lowercase string.
    # Constraints:
    #   Must contain no more than 255 letters, numbers, periods, underscores, spaces, or hyphens.
    #   Must not be default.
    #   First character must be a letter.
    #   Example: mydbsubnetgroup
    name: str
    # The description for the DB subnet group.
    description: str
    # The EC2 Subnet IDs for the DB subnet group.
    subnet_ids: Optional[List[str]] = None
    # Get Subnet IDs from a VPC CloudFormationStack
    # NOTE: only gets privatesubnets from the vpc stack
    vpc_stack: Optional[CloudFormationStack] = None
    # Tags to assign to the DB subnet group.
    tags: Optional[List[Dict[str, str]]] = None

    def _create(self, aws_client: AwsApiClient) -> bool:
        """Creates the DbSubnetGroup

        Args:
            aws_client: The AwsApiClient for the current cluster
        """

        print_info(f"Creating {self.get_resource_type()}: {self.get_resource_name()}")
        try:
            # create a dict of args which are not null, otherwise aws type validation fails
            not_null_args: Dict[str, Any] = {}

            if self.tags:
                not_null_args["Tags"] = self.tags

            subnet_ids = self.subnet_ids
            if subnet_ids is None and self.vpc_stack is not None:
                logger.debug("Getting private subnet_ids from vpc stack")
                subnet_ids = self.vpc_stack.get_private_subnets(aws_client=aws_client)

            # Create DbSubnetGroup
            service_client = self.get_service_client(aws_client)
            create_response = service_client.create_db_subnet_group(
                DBSubnetGroupName=self.name,
                DBSubnetGroupDescription=self.description,
                SubnetIds=subnet_ids,
                **not_null_args,
            )
            logger.debug(f"create_response type: {type(create_response)}")
            logger.debug(f"create_response: {create_response}")

            self.active_resource = create_response.get("DBSubnetGroup", None)
            if self.active_resource is not None:
                print_info(
                    f"{self.get_resource_type()}: {self.get_resource_name()} created"
                )
                logger.debug(f"DbSubnetGroup: {self.active_resource}")
                return True
        except Exception as e:
            print_error(f"{self.get_resource_type()} could not be created.")
            print_error(e)
        return False

    def _read(self, aws_client: AwsApiClient) -> Optional[Any]:
        """Returns the DbSubnetGroup

        Args:
            aws_client: The AwsApiClient for the current cluster
        """
        from botocore.exceptions import ClientError

        logger.debug(f"Reading {self.get_resource_type()}: {self.get_resource_name()}")
        try:
            service_client = self.get_service_client(aws_client)
            describe_response = service_client.describe_db_subnet_groups(
                DBSubnetGroupName=self.name
            )
            logger.debug(f"describe_response type: {type(describe_response)}")
            logger.debug(f"describe_response: {describe_response}")

            db_subnet_group_list = describe_response.get("DBSubnetGroups", None)
            if db_subnet_group_list is not None and isinstance(
                db_subnet_group_list, list
            ):
                for _db_subnet_group in db_subnet_group_list:
                    _db_sg_name = _db_subnet_group.get("DBSubnetGroupName", None)
                    if _db_sg_name == self.name:
                        self.active_resource = _db_subnet_group
                        break

            if self.active_resource is None:
                logger.debug(f"No {self.get_resource_type()} found")
                return None

            logger.debug(f"DbSubnetGroup: {self.active_resource}")
        except ClientError as ce:
            logger.debug(f"ClientError: {ce}")
        except Exception as e:
            print_error(f"Error reading {self.get_resource_type()}.")
            print_error(e)
        return self.active_resource

    def _delete(self, aws_client: AwsApiClient) -> bool:
        """Deletes the DbSubnetGroup

        Args:
            aws_client: The AwsApiClient for the current cluster
        """

        print_info(f"Deleting {self.get_resource_type()}: {self.get_resource_name()}")
        try:
            service_client = self.get_service_client(aws_client)
            self.active_resource = None

            delete_response = service_client.delete_db_subnet_group(
                DBSubnetGroupName=self.name
            )
            logger.debug(f"delete_response: {delete_response}")
            print_info(
                f"{self.get_resource_type()}: {self.get_resource_name()} deleted"
            )
            return True
        except Exception as e:
            print_error(f"{self.get_resource_type()} could not be deleted.")
            print_error("Please try again or delete resources manually.")
            print_error(e)
        return False
